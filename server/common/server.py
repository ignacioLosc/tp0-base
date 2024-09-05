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
        # logging.info(f'bytes_sent: {bytes_sent}, len(msg_bytes): {len(msg_bytes)}')
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
            msg.append(data)
            data = client_sock.recv(1024)
        msg.append(data)
        addr = client_sock.getpeername()
        # msg_without_delimiter = msg[:len(self._message_delimiter)]
        # logging.info(f'action: receive_message | result: success | ip: {addr[0]} | msg: {msg_without_delimiter}')
        # return b"".join((msg_without_delimiter)).rstrip().decode('utf-8')
        return b"".join((msg)).rstrip().decode('utf-8')

class Server:
    def __init__(self, port, listen_backlog):
        # Initialize server socket
        self._server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server_socket.bind(('', port))
        self._server_socket.listen(listen_backlog)
        self._signal_received = False
        self._protocol = Protocol(field_delimiter='|', message_delimiter=b'\n')
        self._threads: list[threading.Thread] = []
        self._barrier = threading.Barrier(NUMBER_OF_AGENCIES, timeout=5) # NUMBER_OF_AGENCIES
        self._lock = threading.Lock()

    def run(self):
        """
        Dummy Server loop

        Server that accept a new connections and establishes a
        communication with a client. After client with communucation
        finishes, servers starts to accept new connections again
        """

        def __sigterm_handler(__signo, __stack_frame):
            """
            Handle SIGTERM signal so as to have
            a graceful shutdown of the program execution
            """
            logging.info(f'action: receive_signal {signal.Signals(__signo).name} | result: success')
            self._server_socket.close()
            self._signal_received = True
            self._barrier.abort()
            for t in self._threads:
                t.join()
            return
        
        signal.signal(signal.SIGTERM, __sigterm_handler)

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
        # logging.info(f'msg: {msg}')
        msg_parts = msg.split(BET_DELIMITER)
        # logging.info(f'msg_parts: {msg_parts}')
        
        betting_ended = False
        for msg in msg_parts:
            # logging.info(f'msg: {msg}')
            if msg.split(FIELD_DELIMITER)[0] == Action.APUESTA and not betting_ended:
                amount_of_bets[0] += 1
                msg_fields = msg.split(FIELD_DELIMITER)
                self.__handle_client_bet(client_sock, msg_fields[1:])
            elif msg.split(FIELD_DELIMITER)[0] == Action.FIN_APUESTA:
                betting_ended = True
                logging.info(f'action: apuesta_recibida | result: success | cantidad: ${amount_of_bets[0]}')
                #if amount_of_bets > 0:
                self._protocol.send_message(client_sock, f'{Action.CONFIRMAR_APUESTA}|{amount_of_bets[0]}')
                amount_of_bets[0] = 0
            elif msg.split(FIELD_DELIMITER)[0] == Action.GANADORES:
                # Hacer sorteo y devolver ganadores
                # Modificar para cambiar barrera y solo si
                # terminaron las 5 hacer el sorteo
                try:
                    remaining = self._barrier.wait()
                    if remaining == 0:
                        logging.info(f'action: sorteo | result: success')
                    #logging.info(f'GANADORES {msg}')
                    winners_documents = self.__get_winners(msg.split(FIELD_DELIMITER)[1])
                    self._protocol.send_message(client_sock, f'{Action.GANADORES}|{FIELD_DELIMITER.join(winners_documents)}')
                except:
                    return
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
                # logging.info(f'Receiving messages')
                msgs = self._protocol.receive_messages(client_sock)
                # logging.info(f'Messages {msgs.split(MESSAGE_DELIMITER_STR)}')
                for msg in msgs.split(MESSAGE_DELIMITER_STR):
                    self.__handle_client_message(client_sock, msg, amount_of_bets)
            except OSError as e:
                logging.error("action: receive_message | result: fail | error: {e}")
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
        self._threads.append(t)