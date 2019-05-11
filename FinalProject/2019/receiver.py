# Written by S. Mevawala, modified by D. Gitzel

import logging
import channelsimulator
import utils
import sys
import socket


# Receiver class
class Receiver(object):

    def __init__(self, inbound_port=50005, outbound_port=50006, timeout=10, debug_level=logging.INFO):
        self.logger = utils.Logger(self.__class__.__name__, debug_level)

        self.inbound_port = inbound_port
        self.outbound_port = outbound_port
        self.simulator = channelsimulator.ChannelSimulator(inbound_port=inbound_port, outbound_port=outbound_port,
                                                           debug_level=debug_level)
        self.simulator.rcvr_setup(timeout)
        self.simulator.sndr_setup(timeout)

    def receive(self):
        raise NotImplementedError("The base API class has no implementation. Please override and add your own.")


# BogoReceiver class, which inherits from the Receiver class
class BogoReceiver(Receiver):
    ACK_DATA = bytes(123)

    def __init__(self):
        super(BogoReceiver, self).__init__()

    def receive(self):
        self.logger.info("Receiving on port: {} and replying with ACK on port: {}".format(self.inbound_port, self.outbound_port))
        while True:
            try:
                 data = self.simulator.u_receive()  # receive data
                 self.logger.info("Got data from socket: {}".format(
                     data.decode('ascii')))  # note that ASCII will only decode bytes in the range 0-127
                 sys.stdout.write(data)
                 self.simulator.u_send(BogoReceiver.ACK_DATA)  # send ACK
            except socket.timeout:
                sys.exit()


# myReceiver class, which inheris from the BogoReceiver class, which inherits from the Receiver class
class myReceiver(BogoReceiver):
    # Attributes of the myReceiver class
    # Declaration/Initialization of attributes

    # Attributes for error checking ...
    ACKsafety = bytearray([0,0,0])
    receiverArray = bytearray([0,0,0,0])
    numberDuplicates  = 0    
    previousACKnumber = -1 
    resend = True


    # Define the mySender class constructor
    def __init__(self, timeout = 0.1):
        # Use super to call the constructor of the parent class
        super(myReceiver, self).__init__()
        self.timeout = timeout                                             # Set timeout attribute
        self.simulator.rcvr_socket.settimeout(self.timeout)                # Set socket timeout


    # Define the receive method
    def receive(self):
        while True:
            try:
                self.receiverArray = self.simulator.u_receive()
                if self.timeout > 0.1:
                    self.timeout = self.timeout - 0.1
                    self.numberDuplicates  = 0
                self.sendACK()
 
            # In the case of a timeout...
            except socket.timeout:
                self.resend = True
                self.simulator.u_send(self.ACKsafety)
                self.numberDuplicates = self.numberDuplicates + 1
                if self.numberDuplicates >= 3:
                    self.numberDuplicates = 0
                    self.timeout = self.timeout * 2
                    self.simulator.rcvr_socket.settimeout(self.timeout)
                    if self.timeout > 6:
                        exit()


    # Define the send method
    # Used to send ACKs back to the sender                
    def sendACK(self):
        ACKsegment = reliableSegment()
        ACKsuccess = ACKsegment.acknowledge(self.receiverArray, self.previousACKnumber)
        if ACKsuccess:
            self.previousACKnumber = ACKsegment.acknowledgementNumber
        if ACKsegment.acknowledgementNumber < 0:
            ACKsegment.acknowledgementNumber = 0
        ACKsegment.checksum = ACKsegment.checksumMethod()
        receiverArray = bytearray([ACKsegment.checksum, ACKsegment.acknowledgementNumber])
        ACKsafety = receiverArray
        self.simulator.u_send(receiverArray)


# The segment contains both data and error checking
# The segment contains the checksum, sequence number, acknowledgement number, and data
class reliableSegment(object):
    #  Define the reliableSegment class constructor
    def __init__(self, checksum = 0, sequenceNumber = 0, acknowledgementNumber = 0, data = []):
        self.data = data
        self.checksum = checksum
        self.sequenceNumber = sequenceNumber
        self.acknowledgementNumber = acknowledgementNumber
         

    # Define the checksumMethod method
    def checksumMethod(self):        
        return self.acknowledgementNumber


    # Define the checkACK method
    def checkACK(self,data):         
        checksumValue =~ data[0]    
        for i in xrange(1,len(data)):
            checksumValue = checksumValue ^ data[i]
        if checksumValue == -1:          
            return True
        else:
            return False
    

    # Define the acknowledge method
    def acknowledge(self, data, previousACKnumber):
        check = self.checkACK(data)
        if check:
            self.acknowledgementNumber = (data[2] + len(data[3:])) % 256
            if data[2] == previousACKnumber or previousACKnumber == -1:
                sys.stdout.write("{}".format(data[3:]))
                sys.stdout.flush()
                return True
        else:
            pass

        return False


if __name__ == "__main__":
    # test out BogoReceiver
    # rcvr = BogoReceiver()
    rcvr = myReceiver()
    rcvr.receive()
