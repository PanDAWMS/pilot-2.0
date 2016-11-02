import logging
logging.basicConfig()
log = logging.getLogger()

try:
    h = logging.NullHandler()
    h = None
except AttributeError:
    # 2.6 workaround
    class NullHandler(logging.Handler):
        """
        Mutes the logging.

        See python 2.7 docs on logging.NullHandler.
        """
        def emit(self, record):
            """
            Mutes the logging.
            """
            pass

    logging.NullHandler = NullHandler
    pass


class LoggingContext(object):
    """
    Class to override logging level for specified handler.
    Used for output header and footer of log file regardless the level.
    Automatically resets level on exit.

    Usage:

        with LoggingContext(handler, new_level):
            log.something

    """
    def __init__(self, handler, level=None):
        self.level = level
        self.handler = handler

    def __enter__(self):
        if self.level is not None:
            self.old_level = self.handler.level
            self.handler.setLevel(self.level)

    def __exit__(self, et, ev, tb):
        if self.level is not None:
            self.handler.setLevel(self.old_level)
