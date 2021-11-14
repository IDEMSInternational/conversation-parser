import uuid
import random
import string

class RapidProAction:
    def render(self):
        return {
            'uuid': str(uuid.uuid4()),
            'text': self.text,
            'type': self.type,
        }

# TODO: Create subclass for each of these actions: https://app.rapidpro.io/mr/docs/flows.html#actions
#    or at least the actions we support in the spreadsheet for now
# Check if the RapidPro implementation has such classes defined in its code somewhere

# Fix naming scheme (inconsistent): RapidProExit or Action/Node/...
class Exit:
    def __init__(self, destination_uuid=None):
        self.destination_uuid = destination_uuid
        self.uuid = str(uuid.uuid4())  # Write a wrapper around this?

    def render(self):
        return {
            'destination_uuid': self.destination_uuid,
            'uuid': self.uuid,
        }



# In practice, nodes have either a router or a non-zero amount of actions.
#     (I don't know if this is a technical restriction, or convention to make
#     visualization in the UI work.)
# The only exception is enter_flow, which has both.
#     (a flow can be completed or expire, hence the router)
# A node with neither is meaningless, so our output shouldn't have such nodes
class RapidProNode:
    def __init__(self):
        self.uuid = str(uuid.uuid4())
        self.actions = []
        self.router = None
        # Each node must have an exit.
        # If our node has a router, this exit will be connected to the
        # 'Other'/'Expired' category
        self.exits = [Exit()]

    def connect_default_exit(self, node):
        self.exits[0].destination_uuid = node.uuid

    def add_exit(self, exit):
        self.exits.append(exit)

    def add_action(self, action):
        self.actions.append(action)

    def add_default_choice(self, destination_node):
        if self.router is not None:
            self.router.add_default_choice(self.exits[0].uuid)
        else:
            # Create a router with a default category connected to our only exit
            self.router = SwitchRouter(self.exits[0].uuid)
        self.exits[0].destination_uuid = destination_node.uuid

    def add_choice(self, destination_node, comparison_variable, comparison_type, comparison_arguments, category_name=None):
        '''
        Add a case for the given choice, link/create a corresponding category,
        link/create a corresponding exit for that category,
        and connect that exit to the destination node.
        '''

        # Find/Create an exit for the appropriate choice
        # TODO: Check if this is how it works if we have multiple categories leading into the same node
        for exit in self.exits:
            if exit.destination_uuid == destination_node.uuid:
                destination_exit = exit
                break
        else:
            destination_exit = Exit(destination_node.uuid)
            self.add_exit(destination_exit)

        if self.router is None:
            self.router = SwitchRouter(self.exits[0].uuid)
        self.router.add_choice(destination_exit, comparison_variable, comparison_type, comparison_arguments, category_name)

    def render(self):
        # recursively render the elements of the node
        fields = {
            'uuid': self.uuid,
            'actions': [action.render() for action in self.actions],
            'exits': [exit.render() for exit in self.exits],
        }
        if self.router is not None:
            fields.update({
                'router': self.router.render(),
            })
        return fields


class RouterCategory:
    def __init__(self, name, exit_uuid):
        self.uuid = str(uuid.uuid4())
        self.name = name
        self.exit_uuid = exit_uuid

    def render(self):
        return {
            'uuid': self.uuid,
            'name': self.name,
            'exit_uuid': self.exit_uuid,
        }

def categoryNameFromComparisonArguments(comparison_arguments):
    # TODO: Implement something sensible
    # Make it a router class method and ensure uniqueness
    return '_'.join([str(a) for a in comparison_arguments]) + '_' + \
           ''.join(random.choice(string.ascii_letters) for _ in range(10))

class RouterCase:
    def __init__(self, comparison_type, arguments, category_uuid):
        self.uuid = str(uuid.uuid4())
        self.type = comparison_type
        self.arguments = arguments
        self.category_uuid = category_uuid

    def render(self):
        return {
            'uuid': self.uuid,
            'type': self.type,
            'category_uuid': self.category_uuid,
            'arguments': self.arguments,
        }


class AbstractRouter:
    def __init__(self, choices=None):
        self.categories = []
        self.choices = choices
        self.cases = []
        self.default_category_uuid = None
        self.exits = []

    def get_router_detail(self):
        router_category = RouterCategory()
        router_exit = Exit()
        router_case = RouterCase()

        current_category = router_category.render(None)

        self.categories.append(current_category)
        self.exits.append(router_exit.render(current_category['exit_uuid']))
        self.default_category_uuid = current_category['uuid']

        for choice in self.choices:
            current_category = router_category.render(None)

            self.categories.append(current_category)
            self.exits.append(router_exit.render(current_category['exit_uuid']))
            self.cases.append(router_case.render(choice, current_category['uuid']))

    def render(self):
        return {
            # These are the only two fields common to switch and random routers
            'type': self.type,
            'categories': [category.render() for category in self.categories],
            # 'operand': '@input',
            # 'cases': self.cases,
            # 'default_category_uuid': self.default_category_uuid,
        }


class SwitchRouter(AbstractRouter):
    # I didn't touch the AbstractRouter class, except for the render function
    # which I invoke here.

    def __init__(self, exit_uuid):
        '''
        exit_uuid: UUID of the exit the default category is connected to.
        '''

        self.type = 'switch'
        self.categories = [RouterCategory('Other', exit_uuid)]
        self.default_category_uuid = self.categories[0].uuid
        self.operand = None
        self.cases = []
        self.wait = None

    def add_category(self, category):
        self.categories.append(category)

    def add_case(self, case):
        self.cases.append(case)

    def set_operand(self):
        # specify the operand that the cases check for
        # done during init?
        pass

    def add_default_choice(self, exit_uuid):
        self.categories[0].exit_uuid = exit_uuid


    def add_choice(self, exit, comparison_variable, comparison_type, comparison_arguments, category_name=None):
        # Adds a case that compares the operand to the comparison_value using comparison_type
        # Adds a category of the given name that the case belongs to
        #     (if not provided, name is auto-generated from comparison_value and ensured to be unique) 
        # Connects the category to the specified exit.
        if category_name is not None:
            # TODO: Check whether the category name already exists.
            # If yes, connect to the existing category, and
            # warn if there is a mismatch between the exit of the category and the exit provided here
            # TODO: Check if this behavior works like this in RapidPro.
            # if category_name in [category.name for category in self.categories]:
            pass
        else:
            category_name = categoryNameFromComparisonArguments(comparison_arguments)

        if self.operand is None:
            self.operand = comparison_variable
        else:
            if self.operand != comparison_variable:
                # TODO: Sensible exception handling that allows us to trace down
                # errors to specific operations/rows
                raise ValueError("A router can only have a single operand.") 

        category = RouterCategory(category_name, exit.uuid)
        case = RouterCase(comparison_type, comparison_arguments, category.uuid)
        self.add_category(category)
        self.add_case(case)

    def render(self):
        if self.operand is None:
            raise ValueError("Trying to render incomplete router.")

        fields = super().render()
        fields.update({
            'default_category_uuid': self.default_category_uuid,
            'operand': self.operand,
            'cases': [case.render() for case in self.cases],
        })
        if self.wait is not None:
            # TODO: Render the wait.
            pass
        return fields


class RandomRouter:
    def __init__(self):
        self.type = 'random'
        self.choices = None
        self.router = {}

    def render(self):
        abstract_router = AbstractRouter(self.choices)

        current_router = abstract_router.render()

        self.router.update(current_router)

        return {
            'uuid': str(uuid.uuid4()),
            'router': self.router,
            'exits': current_router['exits']
        }
