import gzip
import base64


class BitArray:
    def __init__(self, size=(2**16)):
        self.array = '\x00' * (size // 8 + 1)
        # convert to ascii
        self.array = bytearray(self.array.encode('ascii'))  # Compressed bitarray is encoded in utf-8, but the bit array is in ascii
        self.size = size

    def __getitem__(self, index: int):
        return 1 if self.array[index // 8] & (1 << (index % 8)) != 0 else 0

    def __setitem__(self, index: int, value: bool):
        if value:
            self.array[index // 8] = self.array[index // 8] | (1 << (index % 8))
        else:
            self.array[index // 8] = self.array[index // 8] & ~(1 << (index % 8))

    def __len__(self):
        return self.size

    def __str__(self):
        string = ''
        for i in range(self.size):
            string += '1' if self[i] else '0'
        return string

    def compress(self):
        gzip_compressed = gzip.compress(self.array)
        base64_compressed = base64.b64encode(gzip_compressed)
        print(f"Compressed: {base64_compressed}")
        return base64_compressed

    @classmethod
    def decompress(cls, compressed, size=(2**16)):
        print(f"About to decompress {compressed}")
        uncompressed_base64 = base64.b64decode(compressed)
        uncompressed = gzip.decompress(uncompressed_base64)
        bitarray = cls(size)
        bitarray.array = bytearray(uncompressed)
        return bitarray
