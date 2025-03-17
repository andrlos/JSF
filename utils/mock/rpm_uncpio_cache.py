import tempfile
import ntpath
import os
import utils.test_utils
import utils.rpmbuild_utils
import outputControl.logging_access

class Singleton(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


class UcipioCached(metaclass=Singleton):
    """This singletong saves time, by uncipo each archive only once"""

    def __init__(self):
        self.parentFolder=tempfile.gettempdir()+"/JsfUcipioCached"
        utils.test_utils.mkdir_p(self.parentFolder)

    def uncipio(self, rpmPackage):
        """Returns the path to uncpioed tree"""
        target = self.parentFolder+"/"+ntpath.basename(rpmPackage)
        if (os.path.exists(target) and os.path.isdir(target)):
            return  target
        if (os.path.exists(target)):
            raise Exception(target + " exists, but is not directory")
        utils.test_utils.mkdir_p(target)
        o,e,r = utils.rpmbuild_utils.unpackFilesFromRpm(rpmPackage, target)
        outputControl.logging_access.LoggingAccess().log("Uncipio o:" + o)
        outputControl.logging_access.LoggingAccess().log("Uncipio e:" + e)
        if (r!=0):
            raise BaseException("Uncipio failed " + str(r))
        return target