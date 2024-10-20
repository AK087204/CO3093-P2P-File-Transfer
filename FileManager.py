import hashlib

class Piece:
    def __init__(self, piece_id: int, data: bytes, hash_value):
        self.piece_id = piece_id
        self.data = data
        self.hash_value = hash_value

class FileManager:
    def __init__(self, piece_length: int = 8192):
        self.piece_length = piece_length
        self.pieces = []

    def get_piece_length(self):
        return self.piece_length

    def split_file(self, file_path):
        pieces = []
        try:
            with open(file_path, 'rb') as f:
                piece_id = 0
                while data := f.read(self.piece_length):
                    hash_value = hashlib.sha256(data).hexdigest()
                    piece = Piece(piece_id=piece_id, data=data, hash_value=hash_value)
                    pieces.append(piece)
                    piece_id += 1
        except OSError:
            raise FileNotFoundError(f"Unable to open file: {file_path}")
        return pieces

    def get_pieces_code(self):
        result = ""
        for piece in self.pieces:
            result += f"{piece.hash_value}\n"

        return result
