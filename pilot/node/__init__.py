from node_abstract import NodeAbstract
from switchables import Interface
from common.singleton import Singleton


class NodeInterface(Interface):
    """
    Interface to node-related functions, like slots, CPU, memory and other stuff.

    It is a singleton, so any call to this class receives already loaded instance.
    """
    __metaclass__ = Singleton

    def __init__(self):
        # type: () -> NodeAbstract
        """
        As we have two different default classes, one of them is preferable but the other is "fallback", the behaviour
        is described in the abstract class, that then selects one of the used ones.
        """
        Interface.__init__(self, NodeAbstract)
