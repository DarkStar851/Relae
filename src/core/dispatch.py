"""All the command functions should be implemented here.
Feed-forward functions are called on Request objects and must return a pair
containing a string SQL query and a tuple of arguments to place into the query.
Feedback functions are called on the results of a query, and should return a
string message detailing the success/failure of the command.
By convention, corresponding feed-forward and feedback functions should have
the same base name, prefixed with ff_ and fb_ respectively.
These functions are stored in the dispatch_fns dictionary using the command
name as the key and the pair of feed-forward and feedback functions as the
value.
Database table-names are as follows:
reminders     - Reminders to be issued at a certain time.
notifications - Notifications to be issued when a user is next seen online.
"""

import time

TIME_FMT = "%m/%d/%y-%H:%M"

def ff_remind(req):
    return ("insert into reminders (src,dest,created,date,msg) values(?,?,?,?,?)",
            (req.source, req.destination, req.time_created, req.issue_time, 
                                                                  req.message))

def ff_notify(req):
    return ("insert into notifications (src,dest,created,msg) values(?,?,?)",
                (req.source, req.destination, req.time_created, req.message))

def ff_get_time(req):
    return (";", ())

def ff_all_reminders(req):
    return ("select src,dest,msg from reminders where date<=?", (req.issue_time,))

def ff_all_notifications(req):
    return ("select src, msg from notifications where dest=?", (req.destination,))

def fb_remind(req, res):
    print "issue_time", req.issue_time, type(req.issue_time)
    return "Reminder for {0} at {1} added successfully.".format(
                req.destination, time.strftime(
                    TIME_FMT, time.localtime(int(req.issue_time) * 60)))

def fb_notify(req, res):
    return "Notification for {0} added.".format(req.destination)

def fb_get_time(req, res):
    return time.strftime(TIME_FMT, time.localtime())

def fb_all_reminders(req, res):
    if not res: return ""
    return "\n".join("<{0}> {1}, {2}".format(*r) for r in res)

def fb_all_notifications(req, res):
    return "\n".join("{0}, <{1}> {2}".format(req.destination, *r) for r in res)


dispatch_fns = {
    "remind"       : (ff_remind, fb_remind),
    "notify"       : (ff_notify, fb_notify),
    "time"         : (ff_get_time, fb_get_time),
    "allreminders" : (ff_all_reminders, fb_all_reminders),
    "allnotifies"  : (ff_all_notifications, fb_all_notifications)
}
