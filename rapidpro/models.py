import logging
import uuid
import random
import string

from rapidpro.utils import generate_new_uuid

logger = logging.getLogger(__name__)


class Action:

    def __init__(self, type):
        self.uuid = generate_new_uuid()
        self.type = type

    def render(self):
        return {
            'uuid': self.uuid,
            'type': self.type,
        }


class SendMessageAction(Action):
    def __init__(self, text, attachments=[], quick_replies=[], all_urns=None):
        super().__init__('send_msg')
        self.text = text
        self.attachments = attachments
        self.quick_replies = quick_replies
        self.all_urns = all_urns

    def add_quick_reply(self, quick_reply):
        self.quick_replies.append(quick_reply)

    def render(self):
        render_dict = {
            "attachments": self.attachments,
            "text": self.text,
            "type": self.type,

            "quick_replies": [],
            "uuid": "6967333b-8ef0-4983-a223-b0a4c37447d1"
        }

        if self.all_urns:
            render_dict.update({
                'all_urns': self.all_urns
            })

        return render_dict


class SetContactFieldAction(Action):
    def __init__(self, field_key, field_name, value):
        super().__init__('set_contact_field')
        self.field_key = field_key
        self.field_name = field_name
        self.value = value

    def render(self):
        return {
            "uuid": self.uuid,
            "type": self.type,
            "field": {
                "key": self.field_key,
                "name": self.field_name
            },
            "value": self.value
        }


class GenericGroupAction(Action):
    def __init__(self, type, group_names):
        super().__init__(type)
        self.groups = [{
            'uuid': generate_new_uuid(),
            'name': group_name
        } for group_name in group_names]

    def add_group(self, group_name):
        self.groups.append({
            'uuid': generate_new_uuid(),
            'name': group_name
        })

    def render(self):
        return NotImplementedError


class AddContactGroupAction(GenericGroupAction):
    def __init__(self, group_names):
        super().__init__('add_contact_groups', group_names)

    def add_group(self, group_name):
        self.groups.append({
            'uuid': generate_new_uuid(),
            'name': group_name
        })

    def render(self):
        return {
            "type": self.type,
            "uuid": self.uuid,
            "groups": self.groups,
        }


class RemoveContactGroupAction(GenericGroupAction):
    def __init__(self, group_names, all_groups=None):
        super().__init__('remove_contact_groups', group_names)
        self.all_groups = all_groups

    def render(self):
        render_dict = super().render()
        if self.all_groups:
            render_dict.update({
                'all_groups': self.all_groups
            })
        return render_dict


class SetRunResultAction(Action):
    def __init__(self, name, value, category):
        super().__init__('set_run_result')
        self.name = name
        self.value = value
        self.category = category

    def render(self):
        return {
            "type": self.type,
            "name": self.name,
            "value": self.value,
            "category": self.category,
            "uuid": self.uuid
        }


class EnterFlowAction(Action):
    def __init__(self, flow_names):
        super().__init__('enter_flow')
        self.flows = [{
            'uuid': generate_new_uuid(),
            'name': flow_name
        } for flow_name in flow_names]

    def add_flow(self, flow_name):
        self.groups.append({
            'uuid': generate_new_uuid(),
            'name': flow_name
        })

    def render(self):
        return {
            "type": self.type,
            "uuid": self.uuid,
            "flow": self.flows
        }


# Check if the RapidPro implementation has such classes defined in its code somewhere


class Exit:
    def __init__(self, destination_uuid=None):
        self.destination_uuid = destination_uuid
        self.uuid = generate_new_uuid()

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


# TODO: Check enter flow
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

    def _add_exit(self, destination_uuid):
        self.exits.append(Exit(destination_uuid=destination_uuid))

    def add_action(self, action):
        self.actions.append(action)

    def add_default_choice(self, destination_node):
        if self.router is not None:
            self.router.add_default_choice(self.exits[0].uuid)
        else:
            # Create a router with a default category connected to our only exit
            self.router = SwitchRouter(self.exits[0].uuid)
        self.exits[0].destination_uuid = destination_node.uuid

    def add_choice(self, destination_node, comparison_variable, comparison_type, comparison_arguments,
                   category_name=None):
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
            self._add_exit(destination_node.uuid)

        if self.router is None:
            self.router = SwitchRouter(self.exits[0].uuid)
        self.router.add_choice(destination_exit, comparison_variable, comparison_type, comparison_arguments,
                               category_name)

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
    def __init__(self, name, exit_uuid, is_default=False):
        self.uuid = str(uuid.uuid4())
        self.name = name
        self.exit_uuid = exit_uuid
        self.is_default = is_default

    def render(self):
        return {
            'uuid': self.uuid,
            'name': self.name,
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