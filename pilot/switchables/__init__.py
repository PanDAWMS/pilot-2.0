# coding=utf-8

from importlib import import_module
from errors import InheritanceError, ClassLookupError
import os
import hashlib
import binascii
import imp
import sys
import inspect
# import weakref
import logging  # NOQA: F401 -- if commented debug
import types

file_module_prefix = "_file_"


def module_name_from_file(file_name):
    """
    This function creates a distinct module name for a certain file if it is imported by name.
    :param file_name:
    :return str:  new distinct module name
    """
    name = os.path.abspath(file_name)
    m = hashlib.md5()
    m.update(name)
    module_name = binascii.hexlify(m.digest())
    return file_module_prefix + module_name


class Switchable(object):
    """
    This is a base interface for any switchable module. It presents two major functions: initializer and switcher
    these two functions must have the same signature.

    To create a switchable class, just inherit from this and register it in the appropriate interface.
    ```
    import Switchable, Iterface from switchables

    class ExampleClass(Switchable):
        def __init__(self, interface, previous=None):
            Switchable.__init__(self, interface, previous)
            if previous:
                ...fetch values from previous...
            else:
                ...init default values...

        def __switch__(self):
            Switchable.__switch__(self)
            ...serialize all...

        def __switched__(self):
            Switchable.__switched__(self)
            ...close unclosed descriptors...

    # register it as follows
    class ExampleInterface(Interface):
        def __init__(self):
            Interface.__init__(self, ExampleClass)
    ```

    :prop interface: the pointer to the interface class of self
    """
    interface = None

    def __init__(self, interface, previous=None):
        """
        Initializer abstraction.

        Every initializer is provided with a previous object instance, that is at this time prepared for change
        (serialized) by means of `__switch__`. If none passed, this is the default initialization.

        This function is designed to either initialize the object with default values or import the previous values
        from the previous class.

        Interface is a pointer to interface class of self.

        :param interface: Interface to self
        :param previous: previous instance or none.
        """
        self.interface = interface

    def __switch__(self):
        """
        Serializer abstraction.

        This function is called upon an object when it is switching class. To switch for a new one, an object must
        serialize all it's internals into a unified way common for all the classes in this instance.
        For instance, it should end all specific connections, close all descriptors and update all the modified configs.
        It may live unclosed descriptors if
            1) these descriptors are a part of a config and will be maintained either by user or by each and every
               implementation
            2) they are closed in `__switched__` of the same object.
        After serialization this object will be passed to the initialization of a new class (it's `__init__`) as an
        argument.

        At this point the new class is unknown.
        """
        pass

    def __switched__(self):
        """
        Remover abstraction.

        At this point a new class is already invoked and set up. At this point an old class _must_ close all left
        descriptors, unlock semaphores and so on, if they haven't been passed to a new class.

        At this point the new class is working, this class is obsolete and removed. It may still persist while there
        would be some lost hanging links, etc... Thus you shouldn't rely on `__del__`
        """
        pass

    @staticmethod
    def same(obj):
        """
        This method duplicates an object interface and initializes it with default values saving only the class of the
        passed object.
        :param obj: interface to an object.
        :return: the same type of the interface with the same class initialized.
        """
        if not issubclass(obj, Interface):
            raise InheritanceError("Presented object is not a Switchable interface")
        ret = type(obj)()
        ret.switchable_cast(obj)
        return ret


class Interface(object):
    """
    This is an abstraction over the switchable interface providing all necessary functionality.


    To create a switchable class, just inherit from this and register it in the appropriate interface.
    ```
    import Switchable, Iterface from switchables

    class ExampleClass(Switchable):
        def __init__(self, interface, previous=None):
            Switchable.__init__(self, interface, previous)
            if previous:
                ...fetch values from previous...
            else:
                ...init default values...

        def __switch__(self):
            Switchable.__switch__(self)
            ...serialize all...

        def __switched__(self):
            Switchable.__switched__(self)
            ...close unclosed descriptors...

    # register it as follows
    class ExampleInterface(Interface):
        def __init__(self):
            Interface.__init__(self, ExampleClass)
    ```
    """
    __switchable__abstract_class__ = None
    __switchable__default_class__ = None
    __switchable__component__ = None
    __switchable__switch_to__ = None

    def __init__(self, default_class, abstract_class=None):
        """
        This is an abstraction method to register new interface.

        To register an interface, inherit this class and overload this method with calling Super, passing it the default
        class, and if needed, an abstract one (if there is one).

        Registering is done by three following lines:
        ```
        class ExampleInterface(Interface):
            def __init__(self):
                Interface.__init__(self, ExampleClass[, AbstractClass=ExampleClass])
        ```

        After registering with this method overloading, an `ExampleInterface` will initialize with `ExampleClass` as the
        first class and on switch it will test the inheritance of classes from `AbstractClass`. If `AbstractClass` is
        not defined, it is assumed to be the same as default one.

        Note: You can change default class in the future, but abstract class will prevail. Though you still can access
        magic properties to change it.

        :param default_class: The class with which every new instance will be initialized
        :param abstract_class: The class to which any class must inherit to implement this particular Interface instance
        """
        interface = self.__class__
        if interface.__switchable__abstract_class__ is None:
            if abstract_class is None:
                abstract_class = default_class
            interface.__switchable__abstract_class__ = abstract_class
            interface.__switchable__default_class__ = abstract_class
            self.switchable_set_default_class(default_class)

        comp = interface.__switchable__default_class__(self)
        object.__setattr__(self, "__switchable__component__", comp)
        new_cls = object.__getattribute__(self, "__switchable__switch_to__")
        if new_cls is not None:
            object.__setattr__(self, "__switchable__switch_to__", None)
            self.__switch__(new_cls)

    @classmethod
    def set_default_class(cls, new_class=None):
        """
        Sets new default class for all instances of current interface.

        Passed class must inherit from abstract class.
        You can pass not only a class, but also an interface or it's instance. It's current class will be set.
        If none passed, current class will be set to default.

        If new class is not inherited from abstract, no modifications occur.

        To diverge some instances from others, just spawn a new interface class like follows:
        ```
        class OtherExampleInterface(ExampleInterface):
            pass
        ```
        This new `OtherExampleInterface` will have it's own default class setting, separated from `ExampleInterface`,
        though they will resemble the same interface and the same level of abstraction, and will be able to exchange
        classes with `cast` and `set_default_class`.
        Note: newly created interface won't inherit current default class of `ExampleInterface`. To inherit, pass
        `ExampleInterface` into the `switchable_set_default_class`.

        :param new_class:
        """
        if new_class is None:
            new_class = cls
        if isinstance(new_class, Interface):
            new_class = object.__getattribute__(new_class, "__switchable__component__").__class__
        elif issubclass(new_class, Interface):
            new_class = new_class.__switchable__default_class__
        if issubclass(new_class, cls.__switchable__abstract_class__):
            cls.__switchable__default_class__ = new_class

    def __repr__(self):
        """
        Representation transfer.

        :return: Current representation of the class.
        """
        return object.__getattribute__(self, "__switchable__component__").__repr__()

    def switchable_set_default_class(self, new_class=None):
        """
        The wrapper around `set_default_class` interface method to provide shortcut and default parameter setting.

        If called without parameters, sets currently used class.

        :param new_class:
        """
        if new_class is None:
            new_class = self
        self.__class__.set_default_class(new_class)

    def __switch__(self, new_cls):
        """
        Switches interface to a new class.
        Internal.

        :param new_cls:
        """
        interface = self.__class__
        if not issubclass(new_cls, interface.__switchable__abstract_class__):
            raise InheritanceError("Presented class «" + new_cls.__name__ +
                                   "» is not the subclass of the provided abstract class")
        comp = object.__getattribute__(self, "__switchable__component__")
        if comp is not None:
            while new_cls is not None:
                if type(comp) != new_cls:
                    object.__setattr__(self, "__switchable__component__", None)
                    comp.__switch__()
                    newcmp = new_cls(self, comp)
                    object.__setattr__(self, "__switchable__component__", newcmp)
                    comp.__switched__()
                    del comp
                new_cls = object.__getattribute__(self, "__switchable__switch_to__")
                object.__setattr__(self, "__switchable__switch_to__", None)
        else:
            object.__setattr__(self, "__switchable__switch_to__", new_cls)

    def __switchable__load_from_module__(self, module, skip=0, **_):
        """
        Loads first found class from provided module, that is subclass of abstract.
        Internal.

        :param module:
        """
        interface = self.__class__
        for cls_name in dir(module):
            cls = getattr(module, cls_name)
            if issubclass(cls, interface.__switchable__abstract_class__):
                if skip > 0:
                    skip -= 1
                else:
                    self.__switch__(cls)
                    return
        raise ClassLookupError("Can not find proper class in module «" + module.__name__ + "»")

    def switchable_cast(self, other_interface):
        """
        Casts class from another interface instance onto this. The abstract class constraint is ensured.

        :param other_interface: the interface from which to get the class.
        :return:
        """
        other_cls = object.__getattribute__(other_interface, "__switchable__component__").__class__
        self.__switch__(other_cls)

    def __switchable__import_module_or_file__(self, name, package='.', **_):
        """
        Imports file, or module by string.
        Internal.

        :param name:
        :param package:
        :return:
        """
        interface = self.__class__
        if package == '.':
            module = interface.__switchable__abstract_class__.__module__
            package = sys.modules[module].__package__
        if os.path.isfile(name):
            module_name = module_name_from_file(name)
            if package is not None:
                module_name = package + "." + module_name
            if module_name not in sys.modules:
                return imp.load_source(module_name, name)
            else:
                return sys.modules[module_name]
        if package is not None:
            return import_module("." + name, package=package)
        return import_module(name)

    def switchable_load(self, *args, **kwargs):
        """
        Loads new (or already present) class from module or file, provided by string.
        It tries first to use the string as a filename, then as a module name, then falls back to default.
        You can provide a set of strings at one time. It will iterate over the arguments.

        Example:
        ```
        from switchables.example_class import ExampleInterface

        ex=ExampleInterface()
        ex.switchable_load('/mnt/net_disk/mymodule.py', 'class1', 'class2')
        ```
        In this case it will try to load file, then try to load `switchables.class1`, then try to load
        `switchables.class2`.
        If file is loaded, the module loaded will be also relative to `switchables`.

        Module name is prefixed the same way as an abstract class, so the module is always relative to it, as it was in
        the same folder as an abstract class, even if loaded file is loaded from anywhere else.

        To change prefix in the example above, provide named argument `base` with prefix.
        So, previous example will change to:
        ```
        ex.switchable_load('/mnt/net_disk/mymodule.py', 'class1', 'class2', package='myprefix')
        ```

        `package` is interpreted as magic variable `__package__` of every module. The only difference is the case of
        `package='.'`, that is the default value if package is not provided. In this case '.' expands to the package of
        the interface abstract class.
        If `package=None` is passed, the package is assumed to be at the root level.

        If you have multiple implementations in one file/module, pass `skip=N` to select N+1'st one.
        """
        for i in args:
            if isinstance(i, str):
                try:
                    module = self.__switchable__import_module_or_file__(i, **kwargs)
                    self.__switchable__load_from_module__(module, **kwargs)
                    return
                except ImportError or ClassLookupError:
                    pass

    def switchable_to_default(self):
        """
        Switch current instance to current default class, whatever it is.
        Does just this switching. No arguments, no variants.
        """
        interface = self.__class__
        self.__switch__(interface.__switchable__default_class__)

    def __getattr__(self, name):
        """
        One of two major elements of the interface. It provides transparent access to properties and methods of the
        underlying class. The getter.

        So, call for `el.foo()` will result in lookup for `foo()` in a class loaded right now for interface `el`.
        The same is for accessing property `el.bar`.

        For more information, consult python docs.

        :param name: name of property/method
        :return: property/method from current loaded class
        """
        comp = object.__getattribute__(self, "__switchable__component__")
        ret = getattr(comp, name)
        if inspect.ismethod(ret):
            # logging.getLogger('switchables').debug('Creating method %s::%s' % (self.__class__.__name__, name))

            def interface_method(interface, *args, **kwargs):
                # TODO: research weakrefs for this case
                # logging.getLogger('switchables').debug('Calling method %s::%s' % (self.__class__.__name__, name))
                return getattr(object.__getattribute__(interface, "__switchable__component__"), name)(*args, **kwargs)

            interface_method = types.MethodType(interface_method, self)
            return interface_method
        return ret

    def __setattr__(self, name, arg):
        """
        Other of two major elements of the interface. It provides transparent access to properties and methods of the
        underlying class. This is setter.

        While setting `el.bar = 'baz'`, it will search for `bar` in current class and will try to set it to 'baz'.

        For more information, consult python docs.

        :param name: name of property to set
        :param arg: new value for the property
        :return: property/method from current loaded class
        """
        comp = object.__getattribute__(self, "__switchable__component__")
        return setattr(comp, name, arg)


class InterfaceShort(Interface):
    """
    This is an alias container class. If you don't need these methods in your interface, you might want to use this,
    it cuts a few letters for you.
    ```
    cast_default = switchable_to_default
    load_module = switchable_load
    cast_class = switchable_cast
    set_default = switchable_set_default_class
    ```
    You can also do it your way in any of your registration classes.
    """
    cast_default = Interface.switchable_to_default
    load_module = Interface.switchable_load
    cast_class = Interface.switchable_cast
    set_default = Interface.switchable_set_default_class
