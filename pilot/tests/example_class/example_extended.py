from .interface import ExampleSwitchable


class ExampleExtended(ExampleSwitchable):
    def foo(self):
        print("I'm foo() from ExampleExtended")
        print("my class is " + self.__class__.__name__)
        print('my module is ' + self.__class__.__module__)
        return self.__class__.__module__ + "." + self.__class__.__name__ + " test"
