package common

import (
	"bufio"
	"fmt"
	"io"
	"net"
	"os"
	"os/signal"
	"strings"
	"syscall"
	"time"

	"github.com/op/go-logging"
)

const MESSAGE_DELIMITER byte = 10
const FIELD_DELIMITER string = "|"

var log = logging.MustGetLogger("log")

// ClientConfig Configuration used by the client
type ClientConfig struct {
	ID            string
	ServerAddress string
	LoopAmount    int
	LoopPeriod    time.Duration
	NOMBRE        string
	APELLIDO      string
	DOCUMENTO     string
	NACIMIENTO    string
	NUMERO        string
	Protocol      *Protocol
}

type Protocol struct {
	fieldDelimiter   string
	messageDelimiter byte
}

func NewProtocol(fieldDelimiter string, messageDelimiter byte) *Protocol {
	protocol := &Protocol{
		fieldDelimiter,
		messageDelimiter,
	}
	return protocol
}

func (p *Protocol) writeMessage(w io.Writer, message string) error {
	messageLength := len(message)
	bytesWritten, err := fmt.Fprint(w, message)
	for bytesWritten < messageLength {
		newBytesWritten, err := fmt.Fprint(w, message[:bytesWritten])
		if err != nil {
			return err
		}
		bytesWritten += newBytesWritten
	}
	if err != nil {
		return err
	}
	return nil
}

func (p *Protocol) receiveMessage(conn net.Conn) (string, error) {
	msg := make([]byte, 0)
	data := make([]byte, 1024)
	bytesReceived, err := bufio.NewReader(conn).Read(data)
	for data[bytesReceived-1] != MESSAGE_DELIMITER {
		msg = append(msg, data...)
		bytesReceived, err = bufio.NewReader(conn).Read(data)
		if err != nil {
			return "", err
		}
	}
	msg = append(msg, data...)
	if err != nil {
		return "", err
	}
	return string(msg), nil
}

// Client Entity that encapsulates how
type Client struct {
	config ClientConfig
	conn   net.Conn
}

// NewClient Initializes a new client receiving the configuration
// as a parameter
func NewClient(config ClientConfig) *Client {
	client := &Client{
		config: config,
	}
	return client
}

// CreateClientSocket Initializes client socket. In case of
// failure, error is printed in stdout/stderr and exit 1
// is returned
func (c *Client) createClientSocket() error {
	conn, err := net.Dial("tcp", c.config.ServerAddress)
	if err != nil {
		log.Criticalf(
			"action: connect | result: fail | client_id: %v | error: %v",
			c.config.ID,
			err,
		)
	}
	c.conn = conn
	return nil
}

func (c *Client) sendMessage() {
	// Create the connection the server in every loop iteration. Send an
	c.createClientSocket()

	// DONE: Modify the send to avoid short-write
	msg := fmt.Sprintf(
		"%v|%v|%v|%v|%v|%v|%v%c",
		"APUESTA",
		c.config.ID,
		c.config.NOMBRE,
		c.config.APELLIDO,
		c.config.DOCUMENTO,
		c.config.NACIMIENTO,
		c.config.NUMERO,
		MESSAGE_DELIMITER,
	)
	c.config.Protocol.writeMessage(c.conn, msg)

	msg, err := c.config.Protocol.receiveMessage(c.conn)
	//log.Infof("MESSAGE: %v", msg)
	msgParts := strings.Split(msg, FIELD_DELIMITER)
	c.conn.Close()

	if err != nil {
		log.Errorf("action: apuesta_enviada | result: fail | error: %v",
			err,
		)
		return
	}

	log.Infof("action: apuesta_enviada | result: success | dni: %v | numero: %v",
		msgParts[1],
		msgParts[2],
	)

}

// StartClientLoop Send messages to the client until some time threshold is met
func (c *Client) StartClientLoop() {
	signalChannel := make(chan os.Signal, 1)
	signal.Notify(signalChannel, os.Interrupt, syscall.SIGTERM)
	// There is an autoincremental msgID to identify every message sent
	// Messages if the message amount threshold has not been surpassed
	c.sendMessage()
	signalRecv := <-signalChannel
	log.Infof("action: %v | result: success | client_id: %v", signalRecv.String(), c.config.ID)
	c.conn.Close()
	log.Infof("action: close_connection | result: success | client_id: %v", signalRecv.String(), c.config.ID)
}
