from common.switchable_sig import SwitchableWithSignals
import logging
import socket
import os
from common.loggers import LoggingContext
from common.signalslot import Signal
from common.async_decorator import async
from slot_worker import SlotWorkerInterface


class NodeProcessorAbstract(SwitchableWithSignals):
    name = None
    has_available_slots = Signal()
    reserved_slots = []
    max_available_jobs = 1
    jobs_limit = 1
    jobs_count = 0

    def __init__(self, interface, previous=None):
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
            interface.switchable_load('node_processor_basic')
            return
        else:
            interface.switchable_load('node_processor_unix')
            return

    @async
    def request_slots(self):
        available = self.max_available_jobs - len(self.reserved_slots)
        if self.jobs_limit >= 0:
            limit = self.jobs_limit - self.jobs_count
            available = max(0, min(available, limit))
        if available > 0:
            self.has_available_slots(available)

    test_slots = request_slots

    def slot_finished(self):
        slot = Signal.emitted().emmitter
        self.reserved_slots.remove(slot)
        self.test_slots()

    @async
    def push_job(self, job, queue):
        log = logging.getLogger('node')
        slot = SlotWorkerInterface()
        slot.set_job(job)
        self.reserved_slots.append(slot)
        slot.empty.connect(self.slot_finished)
        self.jobs_count += 1
        slot.run()
        log.debug("Have jobs to run: %s" % job)

    def init(self):
        super(NodeProcessorAbstract, self).init()
        self.setup_name()

    def setup_name(self):
        self.name = socket.gethostbyaddr(socket.gethostname())[0]
        if "_CONDOR_SLOT" in os.environ:
            self.name = os.environ.get("_CONDOR_SLOT", '') + "@" + self.name

    def copy_previous(self, previous):
        self.setup_name()
        super(NodeProcessorAbstract, self).copy_previous(previous)
        for i in ['jobs_count', 'jobs_limit', 'max_available_jobs', 'reserved_slots']:
            setattr(self, i, getattr(previous, i))

    def print_packages(self):
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
        log = logging.getLogger('node')
        try:
            import ssl
            log.info("SSL version: " + ssl.OPENSSL_VERSION)
        except ImportError:
            log.warn("No SSL support on this machine. If pilot needs direct communication with a server, it failes.")

    def print_info(self):
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
        pass

    def get_cores(self):
        pass

    def get_mem(self):
        pass

    def get_disk(self, path='.'):
        pass
