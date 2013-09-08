package main

import (
    "database/sql"
    "container/list"
    "bytes"
    "log"
    "net"
    "time"
    "flag"
    "fmt"
)

var (
    ip = flag.String("ip", "127.0.0.1", "IP to bind relae server to.")
    port = flag.Int("port", 9001, "Port to bind relae server on.")
    numConns = flag.Int("max", MAX_CONNECTIONS,
                        "Maximum number of interfaces allowed")
    dbName = flag.String("dbfile", DEFAULT_DB_FILE, "Database file to use.")
)

func ReadFromInterface(in *net.TCPConn, req chan Request, res chan string, killed *bool) {
    buffer := make([]byte, 1024)
    quit := []byte(QUIT_MSG)
    for !*killed {
        n, err := in.Read(buffer)
        if bytes.Equal(buffer, quit) || err != nil {
            break
        }
        r := ParseRequest(string(buffer), res)
        req <- r
    }
}

func (w *Worker) StartWorking(req chan Request, killed *bool) {
    go ReadFromInterface(w.Input, w.Requests, w.Responses, killed)
    pending := list.New()
    pending = pending.Init()
    for !*killed {
        select {
        case r := <-w.Requests:
            pending.PushBack(r)
            req <-r
        default:
            break
        }
        for response := pending.Front(); response != nil; {
            select {
            case r := <-(chan string)(response.Value):
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

/* TODO
 * Check to see if a worker has finished and if so, remove it from
 * the workerList
 */
func IssueReminders(rhreq chan Request, workers chan *Worker, conns int32, sleepSec time.Duration, killed *bool) {
    workerList := make([]*Worker, conns)
    var numWorkers int32 = 0
    for !*killed {
        if numWorkers < conns {
            select {
            case worker := <-workers:
                workerList[numWorkers] = worker
                numWorkers += 1
            default:
            }
        }
        time.Sleep(sleepSec)
        current := time.Now().Unix()
        for worker := range workers {
            req := Request{Command{"", "", "allreminders", current, current, ""}, worker.Responses}
            worker.Requests <- req
        }
        req := Request{Command{"", "", "rmreminders", current, current, ""}, nil}
        rhreq <- req
    }
}

func HandleRequests(req chan Request, dbfile, dbdriver string, killed *bool) {
    db, err := sql.Open(dbdriver, dbfile)
    if err != nil {
        *killed = true
        log.Fatal("Cannot access database " + dbfile)
        return
    }
    defer db.Close()
    db.Exec("create table if not exists reminders " +
            "(src text, dest text, created float, date float, msg text)")
    db.Exec("create table if not exists notifications " +
            "(src text, dest text, created float, msg text)")
    tx, _ := db.Begin()
    for !*killed {
        r := <-req
        dfn, err := Mapping[r.Cmd.FunctionName]
        if !err {
            log.Println("No dispatch function for " + r.Cmd.FunctionName)
            continue
        }
        r.Response <- dfn(r.Cmd, tx, db)
    }
    tx.Commit()
}

func ServeInterfaces(laddr *net.TCPAddr, dbfile string, killed *bool) {
    listener, err := net.ListenTCP("tcp", laddr)
    if err != nil {
        *killed = true
        log.Fatal(err)
        return
    }
    rhrequests := make(chan Request)
    workersToSleeperThread := make(chan *Worker)
    go IssueReminders(rhrequests, workersToSleeperThread, int32(*numConns), REMINDER_INTERVAL, killed)
    go HandleRequests(rhrequests, dbfile, "sqlite3", killed)
    for !*killed {
        incoming, err1 := listener.AcceptTCP()
        outgoing, err2 := listener.AcceptTCP()
        if err1 != nil || err2 != nil {
            log.Println("Error establishing a connection from interface.")
        } else {
            worker := &Worker{incoming, outgoing, make(chan Request), make(chan string)}
            workersToSleeperThread <- worker
            go worker.StartWorking(rhrequests, killed)
        }
    }
}

func main() {
    flag.Parse()
    addr := &net.TCPAddr{net.IP(*ip), *port}
    var killswitch *bool
    *killswitch = false
    go ServeInterfaces(addr, *dbName, killswitch)
    fmt.Println("Press enter to tell Relae to stop.")
    fmt.Scanf("")
    *killswitch = true
}
