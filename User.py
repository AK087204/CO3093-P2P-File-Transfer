
from datetime import datetime
import os

from threading import Thread


from FileManager import FileManager
from info import *
from MetaInfo import MetaInfo
from TorrentUtils import TorrentUtils
from Peer import Peer
import socket

class User:
    def __init__(self, userId, name:str = "Anonymous"):
        self.name = name
        self.peers_and_threads = []
        self.userId = userId

    def download(self, file):
        if self.isTorrent(file):
            info = TorrentUtils.get_info_from_file(file)
        else:
            info = TorrentUtils.get_info_from_magnet(file)

        ip, port = self._get_ip_port()
        file_manager = FileManager(info["length"])
        peer = Peer(ip, port, info, file_manager)
        thread = Thread(target=peer.download)

        self.peers_and_threads.append((peer, thread))

        thread.start()



    def share(self, path):
        total_length = os.path.getsize(path)
        print("Total length",total_length)
        file_manager = FileManager(total_length)
        file_manager.split_file(path)
        if os.path.isdir(path):
            magnet_link = self._input_directory(path, file_manager)
        elif os.path.isfile(path):
            magnet_link = self._input_file(path, file_manager)
        else:
            raise "Invalid path"

        print(f"Magnet link: {magnet_link}")

        info = TorrentUtils.get_info_from_magnet(magnet_link)
        ip, port = self._get_ip_port()
        peer = Peer(ip, port, info, file_manager)
        thread = Thread(target=peer.upload)

        self.peers_and_threads.append((peer, thread))

        thread.start()


    def scrape_tracker(self, file):

        if self.isTorrent(file):
            info = TorrentUtils.get_info_from_file(file)
        else:
            info = TorrentUtils.get_info_from_magnet(file)

        ip, port = self._get_ip_port()
        file_manager = FileManager(info["length"])
        peer = Peer(ip, port, info, file_manager)
        thread = Thread(target=peer.scrape_tracker)

        self.peers_and_threads.append((peer, thread))

        thread.start()

    def stop(self, peer_id):
        for peer, thread in self.peers_and_threads:
            if peer_id == peer.peer_id:
                peer.stop()
                thread.join()
                self.peers_and_threads.remove((peer, thread))

    def stop_all(self):
        for peer, thread in self.peers_and_threads:
            peer.stop()
            thread.join()
            self.peers_and_threads.remove((peer, thread))


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

        return magnet_link



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

    def isTorrent(self, file):
        if not file.endswith(".torrent"):
            return False

        try:
            with open(file, "rb") as f:
                content = f.read()
                # Kiểm tra các từ khóa Bencode đặc trưng
                if b"announce" in content and b"info" in content and b"pieces" in content:
                    return True
        except Exception as e:
            print("Error reading file:", e)

        return False