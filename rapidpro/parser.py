from collections import defaultdict

from rapidpro.models.actions import SendMessageAction, SetContactFieldAction, AddContactGroupAction, \
    RemoveContactGroupAction, SetRunResultAction, Group
from rapidpro.models.containers import Container
from rapidpro.models.nodes import BaseNode, BasicNode


class Dispatcher:

    def __init__(self, rows):
        self.rows = rows

    @classmethod
    def get_node_class_from_type(cls, type):
        if type == 'send_message':
            return BaseNode

    # def create_nodes(self):
    #     nodes = []
    #     current_node_class = None
    #     for row in rows:
    #         current_node_class = Dispatcher.get_node_class_from_type()


class Parser:

    def __init__(self, container, sheet_rows, flow_name=None):
        self.container = container or Container(flow_name=flow_name)
        self.sheet_rows = sheet_rows

        self.sheet_map = defaultdict()
        for row in self.sheet_rows:
            self.sheet_map[row['row_id']] = row

        self.row_id_to_node_map = defaultdict()
        self.node_name_to_node_map = defaultdict()
        self.group_name_to_group_map = defaultdict()

    def parse(self):
        for row in self.sheet_rows:
            self._parse_row(row)

    def get_row_action(self, row):
        attachment_types = ['image', 'audio', 'video']
        if row['type'] == 'send_message':
            send_message_action = SendMessageAction(text=row['message_text'])
            if any([row[attachment_type] for attachment_type in attachment_types]):
                send_message_action.add_attachment(
                    [row[attachment_type] for attachment_type in attachment_types if row[attachment_type]][0])

            choice_cells = [row[f'choice_{i}'] for i in range(1, 10)]
            quick_replies = [qr for qr in choice_cells if qr]
            if quick_replies:
                for qr in quick_replies:
                    send_message_action.add_quick_reply(qr)
            return send_message_action

        elif row['type'] == 'save_value':
            set_contact_field_action = SetContactFieldAction(field_name=row['save_name'], value=row['message_text'])
            return set_contact_field_action

        elif row['type'] == 'add_to_group':
            group = self._get_or_create_group(row)
            add_group_action = AddContactGroupAction(groups=[group])
            return add_group_action

        elif row['type'] == 'remove_from_group':
            group = self._get_or_create_group(row)
            remove_group_action = RemoveContactGroupAction(groups=[group])
            return remove_group_action

        elif row['type'] == 'save_flow_result':
            set_run_result_action = SetRunResultAction(row['save_name'], row['message_text'], category=None)
            return set_run_result_action

        else:
            print(f'Row type {row["type"]} not implemented')

    def _get_or_create_group(self, row):
        existing_group = self.group_name_to_group_map.get(self.get_object_name(row))
        if existing_group:
            return existing_group

        new_group = Group(name=row['message_text'])
        self.group_name_to_group_map[self.get_object_name(row)] = new_group

        return new_group

    def get_row_node(self, row):
        if row['type'] in ['send_message', 'save_value', 'add_to_group', 'remove_from_group', 'save_flow_result']:
            node = BasicNode()
            node.update_default_exit(None)
            return node

    def get_object_name(self, row):
        return row['obj_id'] or row['obj_name']

    def get_node_name(self, row):
        return row['_nodeId'] or row['node_name']

    def _get_last_node(self):
        try:
            return self.container.nodes[-1]
        except IndexError:
            return None

    def _parse_row(self, row):
        row_action = self.get_row_action(row)
        existing_node = self.node_name_to_node_map.get(self.get_node_name(row))

        if existing_node:
            existing_node.add_action(row_action)
            self.row_id_to_node_map[row['row_id']] = existing_node
        else:
            new_node = self.get_row_node(row)

            new_node.add_action(row_action)
            if row['from'] != 'start':
                self.row_id_to_node_map[row['from']].update_default_exit(new_node.uuid)

            self.container.add_node(new_node)

            self.row_id_to_node_map[row['row_id']] = new_node
            self.node_name_to_node_map[self.get_node_name(row)] = new_node



