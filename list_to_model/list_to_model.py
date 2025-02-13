from collections import defaultdict
from typing import List
from pydantic import BaseModel


class MockCellParser:
    def parse(self, value):
        return value


class ParserModel(BaseModel):

    def header_name_to_field_name(header):
        # Given a human-friendly column header name, map it to the
        # string defining which field(s) in the model the cell
        # value corresponds to.
        # This is necessary as we might want
        # to use some string representations as fields which are
        # reserved words in python.
        return header

    def header_name_to_field_name_with_context(header, row):
        # This is used for models representing a full sheet row.
        return header


def is_list_type(model):
    # Determine whether model is a list type,
    # such as list, List, List[str], ...
    # issubclass only works for Python <=3.6
    # model.__dict__.get('__origin__') returns different things in different Python version.
    # This function tries to accommodate both 3.6 and 3.8 (at least)
    return model == list or model == List or model.__dict__.get('__origin__') in [list, List]


def is_parser_model_type(model):
    # Determine whether model is a subclass of ParserModel.
    try:
        return issubclass(model, ParserModel)
    except TypeError:
        # This occurs in Python >= 3.7 if one argument is a nested type, e.g. List[str]
        return False


def is_basic_type(model):
    return model in [str, int, float, bool]


class RowParser:
    # Takes a dictionary of cell entries, whose keys are the column names
    # and the values are the cell content converted into nested lists.
    # Turns this into an instance of the provided model.

    def __init__(self, model, cell_parser):
        self.model = model
        self.output = None  # Gets reinitialized with each call to parse_row
        self.cell_parser = cell_parser

    def try_assign_as_kwarg(self, field, key, value, model):
        # If value can be interpreted as a (field, field_value) pair for a field of model,
        # assign value to field[key] (which represents the field in the model)
        if type(value) == list and len(value) == 2 and type(value[0]) == str:
            first_entry_as_key = model.header_name_to_field_name(value[0])
            if first_entry_as_key in model.__fields__:
                self.assign_value(field[key], first_entry_as_key, value[1], model.__fields__[first_entry_as_key].outer_type_)
                return True
        return False


    def assign_value(self, field, key, value, model):
        # Given a field in the output and a key, assign
        # value (which can be a nested structure) to field[key].
        # This is done recursively, and
        # converts some lists into dicts in the process,
        # as appropriate and as determined by model,
        # which is the model/type of field[key]).
        # Note: field can also be a list and key an index.

        # Using both key and field here because if we passed field[key],
        # we can't do call by reference with basic types.
        if is_parser_model_type(model):
            # The value should be a dict/object
            field[key] = {}
            # Get the list of keys that are available for the target model
            # Note: The fields have a well defined ordering.
            # See https://pydantic-docs.helpmanual.io/usage/models/#field-ordering
            model_fields = list(model.__fields__.keys())

            if type(value) != list:
                # It could be that an object is specified via a single element.
                value = [value]
            if self.try_assign_as_kwarg(field, key, value, model):
                # Check if value could encode a single KWArg; if yes, assign as such.
                # Note: We're resolving an ambiguity here in favor of kwargs.
                # in principle, this could also be two positional arguments.
                return

            for i, entry in enumerate(value):
                # Go through the list of arguments
                kwarg_found = False
                if self.try_assign_as_kwarg(field, key, entry, model):
                    # This looks like a KWArg
                    # Note: We're resolving an ambiguity here in favor of kwargs.
                    # in principle, this could also be a positional argument that is a list.
                    kwarg_found = True
                else:
                    # This isn't a KWarg, so we interpret is as a positional argument
                    # KWArgs should come after positional arguments --> assert
                    assert not kwarg_found
                    entry_key = model_fields[i]
                    self.assign_value(field[key], entry_key, entry, model.__fields__[entry_key].outer_type_)

        elif is_list_type(model):
            # Get the type that's inside the list
            assert len(model.__args__) == 1
            child_model = model.__args__[0]
            # The created entry should be a list. Value should also be a list
            field[key] = []
            # Note: This makes a decision on how to resolve an ambiguity when the target field is a list of lists,
            # but the cell value is a 1-dimensional list. 1;2 → [[1],[2]] rather than [[1,2]]
            if type(value) != list:
                # It could be that a list is specified via a single element.
                value = [value]
            for entry in value:
                # For each entry, create a new list entry and assign its value recursively
                field[key].append(None)
                self.assign_value(field[key], -1, entry, child_model)

        else:
            assert is_basic_type(model)
            # The value should be a basic type
            # TODO: Ensure the types match. E.g. we don't want value to be a list
            field[key] = model(value)

    def find_entry(self, model, output_field, field_path):
        # Within the output_field (which may be a nested structure),
        # traverse the field_path to find the subfield to assign the value to.
        # Return that field (via a parent object and a key, so that we can
        # overwrite its value) and its model.

        # Note: model is the model/type that the output_field should correspond to
        # (though objects are modeled as dicts in the output). It helps us
        # traverse the path in output_field and if necessary create non-existent
        # entries.

        # We're creating the output object's fields as we're going through it.
        # It'd be nicer to already have a template.
        field_name = field_path[0]
        if is_list_type(model):
            # Get the type that's inside the list
            assert len(model.__args__) == 1
            child_model = model.__args__[0]

            index = int(field_name) - 1
            if len(output_field) <= index:
                # Create a new list entry for this, if necessary
                # We assume the columns are always in order 1, 2, 3, ... for now
                assert len(output_field) == index
                # None will later be overwritten by assign_value
                output_field.append(None)

            key = index
        else:
            assert is_parser_model_type(model)
            key = model.header_name_to_field_name(field_name)
            if not key in model.__fields__:
                raise ValueError(f"Field {key} doesn't exist in target type.")
            child_model = model.__fields__[key].outer_type_
            # TODO: how does ModelField.outer_type_ and ModelField.type_
            # deal with nested lists, e.g. List[List[str]]?
            # Write test cases and fix code.

            if not key in output_field:
                # Create a new entry for this, if necessary
                # None will later be overwritten by assign_value
                output_field[key] = None

        if len(field_path) == 1:
            # We're reach the end of the field_path
            # Therefore we've found where we need to assign
            return output_field, key, child_model
        else:
            # The field has subfields, keep going and recurse.
            # If field doesn't exist yet in our output object, create it.
            if is_list_type(child_model) and output_field[key] is None:
                output_field[key] = []
            elif is_parser_model_type(child_model) and output_field[key] is None:
                output_field[key] = {}
            # recurse
            return self.find_entry(child_model, output_field[key], field_path[1:])

    def parse_entry(self, column_name, value):
        # This creates/populates a field in self.output
        # The field is determined by column_name, its value by value
        field_path = column_name.split(':')
        # Find the destination subfield in self.output that corresponds to field_path
        field, key, model = self.find_entry(self.model, self.output, field_path)
        # The destination field in self.output is field[key], its type is model.
        # Therefore the value should be assigned to field[key].
        # (Note: This is a bit awkward; if we returned field[key] itself, we could
        # not easily overwrite its value. So we return field and key separately.
        # Ideally we would return a pointer to the destination field.
        # The model of field[key] is model, and thus value should also be interpreted
        # as being of type model.
        if is_list_type(model) or is_parser_model_type(model):
            # If the expected type of the value is list/object,
            # parse the cell content as such.
            # Otherwise leave it as a string
            value = self.cell_parser.parse(value)
        self.assign_value(field, key, value, model)

    def parse_row(self, data):
        # data is a dict where the keys are column header names,
        # and the values are the corresponding values of the cells
        # in the spreadsheet (i.e. strings).
        # However, because we don't have the string parser yet,
        # the values are assumed to be parsed already, i.e. are
        # nested lists.

        # Initialize the output template as a dict
        self.output = {}

        # Apply map from header string to field specification
        data_rekeyed = {}
        for k, v in data.items():
            k = self.model.header_name_to_field_name_with_context(k, data)
            data_rekeyed[k] = v
        data = data_rekeyed

        # For each column with an asterisk (*) (indicating list of fields),
        # Compute how long the implied list is by taking the maximum
        # over the lengths of all fields that this list refers to.
        # Note: So far, no nested asterisks are supported.
        asterisk_list_lengths = defaultdict(lambda: 1)
        for k,v in data.items():
            if '*' in k and type(v) == list:
                prefix = k.split('*')[0]
                asterisk_list_lengths[prefix] = max(asterisk_list_lengths[prefix], len(v))
        # Process each entry
        for k,v in data.items():
            if '*' in k:
                # Process each prefix:*:suffix column entry by assigning the individual
                # list values to prefix:1:suffix, prefix:2:suffix, etc
                prefix = k.split('*')[0]
                if type(v) != list:
                    v = [v]*asterisk_list_lengths[prefix]
                for i, elem in enumerate(v):
                    self.parse_entry(k.replace('*', str(i+1)), elem)
            else:
                # Normal, non-* column entry.
                self.parse_entry(k,v)
        # Returning an instance of the model rather than the output directly
        # helps us fill in default values where no entries exist.
        return self.model(**self.output)

