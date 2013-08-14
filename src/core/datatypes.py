import threading

class UIDGenerator(object):
    """A singleton object that generates unique ID integers."""
    __generator_exists = False

    class GeneratorSingletonException(Exception):
        def __init__(self):
            Exception.__init__(self, "UIDGenerator must be unique.")
            self.message = "UIDGenerator must be unique."

    def __init__(self, start_val):
        if not UIDGenerator.__generator_exists:
            UIDGenerator.__generator_exists = True
        else:
            raise GeneratorSingletonException()
        self.start = start_value

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
