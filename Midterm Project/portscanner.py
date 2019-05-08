#!/usr/bin/env python3

import sys
import socket
import errno
from tabulate import tabulate 


# Defining error codes
errno.errorcode[errno.EHOSTUNREACH] = "Host Unreachable"
errno.errorcode[errno.ECONNREFUSED] = "No Response"
errno.errorcode[errno.EAGAIN] = "Closed"
errno.errorcode[0] = "Open"


data = []


# Defining the OSDeducer method to determine the OS of the host
def __OSDeducer__(ttl, tcp):
    if ttl == 64:
        if tcp == 5820:
            return "Linux (Kernel 2.4 and 2.6)"
        elif tcp == 5720:
            return "Google's Customized Linux"
        elif tcp == 65535:
            return "FreeBSD"
    elif ttl == 128:
        if tcp == 65535:
            return "Windows XP"
        elif tcp == 8192:
            return "Windows 7, Vista, and Server 2008"
    elif ttl == 255:
        if tcp == 4128:
            return "Cisco Router (IOS 12.4)"
    return "Undetermined OS"


# Defining the scan method to check each port
def __scan__(host,port):
    try:

        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP)
        s.settimeout(0.5)
        result = s.connect_ex((host, port))
    
        try:
            server = ' '.join((socket.getservbyport(port)).split())
        
        except socket.error:
            server = ""

        if result == 0:
            ttl = s.getsockopt(socket.IPPROTO_IP, socket.IP_TTL)
            tcp = s.getsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF) - 1
            os = __OSDeducer__(ttl, tcp)
            data.append([host, port, errno.errorcode[result], server, ttl, tcp, os])
        s.close()

    except KeyboardInterrupt:
        print("Error: User exit program")
        sys.exit()
    except socket.gaierror:
        print("Error: Host %s:%s not found" % (host, port))
        sys.exit()
    except socket.error:
        print("Error: Could not connect to server %s:%s..." % (host, port))
        sys.exit()
    

# Defining the main method to:
# - Parse through the user input
# - Call the scan method
# - Tabulate the data
if __name__ == '__main__':
    args = sys.argv[1:]
    # The first input argument is the host
    host = args[0]
    # If there is only one input argument, then check the first 1024 ports
    if (len(args) == 1):
        start, end = (0, 1024)
    # Otherwise there are two input arguments, find the port range 
    elif (args[1] == "-p"):
        start, end = map(int, args[2].split(":"))

    portrange = list(range(start, end + 1))
    for port in portrange:
        __scan__(host, port)
        print(port)
    print(tabulate(data, headers=['Host', 'Port', 'Status', 'Protocol', 'Initial TTL', 'TCP Window', 'OS'], tablefmt='orgtbl'))
