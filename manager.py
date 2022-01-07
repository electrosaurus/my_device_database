#!/usr/bin/env python3

from random import choices
from data_generating import *
import psycopg2
import sys
import logging
import os.path
from argparse import ArgumentParser

DATA_SOURCES_BASE_PATH = 'data_generating_sources'
TARGETS = [
    'all',
    'manufacturers',
    'device_models',
    'devices',
    'customers',
    'timeline',
    'damage_fines',
    'rent_price',
    'feedbacks',
]

arg_parser = ArgumentParser()
arg_parser.add_argument('action', choices=['fill', 'clear', 'refill'])
arg_parser.add_argument('targets', nargs='*', choices=TARGETS, default='all')
arg_parser.add_argument('--size', type=int)
arg_parser.add_argument('--dry', action='store_true')
arg_parser.add_argument('--log-level', type=str, default='INFO')
arg_parser.add_argument('--db', type=str, default='my_device')
arg_parser.add_argument('--user', type=str, default=None)
arg_parser.add_argument('--password', type=str, default=None)
arg_parser.add_argument('--male-first-names', type=str, default=os.path.join(DATA_SOURCES_BASE_PATH, 'russian_male_first_names.csv'))
arg_parser.add_argument('--female-first-names', type=str, default=os.path.join(DATA_SOURCES_BASE_PATH, 'russian_female_first_names.csv'))
arg_parser.add_argument('--last-names', type=str, default=os.path.join(DATA_SOURCES_BASE_PATH, 'russian_last_names.csv'))
arg_parser.add_argument('--manufacturers', type=str, default=os.path.join(DATA_SOURCES_BASE_PATH, 'manufacturers.yaml'))
arg_parser.add_argument('--device-models', type=str, default=os.path.join(DATA_SOURCES_BASE_PATH, 'device_models.yaml'))
arg_parser.add_argument('--feedbacks', type=str, default=os.path.join(DATA_SOURCES_BASE_PATH, 'feedbacks.yaml'))
arg_parser.add_argument('--fine', type=int, default=3000)
arg_parser.add_argument('--customers', type=int, default=5000)
arg_parser.add_argument('--devices', type=int, default=1000)
arg_parser.add_argument('--rents', type=int, default=10000)

args = arg_parser.parse_args()
if not isinstance(args.targets, list):
    args.targets = [args.targets]
targets = frozenset(args.targets)

logging.basicConfig(level=args.log_level.upper())

connection = psycopg2.connect(database=args.db, user=args.user, password=args.password)
cursor = connection.cursor()
init_models(cursor)


def clear_model(model):
    n = model.clear(cursor)
    logging.info(f'Deleted {n} rows from {model.TABLE_NAME}')

def insert_entity(entity):
    entity.insert(cursor)
    logging.info(entity)


if args.action in ['clear', 'refill']:
    if targets & set(['manufacturers', 'all']):
        clear_model(Manufacturer)
    if targets & set(['device_models', 'all']):
        clear_model(DeviceModelProperty)
        clear_model(DeviceModelImage)
        clear_model(DeviceModel)
    if targets & set(['devices', 'all']):
        clear_model(Device)
    if targets & set(['customers', 'all']):
        clear_model(Customer)
    if targets & set(['timeline', 'all']):
        clear_model(DeviceRepair)
        clear_model(DeviceRentOwnership)
        clear_model(DeviceOwnership)
        clear_model(DeviceRent)
    if targets & set(['damage_fines', 'all']):
        clear_model(DamageFine)
    if targets & set(['rent_price', 'all']):
        clear_model(DeviceModelRentPrice)
    if targets & set(['feedbacks', 'all']):
        clear_model(Feedback)

if args.action in ['fill', 'refill']:
    if targets & set(['manufacturers', 'all']):
        manufacturer_generator = ManufacturerGenerator(args.manufacturers)
        for manufacturer in manufacturer_generator():
            manufacturer.insert(cursor)
            logging.info(manufacturer)
    if targets & set(['device_models', 'all']):
        device_model_generator = DeviceModelGenerator(args.device_models)
        for device_model, device_model_image, device_model_properties in device_model_generator(cursor):
            insert_entity(device_model)
            insert_entity(device_model_image)
            for device_model_property in device_model_properties:
                insert_entity(device_model_property)
    if targets & set(['devices', 'all']):
        device_generator = DeviceGenerator()
        for device in device_generator(cursor, args.devices):
            insert_entity(device)
    if targets & set(['customers', 'all']):
        name_generator = NameGenerator(args.male_first_names, args.female_first_names, args.last_names)
        customer_generator = CustomerGenerator(name_generator)
        for customer in customer_generator(args.customers):
            insert_entity(customer)
    if targets & set(['timeline', 'all']):
        timeline_generator = TimelineGenerator()
        for x in timeline_generator(cursor, args.rents):
            device_rents, device_ownerships, device_rent_ownerships, device_repairs = x
            for device_rent in device_rents:
                insert_entity(device_rent)
            for device_ownership in device_ownerships:
                insert_entity(device_ownership)
            for device_rent_ownership in device_rent_ownerships:
                insert_entity(device_rent_ownership)
            for device_repair in device_repairs:
                insert_entity(device_repair)
    if targets & set(['damage_fines', 'all']):
        damage_fine_generator = DamageFineGenerator(args.fine)
        for damage_fine in damage_fine_generator(cursor):
            insert_entity(damage_fine)
    if targets & set(['rent_price', 'all']):
        rent_price_generator = DeviceModelRentPriceGenerator(args.device_models)
        for rent_price in rent_price_generator(cursor):
            insert_entity(rent_price)
    if targets & set(['feedbacks', 'all']):
        feedback_generator = FeedbackGenerator(args.feedbacks)
        for feedback in feedback_generator(cursor):
            insert_entity(feedback)

if not args.dry:
    connection.commit()
