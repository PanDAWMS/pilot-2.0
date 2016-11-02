from default import DataManagerDefault
from switchables import Interface


class DataManagerInterface(Interface):
    """
    Provides the way to get and send data.
    """
    def __init__(self):
        # type: () -> DataManagerDefault
        Interface.__init__(self, DataManagerDefault)
