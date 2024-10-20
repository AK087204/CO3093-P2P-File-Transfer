import socket
import json
from urllib.parse import parse_qs
from typing import Dict, List, Optional

class TrackerServer:
    def __init__(self, host: str = 'localhost', port: int = 6969):
        self.host = host
        self.port = port
        self.peers: Dict[str, List[Dict[str, str]]] = {}  # {info_hash: [peer_info, ...]}
        self.tracker_id = "example_tracker_id"

    def start(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind((self.host, self.port))
            s.listen()
            print(f"Tracker server listening on {self.host}:{self.port}")
            while True:
                conn, addr = s.accept()
                with conn:
                    print(f"Connected by {addr}")
                    data = conn.recv(1024).decode('utf-8')
                    response = self.handle_request(data)
                    conn.sendall(response.encode('utf-8'))

    def handle_request(self, request: str) -> str:
        # Parse the request
        params = parse_qs(request.split('\r\n')[-1])
        
        # Extract relevant information
        info_hash = params.get('info_hash', [None])[0]
        peer_id = params.get('peer_id', [None])[0]
        ip = params.get('ip', [None])[0]
        port = params.get('port', [None])[0]
        event = params.get('event', [None])[0]
        downloaded = params.get('downloaded', [None])[0]

        if not all([info_hash, peer_id, ip, port]):
            return self.create_error_response("Missing required parameters")

        # Handle different events
        if event == 'started':
            self.add_peer(info_hash, peer_id, ip, port, downloaded)
        elif event == 'stopped':
            self.remove_peer(info_hash, peer_id)
        elif event == 'completed':
            self.update_peer(info_hash, peer_id, completed=True)

        # Create and return the response
        return self.create_response(info_hash)

    def add_peer(self, info_hash: str, peer_id: str, ip: str, port: str, downloaded: str):
        if info_hash not in self.peers:
            self.peers[info_hash] = []
        self.peers[info_hash].append({
            'peer_id': peer_id,
            'ip': ip,
            'port': port,
            'downloaded': downloaded
        })

    def remove_peer(self, info_hash: str, peer_id: str):
        if info_hash in self.peers:
            self.peers[info_hash] = [p for p in self.peers[info_hash] if p['peer_id'] != peer_id]

    def update_peer(self, info_hash: str, peer_id: str, completed: bool = False):
        if info_hash in self.peers:
            for peer in self.peers[info_hash]:
                if peer['peer_id'] == peer_id:
                    peer['completed'] = completed
                    break

    def create_response(self, info_hash: str) -> str:
        response = {
            'tracker_id': self.tracker_id,
            'peers': self.peers.get(info_hash, [])
        }
        return json.dumps(response)

    def create_error_response(self, reason: str) -> str:
        return json.dumps({'failure reason': reason})

if __name__ == "__main__":
    tracker = TrackerServer()
    tracker.start()
