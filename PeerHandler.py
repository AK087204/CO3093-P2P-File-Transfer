import struct
import threading
import time
from enum import IntEnum
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
    def __init__(self, conn, addr, info_hash, peer_id, callback_function):
        """
                Initialize a PeerHandler instance.

                Args:
                    conn: Socket connection to peer
                    addr: Peer address tuple (ip, port)
                    info_hash: Torrent info hash
                    peer_id: Our peer ID
                    callback_function: Callback object for managing pieces
        """

        self.conn = conn
        self.addr = addr
        self.info_hash = info_hash
        self.peer_id = peer_id
        self.callback_function = callback_function

        # State flags
        self.am_choking = True
        self.am_interested = False
        self.peer_choking = True
        self.peer_interested = False

        # Threading control
        self.running = False
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
            # After successful handshake, send interested message
            self.send_interested()

            # Start listening thread
            self.listen_thread = threading.Thread(target=self.listen)
            self.listen_thread.start()

            # Start request thread (will only send requests when unchoked)
            self.request_thread = threading.Thread(target=self.send_requests)
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

            elif message_type == MessageType.INTERESTED:
                self.peer_interested = 1
                print(f"Peer {self.addr} is interested")

            elif message_type == MessageType.NOT_INTERESTED:
                self.peer_interested = 0
                print(f"Peer {self.addr} is not interested")

            elif message_type == MessageType.HAVE:
                piece_index = struct.unpack(">I", payload)[0]
                print(f"Peer {self.addr} has piece {piece_index}")
                if self.bitfield:
                    self.bitfield[piece_index] = 1

            elif message_type == MessageType.BITFIELD:
                self.bitfield = bytearray(payload)
                print(f"Received bitfield from {self.addr}")

            elif message_type == MessageType.PIECE:
                # Handle received piece data
                if len(payload) < 8:
                    return
                index = struct.unpack(">I", payload[0:4])[0]
                begin = struct.unpack(">I", payload[4:8])[0]
                block = payload[8:]
                print(f"Received piece {index} at offset {begin}, length {len(block)}")
                # Call callback to handle the received piece
                if self.callback_function:
                    self.callback_function("piece_received", index, begin, block)

        except Exception as e:
            print(f"Error handling message type {message_type}: {e}")

    def send_requests(self):
        while self.running:
            if not self.peer_choking and self.am_interested:
                try:
                    # Get next piece to request from callback
                    request_info = self.callback_function("get_request")
                    if request_info:
                        index, begin, length = request_info
                        self.request_block(index, begin, length)
                    else:
                        # No more pieces needed, sleep longer
                        time.sleep(1)
                except Exception as e:
                    print(f"Error in send_requests: {e}")
            time.sleep(0.1)

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
        # try:
        #     interested_msg = struct.pack(">I", 1) + struct.pack("B", 2)  # length (1 byte) + message id (2)
        #     self.conn.send(interested_msg)
        #     self.am_interested = 1
        #     print(f"Gửi thông điệp 'interested' đến peer {self.addr}")
        # except Exception as e:
        #     print(f"Gửi thông điệp 'interested' thất bại: {e}")
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

    def send_message(self, message_type, payload=b''):
        """Utility method to send a message with proper length prefix"""
        try:
            message_length = len(payload) + 1  # +1 for message type
            message = struct.pack('>IB', message_length, message_type) + payload
            self.conn.send(message)
        except Exception as e:
            print(f"Error sending message type {message_type}: {e}")

    def request_block(self,index, begin, length):
        """
        Gửi thông điệp 'request' để yêu cầu một block từ peer.
        """
        # try:
        #     index, begin, length = self.callback_function()
        #
        #     request_msg = struct.pack(">I", 13) + struct.pack("B", 6)  # length (13 bytes) + message id (6)
        #     request_msg += struct.pack(">I", index)  # Piece index
        #     request_msg += struct.pack(">I", begin)  # Offset
        #     request_msg += struct.pack(">I", length)  # Requested length
        #
        #     self.conn.send(request_msg)
        #     print(f"Yêu cầu block từ peer {self.addr}: Piece index {index}, offset {begin}, length {length}")
        # except Exception as e:
        #     print(f"Gửi yêu cầu block thất bại: {e}")
        """Send request for a specific block"""
        payload = struct.pack('>III', index, begin, length)
        self.send_message(MessageType.REQUEST, payload)
        print(f"Requested block - index: {index}, begin: {begin}, length: {length}")

        def close(self):
            """Clean shutdown of peer connection"""
            self.running = False
            if self.conn:
                self.conn.close()