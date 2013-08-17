import time

from twisted.words.protocols import irc
from twisted.internet import protocol
from twisted.internet import reactor

import config

# TODO: Think of how to handle incoming responses.
# Idea 1: Create a thread to handle it asynchronously. Very messy.
# Idea 2: Check for responses when a message is received. Too synchronous?

TIME_FMT = "%D-%H:%M:%S"

# Didn't warrant importing.
def tsepoch():
    """Same as in core. Returns minutes since the epoch."""
    return time.time() * 1000000 / 60

def time_to_tse(ts):
    """Convert a TIME_FMT formated time to time since epoch in minutes."""
    datepart, timepart = ts.split("-")
    m, d, y = map(int, datepart.split("/"))
    h, mi, _ = map(int, timepart.split(":"))
    return 525600 * y + 43800 * m + 1440 * d + 60 * h + mi

class Command(object):
    def __init__(self, src, dest, fn, created, issue, msg):
        self.src = src          # User who issued the command.
        self.dest = dest        # User to be reminded/notified.
        self.fn = fn            # Name of the function. See core/dispatch.py.
        self.created = created  # Time created. Minutes since epoch.
        self.issue = issue      # Time to issue reminder. Minutes since epoch.
        self.msg = msg          # Message text for reminders/notifications.

    def parse(self, user, msg):
        """Parses IRC message into a Command object. Update along with core."""
        parts = msg.split(" ")
        now = time.tsepoch()
        if parts[0] == "remind":
            try:
                dest, = parts[1]
                issue = time_to_tse(parts[2])
                msg = " ".join(parts[3:])
                return Command(src, dest, "remind", now, issue, msg)
            except Exception:
                return None
        # Implement the rest of the parsing for these.
        # Would ideally like to find a better way to do it.
        elif parts[0] == "notify":
            pass
        elif parts[0] == "getTime":
            pass
        elif parts[0] == "showRem":
            pass
        elif parts[0] == "showNotif":
            pass

class ReminderBot(irc.IRCClient):
    def __init__(self, responses, requests):
        self.responses = responses # Response socket
        self.requests = requests   # Requests socket

    def _get_nickname(self):
        return self.factory.nickname
    nickname = property(_get_nickname)

    def _get_password(self):
        return self.factory.password
    password = property(_get_password)

    def signedOn(self):
        self.join(self.factory.channel)
        print("Signed on as {0}.".format(self.nickname))

    def join(self, channel):
        print("Joined {0}.".format(channel))

    def userJoined(self, user, channel):
        now = time.time()
        a, b = self.nickname, user
        self.requests.send("{0}@{1}@{2}@{3}@{4}@''".format(
            a, b, "allnotifies", now, now))

    def connectionLost(self, reason):
        print("Disconnected - {0}".format(reason))
    
    def privmsg(self, user, channel, msg):
        if not (msg.startswith(self.nickname + ", ") or \
            (msg.startswith(self.nickname + ": ")):
            return
        cmd = Command.parse(msg)
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
    reactor.connectTCP(config.server, config.portno, ClientFactor())
    reactor.run()

if __name__ == "__main__":
    main()
