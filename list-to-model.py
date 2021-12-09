from typing import List
from pydantic import BaseModel


class Condition(BaseModel):
    value: str = ''
    var: str = ''
    type: str = ''
    name: str = ''
    # TODO: We could specify proper default values here, and write custom
    # validators that replace '' with the actual default value.


class From(BaseModel):
    row_id: str
    conditions: List[Condition]


output_instance = {
    'row_id': '5',
    'conditions': [
        {'value':'1', 'var':'', 'type':'has_phrase', 'name':'A'},
        {'value':'2', 'var':'', 'type':'has_phrase', 'name':'B'},
        {'value':'3', 'var':'', 'type':'has_phrase', 'name':''},
    ]
}

input1 = {
    'row_id': '5',
    'conditions:*:value' : ['1', '2', '3'],
    'conditions:*:var' : '',
    'conditions:*:type' : ['has_phrase', 'has_phrase', 'has_phrase'],
    'conditions:*:name' : ['A','B',''],
}

input2 = {
    'row_id': '5',
    'conditions:*:value' : ['1', '2', '3'],
    'conditions:*:var' : '',
    'conditions:*:type' : ['has_phrase', 'has_phrase', 'has_phrase'],
    'conditions:*:name' : ['A','B'],
}

input3 = {
    'row_id': '5',
    'conditions:*:value' : ['1', '2', '3'],
    'conditions:*:var' : '',
    'conditions:*:type' : 'has_phrase',
    'conditions:*:name' : ['A','B',''],
}

input4 = {
    'row_id': '5',
    'conditions:1' : ['1', '', 'has_phrase', 'A'],
    'conditions:2' : ['2', '', 'has_phrase', 'B'],
    'conditions:3' : ['3', '', 'has_phrase', ''],
}

input5 = {
    'row_id': '5',
    'conditions:1' : ['1', '', 'has_phrase', 'A'],
    'conditions:2' : ['2', '', 'has_phrase', 'B'],
    'conditions:3' : ['3', '', 'has_phrase'],
}

input6 = {
    'row_id': '5',
    'conditions:1' : [['value', '1'], ['type', 'has_phrase'], ['name', 'A']],
    'conditions:2' : [['value', '2'], ['type', 'has_phrase'], ['name', 'B']],
    'conditions:3' : [['value', '3'], ['type', 'has_phrase']],
}

input7 = {
    'row_id': '5',
    'conditions:1' : ['1', '', 'has_phrase', ['name', 'A']],
    'conditions:2' : ['2', '', ['type', 'has_phrase'], ['name', 'B']],
    'conditions:3' : ['3', ['type', 'has_phrase']],
}

input8 = {
    'row_id': '5',
    'conditions' : [['1', '', 'has_phrase', 'A'], ['2', '', 'has_phrase', 'B'], ['3', '', 'has_phrase', '']],
}

input9 = {
    'row_id': '5',
    'conditions:1:value' : '1',
    'conditions:1:type' : 'has_phrase',
    'conditions:1:name' : 'A',
    'conditions:2:value' : '2',
    'conditions:2:type' : 'has_phrase',
    'conditions:2:name' : 'B',
    'conditions:3:value' : '3',
    'conditions:3:type' : 'has_phrase',
}


class RowParser:
    # Takes a dictionary of cell entries, whose keys are the column names
    # and the values are the cell content converted into nested lists.
    # Turns this into an instance of the provided model.

    def __init__(self, model):
        self.model = model
        self.output = None  # Gets reinitialized with each call to parse_row

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
        if issubclass(model, BaseModel):
            # The value should be a dict/object
            field[key] = {}
            # Get the list of keys that are available for the target model
            # Note: The fields have a well defined ordering.
            # See https://pydantic-docs.helpmanual.io/usage/models/#field-ordering
            model_fields = list(model.__fields__.keys())

            if type(value) != list:
                # It could be that an object is specified via a single element.
                value = [value]
            elif len(value) == 2 and value[0] in model_fields:
                # Or via a single KWArg
                # Note: We're resolving an ambiguity here in favor of kwargs.
                # in principle, this could also be two positional arguments.
                self.assign_value(field[key], value[0], value[1], model.__fields__[value[0]].outer_type_)
                return

            for i, entry in enumerate(value):
                # Go through the list of arguments
                kwarg_found = False
                if type(entry) == list and len(entry) == 2 and entry[0] in model_fields:
                    # This looks like a KWArg
                    # Note: We're resolving an ambiguity here in favor of kwargs.
                    # in principle, this could also be a positional argument that is a list.
                    self.assign_value(field[key], entry[0], entry[1], model.__fields__[entry[0]].outer_type_)
                    kwarg_found = True
                else:
                    # This looks like a positional argument
                    # KWArgs should come after positional arguments --> assert
                    assert not kwarg_found
                    entry_key = model_fields[i]
                    self.assign_value(field[key], entry_key, entry, model.__fields__[entry_key].outer_type_)

        elif issubclass(model, List):
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
            # The value should be a basic type
            # TODO: Ensure the types match. E.g. we don't want value to be a list
            field[key] = model(value)

    def find_entry_and_assign(self, model, output_field, field_path, value):
        # Without the output_field (which may be a nested structure),
        # traverse the field_path to find the subfield to assign the value to.
        # Then assign the value.
        # The recursion here is used to find the model and the entry
        # in the output where value should be assigned.
        # We then call assign_value to do the actual assignment.

        # Note: model is the model/type that the output_field should correspond to
        # (though objects are modeled as dicts in the output). It helps us
        # traverse the path in output_field and if necessary create non-existent
        # entries.

        # We're creating the output object's fields as we're going through it.
        # It'd be nicer to already have a template.
        field = field_path[0]
        if issubclass(model, List):
            # Get the type that's inside the list
            assert len(model.__args__) == 1
            child_model = model.__args__[0]

            index = int(field) - 1
            if len(output_field) <= index:
                # Create a new list entry for this, if necessary
                # We assume the columns are always in order 1, 2, 3, ... for now
                assert len(output_field) == index
                # None will later be overwritten by assign_value
                output_field.append(None)

            key = index
        else:
            if not field in model.__fields__:
                raise ValueError(f"Field {field} doesn't exist in target type.")
            key = field
            child_model = model.__fields__[field].outer_type_
            # TODO: how does ModelField.outer_type_ and ModelField.type_
            # deal with nested lists, e.g. List[List[str]]?
            # Write test cases and fix code.

            if not key in output_field:
                # Create a new entry for this, if necessary
                # None will later be overwritten by assign_value
                output_field[key] = None

        if len(field_path) == 1:
            # We're reach the end of the field_path --> assign
            self.assign_value(output_field, key, value, child_model)
        else:
            # The field has subfields, keep going and recurse.
            # If field doesn't exist yet in our output object, create it.
            if issubclass(child_model, List) and output_field[key] is None:
                output_field[key] = []
            elif issubclass(child_model, BaseModel) and output_field[key] is None:
                output_field[key] = {}
            # recurse
            self.find_entry_and_assign(child_model, output_field[key], field_path[1:], value)

    def parse_entry(self, column_name, value):
        # This creates/populates a field in self.output
        # The field is determined by column_name, its value by value
        field_path = column_name.split(':')
        self.find_entry_and_assign(self.model, self.output, field_path, value)

    def parse_row(self, data):
        # Initialize the output template as a dict
        self.output = dict()
        for k,v in data.items():
            self.parse_entry(k,v)   
        # Returning an instance of the model rather than the output directly
        # helps us fill in default values where no entries exist.
        return self.model(**self.output)


# The list syntax from the first 3 inputs is not supported yet.
inputs = [input4, input5, input6, input7, input8, input9]
outputs = []
p = RowParser(From)

for inp in inputs:
    out = p.parse_row(inp)  # We get an instance of the model
    outputs.append(out)
    # Note: we can also serialize via out.json(indent=4) for printing
    # or out.dict()

for out in outputs:
    assert out.dict() == output_instance
