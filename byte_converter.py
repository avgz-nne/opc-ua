byte_array = [200 , 255 >> 2]
print(format(byte_array[1], 'b'))
print(int.from_bytes(byte_array, byteorder='big',signed=True))