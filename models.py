from model import Model
from decimal import *


class Customer(Model):
    TABLE_NAME = 'customer'


class Manufacturer(Model):
    TABLE_NAME = 'manufacturer'


class DeviceModelProperty(Model):
    TABLE_NAME = 'device_model_property'

    def __init__(self, device_model=None, **kwargs):
        self.device_model = device_model
        super().__init__(**kwargs)

    def _prepare_for_insert(self, cursor):
        if self.device_model is not None:
            self.device_model_id = self.device_model.id


class DeviceModelImage(Model):
    TABLE_NAME = 'device_model_image'

    def __init__(self, device_model=None, **kwargs):
        self.device_model = device_model
        super().__init__(**kwargs)

    def _prepare_for_insert(self, cursor):
        if self.device_model is not None:
            self.device_model_id = self.device_model.id


class DeviceModel(Model):
    TABLE_NAME = 'device_model'


class Device(Model):
    TABLE_NAME = 'device'


class DeviceOwnership(Model):
    TABLE_NAME = 'device_ownership'


class DeviceRent(Model):
    TABLE_NAME = 'device_rent'

    def __init__(self, previous_device_rent=None, **kwargs):
        self.previous_device_rent = previous_device_rent
        super().__init__(**kwargs)

    def _prepare_for_insert(self, cursor):
        if self.previous_device_rent is not None:
            self.previous_device_rent_id = self.previous_device_rent.id


class DeviceRentOwnership(Model):
    TABLE_NAME = 'device_rent_ownership'

    def __init__(self, device_rent=None, device_ownership=None, **kwargs):
        self.device_rent = device_rent
        self.device_ownership = device_ownership
        super().__init__(**kwargs)

    def _prepare_for_insert(self, cursor):
        if self.device_rent is not None:
            self.device_rent_id = self.device_rent.id
        if self.device_ownership is not None:
            self.device_ownership_id = self.device_ownership.id


def _parse_money(money):
    return Decimal(money[1:].replace(',', ''))

class DeviceRepair(Model):
    TABLE_NAME = 'device_repair'

    def __init__(self, device_ownership=None, **kwargs):
        self.device_ownership = device_ownership
        if isinstance(kwargs.get('price', None), str) and kwargs['price'].startswith('$'):
            kwargs['price'] = _parse_money(kwargs['price'])
        super().__init__(**kwargs)

    def _prepare_for_insert(self, cursor):
        if self.device_ownership is not None:
            self.device_ownership_id = self.device_ownership.id
            self.device_id = self.device_ownership.device_id


class DamageFine(Model):
    TABLE_NAME = 'damage_fine'

    def __init__(self, **kwargs):
        if isinstance(kwargs.get('fine', None), str) and kwargs['fine'].startswith('$'):
            kwargs['fine'] = _parse_money(kwargs['fine'])
        super().__init__(**kwargs)


class DeviceModelRentPrice(Model):
    TABLE_NAME = 'device_model_rent_price'


class Feedback(Model):
    TABLE_NAME = 'feedback'


MODELS = [
    Customer,
    Manufacturer,
    DeviceModelProperty,
    DeviceModelImage,
    DeviceModel,
    Device,
    DeviceRent,
    DeviceOwnership,
    DeviceRentOwnership,
    DeviceRepair,
    DamageFine,
    DeviceModelRentPrice,
    Feedback,
]

def init_models(cursor):
    for model in MODELS:
        model.init_fields(cursor)
