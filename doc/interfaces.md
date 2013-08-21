# Interfaces

## Two-socket Asynchronous Communication

In order to communicate with Relae, an interface must connect to the Relae
server twice over TCP sockets.  One socket (s1) is used to send requests to
Relae and the other (s2) is used to receive responses from Relae.  Ideally,
the interface would have a separate process (a thread, perhaps) to wait on
responses and send them to another main thread to be displayed to the user,
but this is obviously not required.

## Connection Protocol

Relae keeps track of each interface connected to it by referring to a unique
identifier string that it associates with that interface.  This ID should be
chosen by the connecting interface.  The protocol is as follows:

1. New interface picks an ID and sends it to Relae over s1.
2. Relae receives the ID and determines whether it is unique.
3. If the ID is unique, Relae sends ID_VALID along s2.
4. If not, Relae sends ID_TAKEN along s2 and waits on s1 for a new ID.
5. Upon receiving ID_TAKEN, the interface must create a new ID and send on s1.
6. This continues until the interface receives ID_VALID.

ID_TAKEN is defined in Relae as the string "##IDNAME-TAKEN##"
ID_VALID is defined in Relae as the string "##IDNAME-VALID##"

## Request Messages

Relae expects messages sent to it after the selection of an ID to be formatted
as follows:

SOURCE@DEST@FNNAME@CREATED@DATE@MSG

SOURCE is the name of the user issuing the command.
DEST is the name of the user for whom the command is targetted.  For instance,
the user for whom a reminder or notification is to be issued.
FNNAME is the parsed name of the function determined to be associated with the
command being issued.  See src/core/dispatch.py for the list of existing names.
CREATED is the number of minutes since the epoch in minutes (as an integer),
the time at which the command was issued.
DATE is also the time since the epoch in minutes and should be the date that a
reminder should be issued.  In the case of commands with immediate feedback as
well as notifications, the value of this field does not matter.
MSG is the message to be delivered along with a reminder or notification.
