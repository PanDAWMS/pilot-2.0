# coding=utf-8

try:
    from ...switchables import Switchable, Interface
except ValueError:
    from switchables import Switchable, Interface
    pass


class ExampleSwitchable(Switchable):
    a = None

    def __init__(self, interface, previous=None):
        print("I'm __init__")
        print("my class is " + self.__class__.__name__)
        print('my module is ' + self.__class__.__module__)
        Switchable.__init__(self, interface, previous)
        self.a = "prop test"
        if previous:
            print("previous class was " + previous.__class__.__name__)
            print("previous module was " + previous.__class__.__module__)
        else:
            print("I'm the first one")

    def __switch__(self):
        Switchable.__switch__(self)
        print "I'm __switch__"

    def __switched__(self):
        Switchable.__switched__(self)
        print "I'm __switched__"

    def foo(self):
        print("I'm foo()")
        print("my class is " + self.__class__.__name__)
        print('my module is ' + self.__class__.__module__)
        return self.__class__.__module__ + "." + self.__class__.__name__

    def ti(self, *args):
        print("I'm ti(...)")
        print("my class is " + self.__class__.__name__)
        print('my module is ' + self.__class__.__module__)
        print("args len: %d" % len(args))
        return len(args)

    @classmethod
    def ci(cls, *args):
        print("I'm ci(...)")
        print("i'm for class " + cls.__name__)
        print('my module is ' + cls.__module__)
        print("args len: %d" % len(args))
        return len(args)

    @staticmethod
    def si(*args):
        print("I'm si(...)")
        print("static\nargs len: %d" % len(args))
        return len(args)

    @property
    def prop(self):
        print("I'm property «prop» getter")
        print("my class is " + self.__class__.__name__)
        print('my module is ' + self.__class__.__module__)
        return self.a

    @prop.setter
    def prop(self, arg):
        print("I'm property «prop» setter")
        print("my class is " + self.__class__.__name__)
        print('my module is ' + self.__class__.__module__)
        self.a = arg

    def test(self):
        return self.__class__.__module__ + "." + self.__class__.__name__

    def __getattr__(self, name):
        print("I'm __getattr__ for name " + name)
        print("my class is " + self.__class__.__name__)
        print('my module is ' + self.__class__.__module__)
        try:
            return object.__getattribute__(self, name)
        except AttributeError:
            return None

    def __setattr__(self, name, arg):
        print("I'm __setattr__ for name " + name)
        print("my class is " + self.__class__.__name__)
        print('my module is ' + self.__class__.__module__)
        try:
            return object.__setattr__(self, name, arg)
        except AttributeError:
            pass


class ExampleInterface(Interface):
    def __init__(self):
        Interface.__init__(self, ExampleSwitchable)

    def test(self):
        return self.__class__.__module__ + "." + self.__class__.__name__
