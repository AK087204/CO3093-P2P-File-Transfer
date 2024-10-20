import uuid
import urllib.parse
TRACKER_PORT = 5050
TRACKER_HOST = 'localhost'
EVENT_STATE = ['STARTED', 'STOPPED', 'COMPLETED']
import socket
class Peer:
    def __init__(self, peer_ip, peer_port):
        self.peer_id = str(uuid.uuid4())
        self.peer_ip = peer_ip
        self.peer_port = peer_port
        self.uploaded = 0
        self.downloaded = 0
        self.left = 0
        self.compact = 0
        self.no_peer_id = 0
        self.event = EVENT_STATE[0]

    def request(self, info_hash):
        params = {
            'info_hash': info_hash,
            'peer_id': self.peer_id,
            'ip': self.peer_ip,
            'port': self.peer_port,
            'uploaded': str(self.uploaded),
            'downloaded': str(self.downloaded),
            'left': str(self.left),
            'compact': str(self.compact),
            'event': self.event
        }

        query_string = urllib.parse.urlencode(params)
        # Tạo thông điệp GET request
        request = f"GET /announce?{query_string} HTTP/1.1\r\n"
        request += f"Host: {TRACKER_HOST}\r\n"
        request += "Connection: close\r\n\r\n"

        print(request)

        # Mở kết nối TCP tới tracker
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((TRACKER_HOST, TRACKER_PORT))  # Kết nối đến tracker
            s.sendall(request.encode('utf-8'))  # Gửi yêu cầu GET

            # Nhận phản hồi từ tracker
            response = b""
            while True:
                data = s.recv(4096)
                if not data:
                    break
                response += data

        # Trả về phản hồi nhận được (dưới dạng chuỗi)
        return response.decode('utf-8')
