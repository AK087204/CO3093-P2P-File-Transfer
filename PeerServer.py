import urllib.parse
import socket
import urllib.request
import upnpy
TRACKER_PORT = 5050
TRACKER_HOST = '74.178.89.23'
EVENT_STATE = ['STARTED', 'STOPPED', 'COMPLETED']

"""
Class dùng để communicate với server
"""

class PeerServer:
    def __init__(self, peer_id, peer_ip, peer_port, info_hash):
        # Get public IP from a service
        try:
            public_ip = urllib.request.urlopen('https://api.ipify.org').read().decode('utf8')
        except:
            public_ip = peer_ip  # Fallback to provided IP
        
        self.peer_ip = public_ip
        self.peer_port = peer_port
        self.info_hash = info_hash
        self.is_running = False
        self.peer_id = peer_id
        self.peer_ip = peer_ip
        self.peer_port = peer_port
        self.uploaded = 0
        self.downloaded = 0
        self.left = 0
        self.compact = 0
        self.no_peer_id = 0
        self.event = EVENT_STATE[0]

        # Setup UPnP
        try:
            self.upnp = upnpy.UPnP()
            # Discover UPnP devices on the network
            self.upnp.discover()
            # Get the first IGD (Internet Gateway Device)
            self.igd = self.upnp.get_igd()
            # Add port mapping
            self.igd.get_WANIPConn1().AddPortMapping(
                NewRemoteHost='',
                NewExternalPort=peer_port,
                NewProtocol='TCP',
                NewInternalPort=peer_port,
                NewInternalClient=peer_ip,
                NewEnabled=1,
                NewPortMappingDescription='BitTorrent Peer',
                NewLeaseDuration=0
            )
            print(f"Successfully mapped port {peer_port} using UPnP")
        except Exception as e:
            print(f"Failed to setup UPnP: {e}")
            self.igd = None

    def __del__(self):
        # Clean up port mapping when object is destroyed
        if hasattr(self, 'igd') and self.igd:
            try:
                self.igd.get_WANIPConn1().DeletePortMapping(
                    NewRemoteHost='',
                    NewExternalPort=self.peer_port,
                    NewProtocol='TCP'
                )
                print(f"Successfully removed port mapping for {self.peer_port}")
            except Exception as e:
                print(f"Failed to remove port mapping: {e}")

    def announce_request(self, event_state):
        self.event = event_state
        print(f"Announcing to tracker with port: {self.peer_port}")
        params = {
            'info_hash': self.info_hash,
            'peer_id': self.peer_id,
            'ip': self.peer_ip,
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

        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.connect((TRACKER_HOST, TRACKER_PORT))
        server_socket.sendall(request.encode('utf-8'))
        response = b""
        while True:
            data = server_socket.recv(4096)
            if not data:
                break
            response += data

        return response.decode('utf-8')