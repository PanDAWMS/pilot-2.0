from switchables import Switchable
from signalslot import Signal


class SwitchableWithSignals(Switchable):
    """
    An abstract class to use with Switchable and with signals.
    Serves signals, copies them and sets up their names.
    """
    def __init__(self, interface, previous=None):
        """
        Typical Switchable initializer based on availability of the `previous` class.
        """
        Switchable.__init__(self, interface, previous)

        if previous is None:
            self.init()
        else:
            self.copy_previous(previous)

    def init(self):
        """
        Initializes the Signals with their names and emitters.
        """
        for i in dir(self):
            val = getattr(self, i)
            if isinstance(val, Signal):
                val.emitter = self.interface
                val.name = self.interface.__class__.__name__ + "." + i

    def copy_previous(self, previous):
        """
        Copies the Signals from the `previous`.
        """
        for i in dir(previous):
            val = getattr(previous, i)
            if isinstance(val, Signal):
                setattr(self, i, val)
