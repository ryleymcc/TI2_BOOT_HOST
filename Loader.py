from intelhex import IntelHex
import time


DEBUG = True
class Loader:
    def __init__(self, path):
        self.ih = IntelHex()
        self.ih.loadhex(path)
        self.segments = self.get_segment()
        self.segment = next(self.segments)
        self.addr_idx, self.addr_end = self.segment_to_write_addr(self.segment)
        self.word = self.get_segment_byte(self.segment)

        self.bytes_wrote = 0
        self.short_packet = 0
        
    # get all bytes in a segment. Yield each byte in the segment
    def get_segment_byte(self, seg):
        for byte in range(seg[0], seg[1]):
            yield self.ih[byte]

    # get all segments in the hex file. Yield each segment
    def get_segment(self):
        for segment in self.ih.segments():
            # this is a list of [start address, end address]
            yield segment

    @staticmethod
    # convert segment address to write address
    def segment_to_write_addr(seg):
        if (seg[1] % 2 != 0) or (seg[0] % 2 != 0):
            raise Exception("Segment address is not a multiple of 4")
        return seg[0]//2, seg[1]//2

    # get a packet
    def get_packet(self, gen):
        packet = bytearray()
        while len(packet) < 8:
            try:
                packet.append(next(gen))
            except StopIteration:
                break
        return packet
    
    def get_next_packet(self):
        segments = self.get_segment()
        seg = next(segments)
        addr_idx, addr_end = self.segment_to_write_addr(seg)

        # The bootloader writes 4 16-bit instructions at a time
        # For every 4 instructions, we need to send a packet
        # The client expects an address and 4 instructions.
        # Every time we send a packet, we increment the address 
        # by 4. The address is the address of the first instruction 
        # plus the segment start address.

        word = self.get_segment_byte(seg)


        #print("Segment start address: " + hex(addr_idx) + " Segment end address: " + hex(addr_end))
        while True:
            try:
                while addr_idx <= addr_end:
                    # get next packet
                    #print("Address", hex(addr_idx))
                    packet = self.get_packet(word)
                    if len(packet) != 8:
                        pass
                    if DEBUG:
                        #print("\\".join("{:02x}".format(c) for c in packet))
                        pass
                        
                    yield addr_idx, packet
                    addr_idx += 4
                    
                # get next segment
                try:
                    seg = next(segments)
                    addr_idx, addr_end = self.segment_to_write_addr(seg)
                    word = self.get_segment_byte(seg)
                except StopIteration:
                    print("No more segments")
                    #print("Bytes wrote (including phantom bytes): " + str(bytes_wrote))
                    #print("Short packets: " + str(short_packet))
                    print("Segments wrote: " + str(len(self.ih.segments())))
                    break
                
            except StopIteration:
                print("No more packets")
                break
        

def test():
    # bootloader host
    l = Loader("TI2.hex")
    for segment in l.ih.segments():
        s, e = l.segment_to_write_addr(segment)
        print("Segment Start: " + hex(s) + " Segment End: " + hex(e))
    
    segments = l.get_segment()
    seg = next(segments)
    addr_idx, addr_end = l.segment_to_write_addr(seg)
    
    
    
    word = l.get_segment_byte(seg)
    
    
    print("Segment start address: " + hex(addr_idx) + " Segment end address: " + hex(addr_end))
    while True:
        try:
            while addr_idx <= addr_end:
                # get next packet
                #print("Address", hex(addr_idx))
                packet = l.get_packet(word)
                if len(packet) != 8:
                    pass
                if DEBUG:
                    print("\\".join("{:02x}".format(c) for c in packet))
                print("Address: " + hex(addr_idx))
                addr_idx += 4
                
            # get next segment
            try:
                seg = next(segments)
                addr_idx, addr_end = l.segment_to_write_addr(seg)
                word = l.get_segment_byte(seg)
            except StopIteration:
                print("No more segments")
                #print("Bytes wrote (including phantom bytes): " + str(bytes_wrote))
                #print("Short packets: " + str(short_packet))
                print("Segments wrote: " + str(len(l.ih.segments())))
                break
            
        except StopIteration:
            print("No more packets")
            break
    
    
def main():
    l = Loader("selfdrive/debug/Bootloader/TI2.hex")
    print(l.ih.segments())
    time.sleep(10)
    # The bootloader writes 4 16-bit instructions at a time
    # For every 4 instructions, we need to send a packet
    # The client expects an address and 4 instructions.
    # Every time we send a packet, we increment the address 
    # by 4. The address is the address of the first instruction 
    # plus the segment start address.
    for addr, packet in l.get_next_packet():
        #print(type(packet))
        print("Address: " + hex(addr))
        print("\\".join("{:02x}".format(c) for c in packet))
        
        pass
    

if __name__ == "__main__":
    main()