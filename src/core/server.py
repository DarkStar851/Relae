import threading
import Queue

from datatypes import global_idgenerator as idgen

# This message should be sent by any interface or worker connected
# to an interface before closing the connection, to signal such an action.
QUIT_MSG = "##QUIT-COMM##"

class Request(object):
    """Holds relevant information about a command received from an interface."""
    
    def __init__(self, uid, requeue, src, dest, fn_name, created, date, msg):
        self.unique_id = uid
        self.response_queue = requeue
        self.source = src
        self.destination = dest
        self.function_name = fn_name
        self.time_created = created
        self.issue_time = date
        self.message = msg

    def from_msg(message, uid, requeue):
        """Parse messages of form SRC@DEST@FNNAME@CREATED@DATE@MESSAGE"""
        p = message.split('@')
        return Request(uid, requeue, *p)
    
    from_msg = staticmethod(from_msg)

class Worker(threading.Thread):
    """Communicates asynchronously with an interface to handle requests."""
    
    class Reader(threading.Thread):
        """Listens for input from client's request socket."""

        def __init__(self, insock, req_queue, pending, pend_lock):
            threading.Thread.__init__(self)
            self.requests = insock
            self.request_queue = req_queue
            self.pending = pending
            self.pending_lock = pend_lock

        def run(self):
            data = ""
            while data != QUIT_MSG:
                data = self.requests.recv(1024)
                if not data:
                    break
                resqueue = Queue.Queue(1)
                req = Request.from_msg(data, idgen.new_id(), resqueue)
                self.pending_lock.acquire()
                self.pending.append(resqueue)
                self.pending_lock.release()
    
    def __init__(self, insock, outsock, resevent):
        threading.Thread.__init__(self)
        self.requests = insock
        self.responses = outsock
        self.response_event = resevent
        self.pending_lock = threading.Lock()
        self.pending = []

    def run(self):
        reader = Reader(self.requests, self.request_queue, 
                        self.pending, self.pending_lock)
        while 1:
            self.response_event.wait()
            while 1: # Conditioned on pending items existing
                self.pending_lock.acquire()
                if not self.pending:
                    self.pending_lock.release()
                    break
                responses = []
                for pending in self.pending:
                    if not pending.empty():
                        responses.append(pending.get())
                        self.pending.remove(pending)
                self.pending_lock.release()
                for response in responses:
                    self.responses.send(response)
