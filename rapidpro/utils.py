import csv
import re
import uuid
from collections import defaultdict
from enum import Enum
from pathlib import Path


class CellType(Enum):
    OBJECT = 'object'
    TEXT = 'text'


def generate_new_uuid():
    return str(uuid.uuid4())


def get_dict_from_csv(csv_file_path):
    with open(f'{Path(__file__).parents[1].absolute()}/{csv_file_path}') as csv_file:
        csv_reader = csv.DictReader(csv_file)
        return [row for row in csv_reader]


def get_cell_type_for_column_header(header):
    if re.search('^condition:(\d+)', header):
        return CellType.OBJECT

    return CellType.TEXT


def get_separators(value):
    # TODO: Discuss escape characters
    separators = ['|', ';', ':']

    found_separators = [s for s in separators if s in value]
    iterator = iter(found_separators)

    return [next(iterator, None) for _ in range(0, 3)]


def get_object_from_cell_value(value):
    separator_1, separator_2, _ = get_separators(value)
    obj = defaultdict(str)

    members = value.split(separator_1)
    for member in members:
        key, value = member.split(separator_2)
        obj[key] = value
    return obj
