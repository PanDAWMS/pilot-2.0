from common.switchable_sig import SwitchableWithSignals
from common.signalslot import Signal
from common.async_decorator import async
import urllib2
import urllib
import logging
import json
from minipilot.job_description_fixer import description_fixer
import threading
from node import NodeInterface

log = logging.getLogger('JobserverCommunicator')

# While the Node is singleton, this will get the proper class.
node = NodeInterface()


class JobserverCommunicator(SwitchableWithSignals):
    """
    This is a class to communicate with a server.

    It gets job descriptions, gets queue configs and updates job statuses.
    The default class provides not only server-related calls but also file-related.
    """
    got_new_job = Signal(docstring="""
    Signal that triggers with a new job description.

    Passes the description.
    """)
    got_job_state = Signal(docstring="""
    Signal that triggers with a new job state from server.
    """)
    got_queue = Signal(docstring="""
    Signal that triggers on queue update
    """)
    args = None
    ssl_context = None
    job_server = None
    panda_server = None
    queue_name = None
    job_tag = None
    _async_get_job = threading.Lock()

    def init(self):
        """
        This function is called at the first creation and locks the communicator while a queue info is not ready.
        """
        super(JobserverCommunicator, self).init()
        self._async_get_job.acquire()

    def copy_previous(self, previous):
        """
        This function initializes the class on change.

        :param (JobserverCommunicator) previous:
        """
        super(JobserverCommunicator, self).copy_previous(previous)
        for i in ['args', 'ssl_context', 'job_server', 'panda_server', 'queue', 'job_tag',
                  '_async_get_job']:
            setattr(self, i, getattr(previous, i))

        if self.args is not None and self.queue_name is None:
            self.setup(self.args)

    def setup(self, args):
        """
        If the instance was not set up, this function will do that.

        :param args:
        """
        global log
        # Recreate logger after the pilot logging init.
        log = logging.getLogger('JobserverCommunicator')
        self.args = args
        try:
            import ssl
            self.ssl_context = ssl.create_default_context(capath=args['capath'], cafile=args['cacert'])
        except Exception as e:
            log.warn('SSL communication is impossible due to SSL error:')
            log.warn(e.message)
            pass
        self.job_server = '%s:%d' % (args['job_server'][0], args['job_server'][1])
        self.panda_server = '%s:%d' % (args['panda_server'][0], args['panda_server'][1])
        self.queue_name = self.args['queue']
        self.job_tag = self.args['job_tag']

    @async
    def get_job(self, *_):
        """
        Gets the job from the PanDA server.

        Will try to acquire a lock and will exit if the other process acquired it.
        Thus, throttling the things up and looping in a waiting sequence needs to be done in other parts of the code.

        The procedure triggers the `got_new_job` signal if job is received.
        """
        if not self._async_get_job.acquire(False):
            return
        try:
            log.info("Trying to get a job from queue %s with tag %s" % (self.queue_name, self.job_tag))
            log.info("Using server %s" % self.job_server)
            request = urllib2.Request("https://%s/server/panda/getJob" % self.job_server, urllib.urlencode({
                'cpu': node.get_cpu(),
                'mem': node.get_mem(),
                'node': node.name,
                'diskSpace': node.get_disk(),
                'getProxyKey': False,  # do we need it?
                'computingElement': self.queue_name,
                'siteName': self.queue_name,
                'workingGroup': '',  # do we need it?
                'prodSourceLabel': self.job_tag
            }))
            request.add_header('Accept',
                               'application/json;q=0.9,text/html,application/xhtml+xml,application/xml;q=0.7,*/*;q=0.5')
            request.add_header('User-Agent', self.args['user_agent'])
            try:
                f = urllib2.urlopen(request, context=self.ssl_context)
                result = json.loads(f.read())
                code = result['StatusCode'] if 'StatusCode' in result else result['status_code']
                if code == 0:
                    job_desc = description_fixer(result)
                    log.info("Got new job description, job id %s" % job_desc["job_id"])
                    self.got_new_job.async(job_desc)
                else:
                    log.info("Returned status code = %d", code)
            except urllib2.HTTPError as e:
                log.warn("Server returned error %d:" % e.code)
                log.warn(e.read())
            except urllib2.URLError as e:
                log.warn("Could not reach the server %s:" % e.reason)
        finally:
            self._async_get_job.release()

    def get_job_from_file(self, file_name):
        """
        This procedure gets job from file.

        The procedure will wait until the lock is open unlike server one, because the file has the highest priority for
        a job description.

        The procedure triggers the `got_new_job` signal if job is received.

        :param (str) file_name: the json file of the job description
        """
        with self._async_get_job:
            with open(file_name) as f:
                j = json.load(f)
                log.info("Successfully loaded file and parsed.")
                job_desc = description_fixer(j)
                log.info("Got new job description, job id %s" % job_desc["job_id"])
                self.got_new_job.async(job_desc)

    def get_queue(self, file_name=None):
        """
        This function gets a queue description from file or server.

        This function tries to get a queue description from file and if that fails for whatever reason, it then calls
        the server for that.

        The function assumes the lock to be raised and releases that in the end.

        :param (str) file_name: the json file of the queue description
        :return:
        """
        try:
            result = None
            if file_name:
                try:
                    f = open(file_name, "r")
                    result = json.load(f)
                except Exception as e:
                    log.warn('Failed to load queue from file %s' % file_name)
                    log.warn(e.message)
                    pass
            if result is None:
                request = urllib2.Request("http://atlas-agis-api.cern.ch/request/pandaqueue/query/list/?"
                                          "json&preset=schedconf.all&panda_queue=%s" % self.queue_name)
                request.add_header('Accept', 'application/json;q=0.9,'
                                             'text/html,application/xhtml+xml,application/xml;q=0.7,*/*;q=0.5')
                request.add_header('User-Agent', self.args['user_agent'])
                try:
                    f = urllib2.urlopen(request)
                    result = json.loads(f.read())
                except urllib2.HTTPError as e:
                    log.warn("Server returned error %d:" % e.code)
                    log.warn(e.read())
                except urllib2.URLError as e:
                    log.warn("Could not reach the server %s:" % e.reason)
            return result
        finally:
            self._async_get_job.release()

    def send_job_state(self, job):
        """
        Sends the state of the job to the server.

        If the new state or action received, the `got_job_state` signal emitted.

        :param (JobManager) job: job manager to call for state and other params.
        """
        pass
