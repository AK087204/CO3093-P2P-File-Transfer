from datetime import datetime
import os

from info import *
from MetaInfo import MetaInfo
from TorrentUtils import TorrentUtils

class User:
    def __init__(self, name:str = "Anonymous"):
        self.name = name

    def input(self):
        path = input("Nhập vào đường dẫn đến file hoặc directory: ")
        if os.path.isdir(path):
            self._input_directory(path)
        elif os.path.isfile(path):
            self._input_file(path)
        elif not os.path.exists(path):
            print("Invalid path")

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
        magnet_link = TorrentUtils.make_magnet_from_bencode(encoded)
        print(magnet_link)

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
        magnet_link = TorrentUtils.make_magnet_from_bencode(encoded)
        print(magnet_link)


if __name__ == '__main__':
    user = User()
    user.input()
