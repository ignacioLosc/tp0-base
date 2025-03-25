import socket
import logging
import signal

from enum import Enum
import threading
from common.utils import Bet, has_won, load_bets, store_bets

MESSAGE_DELIMITER = b'\n'
MESSAGE_DELIMITER_STR = '\n'
FIELD_DELIMITER = '|'
BET_DELIMITER = ';'
NUMBER_OF_AGENCIES = 5
EMPTY_BYTE_SOCKET_CLOSED = b''

class Action(str, Enum):
    APUESTA = 'APUESTA'
    FIN_APUESTA = 'FINAPUESTA'
    CONFIRMAR_APUESTA = 'CONFIRMARAPUESTA'
    GANADORES = 'GANADORES'

class Protocol:
    def __init__(self, field_delimiter, message_delimiter):
        self._field_delimiter = field_delimiter
        self._message_delimiter = message_delimiter

    def send_message(self, client_sock, msg):
        """
        Sends message to socket.
        Avoids short write error
        """
        msg_bytes = bytes(msg, encoding='utf8') + self._message_delimiter
        bytes_sent = client_sock.send(msg_bytes)
        while bytes_sent != len(msg_bytes):
            bytes_sent += client_sock.send(msg_bytes[:bytes_sent])

    def receive_messages(self, client_sock):
        """
        Receives message from socket.
        Avoids short read error
        """
        msg = []
        data = client_sock.recv(1024)
        while not data.endswith(self._message_delimiter):
            if data == EMPTY_BYTE_SOCKET_CLOSED:
                raise Exception("Error receiving message from client")
            msg.append(data)
            data = client_sock.recv(1024)
        msg.append(data)
        addr = client_sock.getpeername()
        return b"".join((msg)).rstrip().decode('utf-8')

class Server:
    def __init__(self, port, listen_backlog):
        # Initialize server socket
        self._server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server_socket.bind(('', port))
        self._server_socket.listen(listen_backlog)
        self._signal_received = False
        self._protocol = Protocol(field_delimiter='|', message_delimiter=b'\n')
        self._threads: list[(threading.Thread, socket.socket)] = []
        self._barrier = threading.Barrier(NUMBER_OF_AGENCIES, timeout=5)
        self._lock = threading.Lock()
        signal.signal(signal.SIGTERM, self.__sigterm_handler)

    def __sigterm_handler(self, __signo, __stack_frame):
        """
        Handle SIGTERM signal so as to have
        a graceful shutdown of the program execution
        """
        logging.info(f'action: receive_signal {signal.Signals(__signo).name} | result: success')
        self._server_socket.close()
        self._signal_received = True
        self._barrier.abort()
        for _, c in self._threads:
            try:
                c.close()
                logging.info(f'action: close_client_connection | result: success')
            except:
                logging.error(f'action: close_client_connection | result: fail')
        for t, _ in self._threads:
            t.join()
        logging.info(f'action: exit | result: success')
        return
    
    def run(self):
        """
        Dummy Server loop

        Server that accept a new connections and establishes a
        communication with a client. After client with communucation
        finishes, servers starts to accept new connections again
        """

        while not self._signal_received:
            self.__accept_new_connection()
            

    def __save_client_bets(self, bets: list[Bet]):
        for bet in bets:
            logging.info(f'action: apuesta_almacenada | result: success | dni: {bet.document} | numero: {bet.number}')
        with self._lock:
            store_bets(bets)
    
    def __handle_client_bet(self, client_sock, bet_parts: list[str]):
        bet = Bet(bet_parts[0], bet_parts[1], bet_parts[2], bet_parts[3], bet_parts[4], bet_parts[5])
        self.__save_client_bets([bet])
    
    def __get_winners(self, agency):
        winners_documents = []
        with self._lock:
            list_of_bets = load_bets()
            for bet in list_of_bets:
                if bet.agency == int(agency) and has_won(bet):
                    winners_documents.append(bet.document)
        return winners_documents
    
    def __handle_client_message(self, client_sock, msg, amount_of_bets):
        """
        Handle every possible client message
        """
        msg_parts = msg.split(BET_DELIMITER)
        
        betting_ended = False
        for msg in msg_parts:
            if msg.split(FIELD_DELIMITER)[0] == Action.APUESTA and not betting_ended:
                amount_of_bets[0] += 1
                msg_fields = msg.split(FIELD_DELIMITER)
                self.__handle_client_bet(client_sock, msg_fields[1:])
            elif msg.split(FIELD_DELIMITER)[0] == Action.FIN_APUESTA:
                betting_ended = True
                logging.info(f'action: apuesta_recibida | result: success | cantidad: {amount_of_bets[0]}')
                # Envia una vez por batch
                self._protocol.send_message(client_sock, f'{Action.CONFIRMAR_APUESTA}|1|2')
                amount_of_bets[0] = 0
            elif msg.split(FIELD_DELIMITER)[0] == Action.GANADORES:
                self._protocol.send_message(client_sock, f'{Action.GANADORES}|1|2')
            else:
                logging.info(f'UNHANDLED MESSAGE: {msg}, {msg.split(FIELD_DELIMITER)[0]}')
        
        

    def __handle_client_connection(self, client_sock):
        """
        Read message from a specific client socket and closes the socket

        If a problem arises in the communication with the client, the
        client socket will also be closed
        """
        amount_of_bets = [0]
        while True:
            try:
                msgs = self._protocol.receive_messages(client_sock)
                for msg in msgs.split(MESSAGE_DELIMITER_STR):
                    self.__handle_client_message(client_sock, msg, amount_of_bets)
            except Exception as e:
                if not self._signal_received:
                    logging.error(f'action: client_closed | result: success')
                    client_sock.close()
                break

    def __accept_new_connection(self):
        """
        Accept new connections

        Function blocks until a connection to a client is made.
        Then connection created is printed and returned
        """

        # Connection arrived
        logging.info('action: accept_connections | result: in_progress')
        try:
            c, addr = self._server_socket.accept()
        except:
            return None
        logging.info(f'action: accept_connections | result: success | ip: {addr[0]}')
        if c is None:
            return
        t = threading.Thread(target=self.__handle_client_connection, args=[c])
        t.start()
        self._threads.append((t,c))