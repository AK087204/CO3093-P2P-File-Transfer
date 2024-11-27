import urllib.parse
import socket
import urllib.request
import upnpy
import subprocess
import sys
import win32com.client
import pythoncom

TRACKER_PORT = 5050
TRACKER_HOST = '74.178.89.23'
EVENT_STATE = ['STARTED', 'STOPPED', 'COMPLETED']
DEFAULT_PEER_PORT = 6881  # Choose a standar

"""
Class dùng để communicate với server
"""

class AdvancedFirewallManager:
    def __init__(self, port, rule_name="P2P_Transfer"):
        self.port = str(port)
        self.rule_name = rule_name

    def add_firewall_rule(self):
        try:
            # Initialize COM
            pythoncom.CoInitialize()
            
            # Connect to Windows Firewall
            fw = win32com.client.Dispatch("HNetCfg.FwPolicy2")
            
            # Create a new rule
            rule = win32com.client.Dispatch("HNetCfg.FWRule")
            rule.Name = f"{self.rule_name}_in"
            rule.Description = "Allow P2P file transfer incoming connections"
            rule.Protocol = 6  # TCP
            rule.LocalPorts = self.port
            rule.Direction = 1  # Inbound
            rule.Enabled = True
            rule.Action = 1  # Allow
            
            # Add the rule
            fw.Rules.Add(rule)
            
            # Create outbound rule
            rule_out = win32com.client.Dispatch("HNetCfg.FWRule")
            rule_out.Name = f"{self.rule_name}_out"
            rule_out.Description = "Allow P2P file transfer outgoing connections"
            rule_out.Protocol = 6  # TCP
            rule_out.LocalPorts = self.port
            rule_out.Direction = 2  # Outbound
            rule_out.Enabled = True
            rule_out.Action = 1  # Allow
            
            # Add the outbound rule
            fw.Rules.Add(rule_out)
            
            print(f"Successfully added firewall rules for port {self.port}")
            
        except Exception as e:
            print(f"Error adding firewall rules: {e}")
        finally:
            pythoncom.CoUninitialize()

    def remove_firewall_rule(self):
        try:
            # Initialize COM
            pythoncom.CoInitialize()
            
            # Connect to Windows Firewall
            fw = win32com.client.Dispatch("HNetCfg.FwPolicy2")
            
            # Remove both rules
            try:
                fw.Rules.Remove(f"{self.rule_name}_in")
                fw.Rules.Remove(f"{self.rule_name}_out")
                print(f"Successfully removed firewall rules for port {self.port}")
            except:
                print("Rules might have been already removed")
                
        except Exception as e:
            print(f"Error removing firewall rules: {e}")
        finally:
            pythoncom.CoUninitialize()

class PeerServer:
    def __init__(self, peer_id, peer_ip, peer_port, info_hash):
        # Get public IP from a service
        try:
            public_ip = urllib.request.urlopen('https://api.ipify.org').read().decode('utf8')
            print(f"Public IP detected: {public_ip}")
        except:
            public_ip = peer_ip  # Fallback to provided IP
            print(f"Using fallback IP: {public_ip}")
        
        self.peer_ip = public_ip
        self.peer_port = peer_port
        print(f"Initialized PeerServer with IP:{self.peer_ip}, Port:{self.peer_port}")
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

        # Initialize advanced firewall manager
        self.firewall = AdvancedFirewallManager(peer_port)
        
        # Add firewall rules
        try:
            self.firewall.add_firewall_rule()
        except Exception as e:
            print(f"Failed to configure firewall: {e}")

    def __del__(self):
        # Remove firewall rules
        try:
            if hasattr(self, 'firewall'):
                self.firewall.remove_firewall_rule()
        except Exception as e:
            print(f"Failed to remove firewall rules: {e}")
        
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
        print(f"Announcing to tracker - IP:{self.peer_ip}, Port:{self.peer_port}")
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

    def test_connection(self):
        """Test if the port is accessible from outside"""
        try:
            # Try to connect to a port checking service
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            result = sock.connect_ex(('portquiz.net', self.peer_port))
            if result == 0:
                print(f"Port {self.peer_port} appears to be open")
            else:
                print(f"Port {self.peer_port} appears to be closed")
            sock.close()
        except Exception as e:
            print(f"Connection test failed: {e}")