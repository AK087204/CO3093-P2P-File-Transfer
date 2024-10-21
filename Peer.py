import uuid
import urllib.parse
import threading
import socket
from threading import Thread

from PeerHandler import PeerHandler
from FileManager import FileManager

from PeerServer import PeerServer
EVENT_STATE = ['STARTED', 'STOPPED', 'COMPLETED']

class Peer:
    def __init__(self, peer_ip, peer_port, info_hash):
        self.peer_id = str(uuid.uuid4())
        self.peer_ip = peer_ip
        self.peer_port = peer_port
        self.peer_server = PeerServer(self.peer_id, peer_ip, peer_port, info_hash)
        self.info_hash = info_hash
        self.is_running = False
        self.peer_server_thread = None
        self.file_manager = None
        self.bitfields = {}  # Lưu trữ bitfield từ mỗi peer (peer_id -> bitfield)
        self.piece_frequencies = {}  # Đếm tần suất xuất hiện của mỗi piece
        self.lock = threading.Lock()

    def download(self):
        """
        Hàm sẽ tạo một thread cho việc lắng nghe yêu cầu từ các peer qua hàm start_server
        Sau đó nhận peer list từ Tracker Server
        Với mỗi peer sẽ tạo một thread chạy PeerHandler để communicate
        :return: void
        """

        # Tạo server để lắng nghe và phản hồi yêu cầu từ các peer khác
        self.start_server()
        # Gửi request và nhận về peer list từ tracker server
        response = self.peer_server.announce_request("STARTED")
        self.file_manager = FileManager()

        print('List: \n'.join([":".join(line.split(':')[1:]) for line in response.splitlines()]))

        peers = response.split('\n')

        # Tạo PeerHandler để communicate với các peer khác
        for peer in peers:
            peer_id, ip, port = peer.split(':')
            port = int(port)
            conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            conn.connect((ip, port))
            peer_handler = PeerHandler(conn, (ip, port), self.info_hash, peer_id, self.handle_callback)
            thread = Thread(target=peer_handler.run)
            thread.start()



    def upload(self, file_manager):
        self.file_manager = file_manager
        self.start_server()
        respond = self.peer_server.announce_request("STARTED")
        print(respond)

    def scrape_tracker(self):
        respond = self.peer_server.scrape_request()
        print(respond)

    def handle_callback(self, event_type, data, peer_handler):
        """
        Callback function để xử lý các sự kiện từ PeerHandler
        """
        if event_type == 'bitfield_received':
            peer_id = peer_handler.peer_id
            bitfield = data['bitfield']
            with self.lock:
                # Lưu lại bitfield nhận được từ PeerHandler
                self.bitfields[peer_id] = bitfield
                self.update_piece_frequencies(bitfield)

            # Kiểm tra xem đã có đủ thông tin để tìm ra rarest piece chưa
            if self.has_enough_bitfields():
                rarest_piece = self.get_rarest_piece()
                print(f"Rarest piece: {rarest_piece}")
                peer_handler.request_piece(rarest_piece)  # Yêu cầu tải rarest piece

    def start_server(self):
        """Khởi chạy server để lắng nghe các yêu cầu từ peer khác."""
        if not self.is_running:
            self.is_running = True
            self.peer_server_thread = threading.Thread(target=self.listen)
            self.peer_server_thread.start()

    def listen(self):
        """
        Hàm tạo ra nhiều thread cho các connect từ các peer khác
        :return: void
        """
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.bind(('0.0.0.0', self.peer_port))
        server_socket.listen(5)
        while self.is_running:
            conn, addr = server_socket.accept()
            peer_handler = PeerHandler(conn, addr, self.info_hash, self.peer_id, self.handle_callback)
            thread = threading.Thread(target=peer_handler.run)
            thread.start()

    def has_enough_bitfields(self):
        """
        Kiểm tra xem đã thu thập đủ bitfield từ nhiều peer chưa.
        """
        # Giả sử bạn cần thu thập bitfield từ ít nhất 5 peer
        return len(self.bitfields) >= 5

    def update_piece_frequencies(self, bitfield):
        """
        Cập nhật tần suất xuất hiện của mỗi piece dựa trên bitfield nhận được
        """
        for piece_index, has_piece in enumerate(bitfield):
            if has_piece:
                if piece_index not in self.piece_frequencies:
                    self.piece_frequencies[piece_index] = 0
                self.piece_frequencies[piece_index] += 1

    def get_rarest_piece(self):
        """
        Tìm ra piece hiếm nhất dựa trên tần suất xuất hiện trong các bitfield
        """
        rarest_piece = None
        min_frequency = float('inf')
        for piece_index, frequency in self.piece_frequencies.items():
            if frequency < min_frequency and not self.file_manager.has_piece(piece_index):
                min_frequency = frequency
                rarest_piece = piece_index
        return rarest_piece

