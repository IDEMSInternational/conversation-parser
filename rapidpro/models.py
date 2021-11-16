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
    # TODO: Don't use mutable default values (bad things will happen)
    def __init__(self, text, attachments=[], quick_replies=[], all_urns=None):
        super().__init__('send_msg')
        self.text = text
        self.attachments = attachments
        self.quick_replies = quick_replies
        self.all_urns = all_urns

    def add_quick_reply(self, quick_reply):
        self.quick_replies.append(quick_reply)

    def render(self):
        # Can we find a more compact way of invoking the superclass
        # to render the common fields?
        render_dict = super().render()
        render_dict.update({
            "text": self.text,
            "attachments": self.attachments,
            "quick_replies": self.quick_replies,
        })

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
            'name': group_name  # We add group UUIDs during the validation step
        } for group_name in group_names]

    def add_group(self, group_name):
        self.groups.append({
            'name': group_name
        })

    def render(self):
        return NotImplementedError


class AddContactGroupAction(GenericGroupAction):
    def __init__(self, group_names):
        super().__init__('add_contact_groups', group_names)

    def add_group(self, group_name):
        self.groups.append({
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
        render_dict = {
            "type": self.type,
            "uuid": self.uuid,
            "groups": self.groups,
        }
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
    def __init__(self, flow_name):
        super().__init__('enter_flow')
        self.flow = {
            'name': flow_name
            # We add flow UUIDs during the validation step
        }

    def render(self):
        return {
            "type": self.type,
            "uuid": self.uuid,
            "flow": self.flow
        }


class EnterFlowNode(RapidProNode):
    def __init__(self, flow_name):
        super().__init__()
        # The default choice that is created during the super constructor
        # has category name 'Other'. We should be able to choose our own
        # name, in this case 'Expired'. 
        self.add_action(EnterFlowAction(flow_name))
        # add_choice takes a destination node rather than uuid.
        # This is a problem here (code below doesn't work) --> change this.
        super().add_choice(None, '@child.run.status', 'has_only_text', ['completed'],
                           'Completed')
        super().add_choice(None, '@child.run.status', 'has_only_text', ['expired'],
                           'Expired')

    def connect_outcome(self, destination_uuid, outcome):
        pass
        # TODO: implement and choose sensible name (or: connect_completed_exit/connect_expired_exit)
        # outcome is either 'Completed' or 'Expired'
        # change the exit destination of the corresponding category to destination_uuid
        # --> Convenience function that finds the exit for a given category (name)


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
# Node classification:
# - Action-only node (for various actions)
# - No action, split by variable [this includes wait_for_response]
# - Action + split by variable:
# - Enter flow (Router with Completed/Expired)
# - Call webhook (Router with Success/Failure)
# - No action, split by random

# I believe that it is true that whenever we create a node,
# we know what type of node it is.
# Thus it is sensible to implement nodes via classes
# Class tree (suggestion)
# GenericNode (allows for actions)
#   SwitchRouterNode
#     EnterFlowNode
#     WebhookNode
#   RandomRouterNode
# possibly more: dedicated subclasses for any kind of node where
# there is extra complexity that goes beyond the Action object.
#   wait_for_response is a potential instance of that
class RapidProNode:
    def __init__(self):
        # Add optional action to constructor for convenience?
        self.uuid = generate_new_uuid()
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

    # add_choice/add_default_choice is only applicable to nodes that have a switch router.
    # --> These should go into the corresponding subclass of Node?
    # --> Remove router from constructor
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
        # TODO: This is not actually how this works. Even if multiple categories are connected
        # to the same node, each of them has its own exit.
        # --> This code can be simplified
        for exit in self.exits:
            if exit.destination_uuid == destination_node.uuid:
                destination_exit = exit
                break
        else:
            self._add_exit(destination_node.uuid)

        if self.router is None:
            self.router = SwitchRouter(self.exits[0].uuid)
        # TODO: If the category_name already exists, we don't actually
        # want to create a new exit.
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
    def __init__(self, name, destination_uuid, is_default=False):
        """
        :param name: Name of the category
        :param destination_uuid: The UUID of the node that this category should point to
        :param is_default: is this the default category?
        """
        self.uuid = generate_new_uuid()
        self.name = name
        self.exit_uuid = generate_new_uuid()
        self.destination_uuid = destination_uuid
        self.is_default = is_default

    def get_exit(self):
        return Exit(self.destination_uuid)

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
        self.uuid = generate_new_uuid()
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


class BaseRouter:
    def __init__(self, operand, result_name=None, wait_for_message=False):
        self.type = None
        self.categories = []
        self.default_category_uuid = None
        self.cases = []
        self.operand = operand
        self.wait_for_message = wait_for_message
        self.result_name = result_name

    def set_result_name(self, result_name):
        self.result_name = result_name

    def _get_category_or_none(self, category_name):
        result = [c for c in self.categories if c.name == category_name]
        if result:
            return result[0]

    def _has_default_category(self):
        result = [c for c in self.categories if c.is_default]
        return bool(result)

    def _add_category(self, category_name, destination_uuid, is_default):
        if self._has_default_category() and is_default:
            logger.warning(f'Overwriting default category for Router {self.uuid}')

        category = RouterCategory(category_name, destination_uuid, is_default)

        if is_default:
            self.default_category_uuid = category.uuid

        self.categories.append(category)
        return self.categories[-1]

    def _get_case_or_none(self, comparison_type, arguments, category_uuid):
        for case in self.cases:
            if case.comparison_type == comparison_type \
                    and case.arguments == arguments \
                    and case.category_uuid == category_uuid:
                return case

    def _add_case(self, comparison_type, arguments, category_uuid):
        case = RouterCase(comparison_type, arguments, category_uuid)
        self.cases.add(case)
        return self.cases[-1]

    def get_or_create_case(self, comparison_type, arguments, category_name):
        category = self._get_category_or_none()
        if not category:
            raise ValueError(f'Category ({category_name}) not found. Please add category before adding the case')

        case = self._get_case_or_none(comparison_type, arguments, category.uuid)
        return case if case else self._add_case(comparison_type, arguments, category.uuid)

    def get_or_create_category(self, category_name, destination_uuid, is_default=False):
        category = self._get_category_or_none(category_name)

        return category if category else self._add_category(category_name, destination_uuid, is_default)

    def set_operand(self, operand):
        if self.operand and self.operand != operand:
            logger.warning(f'Overwriting operand from {self.operand} -> {operand}')
        self.operand = operand

    def render(self):
        raise NotImplementedError


class SwitchRouter(BaseRouter):

    def __init__(self, operand, result_name=None, wait_for_message=False):
        super().__init__(operand, result_name, wait_for_message)
        self.type = 'switch'

    def add_choice(self, comparison_variable, comparison_type, comparison_arguments, category_name,
                   category_destination_uuid, is_default=False):
        category = self.get_or_create_category(category_name, category_destination_uuid, is_default)
        self.get_or_create_case(comparison_type, comparison_arguments, category.name)

        self.set_operand(comparison_variable)
        return category

    def render(self):
        # TODO: validate
        render_dict = {
            "type": self.type,
            "operand": self.operand,
            "cases": [case.render() for case in self.cases],
            "categories": [category.render() for category in self.categories],
            "default_category_uuid": self.default_category_uuid
        }
        if self.wait_for_message:
            render_dict.update({
                "wait": {
                    "type": "msg",
                }
            })
        return render_dict


class RandomRouter(BaseRouter):
    def __init__(self, operand, result_name=None, wait_for_message=False):
        super().__init__(operand, result_name, wait_for_message)
        self.type = 'random'

    def add_choice(self, category_name, destination_uuid, is_default=False):
        self.get_or_create_category(category_name, destination_uuid, is_default)

    def render(self):
        return {
            "type": self.type,
            "categories": [category.render() for category in self.categories]
        }
