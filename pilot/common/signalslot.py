"""
Module defining the Signal class.
"""

import inspect
import threading
from weakref import WeakSet, WeakKeyDictionary
import logging
import os
from exception_formatter import caught

DEBUG = True


class SignalDispatcher(threading.Thread):
    def __init__(self, sig, args, kwargs):
        super(SignalDispatcher, self).__init__(name=sig.name)
        self.dispatch_async_signal = sig
        self.args = args
        self.kwargs = kwargs

        self.emitter = sig.emitter
        current = threading.currentThread()
        self.parent = (current.getName(), current.ident)

    def run(self):
        logging.debug("Thread: %s(%d), called from: %s(%d)" % (self.getName(), self.ident,
                                                               self.parent[0], self.parent[1]))
        try:
            self.dispatch_async_signal._just_call(*self.args, **self.kwargs)
        except Exception as e:
            caught(e)


class Signal(object):
    """
    This class provides Signal-Slot pattern from Qt to python.

    To create a signal, just make a `sig = Signal` and set up an emitter of it. Or create it with
    `sig = Signal(emitter=foo)`.

    To emit it, just call your `sig()`.
    Or emit it in asynchronous mode: `sig.async()`.

    To connect slots to it, pass callbacks into `sig.connect`. The connections are maintained through weakrefs, thus
    you don't need to search for them and disconnect whenever you're up to destroy some object.
    """
    name = "BasicSignal"

    def __init__(self, emitter=None, docstring=None):
        """
        Creates a Signal class with no connections.

        :param emitter: Any object or anything, that is bound to a signal
        :param (basestring) docstring: if necessary, you may provide a docstring for this signal instead of the default
                                       one.
        """
        self._functions = WeakSet()
        self._methods = WeakKeyDictionary()
        self._slots_lk = threading.RLock()
        self.emitter = emitter  # TODO: Make this weakref
        if isinstance(docstring, basestring):
            self.__doc__ = docstring

    def connect(self, slot):
        """
        Connect a callback ``slot`` to this signal if it is not connected already.
        """
        with self._slots_lk:
            if not self.is_connected(slot):
                if inspect.ismethod(slot):
                    if slot.im_self not in self._methods:
                        self._methods[slot.im_self] = set()

                    self._methods[slot.im_self].add(slot.im_func)

                else:
                    self._functions.add(slot)

    def is_connected(self, slot):
        """
        Check if a callback ``slot`` is connected to this signal.
        """
        with self._slots_lk:
            if inspect.ismethod(slot):
                if slot.im_self in self._methods and slot.im_func in self._methods[slot.im_self]:
                    return True
                return False
            return slot in self._functions

    def disconnect(self, slot):
        """
        Disconnect a slot from a signal if it is connected else do nothing.
        """
        with self._slots_lk:
            if self.is_connected(slot):
                if inspect.ismethod(slot):
                    self._methods[slot.im_self].remove(slot.im_func)
                else:
                    self._functions.remove(slot)

    @staticmethod
    def emitted():
        """
        As the signal may provide emitter and other stuff related, this function gets the signal that was emitted.

        Note! Uses inspect.

        :return Signal:
        """
        frame = inspect.currentframe()
        outer = inspect.getouterframes(frame)
        self = None  # type: Signal
        for i in outer:
            if 'self' in i[0].f_locals and isinstance(i[0].f_locals['self'], Signal):
                self = i[0].f_locals['self']
                break

        del frame
        del outer
        return self

    def debug_frame_message(self):
        if not DEBUG:
            return
        log = logging.getLogger(self.name)
        frame = inspect.currentframe()
        outer = inspect.getouterframes(frame)
        signal_frame = outer[2]
        try:
            log.debug("%s:%d %s" % (os.path.basename(signal_frame[1]), signal_frame[2], signal_frame[4][0].strip()))
        finally:
            del signal_frame
            del outer
            del frame

    def async(self, *args, **kwargs):
        self.debug_frame_message()
        SignalDispatcher(self, args, kwargs).start()

    def __call__(self, *args, **kwargs):
        self.debug_frame_message()
        self._just_call(*args, **kwargs)

    def _just_call(self, *args, **kwargs):
        with self._slots_lk:
            # Call handler functions
            for func in self._functions:
                func(*args, **kwargs)

            # Call handler methods
            for obj, funcs in self._methods.items():
                for func in funcs:
                    func(obj, *args, **kwargs)
