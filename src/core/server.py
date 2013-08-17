import sys
import time
import threading
import sqlite3
import socket
import Queue # Don't you hate how this is capitalized?

import datatypes
import dispatch

idgen = datatypes.global_id_generator

# The default file used for sqlite to store the database.
DEFAULT_DB_FILE = "relae.db"

# This message should be sent by any interface or worker connected
# to an interface before closing the connection, to signal such an action.
QUIT_MSG = "##QUIT-COMM##"

# This message should be understood by interfaces to signal that the
# name it wishes to assume is taken and it must respond with a new one.
ID_TAKEN = "##IDNAME-TAKEN##"

# This message signals to an interface that the id it wishes to use
# is free and has been accepted.
ID_VALID = "##IDNAME-VALID##"

def tsepoch():
    """Time since the epoch as an integral value measured in minutes."""
    return int(time.time() * 1000000) / 60

class Request(object):
    """Holds relevant information about a command received from an interface."""
    
    def __init__(self, iname, uid, requeue, src, dest, fn_name, created, date, msg):
        self.interface_name = iname
        self.unique_id = uid
        self.response_queue = requeue
        self.source = src
        self.destination = dest
        self.function_name = fn_name
        self.time_created = created
        self.issue_time = date
        self.message = msg

    def from_msg(iname, message, uid, requeue):
        """Parse messages of form SRC@DEST@FNNAME@CREATED@DATE@MESSAGE"""
        p = message.split('@')
        return Request(iname, uid, requeue, *p)
    
    from_msg = staticmethod(from_msg)

class Worker(datatypes.MortalThread):
    """Communicates asynchronously with an interface to handle requests."""
    
    class Sleeper(datatypes.MortalThread):
        """Sleeps for some time before making a request for reminders."""

        def __init__(self, iname, interval, requeue, pending, pend_lock):
            datatypes.MortalThread.__init__(self)
            self.interface_name = iname
            self.sleep_time = interval
            self.requests = requeue
            self.pending = pending
            self.pending_lock = pend_lock

        def run(self):
            while self.alivep:
                time.sleep(self.sleep_time)
                requeue = Queue.Queue(1)
                now = tsepoch()
                req = Request(
                    self.interface_name, gid.new_id(), requeue, 
                    "", "", now, now, "")
                self.pending_lock.acquire()
                self.pending.append(requeue)
                self.pending_lock.release()

    class Reader(datatypes.MortalThread):
        """Listens for input from client's request socket."""

        def __init__(self, iname, insock, req_queue, reqevent, pending, pend_lock):
            datatypes.MortalThread.__init__(self)
            self.interface_name = iname
            self.requests = insock
            self.request_event = reqevent
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
                req = Request.from_msg(
                    self.interface_name, data, idgen.new_id(), resqueue)
                self.pending_lock.acquire()
                self.pending.append(resqueue)
                self.pending_lock.release()
                self.request_queue.put(req)
                if not self.request_event.is_set():
                    self.request_event.set()
    
    def __init__(self, insock, outsock, reqevent, resevent):
        datatypes.MortalThread.__init__(self)
        self.requests = insock
        self.responses = outsock
        self.request_event = reqevent
        self.response_event = resevent
        self.pending_lock = threading.Lock()
        self.pending = []

    def run(self):
        reader = Reader(self.requests, self.request_queue, self.request_event,
                        self.pending, self.pending_lock)
        sleeper = Sleeper(1.0, self.request_queue, 
                          self.pending, self.pending_lock)
        reader.start()
        sleeper.start()
        while self.alivep:
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
            self.response_event.clear()
        reader.terminate()
        sleeper.terminate()
        reader.join()
        sleeper.join()

class Server(datatypes.MortalThread):
    """Handles incoming connections and spawns workers."""

    class RequestHandler(datatypes.MortalThread):
        """Handles incoming requests and pushing responses out."""

        def __init__(self, dbfile, requests, req_event):
            datatypes.MortalThread.__init__(self)
            self.dbfile = dbfile
            self.requests = requests
            self.response_events = {} # Maps interface IDs to response events.
            self.request_event = req_event # Signal from workers for requests.

        def has_interface(self, iname):
            return iname in self.response_events.keys()
        
        def add_interface(self, iname, event):
            self.response_events[iname] = event

        def run(self):
            dbconn = sqlite3.connect(self.dbfile)
            cursor = dbconn.cursor()
            cursor.execute(
                "create table if not exists reminders (src text, dest text, created float, date float, msg text)")
            cursor.execute(
                "create table if not exists notifications (src text, dest text, created float, msg text)")
            connection.commit()
            while self.alivep:
                self.request_event.wait()
                while not self.requests.empty():
                    req = self.requests.get()
                    ff, fb = dispatch.dispatch_fns[req.function_name]
                    sql, args = ff(req)
                    cursor.execute(sql, args)
                    req.response_queue.put(fb(cursor.fetchall()))
                    self.response_events[req.interface_name].set()
                for iname in self.response_events.keys()
                    self.response_events[iname].clear()
            dbconn.commit()
            dbcomm.close()

    def __init__(self, dbfile, server_socket):
        datatypes.MortalThread.__init__(self)
        self.dbfile = dbfile
        self.server = server_socket
        self.requests = Queue.Queue()
        self.request_e = threading.Event()

    def run(self):
        handler = RequestHandler(self.dbfile, self.requests, self.request_e)
        handler.start()
        workers = []
        while self.alivep:
            # Client connects over two sockets, one to send requests on,
            # and one to receive responses from.
            client_req = self.server.accept()[0]
            client_res = self.server.accept()[0]
            # Receive a unique ID for the interface.
            client_idn = client_req.recv(1024)
            while handler.has_interface(client_idn):
                client_res.send(ID_TAKEN)
                client_idn = client_req.recv(1024)
            client_rqe = threading.Event()
            client_rse = threading.Event()
            handler.add_interface(client_idn, client_rqe)
            client_res.send(ID_VALID)
            worker = Worker(client_req, client_res, client_rqe, client_rse)
            workers.append(worker)
            worker.start()
        for worker in workers:
            worker.terminate()
            worker.join()

def main(ip, port, dbfile):
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.bind((ip, port))
    server_sock.listen(5) # Max allowed by most systems.
    server = Server(dbfile, server_sock)
    server.start()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print "Usage: python ip port [database file]"
        sys.exit(1)
    if len(sys.argv) == 2:
        main(sys.argv[1], int(sys.argv[2]), DEFAULT_DB_FILE)
    else:
        main(sys.argv[1], int(sys.argv[2]), sys.argv[3])
