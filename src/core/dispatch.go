package main

import (
	"database/sql"
	"fmt"
	"time"
)

func Remind(cmd Command, db *sql.DB) string {
	tx, _ := db.Begin()
    _, err := tx.Exec(
		fmt.Sprintf("insert into reminders (src,dest,created,date,msg) values(%s, %s, %d, %d, %s)"),
		cmd.Source, cmd.Destination, cmd.Created, cmd.Issue, cmd.Message)
	if err != nil {
		return fmt.Sprintf("Failed to create reminder for %s", cmd.Destination)
	}
    tx.Commit()
	return fmt.Sprintf("Successfully createed reminder for %s", cmd.Destination)
}

func Notify(cmd Command, db *sql.DB) string {
	tx, _ := db.Begin()
    _, err := tx.Exec(
		fmt.Sprintf("insert into notifications (src,dest,created,msg) values(%s, %s, %d, %s)",
			cmd.Source, cmd.Destination, cmd.Created, cmd.Message))
	if err != nil {
		return fmt.Sprintf("Failed to create notification for %s", cmd.Destination)
	}
    tx.Commit()
	return fmt.Sprintf("Successfully created notification for %s", cmd.Destination)
}

func GetTime(cmd Command, db *sql.DB) string {
	t := time.Now()
	year, month, day := t.Date()
	hour := t.Hour()
	min := t.Minute()
	return fmt.Sprintf("%d/%d/%d-%d:%d", month, day, year%100, hour, min)
}

func AllReminders(cmd Command, db *sql.DB) string {
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

func AllNotifications(cmd Command, db *sql.DB) string {
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

func RmReminders(cmd Command, db *sql.DB) string {
    tx, _ := db.Begin()
	tx.Exec(fmt.Sprintf("delete from reminders where date<=%d", cmd.Created))
	tx.Commit()
    return ""
}

func RmNotifications(cmd Command, db *sql.DB) string {
    tx, _ := db.Begin()
	tx.Exec(fmt.Sprintf("delete from notifications where dest=%s", cmd.Destination))
	tx.Commit()
    return ""
}

type dispatchFn func(Command, *sql.DB) string

var Mapping map[string]dispatchFn = map[string]dispatchFn{
	"remind":       Remind,
	"notify":       Notify,
	"time":         GetTime,
	"allreminders": AllReminders,
	"allnotifies":  AllNotifications,
	"rmreminders":  RmReminders,
	"rmnotifies":   RmNotifications,
}
