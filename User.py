from datetime import datetime
import os
from info import *
from MetaInfo import MetaInfo
from TorrentUtils import TorrentUtils
from Peer import Peer
import socket

class User:
    def __init__(self, name:str = "Anonymous"):
        self.name = name
        self.peerList = []

    def download(self):
        isTorrent = False
        info_hash = ""

        if isTorrent:
            torrent_file = input("Please input file path: ")
            info_hash = TorrentUtils.get_info_hash_from_file(torrent_file)
        else:
            magnet_link = input("Please input magnet link: ")
            info_hash = TorrentUtils.get_info_hash_from_magnet(magnet_link)

        ip, port = self._get_ip_port()
        peer = Peer(ip, port)



    def share(self):
        magnet_link = self._input()
        return magnet_link

    def _input(self):
        path = input("Nhập vào đường dẫn đến file hoặc directory: ")
        if os.path.isdir(path):
            return self._input_directory(path)
        elif os.path.isfile(path):
            return self._input_file(path)
        elif not os.path.exists(path):
            raise "Invalid path"

    def _input_directory(self, dir_path):
        """
        Cho phép người dùng nhập vào một directory và chuyển nó thành bencode.
        """

        # Lấy các file trong directory và chuyển thành danh sách File
        files = []
        for root, dirs, file_names in os.walk(dir_path):
            for file_name in file_names:
                file_path = os.path.join(root, file_name)
                file_size = os.path.getsize(file_path)
                file_relative_path = os.path.relpath(file_path, dir_path).split(os.sep)
                files.append(File(file_size, file_relative_path))

        # Tạo InfoMultiFile cho directory
        piece_length = 512  # Ví dụ số bytes trong mỗi phần
        pieces = b''  # Giả sử mảng byte trống cho ví dụ
        info = InfoMultiFile(piece_length, pieces, os.path.basename(dir_path), files)

        # Tạo MetaInfo cho torrent file
        meta_info = MetaInfo(info, 'http://localhost:8080', datetime.now(), 'No comment', self.name)
        encoded = meta_info.get_bencode()
        TorrentUtils.create_torrent_file(encoded, 'download.torrent')
        magnet_link = TorrentUtils.make_magnet_from_bencode(encoded)

        return magnet_link


    def _input_file(self, file_path):
        """
        Cho phép người dùng nhập vào một file và chuyển nó thành bencode.
        """

        file_name = os.path.basename(file_path)
        file_size = os.path.getsize(file_path)

        # Tạo InfoSingleFile cho file
        piece_length = 512  # Ví dụ số bytes trong mỗi phần
        pieces = b''  # Giả sử mảng byte trống cho ví dụ
        info = InfoSingleFile(piece_length, pieces, file_name, file_size)

        # Tạo MetaInfo cho torrent file
        meta_info = MetaInfo(info, 'http://localhost:8080', datetime.now(), 'No comment', self.name)
        encoded = meta_info.get_bencode()
        TorrentUtils.create_torrent_file(encoded, 'download.torrent')
        magnet_link = TorrentUtils.make_magnet_from_bencode(encoded)

        return magnet_link

    def _get_ip_port(self):
        """Lấy địa chỉ IP và tìm một cổng trống cho Peer."""
        # Lấy địa chỉ IP của máy người dùng
        hostname = socket.gethostname()
        ip_address = socket.gethostbyname(hostname)

        # Tìm một port trống để dùng
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('', 0))  # Bind tới bất kỳ cổng trống nào (0 là chỉ định hệ thống tự tìm port)
            port = s.getsockname()[1]  # Lấy port đã bind
        return ip_address, port

if __name__ == '__main__':
    user = User()
    magnet_link = user.share()
    print("Magnet link:", magnet_link)
