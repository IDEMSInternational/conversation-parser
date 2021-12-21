import unittest

from typedefs import Condition


class TestTypeDefinitions(unittest.TestCase):

    def test_condition_type(self):
        Condition(value='a', var='expression', name='A', type='has_any_word')
