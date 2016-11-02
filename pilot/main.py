"""
This is the main entrance point.
"""
from pilot import Pilot
import sys
import time
from common.async_decorator import async
import threading
import traceback
from common.exception_formatter import caught
import logging


@async(daemon=True)
def debug_stack_threading():
    """
    This is debugging thread.

    It will print stack traces of all the frames in the program every 1000'th second.
    If something dead-locked or cycled round, you'll see from it.
    """
    while True:
        time.sleep(1000)
        id2name = dict([(th.ident, th.name) for th in threading.enumerate()])
        code = ["Threading stack print",
                "----------------------------------------------------------------"]
        for thread_id, stack in sys._current_frames().items():
            code.append("\n# Thread: %s(%d)" % (id2name.get(thread_id, ""), thread_id))
            for filename, line_no, name, line in reversed(traceback.extract_stack(stack)):
                code.append('%s:%d (in %s): %s' % (filename, line_no, name, line))
        code.append("----------------------------------------------------------------")
        logging.getLogger('Threading').debug("\n".join(code))


if __name__ == "__main__":
    try:
        pilot = Pilot()
        debug_stack_threading()
        pilot.start()
        pilot.join()
    except Exception as e:
        caught(e)
