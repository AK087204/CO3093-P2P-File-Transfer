import uuid
import urllib.parse
import threading
import socket
from PeerHandler import PeerHandler
from FileManager import FileManager
TRACKER_PORT = 5050
TRACKER_HOST = 'localhost'
EVENT_STATE = ['STARTED', 'STOPPED', 'COMPLETED']

class Peer:
    def __init__(self, peer_ip, peer_port, info_hash):
        self.peer_id = str(uuid.uuid4())
        self.peer_ip = peer_ip
        self.peer_port = peer_port
        self.uploaded = 0
        self.downloaded = 0
        self.left = 0
        self.compact = 0
        self.no_peer_id = 0
        self.event = EVENT_STATE[0]
        self.info_hash = info_hash
        self.is_running = False
        self.peer_server_thread = None
        self.file_manager = None


    def download(self):
        """
        Hàm sẽ tạo một thread cho việc lắng nghe yêu cầu từ các peer qua hàm start_server
        Ở main thread sẽ dùng để gửi và nhận request cho Tracker Server
        :return: void
        """

        self.start_server()
        respond = self.announce_request("STARTED")
        self.file_manager = FileManager()

    def share(self, file_manager):
        self.file_manager = file_manager
        self.start_server()
        respond = self.announce_request("STARTED")
        print(respond)

    def scrape_tracker(self):
        respond = self.scrape_request()
        print(respond)

    def start_server(self):
        """Khởi chạy server để lắng nghe các yêu cầu từ peer khác."""
        if not self.is_running:
            self.is_running = True
            self.peer_server_thread = threading.Thread(target=self.peer_server)
            self.peer_server_thread.start()

    def peer_server(self):
        """
        Hàm tạo ra nhiều thread cho các connect từ các peer khác
        :return: void
        """
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.bind(('0.0.0.0', self.peer_port))
        server_socket.listen(5)
        while self.is_running:
            conn, addr = server_socket.accept()
            peer_handler = PeerHandler(conn, addr)
            thread = threading.Thread(target=peer_handler.run)
            thread.start()

    def announce_request(self, event_state):
        self.event = event_state
        params = {
            'info_hash': self.info_hash,
            'peer_id': self.peer_id,
            'port': self.peer_port,
            'uploaded': str(self.uploaded),
            'downloaded': str(self.downloaded),
            'left': str(self.left),
            'compact': str(self.compact),
            'event': self.event,
        }

        query_string = urllib.parse.urlencode(params)
        # Tạo thông điệp GET request
        request = f"GET /announce?{query_string} HTTP/1.1\r\n"
        request += f"Host: {TRACKER_HOST}\r\n"
        request += "Connection: close\r\n\r\n"
        print(request)

        response = self.send_request(request)
        return response

    def scrape_request(self):
        # Mã hóa info_hash
        encoded_info_hash = urllib.parse.quote(self.info_hash)
        request = f"GET /scrape?info_hash={encoded_info_hash} HTTP/1.1\r\nHost: {TRACKER_HOST}\r\n\r\n"

        response = self.send_request(request)
        return response

    def send_request(self, request):
        # Mở kết nối TCP tới tracker
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((TRACKER_HOST, TRACKER_PORT))
            s.sendall(request.encode('utf-8'))
            response = b""
            while True:
                data = s.recv(4096)
                if not data:
                    break
                response += data

        return response.decode('utf-8')
