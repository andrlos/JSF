class DocumentationProcessing(BaseException):
    pass


class JdkConfiguration():
    pass

    def __init__(self):
        self.documenting = False
        self.failed = 0
        self.passed = 0

    def _document(self, message):
        """Documentation used to generate specification-specific lines"""
        if self.documenting:
            raise DocumentationProcessing(message)
