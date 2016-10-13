from unittest import TestCase
from example_class.interface import ExampleInterface


class TestSwitchable(TestCase):

    def test_switchable(self):
        """ test successful init """
        t = ExampleInterface()
        t.foo()

    def test_changing(self):
        """ test changing """
        t = ExampleInterface()
        self.assertEqual(t.foo(), __package__ + '.example_class.interface.ExampleSwitchable')
        t.switchable_load(__package__ + '.example_class.example_extended')
        self.assertEqual(t.foo(), __package__ + '.example_class.example_extended.ExampleExtended test')
        t.switchable_to_default()
        self.assertEqual(t.foo(), __package__ + '.example_class.interface.ExampleSwitchable')

    def test_changing_to_undefined(self):
        """ test changing to undefined """
        t = ExampleInterface()
        self.assertEqual(t.foo(), __package__ + '.example_class.interface.ExampleSwitchable')
        t.switchable_load('undefined')
        self.assertEqual(t.foo(), __package__ + '.example_class.interface.ExampleSwitchable')

    def test_other_stuff(self):
        """ test other stuff """
        t = ExampleInterface()

        self.assertEqual(t.ti(1), 1)
        self.assertEqual(t.ci(1), 1)
        self.assertEqual(t.si(1), 1)

        self.assertEqual(t.prop, 'prop test')
        t.prop = 'setted prop'
        self.assertEqual(t.prop, 'setted prop')
        self.assertEqual(t.smth, None)
        t.smth = 1
        self.assertEqual(t.smth, 1)

    def test_shadows(self):
        """ test shadowing """
        t = ExampleInterface()

        self.assertEqual(t.test(), __package__ + '.example_class.interface.ExampleInterface')
        self.assertEqual(t.__getattr__("test")(), __package__ + '.example_class.interface.ExampleSwitchable')
