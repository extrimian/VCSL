import gzip


class BitArray:
    def __init__(self, size=(2**16)):
        self.array = '\x00' * (size // 8 + 1)
        # convert to ascii
        self.array = bytearray(self.array.encode('ascii'))
        self.size = size

    def __getitem__(self, index):
        return self.array[index // 8] & (1 << (index % 8)) != 0

    def __setitem__(self, index, value: bool):
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
        return gzip.compress(self.array)

    @classmethod
    def decompress(cls, compressed, size=(2**16)):
        bitarray = cls()
        bitarray.array = gzip.decompress(compressed).decode('ascii')
        return bitarray
