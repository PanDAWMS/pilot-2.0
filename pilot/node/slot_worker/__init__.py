from switchables import Interface
from default import SlotWorkerDefault


class SlotWorkerInterface(Interface):
    """
    Provides slot-related functions to the job.

    Think of it as abstraction over nodes while job class is an abstraction over the experiments. Thus we separate one
    from another.
    """
    def __init__(self):
        # type: () -> SlotWorkerDefault
        Interface.__init__(self, SlotWorkerDefault)
