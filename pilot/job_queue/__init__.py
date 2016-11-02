from default import DefaultJobQueue
from switchables import Interface
from common.singleton import Singleton


class JobQueueInterface(Interface):
    """
    This class holds the interface for a job queue. One per pilot.

    For methods, see `DefaultJobQueue`
    """
    __metaclass__ = Singleton

    def __init__(self):
        # type: () -> DefaultJobQueue
        Interface.__init__(self, DefaultJobQueue)
