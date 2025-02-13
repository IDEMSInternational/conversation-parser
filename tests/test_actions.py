import unittest

from rapidpro.models.actions import EnterFlowAction


class TestActions(unittest.TestCase):
    def setUp(self) -> None:
        pass

    def test_enter_flow_node(self):
        enter_flow_node = EnterFlowAction(flow_name='test_flow')
        render_output = enter_flow_node.render()
        self.assertEqual(render_output['type'], 'enter_flow')
        self.assertEqual(render_output['flow']['name'], 'test_flow')
        self.assertIsNotNone(render_output['flow']['uuid'])

