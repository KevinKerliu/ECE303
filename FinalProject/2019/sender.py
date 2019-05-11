# Written by S. Mevawala, modified by D. Gitzel

import logging
import socket
import channelsimulator
import utils
import sys

import math
import random
MAX_SEQUENCE_NUMBER = 256


# Sender class
class Sender(object):

    def __init__(self, inbound_port=50006, outbound_port=50005, timeout=10, debug_level=logging.INFO):
        self.logger = utils.Logger(self.__class__.__name__, debug_level)
        self.inbound_port = inbound_port
        self.outbound_port = outbound_port
        self.simulator = channelsimulator.ChannelSimulator(inbound_port=inbound_port, outbound_port=outbound_port,
                                                           debug_level=debug_level)
        self.simulator.sndr_setup(timeout)
        self.simulator.rcvr_setup(timeout)

    def send(self, data):
        raise NotImplementedError("The base API class has no implementation. Please override and add your own.")


# BogoSender class, which inherits from the Sender class
class BogoSender(Sender):

    def __init__(self):
        super(BogoSender, self).__init__()

    def send(self, data):
        self.logger.info("Sending on port: {} and waiting for ACK on port: {}".format(self.outbound_port, self.inbound_port))
        while True:
            try:
                self.simulator.u_send(data)  # send data
                ack = self.simulator.u_receive()  # receive ACK
                self.logger.info("Got ACK from socket: {}".format(
                    ack.decode('ascii')))  # note that ASCII will only decode bytes in the range 0-127
                break
            except socket.timeout:
                pass


# mySender class, which inherits from the BogoSender class, which inherits from the Sender class 
class mySender(BogoSender):
    # Attributes of the mySender class
    # Declaration/Initialization of attributes
    
    # Attributes for formatting segment stuff ...
    dataFile = 0
    MSS = 250
    segmentNumber = 0
    partitionCount = 0
    partitionStart = 0
    partitionEnd = MSS
    sequenceNumber = random.randint(0, MAX_SEQUENCE_NUMBER - 1)
   
    # Attributes for doing some error checking ...
    numberDuplicates = 0
    wasItSent = False
    resend = False

    # Attributes for buffering data ...
    StartOfBuffer = sequenceNumber
    EndOfBuffer = sequenceNumber
    databuffer = bytearray(MAX_SEQUENCE_NUMBER)


    #  Define the mySender class constructor
    def __init__(self, DATA, timeout = 0.1):
    # Use super to call the constructor of the parent class
        super(mySender, self).__init__()
    # Additional attribute to be set only in the child class (mySender class) constructor 
        self.timeout = timeout                                                             # Set timeout attribute
        self.simulator.sndr_socket.settimeout(self.timeout)                                # Set socket timeout
        self.dataFile = DATA                                                               # Set dataFile attribute equal to DATA
        self.segmentNumber = int(math.ceil(len(self.dataFile)/float(self.MSS)))            # Set segmentNumber based on dataFile size and MSS


    # Define the mySender class segment method
    # The segment method divides the data into segments each less than or equal to the MSS (maximum segment size)
    def segment(self, data, partitionCount, MSS):
        for i in range(self.segmentNumber):
            partitionCount = partitionCount + 1                                   # Increment partitionCount for next segment
            yield data[self.partitionStart:self.partitionEnd]                     # Get data from the beginning to the end of this partition
            self.partitionStart = self.partitionStart + MSS                       # Increment partitionStart for next segment
            self.partitionEnd = self.partitionEnd + MSS                           # Increment partitionEnd for next segement


    # Define the mySender class checkReceiverACK method
    def checkReceiverACK(self, data):
    # Check the checksum of the receiver ACK
    # The logic is as follows: invert, XOR, and compare to an all high (all ones) state
        checksumValue = ~data[0]
        for i in xrange(1, len(data)):  
            checksumValue = checksumValue ^ (data[i])
        if checksumValue == -1:             
            return True 
        else:
            return False


    # Define the mySender class send method
    def send(self, data):
        self.logger.info("Sending on port: {} and waiting for ACK on port: {}".format(self.outbound_port, self.inbound_port))
        
        for s in self.segment(self.dataFile, self.partitionCount, self.MSS):
            try:
                # Initial attempt to send the data
                if not self.resend:
                    seg = reliableSegment(sequenceNumber = 0, acknowledgementNumber = 0, checksum = 0, data = s)
                    seg.sequenceNumber = reliableSegment.seqNumber(self, self.sequenceNumber, self.MSS)
                    self.sequenceNumber = seg.sequenceNumber
                    seg.acknowledgementNumber = 0

                    sendArray = bytearray([seg.checksum, seg.acknowledgementNumber, seg.sequenceNumber])
                    sendArray = sendArray + s
                    seg.checksum = reliableSegment.checksum(self, sendArray)
                    sendArray[0] = seg.checksum
     
                    self.simulator.u_send(sendArray) 

                # Hear back from receiver
                while True:
                    receiverArray = self.simulator.u_receive()
                    # ACK not corrupted
                    if self.checkReceiverACK(receiverArray):
                        if receiverArray[1] == self.sequenceNumber:
                            self.wasItSent = True
                            self.simulator.u_send(sendArray)  
                        # Next ACK not corrupted
                        elif receiverArray[1] == (self.sequenceNumber + len(s)) % MAX_SEQUENCE_NUMBER: 
                            self.numberDuplicates = 0
                            if self.timeout > 0.1:
                                self.timeout = self.timeout - 0.1
                            self.simulator.sndr_socket.settimeout(self.timeout)
                            self.resend = False
                            break
                        # Error, resend
                        else: 
                            self.simulator.u_send(sendArray) 
                    # ACK corrupted
                    else: 
                        self.simulator.u_send(sendArray) 
                        self.numberDuplicates = self.numberDuplicates + 1
                        # Timeout in case of additional errors
                        if self.numberDuplicates == 3 and self.wasItSent:
                            self.timeout = self.timeout * 2
                            self.simulator.sndr_socket.settimeout(self.timeout) 
                            self.numberDuplicates = 0
                            if self.timeout > 5:
                                print("Boohoo :( Timeout!")
                                exit()

            # In case of a timeout...    
            except socket.timeout:
                self.resend = True
                self.simulator.u_send(sendArray)
                self.numberDuplicates = self.numberDuplicates + 1
                if self.numberDuplicates >= 3:
                    self.numberDuplicates = 0
                    self.timeout = self.timeout * 2
                    self.simulator.sndr_socket.settimeout(self.timeout)
                    if self.timeout > 6:
                        print("Boohoo :( Timeout!")
                        exit()                                           


# The segment contains both data and error checking
# The segment contains the checksum, sequence number, acknowledgement number, and data
class reliableSegment(object):
    #  Define the reliableSegment class constructor
    def __init__(self, checksum = 0, sequenceNumber = 0, acknowledgementNumber = 0, data = []):
        self.data = data
        self.checksum = checksum
        self.acknowledgementNumber = acknowledgementNumber
        self.sequenceNumber = sequenceNumber


    # Define seqNumber, a static method (to reduce memory usage)
    @staticmethod
    def seqNumber(self, previousSequenceNumber, MSS):
        return (previousSequenceNumber + MSS) % MAX_SEQUENCE_NUMBER


    # Define checksum, a static method (to reduce memory usage)
    @staticmethod
    def checksum(self, data):
        checksumValue = 0
        dataArray = bytearray(data)
        for i in xrange(len(dataArray)):
            checksumValue = checksumValue ^ (dataArray[i])
        return checksumValue


if __name__ == "__main__":
    # test out BogoSender
    DATA = bytearray(sys.stdin.read())
    # sndr = BogoSender()
    sndr = mySender(DATA)
    sndr.send(DATA)
