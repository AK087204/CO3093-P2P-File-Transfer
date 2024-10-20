

class PeerHandler:
    def __init__(self, conn, addr):
        self.conn = conn
        self.addr = addr

    def run(self):
        response = self.conn.receive(1024)
        if response.startswith('GET'):
            self.conn.send(self.addr)
        else:
            pass

