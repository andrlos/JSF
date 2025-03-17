import enum

class Singleton(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]

class Verbosity(enum.Enum):
    ERROR = 1
    TEST = 2
    JTREG = 3
    MOCK = 4