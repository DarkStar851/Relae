package main

import (
    "database/sql"
    "net"
    "fmt"
    "data"
)

func Remind(cmd data.Command, tx *sql.Tx, db *sql.DB) string {
    _, err := tx.Exec(
        fmt.Sprintf("insert into reminders (src,dest,created,date,msg) values(%s, %s, %d, %d, %s)"),
                    cmd.Source, cmd.Destination, cmd.Created, cmd.Issue, cmd.Message)
    if err != nil {
        return fmt.Sprintf("Failed to create reminder for %s", cmd.Destination)
    }
    return fmt.Sprintf("Successfully createed reminder for %s", cmd.Destination)
}

func Notify(cmd data.Command, tx *sql.Tx, db *sql.DB) string {
    _, err := tx.Exec(
        fmt.Sprintf("insert into notifications (src,dest,created,msg) values(%s, %s, %d, %s)",
                    cmd.Source, cmd.Destination, cmd.Created, cmd.Message))
    if err != nil {
        return fmt.Sprintf("Failed to create notification for %s", cmd.Destination)
    }
    return fmt.Sprintf("Successfully created notification for %s", cmd.Destination)
}

func GetTime(cmd data.Command, tx *sql.Tx, db *sql.DB) string {
    t := time.Now()
    year, month, day = time.Date(t)
    hour := time.Hour(t)
    min := time.Minute(t)
    return fmt.Sprintf("%d/%d/%d-%d:%d", month, day, year % 100, hour, min)
}

func AllReminders(cmd data.Command, tx *sql.Tx, db *sql.DB) string {
    r, e := db.Query(fmt.Sprintf("select src,dest,msg from reminders where date<=%d", cmd.Issue))
    if e != nil {
        return "Could not obtain list of reminders."
    }
    defer r.Close()
    builder := ""
    for r.Next() {
        var src string
        var dest string
        var msg string
        r.Scan(&src, &dest, &msg)
        builder += fmt.Sprintf("<%s> %s, %s\n", src, dest, msg)
    }
    return builder
}

func AllNotifications(cmd data.Command, tx *sql.Tx, db *sql.DB) string {
    r, e := db.Query(fmt.Sprintf("select src,msg from notifications where dest=%s", cmd.Destination))
    if e != nil {
        return "Could not obtain a list of notifications."
    }
    defer r.Close()
    builder := ""
    for r.Next() {
        var src string
        var msg string
        r.Scan(&src, &msg)
        builder += fmt.Sprintf("%s, <%s> %s\n", cmd.Destination, src, msg)
    }
    return builder
}

func RmReminders(cmd data.Command, tx *sql.Tx, db *sql.DB) string {
    tx.Exec(fmt.Sprintf("delete from reminders where date<=%d", cmd.Created))
    return ""
}

func RmNotifications(cmd data.Command, tx *sql.Tx, db *sql.DB) string {
    tx.Exec(fmt.Sprintf("delete from notifications where dest=%s", cmd.Destination))
    return ""
}

const Mapping = {
    "remind"      : Remind,
    "notify"      : Notify,
    "time"        : GetTime,
    "allreminders": AllReminders,
    "allnotifies" : AllNotifications,
    "rmreminders" : RmReminders,
    "rmnotifies"  : RmNotifications
}
