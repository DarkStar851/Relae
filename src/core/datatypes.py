import threading

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
    def __init__(self, outfile):
        self.out = outfile

    def error(self, msg):
        self.out.write("[ERROR] " + msg)

    def debug(self, msg):
        self.out.write("[DEBUG] " + msg)

    def notify(self, msg):
        self.out.write("[NOTIFICATION] " + msg)

    def status(self, msg):
        self.out.write("[STATUS] " + msg)
