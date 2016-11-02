from common.switchable_sig import SwitchableWithSignals
import logging
import socket
import os
from common.loggers import LoggingContext
from common.signalslot import Signal
from common.async_decorator import async
from slot_worker import SlotWorkerInterface


class NodeAbstract(SwitchableWithSignals):
    """
    Abstract node-related worker class.

    Provides basic functions to not reimplement in inherited classes. Also, tries to choose the necessary class from
    the unix class and the basic class. These two differ in the abstraction level: where one uses direct system calls,
    other uses abstraction libraries that provide necessary information, but on some platforms may be absent.
    """
    name = None
    has_available_slots = Signal(docstring="""
    Signal: emitted when new slots are available. Aka node is ready to start a job.
    """)
    reserved_slots = []
    max_available_jobs = 1
    jobs_limit = 1
    jobs_count = 0

    def __init__(self, interface, previous=None):
        """
        Class selector.

        This initializer essentially just selects the new class and switches to it.

        Params resemble those of `Switchable`.
        """
        SwitchableWithSignals.__init__(self, interface, previous)
        # # it's abstract. Removing this
        # if previous is None:
        #     self.init()
        # else:
        #     self.copy_previous(previous)
        have_basics = False
        try:
            import cpuinfo  # NOQA: F401 we are testing it for existence
            import psutil  # NOQA: F401 we are testing it for existence
            have_basics = True
        except ImportError:
            pass
        if have_basics:
            interface.switchable_load('node_basic')
            return
        else:
            interface.switchable_load('node_unix')
            return

    @async
    def request_slots(self):
        """
        Outer function to request a slot on the node to start a pending job.

        On most of machines, where slots are not created on beforehand, just calls
        `NodeProcessorInterface.test_slots`.

        Should try to create a slot to run a job with.
        """
        self.test_slots()

    def test_slots(self):
        """
        Outer function to find out, whether there are any slots available.
        """
        available = self.max_available_jobs - len(self.reserved_slots)
        if self.jobs_limit >= 0:
            limit = self.jobs_limit - self.jobs_count
            available = max(0, min(available, limit))
        if available > 0:
            self.has_available_slots(available)

    def slot_finished(self):
        """
        A signal receiver to remove the slot from running ones.
        """
        slot = Signal.emitted().emitter
        self.reserved_slots.remove(slot)
        self.test_slots()

    @async
    def push_job(self, job, queue):
        """
        Pushes job to a prepared slot and starts it.

        :param (JobManagerDefault) job: job to start.
        :param queue:
        :return:
        """
        log = logging.getLogger('node')
        slot = SlotWorkerInterface()
        slot.set_job(job)
        self.reserved_slots.append(slot)
        slot.empty.connect(self.slot_finished)
        self.jobs_count += 1
        slot.run()
        log.debug("Have jobs to run: %s" % job)

    def init(self):
        """
        First-time initialization.

        In this case, sets up a name (and all the signals, as super suggests).
        """
        super(NodeAbstract, self).init()
        self.setup_name()

    def setup_name(self):
        """
        Sets up node name.

        Tries to do it the wise way.
        """
        self.name = socket.gethostbyaddr(socket.gethostname())[0]
        if "_CONDOR_SLOT" in os.environ:
            self.name = os.environ.get("_CONDOR_SLOT", '') + "@" + self.name

    def copy_previous(self, previous):
        """
        Copies all preserved things from previous class if switched. And sets up node name.

        :param (NodeAbstract) previous:
        """
        self.setup_name()
        super(NodeAbstract, self).copy_previous(previous)
        for i in ['jobs_count', 'jobs_limit', 'max_available_jobs', 'reserved_slots']:
            setattr(self, i, getattr(previous, i))

    def print_packages(self):
        """
        Prints packages loaded by this pilot instance, if possible.

        This function may be necessary to debug classes selected based on module presence. This class is itself an
        example to such a behaviour. If you look to the `__init__`, you'll see the class selection based on present
        modules `psutil` and `cpuinfo`.
        """
        log = logging.getLogger('node')
        rootlog = logging.getLogger()
        log.info("Installed packages:")
        try:
            with LoggingContext(rootlog, max(logging.INFO, rootlog.getEffectiveLevel())):
                # suppress pip debug messages
                import pip
                packages = pip.get_installed_distributions()
            for pack in packages:
                log.info("%s (%s)" % (pack.key, pack.version))
        except Exception as e:
            log.warn("Failed to list installed packages. It may not be the issue, though.")
            log.warn(e.message)
            pass

    def print_ssl_version(self):
        """
        Prints out the SSL version of the pilot, if possible.

        The SSL support may be required in server requests.
        """
        log = logging.getLogger('node')
        try:
            import ssl
            log.info("SSL version: " + ssl.OPENSSL_VERSION)
        except ImportError:
            log.warn("No SSL support on this machine. If pilot needs direct communication with a server, it failes.")

    def print_info(self):
        """
        Prints the node-specific information at startup. This info is then provided to the server on the job requests.
        """
        log = logging.getLogger('node')
        log.info("Node related information.")
        log.info("Node name: %s" % self.name)
        log.info("CPU frequency: %d MHz" % self.get_cpu())
        log.info("CPU cores: %d" % self.get_cores())
        log.info("RAM: %d MB" % self.get_mem())
        log.info("Disk: %d MB" % self.get_disk())
        self.print_packages()
        self.print_ssl_version()

    def get_cpu(self):
        """
        Returns CPU clock in MHz.

        Returns only a clock of one core.

        :return float:
        """
        pass

    def get_cores(self):
        """
        Returns overall available CPU core count.

        :return int:
        """
        pass

    def get_mem(self):
        """
        Returns total RAM in MB.

        :return float:
        """
        pass

    def get_disk(self, path='.'):
        """
        Returns available disk space of the disk associated with the provided path.

        If no path provided, returns the disk space of current working directory.

        :param (basestring) path:
        :return float:
        """
        pass
