import csv
import uuid
from pathlib import Path


def generate_new_uuid():
    return str(uuid.uuid4())


def get_dict_from_csv(csv_file_path):
    with open(f'{Path(__file__).parents[1].absolute()}/{csv_file_path}') as csv_file:
        csv_reader = csv.DictReader(csv_file)
        return [row for row in csv_reader]
