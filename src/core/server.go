package main

import (
    "database/sql"
    "container/list"
    "log"
    "net"
    "time"
    "flag"
    "dispatch"
    "data"
)

var (
    ip = flag.String("ip", "127.0.0.1", "IP to bind relae server to.")
    port = flag.Int("port", 9001, "Port to bind relae server on.")
    numConns = flag.Int("maxconnections", data.MAX_CONNECTIONS,
                        "Maximum number of interfaces allowed")
    dbName = flag.String("dbfile", data.DEFAULT_DB_FILE, "Database file to use.")
)

func ReadFromInterface(in *net.TCPConn, req chan data.Request, res chan string, killed *bool) {
    buffer := make([]byte, 1024)
    quit := string(buffer)
    for !*killed {
        n, err := in.Read(buffer)
        if bytes.Equal(buffer, quit) || err != nil {
            break
        }
        r := data.ParseRequest.Request(string(bytes), res)
        req <- r
    }
}

func (w *data.Worker) StartWorking(req chan data.Request, killed *bool) {
    go ReadFromInterface(w.Input, w.data.Requests, w.Responses, killed)
    pending := list.New()
    pending = pending.Init()
    for !*killed {
        select {
        case r := <-w.data.Requests:
            pending.PushBack(r)
            req <-r
        default:
            break
        }
        for response := pending.Front(); response != nil; {
            select {
            case r := <-response:
                w.Output.Write([]byte(r))
                rcopy := response
                response = response.Next()
                pending.Remove(rcopy)
            default:
                response = response.Next()
            }
        }
    }
}

func IssueReminders(rhreq chan data.Request, workers chan *data.Worker, sleepSec time.Duration, killed *bool) {
    workers := make([]*data.Worker, data.MAX_CONNECTIONS)
    numdata.Workers := 0
    for !*killed {
        select {
        case worker := <-workers:
            workers[numdata.Workers] = worker
            numdata.Workers += 1
        default:
        }
        time.Sleep(sleepSec)
        for worker := range workers {
            current := time.Now.Unix()
            req := data.Request{data.Command{"", "", "allreminders", current, current, ""}, worker.Responses}
            worker.data.Requests <- req
        }
        req := data.Request{data.Command{"", "", "rmreminders", current, current, ""}, nil}
        rhreq <- req
    }
}

func Handledata.Requests(req chan data.Request, dbfile, dbdriver string, killed *bool) {
    db, err = sql.Open(dbdriver, dbfile)
    if err != nil {
        *killed = true
        log.Fatal("Cannot access database " + dbfile)
        return
    }
    defer db.Close()
    db.Exec("create table if not exists reminders " +\
            "(src text, dest text, created float, date float, msg text)")
    db.Exec("create table if not exists notifications " +\
            "(src text, dest text, created float, msg text)")
    tx, _ = db.Begin()
    for !*killed {
        r := <-req
        dfn, err := dispatch.Mapping[r.FunctionName]
        if err != nil {
            log.Println("No dispatch function for " + r.FunctionName)
            continue
        }
        r.Responses <- dfn(r.Cmd, tx)
    }
    tx.Commit()
}

func ServeInterfaces(laddr TCPAddr, dbfile string, killed *bool) {
    listener, err := net.ListenTCP("tcp", laddr)
    if err != nil {
        *killed = true
        log.Fatal(err)
        return
    }
    rhrequests := make(chan data.Request)
    workersToSleeperThread := make(chan *data.Worker)
    go IssueReminders(rhrequests, workersToSleeperThread, data.REMINDER_INTERVAL, killed)
    go Handledata.Requests(rhrequests, dbfile, "sqlite3", killed)
    for !*killed {
        incoming, err1 := listener.AcceptTCP()
        outgoing, err2 := listener.AcceptTCP()
        if err1 != nil || err2 != nil {
            log.Println("Error establishing a connection from interface.")
        } else {
            worker := &data.Worker{incoming, outgoing, make(chan data.Request), make(chan string)}
            workersToSleeperThread <- worker
            go worker.StartWorking(rhrequests, killed)
        }
    }
}

func main() {
    flag.Parse()
    addr := net.TCPAddr{net.IP(*ip), port, ""}
    var killswitch *bool = 0
    go ServeInterfaces(addr, dbfile, killswitch)
    fmt.Println("Press enter to tell Relae to stop.")
    fmt.Scanf("")
    *killed = true
}
