class InheritanceError(TypeError):
    """
    The error, thrown up if a new class does not match the abstract one.
    """
    pass


class ClassLookupError(ImportError):
    """
    The error, thrown up when no classes matching the abstract class found.
    """
    pass
