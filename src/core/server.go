package main

import (
    "database/sql"
    "fmt"
    "strings"
    "strconv"
)

const (
    DEFAULT_DB_FILE string = "relae.db"
    DB_DRIVER string = "sqlite3"
    QUIT_MSG string = "##QUIT-COMM##"
    ID_TAKEN string = "##IDNAME-TAKEN##"
    ID_VALID string = "##IDNAME-VALID##"
)

type Command struct {
    Source string
    Destination string
    FunctionName string
    Created int64
    Issue int64
    Message string
}

type Request struct {
    InterfaceName string
    UniqueID int64
    Responses chan string
    Cmd Command
}

var KILLFLAG bool = false

func ParseRequest(iname, msg string, uid int64, resp chan string) Request {
    p := strings.Split(msg)
    i1 := strconv.ParseInt(p[3], 10, 64)
    i2 := strconv.ParseInt(p[4], 10, 64)
    return Request{iname, uid, resp, Command{p[0], p[1], p[2], i1, i2, p[5]}}
}

func CreateIDGenerator(start int64) (func () int64) {
    return func () int64 {
        start += 1
        return start
    }
}

func HandleRequests(dbdriver, dbfilename string, req chan Request) {
    db, err = sql.Open(dbdriver, dbfilename)
    if err != nil {
        log.Fatal(err)
    }
    defer db.Close()
    db.Exec("create table if not exists reminders " +\
            "(src text, dest text, created float, date float, msg text)")
    db.Exec("create table if not exists notifications " +\
            "(src text, dest text, created float, msg text)")
    tx, _ = db.Begin()
    for !KILLFLAG {
        r := <-req
        dispatchFn, err := dispatch.Mapping[r.FunctionName]
        if err != nil {
            log.Println("No dispatch function for " + r.FunctionName)
            continue
        }
        r.Responses <- dispatchFn(r.Cmd, tx)
    }
    tx.Commit()
}

func main() {
    idGen := CreateIDGenerator(0)
    fmt.Println(idGen())
    fmt.Println(idGen())
}
