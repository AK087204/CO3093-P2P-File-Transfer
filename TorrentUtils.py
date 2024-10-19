import bencodepy
import hashlib
import base64

class TorrentUtils:

    @staticmethod
    def create_torrent_file(meta_info,file_path):
        encoded_data = meta_info.create_bencode()

        with open(file_path, 'wb') as f:
            f.write(encoded_data)

    @staticmethod
    def make_magnet_from_bencode(torrent):
        """
        Create magnet link from torrent file.
        :param torrent:
        :return: magnet_link
        """
        metadata = bencodepy.decode(torrent)
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

        # Lấy tên của directory hoặc file
        name = subj[b'name'].decode()
        trackers = metadata.get(b'announce', b'').decode()

        return 'magnet:?' \
            + 'xt=urn:btih:' + b32hash \
            + '&dn=' + name \
            + '&tr=' + trackers \
            + '&xl=' + str(total_length)

    @staticmethod
    def make_magnet_from_file(self, file_path):
        with open(file_path, 'rb') as f:
            file_data = f.read()
        return self.make_magnet_from_encoded(file_data)