import struct
import threading
import time


class PeerHandler:
    def __init__(self, conn, addr, info_hash, peer_id, callback_function):
        self.conn = conn  # Kết nối socket với peer
        self.addr = addr  # Địa chỉ của peer
        self.am_choking = 1
        self.am_interested = 0
        self.peer_choking = 1
        self.peer_interested = 0
        self.info_hash = info_hash  # Hash của torrent để so khớp
        self.peer_id = peer_id  # Peer ID của chính mình
        self.callback_function = callback_function
        self.listen_thread = None
        self.request_thread = None

    def run(self):
        # Thực hiện hai chiều bắt tay (handshake)
        if self.two_way_handshake():
            # Tạo thread lắng nghe các message từ peer
            self.listen_thread = threading.Thread(target=self.listen)
            self.listen_thread.start()

            # Tạo thread khác để gửi các yêu cầu request piece khi cần thiết
            self.request_thread = threading.Thread(target=self.send_requests)
            self.request_thread.start()

    def listen(self):
        while True:
            # Nhận dữ liệu từ peer
            response = self.conn.recv(1024)
            if not response:
                break  # Ngắt kết nối nếu không còn dữ liệu
            self.handle_message(response)  # Xử lý dữ liệu nhận được từ peer

    def handle_message(self, message):
        pass

    def send_requests(self):
        while True:
            # Lấy thông tin về piece cần tải từ callback
            piece_index = self.callback_function()
            if piece_index is not None:
                self.request_block(piece_index)
            # Có thể thêm điều kiện để kiểm tra nếu không còn piece nào cần tải thì dừng gửi yêu cầu
            # Thêm delay hoặc logic khác để tránh việc gửi yêu cầu quá nhiều
            time.sleep(0.5)

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
        try:
            interested_msg = struct.pack(">I", 1) + struct.pack("B", 2)  # length (1 byte) + message id (2)
            self.conn.send(interested_msg)
            self.am_interested = 1
            print(f"Gửi thông điệp 'interested' đến peer {self.addr}")
        except Exception as e:
            print(f"Gửi thông điệp 'interested' thất bại: {e}")

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

    def request_block(self):
        """
        Gửi thông điệp 'request' để yêu cầu một block từ peer.
        """
        try:
            index, begin, length = self.callback_function()

            request_msg = struct.pack(">I", 13) + struct.pack("B", 6)  # length (13 bytes) + message id (6)
            request_msg += struct.pack(">I", index)  # Piece index
            request_msg += struct.pack(">I", begin)  # Offset
            request_msg += struct.pack(">I", length)  # Requested length

            self.conn.send(request_msg)
            print(f"Yêu cầu block từ peer {self.addr}: Piece index {index}, offset {begin}, length {length}")
        except Exception as e:
            print(f"Gửi yêu cầu block thất bại: {e}")