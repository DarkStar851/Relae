package main

import (
	"net"
	"strconv"
	"strings"
	"time"
)

const (
	DEFAULT_DB_FILE   string        = "relae.db"
	DB_DRIVER         string        = "sqlite3"
	QUIT_MSG          string        = "##QUIT-COMM##"
	ID_TAKEN          string        = "##IDNAME-TAKEN##"
	ID_VALID          string        = "##IDNAME-VALID##"
    DEFAULT_ADDRESS   string        = "127.0.0.1"
    DEFAULT_PORT      int           = 9001
	MAX_CONNECTIONS   int           = 10
	REMINDER_INTERVAL time.Duration = 60
)

type Command struct {
	Source       string
	Destination  string
	FunctionName string
	Created      int64
	Issue        int64
	Message      string
}

type Request struct {
	Cmd      Command
	Response chan string
}

type Worker struct {
	Input     *net.TCPConn
	Output    *net.TCPConn
	Requests  chan Request
	Responses chan string
}

func ParseRequest(msg string, res chan string) Request {
	p := strings.Split(msg, "@")
	i1, e1 := strconv.ParseInt(p[3], 10, 64)
	i2, e2 := strconv.ParseInt(p[4], 10, 64)
	current := time.Now().Unix()
	if e1 != nil {
		i1 = current
	}
	if e2 != nil {
		i2 = current
	}
	return Request{Command{p[0], p[1], p[2], i1, i2, p[5]}, res}
}
