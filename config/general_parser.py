import argparse

import config.runtime_config


class Singleton(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


def _createParser():
    """
    This class is representing a parser, that gets arguments passed from commandline during the script initiation.
    """
    lparser = argparse.ArgumentParser(description="To use the tests correctly you need to have correctly working mock "
                                                  "in non-root mode.")
    lparser.add_argument("-v", "--version",
                         help="display the version of the framework",
                         action="store_true")
    lparser.add_argument("-o", "--docs",
                         help="instead of testrun, generates documentation",
                         action="store_true")
    lparser.add_argument("-d", "--dir",
                         help="set directory where to search for rpms. Dir with rpm files only, "
                              "or subdirs - architectures, which each have its builds. Default: " +
                              config.runtime_config.RuntimeConfig().getPkgsDir())
    lparser.add_argument("-l", "--logfile",
                         help="target file for verbose output. Default: " +
                              config.runtime_config.RuntimeConfig().getLogsFile())
    lparser.add_argument("-b", "--build",
                         help="Will download the build specified by NVR from koji/brew to (empty) --dir")
    lparser.add_argument("-a", "--archs",
                         help="coma separated list t limit/extend download/spepcification to given arches. Use with "
                              "caution, and dont foget srpm/noarch. You can use all for all architectures.")
    lparser.add_argument("--noheader",
                         help="don't print header",
                         action="store_true")
    lparser.add_argument("--verbosity",
                         help="verbosity of logfile, 3 - most verbose, "
                              "2 - only test output, 1 - only fail output, default is 2")

    lparser.add_argument("--diewith",
                         help="specify, how is the framework supposed to fail, int only")
    return lparser


class GeneralParser(metaclass=Singleton):
    pass

    def __init__(self):
        self.parser = _createParser()
