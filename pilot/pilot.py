import sys
import os
import argparse
import pipes
import logging
from node import NodeInterface
from job_queue import JobQueueInterface
from common.signalling import signal_all_setup
from common.signalslot import Signal
import threading
from common.singleton import Singleton
from common.exception_formatter import caught


class Pilot(threading.Thread):
    """
    Main class, singleton.

    Sets up all the system, then runs the pilot.
    Maybe, there will be a loop in the future, thus separate thread.

    Holds all the pilot-related variables.
    Introducing a new variable, remember about god-class antipattern.

    :var (NodeProcessorAbstract) node:
    """
    __metaclass__ = Singleton
    argv = []
    unresolved_arguments = []
    argument_parser = None
    user_agent = 'Pilot/2.0'
    args = None
    log = None
    queue_config = None
    node = None
    ready = Signal()

    def __init__(self, argv=sys.argv):
        """
        Sets up a pilot according to the passed arguments, creates worker classes, sets up the name, the machine and
        else. Establishes the connection between base classes.

        :param argv: essentially the same as sys.argv
        """
        super(Pilot, self).__init__(name='Pilot-main')
        import __main__
        import platform

        self.argv = argv
        self.node = NodeInterface()
        self.queue = JobQueueInterface()

        self.startup_dir = os.path.abspath(os.getcwd())
        self.pilot_dir = os.path.dirname(os.path.abspath(__main__.__file__))
        self.user_agent += " (Python %s; %s %s; rv:alpha) pilot/daniel" % \
                           (sys.version.split(" ")[0],
                            platform.system(), platform.machine())

        self.pilot_id = self.node.name + (":%d" % os.getpid())
        self.log = logging.getLogger('pilot')
        self.setup_argparser()
        self.setup_arguments()

        self.queue.setup({
            'capath': self.args.capath,
            'cacert': self.args.cacert,
            'queue': self.args.queue,
            'job_server': (self.args.jobserver, self.args.jobserver_port),
            'panda_server': (self.args.pandaserver, self.args.pandaserver_port),
            'job_tag': self.args.job_tag,
            'user_agent': self.user_agent,
            'node': self.node
        })
        self.node.has_available_slots.connect(self.queue.fill_node_slots)
        self.queue.has_pending_jobs.connect(self.node.request_slots)
        self.queue.start_job.connect(self.node.push_job)
        signal_all_setup(self.signal_receiver)

    def print_initial_information(self):
        """
        Pilot is initialized somehow, this initialization needs to be print out for debugging and identification.
        """
        log = self.log
        if self.args is not None:
            log.info("Pilot is running.")
            log.info("Started with: %s" % " ".join(pipes.quote(x) for x in self.argv))
        log.info("User-Agent: " + self.user_agent)
        log.info("Pilot ID: " + self.pilot_id)
        log.info("Pilot is started from %s" % self.pilot_dir)
        log.info("Current working directory is %s" % os.getcwd())

    def userproxy_file_standard_path(self):
        """
        Tries to get X509 user proxy file path.
        :return str: user proxy file or None
        """
        base = None
        try:
            base = '/tmp/x509up_u%s' % str(os.getuid())
        except AttributeError:
            # Wow, not UNIX. Nevermind, skip.
            pass

        return os.environ.get('X509_USER_PROXY', base)

    def setup_argparser(self):
        """
        Sets up arguments parser variables. These are common for all the pilot instances and share the same interface.
        The specific configuration must be done in the scope of these parameters and the configuration files.
        """
        qdata = os.path.join(self.startup_dir, "queuedata.json")
        qdata = qdata if os.path.isfile(qdata) else None
        import logging.config

        self.argument_parser = argparse.ArgumentParser(description="This is pilot.")

        self.argument_parser.add_argument("--logconf", type=logging.config.fileConfig,
                                          default=os.path.join(self.pilot_dir, "loggers.ini"),
                                          help="specify logger parameters file", metavar="path/to/loggers.ini")
        self.argument_parser.add_argument("--cacert", default=self.userproxy_file_standard_path(),
                                          type=lambda x: x if os.path.isfile(x) else None,
                                          help="specify CA certificate or path for your transactions to server",
                                          metavar="path/to/your/certificate")
        self.argument_parser.add_argument("--capath", default=os.environ.get('X509_CERT_DIR',
                                                                             '/etc/grid-security/certificates'),
                                          help="specify CA path for certificates",
                                          metavar="path/to/certificates/")
        self.argument_parser.add_argument("--pandaserver", default="pandaserver.cern.ch",
                                          help="Panda server web address.",
                                          metavar="panda.example.com")
        self.argument_parser.add_argument("--jobserver", default="aipanda007.cern.ch",
                                          help="Panda job server web address.",
                                          metavar="pandajob.example.com")
        self.argument_parser.add_argument("--pandaserver_port", default=25085,
                                          type=int,
                                          help="Panda server port.",
                                          metavar="PORT")
        self.argument_parser.add_argument("--jobserver_port", default=25443,
                                          type=int,
                                          help="Panda job server port.",
                                          metavar="PORT")
        self.argument_parser.add_argument("--queuedata", default=qdata,
                                          type=lambda x: x if os.path.isfile(x) else qdata,
                                          help="Preset queuedata file.",
                                          metavar="path/to/queuedata.json")
        self.argument_parser.add_argument("--queue", default='',
                                          help="Queue name",
                                          metavar="QUEUE_NAME")
        self.argument_parser.add_argument("--loglevel", default=None,
                                          choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                                          help="Set logging level",
                                          metavar="LVL")
        self.argument_parser.add_argument("--job_tag", default='prod',
                                          help="Job type tag. Eg. test, user, prod, etc...",
                                          metavar="tag")
        self.argument_parser.add_argument("--job_description", default=None,
                                          type=lambda x: x if os.path.isfile(x) else None,
                                          help="Job description file, preloaded from server. The contents must be JSON",
                                          metavar="tag")
        self.argument_parser.add_argument("--no_job_update", action='store_true',
                                          help="Disable job server updates")
        self.argument_parser.add_argument("--simulate_rucio", action='store_true',
                                          help="Disable rucio, just simulate")

    def setup_arguments(self):
        """
        Parses arguments according the argument parser, overrides logging level.
        """
        self.args, self.unresolved_arguments = self.argument_parser.parse_known_args(self.argv[1:])
        if len(self.unresolved_arguments):
            self.log.warn("Found unresolved arguments: " + " ".join(pipes.quote(x) for x in self.unresolved_arguments))
        if self.args.loglevel is not None:
            self.log.setLevel(getattr(logging, self.args.loglevel))

    def run(self):
        """
        Starts the main loop:
            1. Print info
            2. Get queue
            4. If has saved jobs, start them first
            3. Start job processing loop
        """
        try:
            self.print_initial_information()
            self.node.print_info()
            self.queue_config = self.queue.get_queue_config(self.args.queuedata)

            if self.args.job_description:
                self.queue.load_from_file(self.args.job_description)

            self.ready()
        except Exception as e:
            caught(e)

    def signal_receiver(self, sig, frame):
        """
        Catches signal. This one just receives it and logs.
        All signal handling must be done in other places.
        For the parameter specifics see `signal.signal()`

        :param sig: Signal number.
        :param frame: Stack frame that caught the signal.
        """
        from common.signalling import signals_reverse
        self.log.warn("received signal " + signals_reverse[sig])
