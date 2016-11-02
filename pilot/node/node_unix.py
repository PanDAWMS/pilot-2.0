import node_abstract
import os
import pipes
import string


class NodeProcessorBasic(node_abstract.NodeAbstract):
    """
    Basic node-related worker class.

    Provides basic functions to not reimplement in inherited classes. Also, tries to choose the necessary class from
    the unix class and the basic class. These two differ in the abstraction level: where one uses direct system calls,
    other uses abstraction libraries that provide necessary information, but on some platforms may be absent.

    This class is loaded if `psutil` and `cpuinfo` are not available. It assumes the pilot runs under common linux-like
    environment. On windows and machines with different behaviour, try installing these libraries.
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

        Returns only a clock of first core from "/proc/cpuinfo".

        Overwrites that from NodeAbstract.
        :return float:
        """
        with open("/proc/cpuinfo", "r") as fd:
            lines = fd.readlines()
        for line in lines:
            if not string.find(line, "cpu MHz"):
                return float(line.split(":")[1])
        return 0.

    def get_cores(self):
        """
        Returns overall available CPU core count.

        Basically, just counts present "cpu MHz:" lines in "/proc/cpuinfo".

        Overwrites that from NodeAbstract.
        :return int:
        """
        with open("/proc/cpuinfo", "r") as fd:
            lines = fd.readlines()
        inc = 0
        for line in lines:
            if not string.find(line, "cpu MHz"):
                inc += 1
        return inc

    def get_mem(self):
        """
        Returns total RAM in MB.

        Overwrites that from NodeAbstract.
        :return float:
        """
        with open("/proc/meminfo", "r") as fd:
            mems = fd.readline()
            while mems:
                if mems.upper().find("MEMTOTAL") != -1:
                    return float(mems.split()[1]) / 1024
                mems = fd.readline()
        return 0.

    def get_disk(self, path='.'):
        """
        Returns available disk space of the disk associated with the provided path.

        If no path provided, returns the disk space of current working directory.

        Overwrites that from NodeAbstract.
        :param (basestring) path:
        :return float:
        """
        diskpipe = os.popen("df -mP %s" % pipes.quote(path))  # -m = MB
        disks = diskpipe.read()
        if not diskpipe.close():
            return float(disks.splitlines()[1].split()[3])
        return 0.
