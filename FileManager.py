import hashlib
import math
class Piece:
    def __init__(self, piece_id: int, data: bytes, hash_value):
        self.piece_id = piece_id
        self.data = data
        self.hash_value = hash_value

class FileManager:
    def __init__(self, total_length, piece_length: int = 8192):
        self.piece_length = piece_length
        self.total_length = total_length
        self.pieces = []

    def get_piece_length(self):
        return self.piece_length

    def split_file(self, file_path):

        try:
            with open(file_path, 'rb') as f:
                piece_id = 0
                while data := f.read(self.piece_length):
                    hash_value = hashlib.sha256(data).hexdigest()
                    piece = Piece(piece_id=piece_id, data=data, hash_value=hash_value)
                    self.pieces.append(piece)
                    piece_id += 1
        except OSError:
            raise FileNotFoundError(f"Unable to open file: {file_path}")


    def get_pieces_code(self):
        result = ""
        for piece in self.pieces:
            result += f"{piece.hash_value}\n"

        return result

    def get_bitfield(self):
        # Calculate the total number of pieces
        num_pieces = math.ceil(self.total_length / self.piece_length)
        # Calculate the number of bytes required for the bitfield
        num_bytes = (num_pieces + 7) // 8
        bitfield = [0] * num_bytes  # Initialize as list of zeroed bytes

        # Set each downloaded piece in the bitfield
        for piece in self.pieces:
            byte_index = piece.piece_id // 8
            bit_index = piece.piece_id % 8
            bitfield[byte_index] |= (1 << (7 - bit_index))

        # Ensure spare bits in the last byte are cleared if not a full byte
        remaining_bits = num_pieces % 8
        if remaining_bits != 0:
            bitfield[-1] &= (0xFF << (8 - remaining_bits))

        # Convert list to bytes
        return bytes(bitfield)

    def get_total_pieces(self):
        return len(self.pieces)

    def is_interested(self, bitfield):
        num_pieces = math.ceil(self.total_length / self.piece_length)
        current_piece_ids = {piece.piece_id for piece in self.pieces}

        for piece_id in range(num_pieces):
            byte_index = piece_id // 8
            bit_index = piece_id % 8
            # Check if the piece is available in the bitfield
            if bitfield[byte_index] & (1 << (7 - bit_index)):
                # Check if we don't have this piece
                if piece_id not in current_piece_ids:
                    return True

        return False

    def add_piece(self, piece: Piece):
        for has_piece in self.pieces:
            if has_piece.piece_id == piece.piece_id:
                return
        self.pieces.append(piece)