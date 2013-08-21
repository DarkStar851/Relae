# Relae

Relae is a simple TCP server that asynchronously handles a variety of commands
for the purpose of maintaining and issuing reminders and notifications across
a variety of media.

## Commands

Relae can have any sort of user-defined functionality added to it in Python
code by writing to the src/core/dispatch.py file.  For more information on
extending the functionality of Relae, see docs/dispatch.md.

## Interfaces

Any interface that can connect to Relae via two TCP sockets can issue and
receive commands from Relae.  Currently, an irc bot is provided within the
src/irc/ircbot.py file, which completely interfaces with the server to provide
all the functionality currently supported.  To create your own interface, read
more in doc/interfaces.md
