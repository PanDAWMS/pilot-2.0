from unittest import TestCase

import os
import sys
sys.path.insert(0, os.path.abspath('..'))
# import


class TestMock(TestCase):

    def test_mock(self):
        """ Assert that true is not false """
        self.assertTrue(True)
        self.assertFalse(False)
