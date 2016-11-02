from common.switchable_sig import SwitchableWithSignals
from common.signalslot import Signal
from common.async_decorator import async
import tempfile
import shutil


class SlotWorkerDefault(SwitchableWithSignals):
    """
    Provides slot-related functions to the job.

    Think of it as abstraction over nodes while job class is an abstraction over the experiments. Thus we separate one
    from another.
    """
    payload_finished = Signal(docstring="""
    Fired when payload exits.
    """)
    files_pushed = Signal(docstring="""
    Fired when files are on the worker slot and the job is ready to start.
    """)
    files_fetched = Signal(docstring="""
    Fires when files are fetched from the worker node and ready to be sent to storage.
    """)
    folder = None
    job = None
    empty = Signal(docstring="""
    Fires when the job is finished at all and slot is cleaned up.
    """)

    def set_job(self, job):
        """
        Links the job to the slot.

        :param (JobManagerDefault) job:
        """
        self.job = job
        job.finished.connect(self.job_finished)

    def job_finished(self):
        """
        Signal receiver on job finish.

        Cleans up.
        """
        self.job = None
        self.cleanup()
        self.empty()

    def create_folder(self):
        """
        Creates temporary folder to run job in.
        """
        self.folder = tempfile.mkdtemp("", "slot_folder", '.')
        pass

    def cleanup(self):
        """
        Cleans up all the mess left by job payload. With the temp. folder.
        """
        if self.folder:
            shutil.rmtree(self.folder)

    @async
    def push_files(self, files):
        """
        Pushes all the `files` to the dedicated folder on the slot.
        :param (list) files:
        """
        [shutil.move(fn, self.folder) for fn in files]
        self.files_pushed()

    @async
    def fetch_files(self, files):
        """
        Gets all the `files` from the dedicated folder on the slot.
        :param (list) files:
        """
        self.files_fetched()

    @async
    def run_payload(self, script="", env=None, **kwargs):
        """
        Runs the payload script.

        The script is supposed to be a valid bash script with provided necessary env. variables.

        :param (basestring) script: A valid BASH script.
        :param (dict) env: A dictionary of necessary env variables.
        :param kwargs:
        """
        pass

    def run(self):
        """
        Prepares the slot and starts the job.
        """
        self.job.start()
