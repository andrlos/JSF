

class Singleton(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


class Tests(metaclass=Singleton):
    def __init__(self):
        self.testcases = []

    def add_testcase(self, testcase):
        self.testcases.append(testcase)

    def clear_tests(self):
        self.testcases.clear()

    def get_tests(self):
        return self.testcases

    def count_failed(self):
        return len([a for a in self.testcases if a.viewFileStub != ""])


class Testcase:
    def __init__(self, classname, name):
        self.classname = classname
        self.name = name
        self.time = 0
        self.logFile = ""
        self.viewFileStub = ""

    def set_log_file(self, logFile):
        self.logFile = logFile

    def set_view_file_stub(self, viewFileStub):
        self.viewFileStub = viewFileStub

    def print_test_case(self):
        text = "    <testcase classname=\"{}\" name=\"{}\" time=\"{}\"".format(self.classname, self.name, self.time)
        if self.viewFileStub == "":
            text += "/>"
        else:
            text += ">\n"
            text += "      <failure message=\"{}\" type=\"\">\n".format(self.viewFileStub)
            text += "      </failure>\n"
            text += "    </testcase>"
        return text


