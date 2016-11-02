from default import JobserverCommunicator
from switchables import Interface


class JobserverCommunicatorInterface(Interface):
    """
    Interface to communicate with the PanDA server.

    The interface methods look in the `JobserverCommunicator`.
    """
    def __init__(self):
        # type: () -> JobserverCommunicator
        Interface.__init__(self, JobserverCommunicator)
