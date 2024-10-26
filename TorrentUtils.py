import bencodepy
import hashlib
import base64
import urllib.parse

class TorrentUtils:

    @staticmethod
    def get_info_from_file(torrent_file):
        """
        Get the hash of info in torrent file.
        :param torrent_file:
        :return: hash code
        """
        with open(torrent_file, 'rb') as f:
            file_data = f.read()

        metadata = bencodepy.decode(file_data)
        subj = metadata[b'info']
        # Nếu torrent là một directory, sẽ có 'files' thay vì 'length'
        if b'files' in subj:
            # Tính tổng kích thước của tất cả các file trong directory
            total_length = sum(file[b'length'] for file in subj[b'files'])
        else:
            # Nếu không phải directory, sử dụng 'length' của file đơn
            total_length = subj[b'length']

        hash_contents = bencodepy.encode(subj)
        digest = hashlib.sha1(hash_contents).digest()
        b32hash = base64.b32encode(digest).decode()
        return b32hash, total_length

    @staticmethod
    def get_info_from_magnet(magnet_link):
        # Phân tích (parse) magnet link
        parsed_link = urllib.parse.urlparse(magnet_link)

        # Tách các tham số query của magnet link
        query_params = urllib.parse.parse_qs(parsed_link.query)

        # Lấy giá trị của 'xt' (exact topic), trong đó chứa 'urn:btih:<info_hash>'
        xt_param = query_params.get('xt', [])
        info_hash = None
        total_length = None

        if xt_param:
            # 'urn:btih:<info_hash>' - chúng ta cần lấy phần <info_hash>
            xt_value = xt_param[0]

            if xt_value.startswith("urn:btih:"):
                # Trích xuất và chuyển info_hash sang dạng byte
                info_hash_hex = xt_value[9:]  # Bỏ qua "urn:btih:"
                info_hash = bytes.fromhex(info_hash_hex)

        # Kiểm tra nếu 'xl' có trong query params và lấy giá trị nếu có
        xl_param = query_params.get('xl', [])
        if xl_param:
            try:
                total_length = int(xl_param[0])  # Chuyển đổi sang kiểu số nguyên
            except ValueError:
                total_length = None  # Nếu không thể chuyển đổi, đặt total_length là None

        return info_hash, total_length

    @staticmethod
    def create_torrent_file(encoded_data, file_path):

        with open(file_path, 'wb') as f:
            f.write(encoded_data)

    @staticmethod
    def make_magnet_from_file(file_path):
        with open(file_path, 'rb') as f:
            file_data = f.read()
        return TorrentUtils.make_magnet_from_bencode(file_data)

    @staticmethod
    def make_magnet_from_bencode(bencode_data):
        """
        Create magnet link from torrent file.
        :param bencode_data: bencoded torrent file data
        :return: magnet_link
        """
        # Decode the bencoded data
        metadata = bencodepy.decode(bencode_data)
        subj = metadata[b'info']
        
        # If torrent is a directory, 'files' will exist instead of 'length'
        if b'files' in subj:
            # Calculate the total length of all files in the directory
            total_length = sum(file[b'length'] for file in subj[b'files'])
        else:
            # If it's not a directory, use the 'length' of the single file
            total_length = subj[b'length']

        # Encode the 'info' part and generate the SHA-1 hash
        hash_contents = bencodepy.encode(subj)
        info_hash = hashlib.sha1(hash_contents).digest()
        print(f"info_hash from magnet: {info_hash}")
        info_hash_hex = info_hash.hex()

        # Get the name of the directory or file
        name = subj[b'name'].decode()

        # Handle multiple trackers if present, and build tracker parameters
        trackers = metadata.get(b'announce-list', [[metadata.get(b'announce', b'')]])
        tracker_params = ''
        for tracker_group in trackers:
            for tracker in tracker_group:
                tracker_url = tracker.decode()
                tracker_params += '&tr=' + urllib.parse.quote(tracker_url)
        
        # Return the final magnet link
        # NOTE: info_hash_hex is NOT URL-encoded
        return 'magnet:?' \
            + 'xt=urn:btih:' + info_hash_hex \
            + '&dn=' + urllib.parse.quote(name) \
            + tracker_params \
            + '&xl=' + str(total_length)

