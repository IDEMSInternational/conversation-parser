import csv
import json
from rapidpro.models import RapidProNode, RapidProAction
import uuid

other_case_flow = "PLH - No content"
infile = "inputs/example_dispatcher.csv"

with open(infile) as csv_file:
    csv_reader = csv.reader(csv_file)
    data = list(csv_reader)
    header, data = data[0], data[1:]

# Parse header
n_levels = 0
parsed_header = []
for field in header[1:]:
    if field != 'Flow':
        n_levels += 1
        var, check = field.split(':')
        parsed_header.append({'var': '@'+var, 'check': check})

# Compile cases into a nested dictionary
cases = dict()
for row in data:
    subdict = cases
    for level in range(n_levels-1):
        comparison_value = row[level+1]
        if not comparison_value in subdict:
            subdict[comparison_value] = dict()
        subdict = subdict[comparison_value]
    subdict[row[n_levels]] = row[n_levels+1]
subdict = cases

# Add 'Other' in the dicts wherever it doesn't already exist
def add_other(subdict):
    if "" not in subdict:
        subdict[""] = other_case_flow
    for k,v in subdict.items():
        if type(v) == dict:
            add_other(v)
add_other(cases)
print(json.dumps(cases, indent=4))

# Create the nodes in the flow
all_nodes = []

def cases_to_nodes(entry, depth=0):
    if type(entry) == dict:
        default_case = entry.pop("")
        if len(entry) == 0:
            # Other is the only choice -> don't make router node
            root = cases_to_nodes(default_case, depth+1)
        else:
            root = RapidProNode()
            all_nodes.append(root)
            default_root = cases_to_nodes(default_case, depth+1)
            root.add_default_choice(default_root)
            for k,v in entry.items():
                child_root = cases_to_nodes(v, depth+1)
                root.add_choice(child_root, parsed_header[depth]['var'], parsed_header[depth]['check'], [k])
        return root
    else:
        enter_flow_node = RapidProNode()
        all_nodes.append(enter_flow_node)
        # Temp placeholder until Actions are implemented properly
        a = RapidProAction()
        a.text = entry
        a.type = 'send_msg' # This should be enter_flow
        enter_flow_node.add_action(a)
        return enter_flow_node

cases_to_nodes(cases)

export = {
    'flows': [{
        'name': 'Dispatcher - Test',
        'uuid': str(uuid.uuid4()),
        'spec_version': '13.1.0',
        'language': 'base',
        'type': 'messaging',
        'nodes': [node.render() for node in all_nodes],
        'revision': 0,
        'expire_after_minutes': 60,
        'metadata': {'revision': 0},
        'localization': {}
    }],
    'campaigns': [],
    'triggers': [],
    'fields': [],
    'groups': [],
    'version': '13',
    'site': 'https://rapidpro.idems.international',
}
json.dump(export, open("out.json", 'w'), indent=4)