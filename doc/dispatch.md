# Dispatch Functions

When Relae receives a request message, it parses the information from the
message into a Request object (defined in src/core/server.py), and this
Request object is then passed as an argument first into a feedforward function
and again passed, along with the results of the query performed, into the
appropriate feedback function.

## Feedforward Functions

All feedforward functions create and return a tuple containing a SQL query
and a tuple of arguments to be filled in that query.  Feedforward functions
are called with Request objects as input, to use for extracting useful 
information such as the source of a command and the time at which it was issued
etc.

## Feedback Functions

Feedback functions are called again with the Request object and also with the
results of the SQL query specified by the corresponding feedforward function.
Feedback functions can do any sort of manipulation of these results desired,
such as producing statistical information or simply a message confirming a
successful operation.  These functions are only expected to return a single
string argument.
