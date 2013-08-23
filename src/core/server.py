import sys
import time
import threading
import sqlite3
import socket
import Queue # Don't you hate how this is capitalized?

import datatypes
import dispatch

idgen = datatypes.global_id_generator
debug = datatypes.DebugWriter(sys.stdout)

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
    return int(time.time() / 60)

class Request(object):
    """Holds relevant information about a command received from an interface."""
    
    def __init__(self, iname, uid, requeue, src, dest, fn_name, created, date, msg):
        self.interface_name = iname
        self.unique_id = uid
        self.response_queue = requeue
        self.source = src
        self.destination = dest
        self.function_name = fn_name
        self.time_created = int(created)
        self.issue_time = int(date) if date else 0
        self.message = msg

    def from_msg(iname, message, uid, requeue):
        """Parse messages of form SRC@DEST@FNNAME@CREATED@DATE@MESSAGE"""
        p = message.split('@')
        debug.debug("from_msg p = " + str(p))
        return Request(iname, uid, requeue, *p)
    
    from_msg = staticmethod(from_msg)

class Sleeper(datatypes.MortalThread):
    """Sleeps for some time before making a request for reminders."""

    def __init__(self, iname, interval, requeue, pending, pend_lock, req_event):
        datatypes.MortalThread.__init__(self)
        self.interface_name = iname
        self.sleep_time = interval
        self.requests = requeue
        self.pending = pending
        self.pending_lock = pend_lock
        self.request_event = req_event

    def run(self):
        while self.alivep:
            time.sleep(self.sleep_time)
            requeue1 = Queue.Queue(1)
            requeue2 = Queue.Queue(1)
            now = tsepoch()
            req1 = Request(self.interface_name, idgen.new_id(), requeue1,
                "", "", "allreminders", now, now, "")
            req2 = Request(self.interface_name, idgen.new_id(), requeue2,
                "", "", "rmreminders", now, now, "")
            self.requests.put(req1)
            self.requests.put(req2)
            debug.status("Issued request to check for reminders.")
            self.pending_lock.acquire()
            self.pending.append(requeue1)
            self.pending.append(requeue2)
            self.pending_lock.release()
            self.request_event.set()

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
            debug.debug("Received request message {0}.".format(data))
            resqueue = Queue.Queue(1)
            req = Request.from_msg(
                self.interface_name, data, idgen.new_id(), resqueue)
            debug.debug("Successfully parsed into request object #{0}.".format(
                req.unique_id))
            self.pending_lock.acquire()
            self.pending.append(resqueue)
            self.pending_lock.release()
            self.request_queue.put(req)
            self.request_event.set()

class Worker(datatypes.MortalThread):
    """Communicates asynchronously with an interface to handle requests."""
    
    def __init__(self, iname, requeue, insock, outsock, reqevent, resevent):
        datatypes.MortalThread.__init__(self)
        self.iname = iname
        self.request_queue = requeue
        self.requests = insock
        self.responses = outsock
        self.request_event = reqevent
        self.response_event = resevent
        self.pending_lock = threading.Lock()
        self.pending = []

    def run(self):
        reader = Reader(self.iname, self.requests, self.request_queue, 
            self.request_event, self.pending, self.pending_lock)
        sleeper = Sleeper(self.iname, 60.0, self.request_queue, 
                          self.pending, self.pending_lock, self.request_event)
        reader.start()
        sleeper.start()
        debug.debug("Reader and sleeper threads started.")
        while self.alivep:
            self.response_event.wait()
            responses = []
            self.pending_lock.acquire()
            for pending in self.pending:
                if not pending.empty():
                    # Check that there's anything worth sending.
                    data = pending.get()
                    if len(data) <= 1:
                        continue
                    responses.append(data)
                    self.pending.remove(pending)
            self.pending_lock.release()
            for response in responses:
                self.responses.send(response)
                debug.debug("Sent response {0}.".format(response))
            self.response_event.clear()
        reader.terminate()
        sleeper.terminate()
        self.requests.close()
        self.responses.send(QUIT_MSG)
        self.responses.close()
        reader.join()
        sleeper.join()

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
        cursor.execute("create table if not exists reminders " +\
            "(src text, dest text, created float, date float, msg text)")
        cursor.execute("create table if not exists notifications " +\
            "(src text, dest text, created float, msg text)")
        dbconn.commit()
        debug.status("Connection to database established.")
        while self.alivep:
            self.request_event.wait()
            debug.debug("Request event triggered.")
            while not self.requests.empty():
                req = self.requests.get()
                ff, fb = dispatch.dispatch_fns[req.function_name]
                sql, args = ff(req)
                cursor.execute(sql, args)
                req.response_queue.put(fb(req, cursor.fetchall()))
                self.response_events[req.interface_name].set()
                debug.debug("Handled request #{0}.".format(req.unique_id))
            for iname in self.response_events.keys():
                self.response_events[iname].clear()
            self.request_event.clear()
        dbconn.commit()
        dbcomm.close()

class Server(datatypes.MortalThread):
    """Handles incoming connections and spawns workers."""

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
            debug.status("Waiting for connection from interface.")
            # Client connects over two sockets, one to send requests on,
            # and one to receive responses from.
            client_req = self.server.accept()[0]
            client_res = self.server.accept()[0]
            debug.notify("Connection received.")
            # Receive a unique ID for the interface.
            client_idn = client_req.recv(1024)
            while handler.has_interface(client_idn):
                client_res.send(ID_TAKEN)
                client_idn = client_req.recv(1024)
            debug.status("ID {0} set for new interface.".format(client_idn))
            client_rse = threading.Event()
            handler.add_interface(client_idn, client_rse)
            client_res.send(ID_VALID)
            worker = Worker(client_idn, self.requests, client_req, 
                client_res, self.request_e, client_rse)
            workers.append(worker)
            worker.start()
            debug.status("Spawned worker thread for {0}.".format(client_idn))
        for worker in workers:
            worker.terminate()
            # Cause the worker to stop waiting, do one last cycle, and exit.
            worker.response_event.set()
            worker.join()
        handler.terminate()
        # Signal a request event so the handler can exit.
        self.request_e.set()
        handler.join()
        debug.status("All workers terminated.")

def main(ip, port, dbfile):
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.bind((ip, port))
    server_sock.listen(10)
    server = Server(dbfile, server_sock)
    server.start()
    debug.status("Server started.")
    try:
        while 1:
            time.sleep(100)
    except Exception:
        server.terminate()
        # Need to complete a connection for Server to check its status.
        s1, s2 = [socket.socket(socket.AF_INET, socket.SOCK_STREAM) 
                  for i in range(2)]
        s1.connect((ip, port))
        s2.connect((ip, port))
        s1.send("".join(random.choice("123457890") for i in range(64)))
        s2.recv(1024)
        s1.close()
        s2.close()
        server.join()
    print("Server terminated.")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print "Usage: python ip port [database file]"
        sys.exit(1)
    if len(sys.argv) == 3:
        main(sys.argv[1], int(sys.argv[2]), DEFAULT_DB_FILE)
    else:
        main(sys.argv[1], int(sys.argv[2]), sys.argv[3])
