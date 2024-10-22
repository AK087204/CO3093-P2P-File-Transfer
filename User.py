from datetime import datetime
import os

from FileManager import FileManager

from FileManager import FileManager
from info import *
from MetaInfo import MetaInfo
from TorrentUtils import TorrentUtils
from Peer import Peer
import socket

class User:
    def __init__(self, userId, name:str = "Anonymous"):
        self.name = name
        self.peerList = []
        self.userId = userId

    def download(self):
        isTorrent = False

        if isTorrent:
            torrent_file = input("Please input file path: ")
            info_hash = TorrentUtils.get_info_hash_from_file(torrent_file)
        else:
            magnet_link = input("Please input magnet link: ")
            info_hash = TorrentUtils.get_info_hash_from_magnet(magnet_link)

        ip, port = self._get_ip_port()
        peer = Peer(ip, port, info_hash)
        self.peerList.append(peer.peer_id)
        peer.download()



    def share(self):
        path = input("Nhập vào đường dẫn đến file hoặc directory: ")
        file_manager = FileManager()
        file_manager.split_file(path)

        if os.path.isdir(path):
            info_hash, magnet_link = self._input_directory(path, file_manager)
        elif os.path.isfile(path):
            info_hash, magnet_link = self._input_file(path, file_manager)
        else:
            raise "Invalid path"

        print(f"Magnet link: {magnet_link}")

        ip, port = self._get_ip_port()
        peer = Peer(ip, port, info_hash)
        self.peerList.append(peer.peer_id)

        peer.upload(file_manager)


    def scrape_tracker(self):
        isTorrent = False

        if isTorrent:
            torrent_file = input("Please input file path: ")
            info_hash = TorrentUtils.get_info_hash_from_file(torrent_file)
        else:
            magnet_link = input("Please input magnet link: ")
            info_hash = TorrentUtils.get_info_hash_from_magnet(magnet_link)

        ip, port = self._get_ip_port()
        peer = Peer(ip, port, info_hash)
        self.peerList.append(peer.peer_id)
        peer.scrape_tracker()


    def _input_directory(self, dir_path, file_manager):
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
        piece_length = file_manager.get_piece_length()  # Ví dụ số bytes trong mỗi phần
        pieces = file_manager.get_pieces_code()  # Giả sử mảng byte trống cho ví dụ
        info = InfoMultiFile(piece_length, pieces, os.path.basename(dir_path), files)

        # Tạo MetaInfo cho torrent file
        meta_info = MetaInfo(info, 'http://localhost:5050', datetime.now(), 'No comment', self.name)
        encoded = meta_info.get_bencode()
        TorrentUtils.create_torrent_file(encoded, 'download.torrent')
        magnet_link = TorrentUtils.make_magnet_from_bencode(encoded)

        info_hash = TorrentUtils.get_info_hash_from_magnet(magnet_link)
        return info_hash, magnet_link


    def _input_file(self, file_path, file_manager):
        """
        Cho phép người dùng nhập vào một file và chuyển nó thành bencode.
        """
        file_name = os.path.basename(file_path)
        file_size = os.path.getsize(file_path)

        # Tạo InfoSingleFile cho file
        piece_length = file_manager.get_piece_length()  # Ví dụ số bytes trong mỗi phần
        pieces = file_manager.get_pieces_code()  # Giả sử mảng byte trống cho ví dụ
        info = InfoSingleFile(piece_length, pieces, file_name, file_size)

        # Tạo MetaInfo cho torrent file
        meta_info = MetaInfo(info, 'http://localhost:5050', datetime.now(), 'No comment', self.name)
        encoded = meta_info.get_bencode()
        TorrentUtils.create_torrent_file(encoded, 'download.torrent')
        magnet_link = TorrentUtils.make_magnet_from_bencode(encoded)

        info_hash = TorrentUtils.get_info_hash_from_magnet(magnet_link)
        return info_hash, magnet_link

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

