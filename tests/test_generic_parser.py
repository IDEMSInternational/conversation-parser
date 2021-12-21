import unittest

from parsers.generic import GenericParser


class TestGenericParser(unittest.TestCase):
    def setUp(self) -> None:
        self.parser = GenericParser('inputs/simple conditions - Sheet1.csv', column_configs={})


    def test_parse(self):
        self.parser.preprocess()