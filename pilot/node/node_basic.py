import node_abstract
import psutil
import cpuinfo


class NodeBasic(node_abstract.NodeAbstract):
    """
    Basic node-related worker class.

    Provides basic functions to not reimplement in inherited classes. Also, tries to choose the necessary class from
    the unix class and the basic class. These two differ in the abstraction level: where one uses direct system calls,
    other uses abstraction libraries that provide necessary information, but on some platforms may be absent.

    This class uses `psutil` and `cpuinfo` to get node-related information. If those not available, unix class is used
    instead.
    """
    def __init__(self, interface, previous=None):
        """
        Initializes the node processor bypassing the NodeAbstract's `__init__`, but otherwise a common init for
        `SwitchableWithSignals`.

        Params resemble those of `SwitchableWithSignals`.
        """
        node_abstract.SwitchableWithSignals.__init__(self, interface, previous)

    def get_cpu(self):
        """
        Returns CPU clock in MHz.

        Overwrites that from NodeAbstract.
        Returns only a clock of the first core returned by `cpuinfo.get_cpu_info()`.

        :return float:
        """
        return float(cpuinfo.get_cpu_info()['hz_actual_raw'][0]) / 1000000.

    def get_cores(self):
        """
        Returns overall available CPU core count.

        Overwrites that from NodeAbstract.
        :return int:
        """
        return cpuinfo.get_cpu_info()['count']

    def get_mem(self):
        """
        Returns total RAM in MB.

        Overwrites that from NodeAbstract.
        :return float:
        """
        return float(psutil.virtual_memory().total) / 1024. / 1024.

    def get_disk(self, path='.'):
        """
        Returns available disk space of the disk associated with the provided path.

        If no path provided, returns the disk space of current working directory.

        Overwrites that from NodeAbstract.
        :param (basestring) path:
        :return float:
        """
        return float(psutil.disk_usage(path).free) / 1024. / 1024.
