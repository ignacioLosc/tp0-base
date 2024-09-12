package common

import (
	"archive/zip"
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
const BET_DELIMITER string = ";"
const MAX_PACKET_SIZE int = 8000
const APUESTA string = "APUESTA"
const FIN_APUESTA string = "FINAPUESTA"
const GANADORES string = "GANADORES"

var log = logging.MustGetLogger("log")

type Bet struct {
	agency    string
	firstName string
	lastName  string
	document  string
	birthdate string
	number    string
}

// ClientConfig Configuration used by the client
type ClientConfig struct {
	ID             string
	ServerAddress  string
	LoopAmount     int
	LoopPeriod     time.Duration
	BatchMaxAmount int
	NOMBRE         string
	APELLIDO       string
	DOCUMENTO      string
	NACIMIENTO     string
	NUMERO         string
	Protocol       *Protocol
	DataPath       string
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
	if err != nil {
		return err
	}
	for bytesWritten < messageLength {
		newBytesWritten, err := fmt.Fprint(w, message[:bytesWritten])
		if err != nil {
			return err
		}
		bytesWritten += newBytesWritten
	}
	return nil
}

func (p *Protocol) receiveMessage(conn net.Conn) (string, error) {
	msg := make([]byte, 0)
	data := make([]byte, 1024)
	bytesReceived, err := bufio.NewReader(conn).Read(data)
	if err != nil {
		return "", err
	}
	for data[bytesReceived-1] != MESSAGE_DELIMITER {
		msg = append(msg, data...)
		bytesReceived, err = bufio.NewReader(conn).Read(data)
		if err != nil {
			return "", err
		}
	}
	msg = append(msg, data[:bytesReceived-1]...)
	if err != nil {
		return "", err
	}
	return string(msg), nil
}

func (p *Protocol) formatBets(bets []Bet) (string, error) {
	formattedBets := ""
	if len(bets) == 0 {
		return formattedBets, nil
	}
	for idx, bet := range bets {
		formattedBets += APUESTA + FIELD_DELIMITER + bet.agency + FIELD_DELIMITER + bet.firstName + FIELD_DELIMITER + bet.lastName + FIELD_DELIMITER + bet.document + FIELD_DELIMITER + bet.birthdate + FIELD_DELIMITER + bet.number
		if idx != len(bets)-1 {
			formattedBets += BET_DELIMITER
		}
	}
	return formattedBets, nil
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
		return err
	}
	c.conn = conn
	return nil
}

func (c *Client) sendAndReceiveMessage(msg string) error {
	err := c.config.Protocol.writeMessage(c.conn, msg)

	if err != nil {
		log.Errorf("action: apuesta_enviada | result: fail | error: %v",
			err,
		)
		return err
	}

	msg, err = c.config.Protocol.receiveMessage(c.conn)
	msgParts := strings.Split(msg, FIELD_DELIMITER)

	if err != nil {
		log.Errorf("action: apuesta_enviada | result: fail | error: %v",
			err,
		)
		return err
	}
	if msgParts[0] == GANADORES {
		cantGanadores := 0
		if len(msgParts[1]) > 0 {
			cantGanadores = len(strings.Split(msgParts[1], FIELD_DELIMITER))
		}
		log.Infof("action: consulta_ganadores | result: success | cant_ganadores: %v",
			cantGanadores,
		)

	} else {
		log.Infof("action: apuesta_enviada | result: success | cantidad: %v",
			msgParts[1],
		)
	}
	return nil
}

func (c *Client) waitForWinners() {
	receivedResult := false
	for !receivedResult {
		msg, err := c.config.Protocol.receiveMessage(c.conn)
		msgParts := strings.Split(msg, FIELD_DELIMITER)

		if err != nil {
			log.Errorf("action: consulta_ganadores | result: fail | error: %v",
				err,
			)
			return
		}
		if msgParts[0] == GANADORES {
			receivedResult = true
			cantGanadores := 0
			if len(msgParts[1]) > 0 {
				cantGanadores = len(strings.Split(msgParts[1], FIELD_DELIMITER))
			}
			log.Infof("action: consulta_ganadores | result: success | cant_ganadores: %v",
				cantGanadores,
			)

		}
	}
}

func (c *Client) getBets(fileScanner *bufio.Scanner, currPacketSize *int) ([]Bet, error) {
	if c.config.BatchMaxAmount == 0 {
		return nil, fmt.Errorf("cant send 0 bets")
	}
	bets := make([]Bet, 0)

	for i := 0; i < c.config.BatchMaxAmount; i++ {
		canScan := fileScanner.Scan()
		if !canScan {
			// return bets, nil
			return bets, fmt.Errorf("no more bets to read")
		} else {
			betCsv := fileScanner.Text()
			*currPacketSize += len(betCsv)
			if *currPacketSize > MAX_PACKET_SIZE {
				break
			}
			betFields := strings.Split(betCsv, ",")
			bets = append(bets, Bet{c.config.ID, betFields[0], betFields[1], betFields[2], betFields[3], betFields[4]})
		}
	}
	return bets, nil
}

func (c *Client) makeBets(agency_files []*zip.File) error {
	signalChannel := make(chan os.Signal, 1)
	signal.Notify(signalChannel, os.Interrupt, syscall.SIGTERM)

	currPacketSize := 0
	lastBet := false
	for _, agency_file := range agency_files {
		file, err := agency_file.Open()
		if err != nil {
			log.Infof("COULDNT OPEN FILE %v", err.Error())
			return err
		}
		fileScanner := bufio.NewScanner(file)
		fileScanner.Split(bufio.ScanLines)
		for {
			select {
			case signalRecv := <-signalChannel:
				log.Infof("action: %v | result: success | client_id: %v", signalRecv.String(), c.config.ID)
				file.Close()
				return nil
			default:
			}
			bets, err := c.getBets(fileScanner, &currPacketSize)
			if err != nil {
				if len(bets) == 0 {
					return err
				} else {
					lastBet = true
				}
			}

			formattedBets, err := c.config.Protocol.formatBets(bets)
			if err != nil || len(formattedBets) == 0 {
				break
			}
			currPacketSize = 0
			if lastBet {
				message := formattedBets + BET_DELIMITER + FIN_APUESTA + BET_DELIMITER + GANADORES + FIELD_DELIMITER + c.config.ID
				err := c.sendAndReceiveMessage(fmt.Sprintf("%v%c", message, MESSAGE_DELIMITER))
				if err != nil {
					return err
				}
				c.waitForWinners()
				break
			} else {
				err := c.sendAndReceiveMessage(fmt.Sprintf("%v%c", formattedBets+BET_DELIMITER+FIN_APUESTA, MESSAGE_DELIMITER))
				if err != nil {
					return err
				}
			}
		}
		file.Close()
	}
	return nil
}

func (c *Client) getAllAgencyFiles(dataset *zip.ReadCloser) []*zip.File {
	agency_files := make([]*zip.File, 0)
	for _, f := range dataset.File {
		if strings.HasPrefix(f.Name, fmt.Sprintf("agency-%v", c.config.ID)) {
			agency_files = append(agency_files, f)
		}
	}
	return agency_files
}

// StartClientLoop Send messages to the client until some time threshold is met
func (c *Client) StartClientLoop() {
	dataset, err := zip.OpenReader("dataset.zip")
	if err != nil {
		log.Infof("action: open_dataset | result: fail %v", err.Error())
	}

	agency_files := c.getAllAgencyFiles(dataset)
	if len(agency_files) != 0 {
		log.Infof("agency_files_last_name: %v", agency_files[len(agency_files)-1].Name)
		err = c.createClientSocket()
		if err != nil {
			dataset.Close()
			log.Infof("action: close_connection | result: success | client_id: %v", c.config.ID)
			return
		}
		err = c.makeBets(agency_files)
		if err != nil {
			dataset.Close()
			log.Infof("action: end_bets | result: success | client_id: %v", c.config.ID)
			log.Infof("action: close_connection | result: success | client_id: %v", c.config.ID)
			return
		}
	}

	c.conn.Close()
	dataset.Close()
	log.Infof("action: close_connection | result: success | client_id: %v", c.config.ID)
}
