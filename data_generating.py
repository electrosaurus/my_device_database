import logging
import random
from hashlib import md5
from datetime import datetime, timedelta
import csv
import re
import numpy as np
from numpy.random.mtrand import rand
from models import *
from decimal import *
import yaml
import scipy.stats as stats
from distributions import *
from dateutil.relativedelta import relativedelta
from itertools import product


default_datetime_distr = DateTimeDistribution(datetime(2016, 3, 5))

CITIES = [
    'Москва', 'Санкт-Петербург', 'Казань', 'Краснодар', 'Нижний Новгород',
]

class NameGenerator:
    _LAST_NAME_FEMINIZATION_PATTERNS = [
        (re.compile(r'(ов)$'), 'ова'),
        (re.compile(r'(ев)$'), 'ева'),
        (re.compile(r'(ёв)$'), 'ёва'),
        (re.compile(r'(ин)$'), 'ина'),
        (re.compile(r'(ий)$'), 'ая'),
    ]

    @staticmethod
    def _feminize_last_name(last_name):
        for ending_re, ending_replacement in NameGenerator._LAST_NAME_FEMINIZATION_PATTERNS:
            last_name = ending_re.sub(ending_replacement, last_name)
        return last_name

    def __init__(self, male_first_names_filename, female_first_names_filename, last_names_filename):
        self.first_names = {'m': [], 'f': []}
        self.first_name_weights = {'m': [], 'f': []}
        self.last_names = []
        self.last_name_weights = []
        for first_names_filename, sex in [
            (male_first_names_filename, 'm'),
            (female_first_names_filename, 'f')
        ]:
            with open(first_names_filename, 'r') as first_names_file:
                first_name_reader = csv.DictReader(first_names_file, delimiter=';')
                for first_name_data in first_name_reader:
                    first_name = first_name_data['Name'].split(', ')[0]
                    weight = int(first_name_data['Frequency'])
                    self.first_names[sex].append(first_name)
                    self.first_name_weights[sex].append(weight)
        with open(last_names_filename, 'r') as last_names_file:
            last_name_reader = csv.DictReader(last_names_file, delimiter=';')
            for last_name_data in last_name_reader:
                last_name = last_name_data['LastName']
                weight = float(last_name_data['Weight'].replace(',', '.'))
                self.last_names.append(last_name)
                self.last_name_weights.append(weight)

    def __call__(self, sex, count=None):
        is_bulk = True
        if count is None:
            is_bulk = False
            count = 1
        first_names = random.choices(
            population=self.first_names[sex],
            weights=self.first_name_weights[sex],
            k=count
        )
        last_names = random.choices(
            population=self.last_names,
            weights=self.last_name_weights,
            k=count
        )
        if sex == 'f':
            last_names = map(self._feminize_last_name, last_names)
        names = zip(first_names, last_names)
        return names if is_bulk else next(names)


class PhoneGenerator:
    def __call__(self, count=None):
        is_bulk = True
        if count is None:
            is_bulk = False
            count = 1
        pool = set()
        while len(pool) < count:
            a = random.randint(100, 999)
            b = random.randint(0, 999)
            c = random.randint(0, 99)
            d = random.randint(0, 99)
            pool.add(f'+7 ({a:03d}) {b:03d}-{c:02d}-{d:02d}')
        return pool if is_bulk else next(iter(pool))


default_phone_generator = PhoneGenerator()


class CustomerGenerator:
    def __call__(self, name_generator,
            count=None,
            phone_generator=default_phone_generator,
            datetime_distr=default_datetime_distr
        ):
        is_bulk = True
        if count is None:
            is_bulk = False
            count = 1
        male_count = sum(np.random.binomial(1, 0.5, count))
        female_count = count - male_count
        male_names = list(name_generator('m', male_count))
        female_names = list(name_generator('f', female_count))
        names = male_names + female_names
        random.shuffle(names)
        phones = phone_generator(count)
        pool = (
            Customer(
                first_name=name[0],
                last_name=name[1],
                password_md5=md5(random.randbytes(10)).hexdigest(),
                phone=phone,
                registration_timestamp=datetime_distr.rvs()
            )
            for name, phone in zip(names, phones)
        )
        return pool if is_bulk else next(pool)


class ManufacturerGenerator:
    def __init__(self, data_filename):
        self.data_filename = data_filename
    
    def __call__(self):
        with open(self.data_filename, 'r') as data_file:
            for name, kwargs in yaml.safe_load(data_file).items():
                yield Manufacturer(name=name, **kwargs)


class DeviceModelGenerator:
    def __init__(self, data_filename):
        self.data_filename = data_filename
    
    def __call__(self, cursor):
        with open(self.data_filename, 'r') as data_file:
            for kwargs in yaml.safe_load(data_file):
                manufacturer = next(Manufacturer.select(cursor, {'name': kwargs['manufacturer_name']}))
                device_model = DeviceModel(manufacturer_id=manufacturer.id, **kwargs)
                device_model_image = DeviceModelImage(
                    device_model=device_model,
                    image_url=kwargs['image_url']
                )
                device_model_properties = []
                for k, v in kwargs['properties'].items():
                    device_model_properties.append(DeviceModelProperty(
                        device_model=device_model,
                        key=k,
                        value=v
                    ))
                yield device_model, device_model_image, device_model_properties


class DeviceGenerator:
    def __call__(self, cursor, count=None, datetime_distr=default_datetime_distr):
        if count is None:
            return next(self(cursor, count))
        device_models = list(DeviceModel.select(cursor))
        k = len(device_models)
        marks = [0] + sorted(np.random.randint(low=0, high=count, size=k-1)) + [count]
        model_counts = [b - a for a, b in zip(marks[:-1], marks[1:])]
        purchases = int(count / 10)
        initial_purchases = int(np.ceil(purchases / 2))
        additional_purchases = purchases - initial_purchases
        purchase_timestamps = [datetime_distr.a] * initial_purchases + \
            [datetime_distr.rvs() for _ in range(additional_purchases)]
        for device_model, count in zip(device_models, model_counts):
            for i in range(count):
                purchase_timestamp = random.choice(purchase_timestamps)
                duration = timedelta(days=np.random.normal(10, 3) * 365)
                retirement_timestamp = purchase_timestamp + duration
                if retirement_timestamp > datetime.now():
                    retirement_timestamp = None
                years = datetime.now().year - purchase_timestamp.year
                condition = max(1, 10 - int(sum(random.uniform(0.2, 2) for _ in range(years))))
                yield Device(
                    model_id=device_model.id,
                    purchase_timestamp=purchase_timestamp,
                    retirement_timestamp=retirement_timestamp,
                    condition=condition,
                )


class TimelineGenerator:
    def __call__(self, cursor,
            rent_count=None,
            datetime_distr=default_datetime_distr,
            months_count_distr=stats.geom(0.5),
            insurance_p=1/20,
            breakage_p=1/150,
            delay_distr=TimeDeltaDistribution(timedelta(days=0.5), timedelta(days=0.5)),
            repair_duration_distr=TimeDeltaDistribution(timedelta(days=10), timedelta(days=5)),
            repair_price_distr=PriceDistribution(10000, 2000),
            cities=CITIES
        ):
        if rent_count is None:
            return next(self(cursor, rent_count))
        months_counts = []
        c = 0
        while c < rent_count:
            months_count = months_count_distr.rvs()
            months_counts.append(months_count)
            c += months_count
        months_counts[-1] -= (c - rent_count)
        rent_begin_datetimes = sorted(datetime_distr.rvs() for _ in range(len(months_counts)))
        customers = list(Customer.select(cursor))
        available_devices = list(Device.select(cursor))
        device_return_datetimes = {}
        for rent_begin_datetime, months_count in zip(rent_begin_datetimes, months_counts):
            # --- Make returned devices available again ---
            for device in list(device_return_datetimes.keys()):
                return_datetime = device_return_datetimes[device]
                if return_datetime <= rent_begin_datetime:
                    available_devices.append(device)
                    del device_return_datetimes[device]

            # --- Choose a customer and a device kind ---
            is_insured = bool(stats.bernoulli.rvs(insurance_p))
            actual_customers = [c for c in customers if c.registration_timestamp < rent_begin_datetime]
            try:
                customer = random.choice(actual_customers)
            except:
                logging.error('Failed to choose a valid customer')
                continue
            rents_end_datetime = rent_begin_datetime + relativedelta(months=months_count)
            try:
                actual_devices = [
                    d for d in available_devices
                    if d.purchase_timestamp < rent_begin_datetime and
                        (d.retirement_timestamp is None or rents_end_datetime < d.retirement_timestamp)
                ]
                device_model_id = random.choice(actual_devices).model_id
            except:
                logging.error('No devices available')
                continue

            # --- Generate device rents ---
            device_rents = []
            device_rent = None
            for i in range(months_count):
                if rent_begin_datetime > datetime.now():
                    break
                rent_end_datetime = rent_begin_datetime + relativedelta(months=1)
                device_rent = DeviceRent(
                    customer_id=customer.id,
                    device_model_id=device_model_id,
                    begin_timestamp=rent_begin_datetime,
                    end_timestamp=rent_end_datetime,
                    previous_device_rent=device_rent,
                    is_insured=is_insured,
                )
                device_rents.append(device_rent)
                rent_begin_datetime = rent_end_datetime

            # --- Generate device ownerships and repairs ---
            device_ownerships = []
            device_repairs = []
            ownership_begin_datetime = device_rents[0].begin_timestamp
            ownerships_end_datetime = device_rents[-1].end_timestamp - delay_distr.rvs()
            breakages = stats.poisson(breakage_p * months_count).rvs()
            breakage_datetime_distr = DateTimeDistribution(ownership_begin_datetime, ownerships_end_datetime)
            breakage_datetimes = sorted(breakage_datetime_distr.rvs() for _ in range(breakages))
            for ownership_end_datetime in breakage_datetimes + [ownerships_end_datetime]:
                ownership_begin_datetime += delay_distr.rvs()
                if ownership_begin_datetime > ownership_end_datetime:
                    ownership_begin_datetime, ownership_end_datetime = ownership_end_datetime, ownership_begin_datetime
                try:
                    actual_devices = [
                        d for d in available_devices
                        if d.purchase_timestamp < ownership_begin_datetime and
                            (d.retirement_timestamp is None or ownership_end_datetime < d.retirement_timestamp) and
                            d.model_id == device_model_id
                    ]
                    device = random.choice(actual_devices)
                except:
                    logging.error('No device of a needed model')
                    break
                available_devices.remove(device)
                if ownership_end_datetime == ownerships_end_datetime:
                    return_status = 'period_expired'
                    device_return_datetimes[device] = ownership_end_datetime
                else:
                    return_status = 'breakage'
                    repair_begin_datetime = ownership_end_datetime + delay_distr.rvs()
                    repair_end_datetime = repair_begin_datetime + repair_duration_distr.rvs()
                    device_return_datetimes[device] = repair_end_datetime
                if ownership_end_datetime > datetime.now():
                    ownership_end_datetime = None
                device_ownership = DeviceOwnership(
                    device_id=device.id,
                    begin_timestamp=ownership_begin_datetime,
                    end_timestamp=ownership_end_datetime,
                    city=random.choice(cities),
                    return_status=return_status,
                )
                device_ownerships.append(device_ownership)
                if return_status == 'breakage' and ownership_end_datetime is not None:
                    device_repairs.append(DeviceRepair(
                        device_ownership=device_ownership,
                        begin_timestamp=repair_begin_datetime,
                        end_timestamp=repair_end_datetime,
                        price=repair_price_distr.rvs(),
                    ))
                if ownership_end_datetime is None:
                    break
                ownership_begin_datetime = ownership_end_datetime
            
            # --- Generate rent-ownership relations ---
            device_rents_ownerships = []
            for device_rent, device_ownership in product(device_rents, device_ownerships):
                device_rents_ownerships.append(DeviceRentOwnership(
                    device_rent=device_rent,
                    device_ownership=device_ownership,
                ))

            yield device_rents, device_ownerships, device_rents_ownerships, device_repairs

            
class DamageFineGenerator:
    def __call__(self, cursor, fine=3000, customer_blame_probability=0.5):
        device_repairs = list(DeviceRepair.select(cursor))
        for device_repair in device_repairs:
            if random.random() > customer_blame_probability:
                continue
            device_rent_id = next(DeviceRentOwnership.select(
                cursor, {'device_ownership_id': device_repair.device_ownership_id}, limit=1
            )).device_rent_id
            device_rent = next(DeviceRent.select(cursor, {'id': device_rent_id}, limit=1))
            if not device_rent.is_insured:
                print(device_repair.price)
                yield DamageFine(
                    device_ownership_id=device_repair.device_ownership_id,
                    fine=device_repair.price+fine,
                    device_repair_id=device_repair.id,
                )


class DeviceModelRentPriceGenerator:
    def __init__(self, data_filename):
        self.data_filename = data_filename
    
    def __call__(self, cursor,
            price_updates=stats.poisson(5, loc=5).rvs(),
            affected_devices=0.7,
            delta_price_distr=PriceDistribution(100, 30),
            datetime_distr=default_datetime_distr,
        ):
        price_change_timestamps = sorted(datetime_distr.rvs(price_updates))
        with open(self.data_filename, 'r') as data_file:
            for kwargs in yaml.safe_load(data_file):
                if random.random() > affected_devices:
                    continue
                device_model = next(DeviceModel.select(cursor, {'name': kwargs['name']}, limit=1))
                prices = [kwargs['rent_price']]
                while len(prices) < price_updates:
                    prices.insert(0, prices[0] - delta_price_distr.rvs())
                for price_change_timestamp, price in zip(price_change_timestamps, prices):
                    yield DeviceModelRentPrice(
                        device_model_id=device_model.id,
                        price=price,
                        update_timestamp=price_change_timestamp,
                    )


class FeedbackGenerator:
    def __init__(self, data_filename):
        with open(data_filename, 'r') as data_file:
            self.messages = dict(yaml.safe_load(data_file).items())

    def __call__(self, cursor,
            feedback_p=0.8,
            message_p=0.1,
            stars_distr=stats.rv_discrete(name='stars', values=([1, 2, 3, 4, 5], [0.15, 0.05, 0.10, 0.20, 0.50]))
        ):
        q = '''
            SELECT id, end_timestamp FROM (
                SELECT id, end_timestamp, (SELECT COUNT (*) FROM succeeding_device_rents(id)) AS c FROM device_rent
            ) AS t WHERE c = 0;
        '''
        logging.info('Fetching last rent periods...')
        cursor.execute(q)
        device_rents_data = cursor.fetchall()
        device_rents_data = set(random.choices(device_rents_data, k=int(len(device_rents_data) * feedback_p)))
        for device_rent_data in device_rents_data:
            device_rent_id, device_rent_end_datetime = device_rent_data
            stars = stars_distr.rvs()
            message = None
            if random.random() < message_p:
                message = random.choice(self.messages[stars])
            yield Feedback(
                device_rent_id=device_rent_id,
                stars=stars,
                message=message,
                timestamp=device_rent_end_datetime,
            )
