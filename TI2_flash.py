from intelhex import IntelHex
from Flasher import TIFlasher
from panda import Panda
import struct
import time





# a generator that yields 16 data byte at a time
def get_data(ih):
    for segment in ih.segments():
        seg_size = segment[1] - segment[0]
        print(f'{seg_size} Byte Segment, at Address From:{hex(segment[0])} To:{hex(segment[1])}')
        for addr in range(segment[0], segment[1], 8):
            #print("addr", hex(addr))
            bytearray = b''
            for i in range(8): 
                bytearray += struct.pack('B', ih[addr+i])
            
            yield len(bytearray), addr, bytearray
        
def main():
    ih = IntelHex()
    ih.loadfile("selfdrive/debug/TI2.hex", format="hex")
    tif = TIFlasher()
    
    byte = get_data(ih) # get the generator object
    
    # flash the data
    while True:
        try:
            length, addr, bytearray = next(byte)
            print("here")
            
            addr = addr + tif.memory_start_addr
            print("length", length, "addr", hex(addr))
            tif.parse_data(tif.create_a_function(1,2,4,4,1), tif.write_flash(length, addr, bytearray))
            time.sleep(1.50)
        except StopIteration:
            break
    
if __name__ == "__main__":
    main()
        
    
    
        
        
        