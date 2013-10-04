import threading
import socket
import random
import Queue
import time
import re

from twisted.words.protocols import irc
from twisted.internet import protocol
from twisted.internet import reactor

import config

TIME_FMT = "%m/%d/%y-%H:%M"
ID_VALID = "##IDNAME-VALID##"
ID_TAKEN = "##IDNAME-TAKEN##"
QUIT_MSG = "##QUIT-COMM##"

rules = {
    "DATE" : "\d\d/\d\d/\d\d-\d\d:\d\d",
    "DEST" : "[\w\d\|_`\-\[\]\^]+",
    "MSG"  : ".+"
}

reverse_rule = {}
for rule in rules.keys():
    reverse_rule[rules[rule]] = rule

r = rules # Temporary short name.
grammar = {
    "remind\s%s\s%s\s%s" %(r["DEST"], r["DATE"], r["MSG"]) : "remind",
    "notify\s%s\s%s" %(r["DEST"], r["MSG"])                : "notify",
    "get_time"                                             : "time",
    "all_reminders\s%s" % r["DATE"]                        : "allreminders",
    "all_notifications\s%s" % r["DEST"]                    : "allnotifies"
}
del r # Remove temporaryn name for rules variable.

# Didn't warrant importing.
def tsepoch():
    """Same as in core. Returns minutes since the epoch."""
    return int(time.time() / 60)

class Command(object):
    def __init__(self, src, dest, fn, created, issue, msg):
        self.src = src          # User who issued the command.
        self.dest = dest        # User to be reminded/notified.
        self.fn = fn            # Name of the function. See core/dispatch.py.
        self.created = created  # Time created. Minutes since epoch.
        self.issue = issue      # Time to issue reminder. Minutes since epoch.
        self.msg = msg          # Message text for reminders/notifications.

    # Expects that the "$NICK, " prefix has been removed.
    def parse(user, msg):
        """Parses IRC message into a Command object. Update along with core."""
        rule = None
        parsing = { 
            "SRC"  : user,      "DEST" : "",  "FN"   : "", 
            "CRE8" : tsepoch(), "DATE" : "",  "MSG"  : ""
        }
        for syntax in grammar.keys():
            if re.match(syntax, msg) is not None:
                rule, parsing["FN"] = syntax, grammar[syntax]
                break
        if rule is None:
            return None
        if msg.strip().count(' ') == 0:
            # Nothing to parse here
            return Command(user, "", parsing["FN"], parsing["CRE8"], "", "")
        msg = msg[msg.index(" ")+1:].strip()
        for token in rule.split("\\s")[1:]:
            # In case insufficient arguments were passed.
            if not msg:
                return None
            match = re.match(token, msg).group(0)
            msg = msg[len(match)+1:]
            parsing[reverse_rule[token]] = match
        if parsing is not None and len(parsing["DATE"]) > 0:
            parsing["DATE"] = int(time.mktime(
                time.strptime(parsing["DATE"], TIME_FMT)) / 60)
        return Command(user, parsing["DEST"], parsing["FN"], 
            parsing["CRE8"], parsing["DATE"], parsing["MSG"])
    parse = staticmethod(parse)

class Receiver(threading.Thread):
    def __init__(self, response_sock):
        threading.Thread.__init__(self)
        self.responses = response_sock
        self.queue = Queue.Queue()

    def has_responses(self):
        return not self.queue.empty()

    def get_response(self):
        return self.queue.get()

    def run(self):
        while 1:
            data = self.responses.recv(4096)
            if not data:
                break
            self.queue.put(data)

class ReminderBot(irc.IRCClient):
    def __init__(self):
        self.responses = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.requests = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.receiver = Receiver(self.responses)

    def _get_nickname(self):
        return self.factory.nickname
    nickname = property(_get_nickname)

    def _get_password(self):
        return self.factory.password
    password = property(_get_password)

    def signedOn(self):
        response = ""
        print("Signed on as {0}.".format(self.nickname))
        self.requests.connect((config.relae_ip, config.relae_port))
        self.responses.connect((config.relae_ip, config.relae_port))
        print("Connected to ({0}, {1}).".format(
            config.relae_ip, config.relae_port))
        while response != ID_VALID:
            idcode = ''.join(random.choice('0123456789') for i in range(3))
            self.requests.send("IRC_rb" + idcode)
            response = self.responses.recv(1024)
        self.receiver.start()
        self.join(self.factory.channel)

    def joined(self, channel):
        print("Joined {0}.".format(channel))

    def userJoined(self, user, channel):
        now = tsepoch()
        a, b = self.nickname, user.split('!')[0]
        m = "{0}@{1}@{2}@{3}@{4}@".format(a, b, "allnotifies", now, now)
        self.requests.send(m)
        time.sleep(2.0) # Sending messages too soon causes both to merge.
        m = "{0}@{1}@{2}@{3}@{4}@".format(a, b, "rmnotifies", now, now)
        self.requests.send(m)

    def connectionLost(self, reason):
        print("Disconnected - {0}".format(reason))
        self.receiver.terminate()
        self.requests.send(QUIT_MSG)
        self.requests.close()
        self.responses.close()
    
    def privmsg(self, user, channel, msg):
        user = user.split("!")[0]
        while self.receiver.has_responses():
            self.say(channel, self.receiver.get_response())
        if not msg.startswith(self.nickname):    
            return
        cmd = Command.parse(user, msg[msg.index(" ") + 1:])
        if cmd is None:
            return
        print("Parsed command for function {0}.".format(cmd.fn))
        self.requests.send("{0}@{1}@{2}@{3}@{4}@{5}".format(
            cmd.src, cmd.dest, cmd.fn, cmd.created, cmd.issue, cmd.msg))

class ClientFactory(protocol.ClientFactory):
    protocol = ReminderBot

    def __init__(self, channel=config.channel, 
                 nickname=config.nickname, password=config.password):
        self.channel = channel
        self.nickname = nickname
        self.password = password

    def clientConnectionLost(self, connector, reason):
        print("Lost connection - {0} -\nReconnecting.".format(reason))
        connector.connect()

    def clientConnectionFailed(self, connector, reason):
        print("Could not connect - {0}".format(reason))

def main():
    if not config.relae_ip:
        print("Pease edit config.py to provide a value for relae_ip.")
        return
    reactor.connectTCP(config.server, config.portno, ClientFactory())
    reactor.run()

if __name__ == "__main__":
    main()
