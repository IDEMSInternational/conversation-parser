import re

from rapidpro.utils import get_dict_from_csv, get_separators


class GenericParser:
    def __init__(self, sheet_path, column_configs):
        self.sheet_rows = get_dict_from_csv(sheet_path)
        self.column_configs = column_configs

    # TODO: Have the generic parser support type definitions for specific columns.

    def preprocess(self):
        self.merge_columns()

    def merge_columns(self):
        row = self.sheet_rows[0]
        column_names = ' '.join(row.keys())
        object_of_list_columns = re.findall('condition[_a-z0-9]*', column_names)
        list_of_objects_columns = re.findall('condition[:a-z0-9]*', column_names)

        if object_of_list_columns:
            num_objects =



            num_objects = len(row[object_of_list_columns[0].split(';')])
            objects = []
            for i in range(num_objects):
                objects.append({
                    object_of_list_columns[0]: object_of_list_columns
                })


        # Merge all columns with condition.type, condition.value, condition.comment ... format
        # Merge all columns with condition:1, condition:2, condition:3 format
        pass

    def _parse_cell_value(self, value):
        for separator in get_separators(value):
            if separator:
                pass

    def parse(self):
        for row in self.sheet_rows:
            for key in row.keys():
                print(row[key])


class RapidProParser:

    def preprocess(self):
        pass
