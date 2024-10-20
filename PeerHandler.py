import struct


class PeerHandler:
    def __init__(self, conn, addr, info_hash, peer_id):
        self.conn = conn  # Kết nối socket với peer
        self.addr = addr  # Địa chỉ của peer
        self.am_choking = 1
        self.am_interested = 0
        self.peer_choking = 1
        self.peer_interested = 0
        self.info_hash = info_hash  # Hash của torrent để so khớp
        self.peer_id = peer_id  # Peer ID của chính mình

    def run(self):
        self.two_way_handshake()


    def two_way_handshake(self):

        # Gửi thông điệp handshake tới peer client
        self.send_handshake()
        # Nhận response từ peer (handshake message)
        response = self.conn.recv(1024)  # Receive the handshake message

        # Phân tích thông điệp handshake nhận được
        if self.parse_handshake(response):

            # Sau khi handshake thành công, gửi thông điệp 'interested'
            self.send_interested()

            # Chờ peer gửi lại thông điệp 'unchoke' để tiếp tục
            self.listen_for_unchoke()

        else:
            self.conn.close()

    def parse_handshake(self, response):
        """
        Phân tích thông điệp handshake từ peer.
        Kiểm tra info_hash và trả về True nếu hợp lệ, False nếu không.
        """
        try:
            # Thông điệp handshake có format:
            # <pstrlen><pstr><reserved><info_hash><peer_id>
            pstrlen = struct.unpack("B", response[0:1])[0]  # Độ dài của chuỗi giao thức
            pstr = response[1:20].decode("utf-8")  # Chuỗi giao thức (BitTorrent protocol)
            reserved = response[20:28]  # 8 bytes reserved
            received_info_hash = response[28:48]  # 20 bytes info_hash
            received_peer_id = response[48:68]  # 20 bytes peer_id

            # Kiểm tra chuỗi giao thức và info_hash
            if pstr == "BitTorrent protocol" and received_info_hash == self.info_hash:
                print(f"Handshake nhận thành công từ {self.addr}")
                print(f"Peer ID: {received_peer_id}")
                return True
            else:
                print("Handshake không hợp lệ")
                return False
        except Exception as e:
            print(f"Phân tích handshake thất bại: {e}")
            return False

    def send_handshake(self):
        """
        Gửi thông điệp handshake đến peer.
        """
        try:
            pstr = "BitTorrent protocol"
            pstrlen = len(pstr)
            reserved = b'\x00' * 8  # 8 bytes reserved (all zeros)

            # Định dạng thông điệp handshake:
            # <pstrlen><pstr><reserved><info_hash><peer_id>
            handshake_message = struct.pack(
                f"B{pstrlen}s8s20s20s",
                pstrlen,
                pstr.encode('utf-8'),
                reserved,
                self.info_hash,
                self.peer_id.encode('utf-8')
            )

            # Gửi thông điệp handshake
            self.conn.send(handshake_message)
            print(f"Handshake gửi đến {self.addr}")
        except Exception as e:
            print(f"Gửi handshake thất bại: {e}")

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
            index = 0  # Index của piece cần download
            begin = 0  # Offset trong piece
            length = 16384  # Độ dài block (16KB)

            request_msg = struct.pack(">I", 13) + struct.pack("B", 6)  # length (13 bytes) + message id (6)
            request_msg += struct.pack(">I", index)  # Piece index
            request_msg += struct.pack(">I", begin)  # Offset
            request_msg += struct.pack(">I", length)  # Requested length

            self.conn.send(request_msg)
            print(f"Yêu cầu block từ peer {self.addr}: Piece index {index}, offset {begin}, length {length}")
        except Exception as e:
            print(f"Gửi yêu cầu block thất bại: {e}")