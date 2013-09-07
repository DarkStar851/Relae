import (
    "strings"
    "strconv"
    "time"
    "net"
)

const (
    DEFAULT_DB_FILE string = "relae.db"
    DB_DRIVER string = "sqlite3"
    QUIT_MSG string = "##QUIT-COMM##"
    ID_TAKEN string = "##IDNAME-TAKEN##"
    ID_VALID string = "##IDNAME-VALID##"
    MAX_CONNECTIONS int32 = 10
    REMINDE_INTERVAL time.DURATION = 60
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
    Cmd Command
    Response chan string
}

type Worker struct {
    Input *net.TCPConn
    Output *net.TCPConn
    Requests chan Request
    Responses chan string
}

func ParseRequest(msg string, res chan string) Request {
    p := strings.Split(msg)
    i1 := strconv.ParseInt(p[3], 10, 64)
    i2 := strconv.ParseInt(p[4], 10, 64)
    return Request{Command{p[0], p[1], p[2], i1, i2, p[5]}, res}
}
