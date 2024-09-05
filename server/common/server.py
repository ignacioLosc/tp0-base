import socket
import logging
import signal

from enum import Enum
from common.utils import Bet, store_bets

MESSAGE_DELIMITER = b'\n'
FIELD_DELIMITER = '|'
class Action(str, Enum):
    APUESTA = 'APUESTA'
    FIN_APUESTA = 'FINAPUESTA'
    CONFIRMAR_APUESTA = 'CONFIRMARAPUESTA'

class Protocol:
    def __init__(self, field_delimiter, message_delimiter):
        self._field_delimiter = field_delimiter
        self._message_delimiter = message_delimiter

    def send_message(self, client_sock, msg):
        msg_bytes = bytes(msg) + self._message_delimiter
        bytes_sent = client_sock.send(msg_bytes)
        while bytes_sent != len(msg_bytes) + len(self._message_delimiter):
            bytes_sent += client_sock.send(msg_bytes[:bytes_sent])

    def receive_message(self, client_sock):
        msg = []
        data = client_sock.recv(1024)
        while not data.endswith(self._message_delimiter):
            msg.append(data)
            data = client_sock.recv(1024)
        msg.append(data)
        addr = client_sock.getpeername()
        msg_without_delimiter = msg[:len(self._message_delimiter)]
        logging.info(f'action: receive_message | result: success | ip: {addr[0]} | msg: {msg_without_delimiter}')
        return b"".join((msg_without_delimiter)).rstrip().decode('utf-8')

class Server:
    def __init__(self, port, listen_backlog):
        # Initialize server socket
        self._server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server_socket.bind(('', port))
        self._server_socket.listen(listen_backlog)
        self._signal_received = False
        self._protocol = Protocol(field_delimiter='|', message_delimiter=b'\n')

    def run(self):
        """
        Dummy Server loop

        Server that accept a new connections and establishes a
        communication with a client. After client with communucation
        finishes, servers starts to accept new connections again
        """

        def __sigterm_handler(__signo, __stack_frame):
            logging.info(f'action: receive_signal {signal.Signals(__signo).name} | result: success')
            self._server_socket.close()
            self._signal_received = True
            return
        
        signal.signal(signal.SIGTERM, __sigterm_handler)

        while not self._signal_received:
            client_sock = self.__accept_new_connection()
            if client_sock is None:
                return
            self.__handle_client_connection(client_sock)

    def __save_client_bets(self, bets: list[Bet]):
        for bet in bets:
            logging.info(f'action: apuesta_almacenada | result: success | dni: {bet.document} | numero: {bet.number}')
        store_bets(bets)
    
    def __handle_client_bet(self, client_sock, bet_parts: list[str]):
        bet = Bet(bet_parts[0], bet_parts[1], bet_parts[2], bet_parts[3], bet_parts[4], bet_parts[5])
        self.__save_client_bets([bet])
        self._protocol.send_message(client_sock, bytes(f'{Action.CONFIRMAR_APUESTA}|{bet.document}|{bet.number}', encoding='utf8')) 
    
    def __handle_client_message(self, client_sock, msg):
        # TODO: Add support for batch messages
        msg_parts = msg.split(FIELD_DELIMITER)
        if msg_parts[0] == Action.APUESTA:
            self.__handle_client_bet(client_sock, msg_parts[1:])
        

    def __handle_client_connection(self, client_sock):
        """
        Read message from a specific client socket and closes the socket

        If a problem arises in the communication with the client, the
        client socket will also be closed
        """
        try:
            msg = self._protocol.receive_message(client_sock)
            self.__handle_client_message(client_sock, msg)            
            
        except OSError as e:
            logging.error("action: receive_message | result: fail | error: {e}")
        finally:
            client_sock.close()

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
        return c
