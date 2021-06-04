
import socket
import io
import time
import typing
import struct
import util
import util.logging
import threading
from threading import Timer

sock_g = []
packet_g = []

# Timer class
class RepeatTimer(Timer):
    def run(self):
        while not self.finished.wait(self.interval):
            self.function(*self.args, **self.kwargs)

def timeoutInterval(estRTT, sampleRTT, devRTT):
    insideEstRTT = (1 - 0.125) * estRTT + (0.125 * sampleRTT)
    insideDevRTT = (1 - 0.25) * devRTT * 0.25 * (abs(sampleRTT - estRTT))
    timeout = insideEstRTT + insideDevRTT
    return insideEstRTT, insideDevRTT, timeout

#Resends Last Packet to Not Be Acked
def resendPacket():
    sock_g.send(packet_g)                           #Global Variable
    chunk, seqNum = parsePacket(packet_g)             #Gets Sequence Number to Print
    print("RESENDING PACKET: ", seqNum)

#Puts a Chunk and its Corresponding Sequence Number in a Packet
#and Encodes the Value to be Sent on the Socket
def makePacket(seqNum, chunk):
    packet = chunk.decode("utf-8")                     #Add Chunk to Packet as String
    packet += ";" + str(seqNum)                           #Separate Chunk and Add Sequence Number to Packet
    return bytes(str.encode(packet))

#Deconstructs a Packet Built in makePacket
#Splits the Packet into a Chunk of Data and a Sequence number
#Then Returns the Values as Separate Variables
def parsePacket(packet):
    packetData = packet.decode("utf-8")                  #Converts Input Packet to String
    splitData = packetData.split(";")                   #Separates Chunk and Sequence Number
    chunk = splitData[0]
    seqNum = splitData[1]
    return chunk, seqNum


#Takes in a Socket and a Given Data Input and Reliabily Sends data in the Correct Order
def send(sock: socket.socket, data: bytes):
    sock.setblocking(0)                                         #Keeps Program from Waiting to Receive Information
    global packet_g                                             #Used for Resending Packets
    global sock_g                                               #Used for Resending Packets
    sock_g = sock
    chunk_size = util.MAX_PACKET                                #Allows Room for Sequence Number in Chunk
    holdChunks = []                                             #Holds the Chunks of Data
    seqNum = 0
    offsets = range(0, len(data), util.MAX_PACKET - 8)          #Moves Through Data at Range of Chunk not Range of Packet
    count = 0
    isAcked = None
    timeOut = 1.5

    #Creates a Packet for all Chunks in Data and Adds Sequence Number
    for chunk in [data[i:i + chunk_size - 8] for i in offsets]:
        packet = makePacket(seqNum, chunk)
        holdChunks.append(packet)
        seqNum += len(chunk)

    firstRun = True                                             #Used to Send First Chunk with Ack Needed
    while True:
        #Try to Read Information from the socket
        #If no Info, Skip
        try:
            ackData = sock.recv(util.MAX_PACKET)
            timer.cancel()
            ack = int.from_bytes(ackData, "big")
            print("***************************************************************************************************************************")
            print("ACKNOWLEDGMENT RECEIVED: ", ack)
            print("***************************************************************************************************************************")
            isAcked = True
            count += 1
        except:
            #NO INFORMATION RECEIVED
            isAcked = None

        #If all Packets Have Been Acked End Transmission
        if(count >= len(holdChunks)):
            print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
            print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
            print("ALL DATA SENT AND ACKNOWLEDGED")
            print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
            print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
            break

        #Send a Packet if There has Been an Acknowledgement or it is the First Iteration
        if(isAcked or firstRun):
            sock.send(holdChunks[count])                          #Sends the Packet Depending on Ack Count
            timer = RepeatTimer(timeOut, resendPacket)      #Creates a Timer for the New Packet and Resends the Packet if not Cancelled
            timer.start()
            packet_g = holdChunks[count]                          #Sets Value in Case of Resend
            firstRun = False


#Waits for Incoming Information from a Socket and Acknowledges that a Packet
#has Been Received. It Ensures that a Specific Packet will only be Written Once
def recv(sock: socket.socket, dest: io.BufferedIOBase) -> int:
    pause = .1
    num_bytes = 0
    lastSeqNum = -1                                         #Checks if Packet has Already been Recieved
    while True:
        data = sock.recv(util.MAX_PACKET)
        if(not data):
            break
        chunk, seqNum = parsePacket(data)                  #Separates Packet into Chunk and Sequence Number
        print("***************************************************************************************************************************")
        print("***************************************************************************************************************************")
        print("Received sequence number:" , seqNum)
        print("***************************************************************************************************************************")
        ackNum = int(seqNum) + len(chunk)               #Creates Ack Number Using Chunk Length and Sequence Number
        ack = ackNum.to_bytes(3, "big")
        print("Sending Ack:", ackNum)
        print("***************************************************************************************************************************")
        print("***************************************************************************************************************************")
        sock.send(ack)                                      #Send Acknowledgment for Packet

        #Checks if Chunk has Already Been Written
        if(not lastSeqNum == seqNum):
            dest.write(chunk.encode())
            num_bytes += len(chunk)
            lastSeqNum = seqNum
        dest.flush()
    return num_bytes
