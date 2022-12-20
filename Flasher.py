#!/usr/bin/env python3
from panda import Panda
from panda.python.uds import UdsClient, MessageTimeoutError, NegativeResponseError, SESSION_TYPE, DATA_IDENTIFIER_TYPE
from subprocess import call
from intelhex import IntelHex
import numpy as np
import time
import struct

# to install pip package on c2
# mount -o rw,remount /system
# mount -o rw,remount /data
# pip install intelhex




class TIFlasher():
    def __init__(self):
        self.panda = Panda()
        self.panda.set_safety_mode(Panda.SAFETY_ELM327)
        self.uid120 = 0
        self.unlock_sequence = 0x00AA0055
        self.minimum_write_size = 0x00000008
        self.memory_start_addr = 0x00000000
        self.memory_end_addr = 0x00000000
        self.send_addr = 0x7DF
        self.recv_addr = 0xA2
        self.bus = 0
        self.parse_data(self.create_a_function(1,2,4,4,2,2,4,4,4,4,4,2,2,4,4), self.get_version())
        self.parse_data(self.create_a_function(1,2,4,4,1,4,4), self.get_mem_addr())
        
        
    def send(self, bytes):
        self.panda.isotp_send(self.send_addr, bytes, self.bus,  recvaddr = self.recv_addr)
    def recv(self):
        return self.panda.isotp_recv(self.recv_addr, sendaddr = self.send_addr)


    def create_a_function(self, *args):
        """
        given given an arbitry number of byte lenth arguments and a bytearray, 
        this function creates a function that will return a list of the values 
        the bytearray depending on the byte length arguments
        """
        def function(bytearray):
            # start time
            # check if the bytearray is long enough
            # sum of all the arguments
            sum = 0
            for i in range(len(args)):
                sum += args[i]
            if len(bytearray) < sum:
                raise Exception("Bytearray is not long enough")
            elif len(bytearray) > sum:
                raise Exception("Bytearray is too long")
            else:
                pass

            ret = [] # return list
            for i in range(len(args)):
                bytes = bytearray[:args[i]]
                # reverse the bytes
                b = 0
                for j in range(args[i]):
                    b += bytes[j] << (8 * j)
                bytearray = bytearray[args[i]:]
                ret.append(b)

            return ret

        return function
    

    # given a function that  is generated from above, parse the data and print it out
    def parse_data(self,function, data):
        ret = function(data)
        print("Command: ", self.get_command_type(ret[0]))
        print("Data Length", hex(ret[1]))
        print("Unlock Sequence", hex(ret[2]))
        print("Some Address", hex(ret[3]))
        # first value is the command so we use that to determine what to print
        if ret[0] == 0x00: # GetVersion
            # check if the data is long enough
            if len(ret) < 14:
                raise Exception("Data is not long enough. Expected 15 bytes, got " + str(len(ret)))
            print("Bootloader Version", hex(ret[4]))
            print("Max Packet Size", hex(ret[5]))
            print("Device UID1", hex(ret[6]))
            print("Device UID2", hex(ret[7]))
            print("Device UID3", hex(ret[8]))
            print("Device UID4", hex(ret[9]))
            print("Device UID5", hex(ret[10]))
            uid120 = ret[10] + (ret[9] << 24) + (ret[8] << 48) + (ret[7] << 72) + (ret[6] << 96)
            print("Device UID120", hex(uid120))
            print("Erase Page Size", hex(ret[11]))
            print("Min Write Size", hex(ret[12]))
            self.minimum_write_size = ret[12]

            # skip 11 unused
            print("User Reserved Area Start Address", hex(ret[12]))
            print("User Reserved Area End Address", hex(ret[13]))

        elif ret[0] == 0x01: # ReadFlash
            # check if the data is long enough
            if len(ret) < 5:
                raise Exception("Data is not long enough. Expected 5 bytes, got " + str(len(ret)))
            print("Status", self.get_status(ret[0], ret[4]))

        elif ret[0] == 0x02: # WriteFlash
            # check if the data is long enough
            if len(ret) < 5:
                raise Exception("Data is not long enough. Expected 5 bytes, got " + str(len(ret)))
            print("Status", self.get_status(ret[0], ret[4]))
        elif ret[0] == 0x03: # EraseFlash
            # check if the data is long enough
            if len(ret) < 5:
                raise Exception("Data is not long enough. Expected 5 bytes, got " + str(len(ret)))
            print("Status", self.get_status(ret[0], ret[4]))
        elif ret[0] == 0x08: # CalculateAndReadChecksum
            if len(ret) < 5: # TODO: length is based on checksum type
                raise Exception("Data is not long enough. Expected 6 bytes, got " + str(len(ret)))
            print("Status", self.get_status(ret[0], ret[4]))
            if len(ret) > 5:
                print("Checksum", hex(ret[5]))
        elif ret[0] == 0x09: # ResetDevice
            if len(ret) < 4:
                raise Exception("Data is not long enough. Expected 4 bytes, got " + str(len(ret)))
            print("Status", self.get_status(ret[0], ret[4]))
        elif ret[0] == 0x0A: # SelfVerifyProgramMemory
            if len(ret) < 5:
                raise Exception("Data is not long enough. Expected 5 bytes, got " + str(len(ret)))
            print("Status", self.get_status(ret[0], ret[4]))
        elif ret[0] == 0x0B: # GetMemoryAddressRange
            # check if the data is long enough
            if len(ret) < 7:
                raise Exception("Data is not long enough. Expected 7 bytes, got " + str(len(ret)))
            print("Status", self.get_status(ret[0], ret[4]))
            print("Memory Start Address", hex(ret[5]))
            print("End Address", hex(ret[6]))
            self.memory_start_addr = ret[5]

        else: # not implemented error
            raise Exception("Not implemented")


    def get_command_type(self, cmd):
        if cmd == 0x00:
            return "Get Version"
        elif cmd == 0x01: # ReadFlash
            return "Read Flash"
        elif cmd == 0x02: # WriteFlash
            return "Write Flash"
        elif cmd == 0x03: # EraseFlash
            return "Erase Flash"
        elif cmd == 0x08:
            return "Calculate And Read Checksum"
        elif cmd == 0x09:
            return "Reset Device"
        elif cmd == 0x0A:
            return "Self Verify Program Memory"
        elif cmd == 0x0B:
            return "Get Memory Address Range"
        else:
            raise Exception("Unknown Command")


    def get_status(self, cmd, status):
        if status == 0x01:
            return "Success"
        elif status == 0xFF:
            return "Unsupported command"
        elif status == 0xFE:
            return "Invalid Address"
        elif cmd == 0x0A: # SelfVerifyProgramMemory
            # 0x01 Success 0xFF Unsupported command 0xFE Invalid Address 0xFD Invalid Compare
            if status == 0xFD:
                return "Invalid Compare"
            elif status == 0xFC:
                return "Verify Failed"
            else:
                pass
        else:
            return "Unknown Status"



    def read_flash(self, length, address):
        """This command will read the program flash and return the \n
        data read in the response packet. Because of the flash \n
        architecture, flash must always be read in modulus 4 byte \n
        lengths and the address must also be aligned to an instruction \n
        boundry which is modulus 2 on PIC24/dsPIC devices. The address \n
        of the memory range must reside entirely within the application \n
        space. If any of the requested data is outside of the \n
        application space, a status of 0xFE, Invalid Address, with no data will be returned"""
        # 1 Cmd uint8_t Command (0x01) - Read Program Memory 
        # 2 Length uint16_t Number of bytes to read. Length must be modulus 4 in length.  
        # 4 Unlock Seqeunce uint32_t Unlock sequence for flash. Key for currently supported parts is 0x00AA0055  
        # 4 Address uint32_t Address of the first memory location to read. Address must be modulus 2(Even). 
        bytes = b'\x01' + length.to_bytes(2, byteorder='little') + self.unlock_sequence.to_bytes(4, byteorder='little') + address.to_bytes(4, byteorder='little')
        self.send(bytes)
        return self.recv()

    def device_checksum(self):
        """This command will cause the device to perform a \n
        checksum and return the results. The specific checksum \n
        will depend on the device and the algorythm used."""
        # 1 Cmd uint8_t Command (0x08) - Calculate and Read Checksum of Program Memory 
        # 2 Length uint16_t TBD  
        # 4 Unlock Seqeunce uint32_t TBD  
        # 4 Address uint32_t TBD 
        bytes = b'\x08' + b'\x00\x00' + self.unlock_sequence.to_bytes(4, byteorder='little') + b'\x00\x00\x00\x00'
        self.send(bytes)
        # 1 Cmd uint8_t Command (0x08) - Calculate and Read Checksum of Program Memory 
        # 2 Length uint16_t TBD 
        # 4 Unlock Seqeunce uint32_t TBD  
        # 4 Address uint32_t TBD 
        # 1 Status uint8_t Status of Command 0x01 Success 0xFF Unsupported command 0xFE Invalid Address  
        # Variable Checksum uint8_t TBD 
        return self.recv()

    def reset_device(self):
        """This command will cause the device to do a software device \n
        reset. The reset will occur right after the last byte of data \n
        is set out of the CANbus"""
        # 1 Cmd uint8_t Command (0x09) - Reset Device 
        # 2 Length uint16_t 0x0000 - Field Ignored 
        # 4 Unlock Seqeunce uint32_t 0x00000000 - Field Ignored 
        # 4 Address uint32_t 0x00000000 - Field Ignored 
        bytes = b'\x09\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
        self.send(bytes)
        # 1 Cmd uint8_t Command (0x09) - Reset Device 
        # 2 Length uint16_t 0x0000 - Field Ignored 
        # 4 Unlock Seqeunce uint32_t 0x00000000 - Field Ignored 
        # 4 Address uint32_t 0x00000000 - Field Ignored 
        # 1 Status uint8_t Status of Command 0x01 Success 0xFF Unsupported command 0xFE Invalid Address 
        return self.recv()

    def self_verify(self):
        """This command will cause the device to verify the contents \n
        of its flash by computing the Checksum/SHA256 of the application \n
        program and compare the computed value to the expected value \n
        located in the application program header. If the compared \n
        contents match, a Success value is returned. If they do not \n
        match, an Invalid Compare value is returned."""
        # 1 Cmd uint8_t Command (0x0A) - Self Verify Program Memory 
        # 2 Length uint16_t 0  
        # 4 Unlock Seqeunce uint32_t 0 
        # 4 Address uint32_t 0 
        bytes = b'\x0A' + b'\x00\x00' + self.unlock_sequence.to_bytes(4, byteorder='little') + b'\x00\x00\x00\x00'
        self.send(bytes)
        # 1 Cmd uint8_t Command (0x0A) - Self Verify Program Memory 
        # 2 Length uint16_t 0. 
        # 4 Unlock Seqeunce uint32_t 0  
        # 4 Address uint32_t 0 
        # 1 Status uint8_t Status of Command 0x01 Success 0xFF Unsupported command 0xFE Invalid Address 0xFD Invalid Compare 
        return self.recv()

    def get_version(self):
        """The GetVersion command does two things. As the first command \n
        that is sent to the bootloader, its used to establish \n
        communication with the device. Therefore, if the communications \n
        channel is not setup correctly, this command will fail. \n
        Secondly, it returns the device information such as: Bootloader \n
        version Max Packet size Device ID Erase row size Write latch \n
        size Config words """
        # 1 Cmd uint8_t Command (0x00) - Get Version Command 
        # 2 Length uint16_t Unused - Set to 0x0000 
        # 4 Unlock Seqeunce uint32_t Unused - Set to 0x00000000 
        # 4 Address uint32_t Unused - Set to 0x00000000 
        bytes = b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
        self.send(bytes)
        # 1 Cmd uint8_t Command (0x00) - Get Version 
        # 2 Length uint16_t 0x0000 
        # 4 Unlock Sequence uint32_t 0x00000000 
        # 4 Address uint32_t 0x00000000 
        # 2 Bootloader Version uint16_t 0x0600 The version of the bootloader 
        # 2 Max Packet Size in Bytes uint16_t Maximum size of any packet in either direction. This includes all header and payload data  
        # 4 uid1 uint32_t Unique ID of the device
        # 4 uid2 uint32_t Unique ID of the device
        # 4 uid3 uint32_t Unique ID of the device
        # 4 uid4 uint32_t Unique ID of the device
        # 4 uid5 uint32_t Unique ID of the device
        # 2 Erase Page Size in Bytes uint16_t Size of a erase page on the device in bytes including phantom bytes. This will vary from device to device and the value can be found if the device manual.  
        # 2 Minimumn Write Size in Bytes uint16_t The minimum amount of data in bytes that can be written. This also defines the alignment of the data. So if the min write size is 8, then the data must also be 8 byte aligned  
        # 4 User Reserved Area Start Address  uint32_t 0x00000000 - Currently not supported  
        # 4 User Reserved Area End Address  uint32_t 0x00000000 - Currently not supported  
        return self.recv()

    def get_mem_addr(self):
        """This command will request the memory range for a specific \n
        memory section on the device. The specific memory will be placed\n
        in the "Address" field. This field should be populated with 0 if \n
        only one memory range is supported. The device will response \n
        with the start and end address of the programable memory range. \n
        This will allow the programmer to determine what ranges are \n
        supported and allow the programmer to filter out all other \n
        memory addresses."""

        # 1 Cmd uint8_t 0x0B 
        # 2 Length uint16_t 0x0008 
        # 4 Unlock Seqeunce uint32_t 0x00000000  
        # 4 Address uint32_t 0x00000000 
        bytes = b'\x0B\x08\x00\x00\x00\x00\x00\x00\x00\x00\x00'
        self.send(bytes)
        # 1 Cmd uint8_t Command 0x0B) - Get Memory Address Range  
        # 2 Length uint16_t 8 -Number of bytes to read. 
        # 4 Unlock Seqeunce uint32_t 0 Unlock sequence for flash. Key for currently supported parts is 0x00AA0055  
        # 4 Address uint32_t Which memory range. 0x0 is default for a divice with just single flash. 
        # 1 Status uint8_t Status of Command 0x01 Success 0xFF Unsupported command 0xFE Invalid Address 
        return self.recv()

    def erase_flash(self, length, address):
        """This command erases the number of flash PAGES in the length field. \n
        The actual size of the page depends upon the device being programmed. \n
        The address must be the beginning address of the first page to be programmed.\n
        In addition, attempting to erase memory outsize the application space will result \n
        in a Invalid Address (0xFE) status. The correct unlock sequence must be sent to \n
        the part for each command as it is not stored on the device"""
        # 1 Cmd uint8_t Command (0x03) - Erase Program Memory 
        # 2 Length uint16_t Number of pages to erase. Low Byte First 
        # 4 Unlock Seqeunce uint32_t Unlock sequence for flash. Key for currently supported parts is 0x00AA0055  
        # 4 Address uint32_t Address of the first memory location to erase. Must be page aligned. Low byte first. 
        bytes = b'\x03' + length.to_bytes(2, byteorder='little') + b'\x00\x00\x00\x00' + address.to_bytes(4, byteorder='little')
        self.send(bytes)
        """
        Field Size | Description | Data Type | Comments 
        |----------|-------------|-----------|----------------
        |1         | Cmd         | uint8_t   | Command (0x03) - Erase Program Memory 
        |2         | Length      | uint16_t  | Number of pages to erase. Low Byte First 
        |4         | Unlock Seq  | uint32_t  | Unlock sequence for flash. Key for currently supported parts is 0x00AA0055 
        |4         | Address     | uint32_t  | Address of the first memory location to erase. Must be page aligned. Low byte first.
        |1         | Status      | uint8_t   | Status of Command 0x01 Success 0xFF Unsupported command 0xFE Invalid Address
        """
        return self.recv()

    def write_flash(self, length, address, data):
        """This command will program the flash with the data in the payload section. \n
        The address and size of the payload will be inspected by the bootloader to prevent \n
        accidental over-write of protected space. Attempts to write into the memory where \n
        the bootloader or configuration bits resides will be prevented and an error will be returned. \n
        The flash architecture also places limitations on the address alignment and size of the requests. \n
        The start address must always be on an Min Write Size aligned address and it's \n
        length must also be modulus the Min Write Size in bytes. If either address or length \n
        is not aligned the device will not write the data and a status of 0xFE (Invalid Address) will \n
        be returned. The user is responsible for erasing flash before writting. Failure to do so will \n
        have unexpected results. The correct unlock sequence must be sent to the part for each command \n
        as it is not stored on the device"""
        # 1 Cmd uint8_t Command (0x02) - Write Program Memory 
        # 2 Length uint16_t Number of bytes to program. Must be evenly divisable by the Minimum Write Size parameter in the Get Version response. Command will return error if it's not evenly divisable 
        # 4 Unlock Seqeunce uint32_t Unlock sequence for flash. Key for currently supported parts is 0x00AA0055  
        # 4 Address uint32_t Address of the first memory location to program. Must be aligned to the Minimum Write Size parameter in the Get Version response. Command will return error if it's not aligned 
        # Variable Data To Write uint8_t Seqeunce of bytes. Data to write.

        # check if length is evenly divisable by the Minimum Write Size parameter in the Get Version response
        if length % self.minimum_write_size  != 0:
            raise Exception("Length is not evenly divisable by the Minimum Write Size parameter in the Get Version response")
        # check if address is aligned to the Minimum Write Size parameter in the Get Version response
        if address % (self.minimum_write_size//2) != 0:
            raise Exception("Address is not aligned to the Minimum Write Size parameter in the Get Version response")
        # check that the length of the data is the same as the length
        if len(data) != length:
            raise Exception("Length of data is not the same as the length")
        # check that dara is a bytes object
        if type(data) == bytes or type(data) == bytearray:
            pass
        else:
            raise Exception("Data is not a bytes object")
        
        swap_bytes = False
        if swap_bytes:
            data = bytearray(data)
            data = [data[i:i+2] for i in range(0, len(data), 2)]
        
        b = b'\x02' + length.to_bytes(2, byteorder='little') + self.unlock_sequence.to_bytes(4, byteorder="little") + address.to_bytes(4, byteorder='little') + data
        #print(b)
        self.send(b)
        # 1 Cmd uint8_t Command (0x02) - Write Program Memory 
        # 2 Length uint16_t Number of bytes to write. 
        # 4 Unlock Seqeunce uint32_t Unlock sequence for flash. Key for currently supported parts is 0x00AA0055  
        # 4 Address uint32_t Address of the first memory location to write. Must be aligned to and modulus of the Minimum Write Size. 
        # 1 Status uint8_t Status of Command 0x01 Success 0xFF Unsupported command 0xFE Invalid Address 
        return self.recv()

    def read_flash(self, length, address):
        """This command will read the program flash and return the data read in the response packet. \n
        Because of the flash architecture, flash must always be read in modulus 4 byte lengths \n
        and the address must also be aligned to an instruction boundry which is modulus 2 on PIC24/dsPIC \n
        devices. The address of the memory range must reside entirely within the application space. \n
        If any of the requested data is outside of the application space, a status of 0xFE, \n
        Invalid Address, with no data will be returned."""
        """
        Field Size | Description | Data Type | Comments
        |----------|-------------|-----------|----------------
        |1         | Cmd         | int8_t    | Command (0x01) - Read Program Memory 
        |2         | Length      | int16_t   | Number of bytes to read. Length must be modulus 4 in length.  
        |4         | Unlock Seq  | uint32_t  | Unlock sequence for flash. Key for currently supported parts is 0x00AA0055  
        |4         | Address     | uint32_t  | Address of the first memory location to read. Address must be modulus 2(Even). 
        """
        # chck if length is modulus 4
        if length % 4 != 0:
            raise Exception("Length is not modulus 4")
        if address % 2 != 0:
            raise Exception("Address is not modulus 2")
        bytes = b'\x01' + length.to_bytes(2, byteorder='little') + b'\x00\x00\x00\x00' + address.to_bytes(4, byteorder='little')
        self.send(bytes)
        """
        Field Size | Description | Data Type | Comments
        |----------|-------------|-----------|----------------
        | 1        | Cmd         |uint8_t    | Command (0x01) - Read Program Memory 
        | 2        | Length      |uint16_t   | Number of bytes to read. 
        | 4        | Unlock Seq  |uint32_t   | Unlock sequence for flash. Key for currently supported parts is 0x00AA0055  
        | 4        | Address     |uint32_t   | Address of the first memory location to read. Must be modulus of 2. 
        | 1        | Status      |uint8_t    | Status of Command 0x01 Success 0xFF Unsupported command 0xFE Invalid Address 
        """
        return self.recv()

def main():
    tif = TIFlasher()
    # get version
    #tif.parse_data(tif.create_a_function(1,2,4,4,2,2,4,4,4,4,4,2,2,4,4), tif.get_version()) 
    ## get memory address
    #tif.parse_data(tif.create_a_function(1,2,4,4,1,4,4), tif.get_mem_addr()) 
    ## self verify
    #tif.parse_data(tif.create_a_function(1,2,4,4,1), tif.self_verify())
    ## erase
    #tif.parse_data(tif.create_a_function(1,2,4,4,1), tif.erase_flash(1,2))
    ## write
    ##tif.parse_data(tif.create_a_function(1,2,4,4,1,4,4), tif.write_flash())
    ##tif.parse_data(tif.create_a_function(1,2,4,4,1), tif.read_flash(4,2)) # read
    tif.parse_data(tif.create_a_function(1,2,4,4,1), tif.reset_device()) # reset
    #tif.parse_data(tif.create_a_function(1,2,4,4,1), tif.device_checksum()) # checksum
    
def test():
    panda = Panda()
    panda.set_safety_mode(Panda.SAFETY_ELM327)
    print(panda.can_send(0x7DF, b'\x01\x02\x04\x04\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00', 0))
    print(panda.can_recv())
    
if __name__ == "__main__":
    main()
    #test()
    
    
    
