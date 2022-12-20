from Loader import Loader
from Flasher import TIFlasher
import time

def main():
    # bootloader host
    l = Loader("selfdrive/debug/Bootloader/TI2.hex")
    f = TIFlasher()
    
    for addr, packet in l.get_next_packet():
        print("Address: " + hex(addr))
        print("\\".join("{:02x}".format(c) for c in packet))
        f.parse_data(f.create_a_function(1,2,4,4,1), f.write_flash(len(packet), addr, packet))
    
        # print a status bar based on the address
    # reset the device
    f.parse_data(f.create_a_function(1,2,4,4,1), f.reset_device())
        
        
if __name__ == "__main__":
    main()