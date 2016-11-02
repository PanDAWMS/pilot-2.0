class Singleton(type):
    """
    Singleton metaclass.
    Nothing special. See wikipedia if you don't know any of these.
    """
    _instances = {}

    def __call__(cls, *args, **kwargs):  # NOQA N805: it is metaclass, so "cls", not "self".
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]
