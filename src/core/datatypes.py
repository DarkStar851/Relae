import threading

class TermColors(object):
    ERROR = "\033[91m"
    DEBUG = "\033[96m"
    NOTIFY = "\033[94m"
    STATUS = "\033[92m"

    def disable(self):
        self.ERROR = self.DEBUG = self.NOTIFY = self.STATUS = ""

class GeneratorSingletonException(Exception):
    def __init__(self):
        Exception.__init__(self, "UIDGenerator must be unique.")
        self.message = "UIDGenerator must be unique."

class UIDGenerator(object):
    """A singleton object that generates unique ID integers."""
    __generator_exists = False

    def __init__(self, start_val):
        if not UIDGenerator.__generator_exists:
            UIDGenerator.__generator_exists = True
        else:
            raise GeneratorSingletonException()
        self.start = start_val

    def new_id(self):
        v = self.start
        self.start += 1
        return v

global_id_generator = UIDGenerator(1)

class MortalThread(threading.Thread):
    """A thread that can be sent a terminate signal."""
    
    def __init__(self):
        threading.Thread.__init__(self)
        self.alivep = True

    def terminate(self):
        self.alivep = False

class DebugWriter(object):
    def __init__(self, outfile, endline="\n"):
        self.out = outfile
        self.endl = endline

    def _write(self, prefix, msg):
        self.out.write(prefix + " " + msg + self.endl)
        self.out.flush()

    def error(self, msg):
        self._write(TermColors.ERROR + "[-]",  msg)

    def debug(self, msg):
        self._write(TermColors.DEBUG + "[~]", msg)

    def notify(self, msg):
        self._write(TermColors.NOTIFY + "[!]", msg)

    def status(self, msg):
        self._write(TermColors.STATUS + "[+]", msg)
