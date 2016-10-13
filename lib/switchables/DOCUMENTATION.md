Introduction
============

`switchables` is a library providing simple runtime plug-in interface to
your project.

You can load any file to your project as if it was a plugin.
Containing the class providing the same interface, file will be loaded
as a module, and an interface will switch to loaded class.


Plugin switching
================

If you have some interface loaded in your project, just call
`switchable_load` with a filename or a module name, and it will be
switched automatically. If possible.

For example, you have next situation:
```python
from my_interface import MyInterface

foo = MyInterface()
```
Now, you use your `foo` and suddenly decide, that you need another
implementation of it. And you don't want to setup changes for the
implementation, you just want to start it right away and use, you don't
want to collect all the references to your `foo` all over your project,
you just swap that `foo`.
You just do:
```python
foo.switchable_load('other_interface')
```
Then, the `other_interface` module is loaded and from it the class
corresponding to `MyInterface` is used. Then our `foo` becomes this new
class.
Or you downloaded the implementation from elsewhere:
```python
foo.switchable_load('/tmp/dl_234124.py')
```
You may also cast the class to another instance:
```python
bar = MyInterface()
bar.switchable_cast(foo)
```
Or set the downloaded class to default:
```python
foo.switchable_set_default_class()
# or
MyInterface.set_default_class(foo)
```
Or you can drop back to default class:
```python
bar.switchable_to_default()
```


Module loading
==============

When you load module at some point, you may wonder, how to state it's
nesting level in Python. Basically, every plugin interface has plugin
abstract class. This class is loaded in some module with some package.
Then if you try to load another module, when switching, the loader
assumes, you do your loading from the level of the package containing
the abstract class. So, it will be easy to just collect all the variants
of your plugin into one folder and use them from there.

Let's illustrate it with a next example.
This is our file tree
```
|- main.py
|- my_plugin_pack
|  |- default.py  # will be the same as the abstract
|  |- other.py
|- some_other_package
|  |- some_file.py
|  |- strange_desicion.py
```
So, if you setup your plugin in main, you doo:
```python
from my_plugin_pack.default import MyInterface

foo = MyInterface()
```
Then if you want to change your plugin to other, you just do:
```python
foo.switchable_load('other')
```
As you can see, there is no need in defining prefix `my_plugin_pack`,
it is done automatically by system.
This line is all the same, wherever you decided to change the plugin.
If you want to switch in, for instance, `some_other_package.some_file`,
the line will be the same:
```python
foo.switchable_load('other')
```
But if your other implementation is in `strange_desicion.py`?
In this case you can state the path with named parameter `base` as
follows:
```python
foo.switchable_load('strange_desicion', base='some_other_package')
```
In this case, we use an absolute base to our file. But if you don't know
exactly the nesting of your code, just use a magic python variable
`__package__` according to it's documentation.

If you import a module, containing more than one implementation, ensure,
you're selecting the right one by passing `skip=N` into the importing
function.
The next example loads 3'rd implementation (if present).
```python
foo.switchable_load('strange_desicion', skip=2)
```


File loading
============

While module loading is kind of obvious, file loading might be a bit
tricky. For example, you have a solution for some interface, specific
for your environment, and you load all other code from some shared
storage. In this case, you may want to have your specific code lay only
on your machine, and now it's placed somewhere, and you added the path
to the file to your config.
Or the other case, you have this specific piece of interface downloaded
at some time, during the process. In that case, the file wasn't even
present at the moment of first start, and sure, it's filename wasn't
known...
Either ways, comes the moment, you want to switch to this file.
As the documentation says, just do:
```python
from my_plugin_pack.default import MyInterface

that_file_name = '/tmp/downloaded.py' # or whatever it was
foo = MyInterface()
foo.switchable_load(that_file_name)
```
In this case, the most interesting question is, what is the file's
scope, or how should you import the stuff (like abstract class to be
inherited). As in previous case, the base is the same, so in your file
you just can import default class straight away:
```python
# that /tmp/downloaded.py or whatever
from .default import MyImplementation

class MyExtendedImplementation(MyImplementation):
    ...
```
And `.default` in this case will be exactly `my_plugin_pack.default`.

And as in the case of modules, if you did your file in a different
scope, just provide it's base in a `base` parameter:
```python
foo.switchable_load(that_file_name, base='some_other_package')
```


Plugin development
==================

To create switchable plugin, you need to follow these simple things.

Basics
------

1. **Default class**
   Any plugin should have a default class, that is loaded first.
2. **Abstract class**
   Any plugin should have an abstract class. It may be a default class.
   An abstract class must inherit from `Switchable`.
3. **Proper heritage**
   Any implementation must inherit from abstract class.
4. **Registration**
   Registration is done by creating interface class, a subclass of
   `Interface`.
5. **Initialization**
   Implementation initializer must be of the same signature as the one
   of `Switchable`. It may or may not be present.

These practices may be illustrated by the next example:
```python
from switchables import Switchable, Interface

class MyImplementation(Switchable):
    pass

class MyInterface(Interface):
    def __init__(self):
        Interface.__init__(self, MyImplementation)
```
And in case of a separated abstract class:
```python
from switchables import Switchable, Interface

class MyAbstract(Switchable):
    pass

class MyImplementation(MyAbstract):
    pass

class MyInterface(Interface):
    def __init__(self):
        Interface.__init__(self, MyImplementation, MyAbstract)
```
Then any other implementation will inherit from abstract:
```python
from my_default import MyAbstract

class MyOtherImplementation(MyAbstract):
    pass
```
Other implementations don't need to be registered.

Switching
---------

The next theme is to implement switching on the go. For this procedure,
there are three functions, that do the stuff, in order, they are
triggered:

1. `Switchable.__switch__(self)`
   Prepares the old class.
2. `Switchable.__init__(self, previous=None)`
   Does switching.
3. `Switchable.__switched__(self)`
   Cleans the old class.

#### `__switch__(self)`

This function is triggered first. It is triggered on a class, that is
going to be switched, the old one.
The meaning of this function is to _prepare_ the class to switch: to
consolidate all the configs, to end all opened connections and do 
whatever might be necessary.

The procedure does not provide the new class because of the procedure
is meant to be common for all the cases, the switch happens.

#### `__init__(self, previous=None)`

This function is initializing the implementation class. At this point,
it may be that there was a previous class or there haven't been any.
In the first case, the class is already prepared to be switched with
the corresponding function. In the second case, `None` is passed.
The new class should configure itself according to all what had been
done in the previous class, to save the consistency. It should provide
the same config as the previous, because it might be not the last
change.

#### `__switched__(self)`

This is the destructor function. It is triggered immediately after the
switch was performed and meant to end all the things in a previous
class. We don't know, how long it will remain in memory before `__die__`
triggers, thus ew provide our own function.
For most cases this function is unnecessary and may be omitted.


Common misuses
==============

Referencing
-----------

If you reference any instance of the interface, on it's change, all
references got the update. But if you reference some object inside,
you might loose the connection to the object.
See the example:
```python
foo = MyInterface()

foo.bar = {}
foo.bar.baz = 1
bar = foo.bar

foo.switchable_load('other_interface')

bar != foo.bar  # True
```
Why it is so? -- Because the interfaces can not see deep into objects
they share, the interfaces are rather robust and simple, but useful.
Switching back won't solve the problem in this situation:
```python
foo.switchable_to_default()
bar != foo.bar  # still True
```
