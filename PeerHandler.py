import struct
import threading
import time
from enum import IntEnum
from gc import callbacks


class MessageType(IntEnum):
    CHOKE = 0
    UNCHOKE = 1
    INTERESTED = 2
    NOT_INTERESTED = 3
    HAVE = 4
    BITFIELD = 5
    REQUEST = 6
    PIECE = 7
    CANCEL = 8

class PeerHandler:
    def __init__(self, conn, addr, info_hash, peer_id, callback):
        """
                Initialize a PeerHandler instance.

                Args:
                    conn: Socket connection to peer
                    addr: Peer address tuple (ip, port)
                    info_hash: Torrent info hash
                    peer_id: Our peer ID
                    callback: Callback object for managing pieces
        """

        self.conn = conn
        self.addr = addr
        self.info_hash = info_hash
        self.peer_id = peer_id
        self.callback = callback

        self.client_id = None
        # State flags
        self.am_choking = True
        self.am_interested = False
        self.peer_choking = True
        self.peer_interested = False

        # Threading control
        self.running = True
        self.listen_thread = None
        self.request_thread = None

        # Peer state
        self.bitfield = None
        self.pending_requests = {}  # {(index, begin): request_time}
        self.max_pending_requests = 5
        self.last_message_time = time.time()

        # Statistics
        self.total_downloaded = 0
        self.download_rate = 0
        self.last_download_measurement = time.time()

    def run(self):
        if self.two_way_handshake():

            # Start listening thread
            self.listen_thread = threading.Thread(target=self.listen)
            self.listen_thread.start()

            # Start request thread (will only send requests when unchoked)
            self.request_thread = threading.Thread(target=self.requests)
            self.request_thread.start()

    def listen(self):
        while self.running:
            try:
                # First read the message length (4 bytes)
                length_prefix = self.conn.recv(4)
                if not length_prefix:
                    break

                # Unpack the length
                length = struct.unpack(">I", length_prefix)[0]

                # Keep-alive message
                if length == 0:
                    continue

                # Read the message type
                message_type = struct.unpack("B", self.conn.recv(1))[0]

                # Read the payload (length - 1 because we already read the message type)
                payload = b""
                remaining = length - 1
                while remaining > 0:
                    chunk = self.conn.recv(min(remaining, 16384))
                    if not chunk:
                        break
                    payload += chunk
                    remaining -= len(chunk)

                self.handle_message(message_type, payload)

            except Exception as e:
                print(f"Error in listen loop: {e}")
                break

        self.running = False

    def handle_message(self, message_type, payload):
        try:
            if message_type == MessageType.CHOKE:
                self.peer_choking = 1
                print(f"Peer {self.addr} choked us")

            elif message_type == MessageType.UNCHOKE:
                self.peer_choking = 0
                print(f"Peer {self.addr} unchoked us")
                data = self.callback(self.client_id, "request_piece")
                print(data)
                self.send_request(data['index'], data['begin'], data['length'])

            elif message_type == MessageType.INTERESTED:
                self.peer_interested = 1
                print(f"Peer {self.addr} is interested")
                self.send_unchoke()

            elif message_type == MessageType.NOT_INTERESTED:
                self.peer_interested = 0
                print(f"Peer {self.addr} is not interested")

            elif message_type == MessageType.HAVE:
                piece_index = struct.unpack(">I", payload)[0]
                print(f"Peer {self.addr} has piece {piece_index}")
                if self.bitfield:
                    self.bitfield[piece_index] = 1

            elif message_type == MessageType.BITFIELD:
                bitfield = bytearray(payload)
                data = self.callback(self.client_id, "bitfield_received", {'bitfield':bitfield})
                print(f"Received bitfield from {self.addr}, bitfield: {bitfield}")
                print(data)
                if data['interested']:
                    self.send_interested()

            elif message_type == MessageType.REQUEST:
                print(f"Received request from {self.addr}")

            elif message_type == MessageType.PIECE:
                # Handle received piece data
                if len(payload) < 8:
                    return
                index = struct.unpack(">I", payload[0:4])[0]
                begin = struct.unpack(">I", payload[4:8])[0]
                block = payload[8:]
                print(f"Received piece {index} at offset {begin}, length {len(block)}")
                # Call callback to handle the received piece
                if self.callback:
                    self.callback("piece_received", index, begin, block)

        except Exception as e:
            print(f"Error handling message type {message_type}: {e}")

    def requests(self):
        while self.running:
            self.send_bitfield()
            break


    def two_way_handshake(self):

        # Gửi thông điệp handshake tới peer client
        self.send_handshake()
        # Nhận response từ peer (handshake message)
        response = self.conn.recv(1024)  # Receive the handshake message

        # Phân tích thông điệp handshake nhận được
        if self.parse_handshake(response):
            return True
        else:
            return False

    def parse_handshake(self, response):
        """
        Parse the handshake message from a peer.
        Check the info_hash and return True if valid, False otherwise.
        """
        try:
            print(f"handshake response: {response}")
            # Handshake message format:
            # <pstrlen><pstr><reserved><info_hash><peer_id>
            pstrlen = struct.unpack("B", response[0:1])[0]  # Length of the protocol string
            pstr = response[1:20].decode("utf-8")  # Protocol string (BitTorrent protocol)
            reserved = response[20:28]  # 8 bytes reserved
            received_info_hash = response[28:48]  # 20 bytes info_hash (raw bytes)
            received_peer_id = response[48:68].decode("utf-8")  # 20 bytes peer_id (raw bytes)
            self.client_id = received_peer_id
            # Check protocol string and info_hash (compare raw bytes, no decoding)
            if pstr == "BitTorrent protocol" and received_info_hash == self.info_hash:
                print(f"Handshake received successfully from {self.addr}")
                print(f"Peer ID: {received_peer_id}")
                return True
            else:
                print("Handshake invalid")
                return False
        except Exception as e:
            print(f"Handshake parsing failed: {e}")
            return False

    def send_handshake(self):
        """
        Send handshake message to the peer.
        """
        try:
            pstr = "BitTorrent protocol"
            pstrlen = len(pstr)
            reserved = b'\x00' * 8  # 8 bytes reserved (all zeros)

            # Ensure info_hash and peer_id are bytes (SHA-1 hash is 20 bytes)
            if isinstance(self.info_hash, str):
                raise ValueError("info_hash must be in bytes, not a string.")

            # Ensure info_hash and peer_id are exactly 20 bytes
            info_hash_bytes = self.info_hash if len(self.info_hash) == 20 else None
            if isinstance(self.peer_id, str):
                self.peer_id = self.peer_id.encode('utf-8')

            if info_hash_bytes is None:
                raise ValueError("info_hash must be exactly 20 bytes.")

            # Construct the handshake message:
            # <pstrlen><pstr><reserved><info_hash><peer_id>
            handshake_message = struct.pack(
                f"B{pstrlen}s8s20s20s",
                pstrlen,
                pstr.encode('utf-8'),  # pstr needs to be encoded as text
                reserved,
                info_hash_bytes,
                self.peer_id
            )

            print(f"handshake message: {handshake_message}")
            # Send the handshake message
            self.conn.send(handshake_message)
            print(f"Handshake sent to {self.addr}")
        except Exception as e:
            print(f"Handshake send failed: {e}")

    def send_interested(self):
        """
        Gửi thông điệp 'interested' để báo hiệu rằng mình muốn download dữ liệu từ peer.
        """

        """Send interested message to peer"""
        self.send_message(MessageType.INTERESTED)
        self.am_interested = 1
        print(f"Sent interested message to {self.addr}")

    def listen_for_unchoke(self):
        """
        Lắng nghe và chờ thông điệp 'unchoke' từ peer để bắt đầu yêu cầu dữ liệu.
        """
        try:
            while True:
                message = self.conn.recv(1024)
                if len(message) < 5:
                    continue

                # Phân tích message
                length = struct.unpack(">I", message[:4])[0]
                msg_id = struct.unpack("B", message[4:5])[0]

                if msg_id == 1:  # Unchoke
                    print(f"Nhận thông điệp 'unchoke' từ peer {self.addr}")
                    self.peer_choking = 0
                    break
        except Exception as e:
            print(f"Lắng nghe 'unchoke' thất bại: {e}")

    def send_bitfield(self):
        """Send bitfield message to the peer."""
        data = self.callback(self.peer_id, "request_bitfield")
        bitfield = data['bitfield']
        print(f"My bitfield: {bitfield}")
        self.send_message(MessageType.BITFIELD, payload=bitfield)
        print(f"Sent bitfield message to {self.addr}")

    def send_message(self, message_type, payload=b''):
        """Utility method to send a message with proper length prefix"""
        try:
            # Convert message_type to integer
            if not isinstance(message_type, MessageType):
                raise TypeError(f"Expected MessageType, got {type(message_type)}")

            message_type_int = message_type.value
            message_length = len(payload) + 1  # +1 for message type
            message = struct.pack('>IB', message_length, message_type_int) + payload
            print("Packed message:", message)  # Debug packed message

            self.conn.send(message)
        except Exception as e:
            print(f"Error sending message type {message_type}: {e}")

    def send_request(self,index, begin, length):

        """Send request for a specific block"""
        payload = struct.pack('>III', index, begin, length)
        self.send_message(MessageType.REQUEST, payload)
        print(f"Requested block - index: {index}, begin: {begin}, length: {length}")

    def send_unchoke(self):
        """Send unchoke message to the peer."""
        self.send_message(MessageType.UNCHOKE)
        self.am_choking = False

    def close(self):
        """Clean shutdown of peer connection"""
        self.running = False
        if self.conn:
            self.conn.close()