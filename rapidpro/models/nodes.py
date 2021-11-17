from rapidpro.models.actions import EnterFlowAction
from rapidpro.models.common import Exit

from rapidpro.models.routers import SwitchRouter, RandomRouter
from rapidpro.utils import generate_new_uuid


# In practice, nodes have either a router or a non-zero amount of actions.
#     (I don't know if this is a technical restriction, or convention to make
#     visualization in the UI work.)
# The only exception is enter_flow, which has both.
#     (a flow can be completed or expire, hence the router)
# A node with neither is meaningless, so our output shouldn't have such nodes


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


class BaseNode:
    def __init__(self):
        self.uuid = generate_new_uuid()
        self.actions = []
        self.router = None

        # has_basic_exit denotes if the node should have only one exit
        # This generally occurs in cases where there is no router
        # if has_basic_exit is True, we will render a (very basic) exit which
        # points to default_exit_uuid
        self.has_basic_exit = True
        self.default_exit = None
        self.exits = []

    def add_default_exit(self, destination_uuid):
        self.default_exit = Exit(destination_uuid=self.default_exit_uuid)

    def _add_exit(self, exit):
        self.exits.append(exit)

    def _add_action(self, action):
        self.actions.append(action)

    def add_choice(self):
        raise NotImplementedError

    def validate(self):
        raise NotImplementedError

    def render(self):
        raise NotImplementedError
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


class BasicNode(BaseNode):
    # A basic node can accomodate actions and a very basic exit

    def _add_exit(self, exit):
        raise NotImplementedError

    def validate(self):
        if not self.has_basic_exit:
            raise ValueError('has_basic_exit must be True for BasicNode')

        if not self.default_exit_uuid:
            raise ValueError('default_exit_uuid must be set for BasicNode')

    def render(self):
        self.validate()
        return {
            "uuid": self.uuid,
            "actions": [action.render() for action in self.actions],
            "exits": [self.default_exit.render()]
        }


class SwitchRouterNode(BaseNode):

    def __init__(self, operand, result_name=None, wait_for_message=False):
        super().__init__()
        self.router = SwitchRouter(operand, result_name, wait_for_message)
        self.has_basic_exit = False

    def add_choice(self, **kwargs):
        self.router.add_choice(**kwargs)

    def validate(self):
        if self.has_basic_exit or self.default_exit_uuid:
            raise ValueError('Default exits are not supported in SwitchRouterNode')

        self.router.validate()

    def render(self):
        return {
            "uuid": self.uuid,
            "router": self.router.render(),
            "exits": [category.get_exit() for category in self.router.categories]
        }


class RandomRouterNode(BaseNode):

    def __init__(self, operand, result_name=None, wait_for_message=False):
        super().__init__()
        self.router = RandomRouter(operand, result_name, wait_for_message)
        self.has_basic_exit = False

    def add_choice(self, **kwargs):
        self.router.add_choice(**kwargs)

    def validate(self):
        if self.has_basic_exit or self.default_exit_uuid:
            raise ValueError('Default exits are not supported in SwitchRouterNode')

        self.router.validate()

    def render(self):
        return {
            "uuid": self.uuid,
            "router": self.router.render(),
            "exits": [category.get_exit() for category in self.router.categories]
        }


class EnterFlowNode(BaseNode):
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
