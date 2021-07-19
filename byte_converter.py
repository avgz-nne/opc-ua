byte_array = [200, 255]

print(int.from_bytes(byte_array, byteorder='big',signed=True))