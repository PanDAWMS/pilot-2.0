from default import JobManagerDefault
from switchables import Interface


class JobManagerInterface(Interface):
    """
    This is an interface to a job manager. The job manager is responsible for experiment specific regulations.

    For the interface documentation, see `JobManagerDefault`.
    """
    def __init__(self):
        # type: () -> JobManagerDefault
        Interface.__init__(self, JobManagerDefault)
