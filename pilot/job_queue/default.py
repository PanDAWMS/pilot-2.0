from common.switchable_sig import SwitchableWithSignals
from jobserver_communicator import JobserverCommunicatorInterface
from common.signalslot import Signal
import logging
from job_manager import JobManagerInterface


class DefaultJobQueue(SwitchableWithSignals):
    """
    This class represents Job Queue Interface.

    This class serves the queue and works with it in the way it needs. Also, it schedules pending jobs and waits for the
    node to be ready to get the jobs, and feeds them.
    """
    args = None
    communicator = None
    jobs_pending = []
    has_pending_jobs = Signal(docstring="""
    Signal triggered when a new pending job is arrived or if the `jobs_pending` queue is appeared to be not empty.
    """)
    has_available_slots = Signal(docstring="""
    Signal triggered when there are available slots on the node and there are no pending jobs left.
    """)
    start_job = Signal(docstring="""
    Signal triggered with the job do be started when there is an available slot on the node and the job is ready to
    start.
    """)

    @property
    def log(self):
        """
        Gets a logger with the name of the class.

        :return logging.Logger:
        """
        return logging.getLogger(self.__class__.__name__)

    def init(self):
        """
        At the first init, we connect logger to see the list of pending jobs.
        I don't know, whether it is necessary, so it does not connect to the interface.
        """
        self.has_pending_jobs.connect(self.log_jobs)
        super(DefaultJobQueue, self).init()

    def log_jobs(self):
        """
        Just prints out pending jobs. The formatting is done by `__str__` or `__repr__` of the jobs.
        """
        for i in self.jobs_pending:
            self.log.debug("Pending job: %s" % i)

    def setup(self, args):
        """
        Sets the queue up and creates the server communicator.
        :param args:
        """
        self.args = args
        self.set_server_communicator()

    def fill_node_slots(self, number):
        """
        Tries to fill in present slots with pending jobs. If none, calls the server for some.

        For each job emits `start_job`.

        :param (int) number: 'of slots present.
        """
        while number > 0:
            if len(self.jobs_pending) == 0:
                break
            job = self.jobs_pending.pop()

            self.start_job(job, self.interface)
            number -= 1
        if number:
            self.has_available_slots(number)

    def get_job(self):
        """
        Gets job from server.
        """
        self.communicator.get_job()

    def push_job(self, job_desc):
        """
        Validates job and pushes it to pending.

        Emits in the end `has_pending_jobs`.

        :param job_desc:
        """
        if self.validate_job(job_desc):
            job = JobManagerInterface()
            job.setup(job_desc, self.interface)
            self.jobs_pending.append(job)
            self.has_pending_jobs.async()

    def validate_job(self, job_desc):
        """
        Validates job according to the queue, experiment, node and whatever.

        :param job_desc:
        :return Boolean:
        """
        return True

    def get_queue_config(self, filename=None):
        """
        Retrieves queue config from the server or from the file. Through the communicator.

        :param (str) filename: queue config file, if present
        :return: queue config
        """
        return self.communicator.get_queue(filename)

    def load_from_file(self, file_name):
        """
        tries to get job from file. Uses the communicator.
        :param (str) file_name:
        """
        self.communicator.get_job_from_file(file_name)

    def set_server_communicator(self):
        """
        Creates a communicator and connects the signals.
        """
        self.communicator = JobserverCommunicatorInterface()
        self.communicator.setup(self.args)
        self.communicator.got_new_job.connect(self.interface.push_job)
        self.has_available_slots.connect(self.communicator.get_job)

    def has_empty_slots(self):
        """
        Todo
        """
        return 0

    def graceful_shutdown(self):
        """
        Should make exit possible.
        """
        self.graceful_shutdown_jobs()

    def graceful_shutdown_jobs(self):
        """
        Should empty pending jobs and send them back to the server.
        Todo
        """
        pass
