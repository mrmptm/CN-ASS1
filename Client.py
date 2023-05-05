import tkinter
from tkinter import *
import tkinter.messagebox as messageBox
from PIL import Image, ImageTk
import socket, threading, sys, traceback, os
import time

from RtpPacket import RtpPacket

CACHE_FILE_NAME = "cache-"
CACHE_FILE_EXT = ".jpg"


class Client:
    INIT = 0
    READY = 1
    PLAYING = 2
    state = INIT

    SETUP = 0
    PLAY = 1
    PAUSE = 2
    TEARDOWN = 3

    # Initiation..
    def __init__(self, master, serveraddr, serverport, rtpport, filename):
        self.master = master
        self.master.protocol("WM_DELETE_WINDOW", self.handler)
        self.createWidgets()
        self.serverAddr = serveraddr
        self.serverPort = int(serverport)
        self.rtpPort = int(rtpport)
        self.fileName = filename
        self.rtspSeq = 0
        self.sessionId = 0
        self.requestSent = -1
        self.teardownAcked = 0
        self.connectToServer()
        self.frameNbr = 0
        self.lossRate = 0
        self.dataRate = 0
        self.startTime = 0

    # THIS GUI IS JUST FOR REFERENCE ONLY, STUDENTS HAVE TO CREATE THEIR OWN GUI
    def createWidgets(self):
        """Build GUI."""
        # Create Setup button
        # self.setup = Button(self.master, width=20, padx=3, pady=3)
        # self.setup["text"] = "Setup"
        # self.setup["command"] = self.setupMovie
        # self.setup.grid(row=1, column=0, padx=2, pady=2)

        # Create Play button
        self.start = Button(self.master, width=40, padx=3, pady=3, bg="#82E0AA")
        self.start["text"] = "Play"
        self.start["command"] = self.playMovie
        self.start.grid(row=1, column=1, padx=2, pady=2)
        self.start.config(state=tkinter.NORMAL)

        def onEnterPlay(e):
            self.start["background"] = "#ABEBC6"

        def onLeavePlay(e):
            self.start["background"] = "#82E0AA"

        self.start.bind("<Enter>", onEnterPlay)
        self.start.bind("<Leave>", onLeavePlay)

        # Create Pause button
        self.pause = Button(self.master, width=40, padx=3, pady=3, bg="#F7DC6F")
        self.pause["text"] = "Pause"
        self.pause["command"] = self.pauseMovie
        self.pause.grid(row=1, column=1, padx=2, pady=2)
        self.pause.config(state=tkinter.DISABLED)
        self.pause.grid_forget()

        def onEnterPause(e):
            self.pause["background"] = "#F9E79F"

        def onLeavePause(e):
            self.pause["background"] = "#F7DC6F"

        self.pause.bind("<Enter>", onEnterPause)
        self.pause.bind("<Leave>", onLeavePause)

        # Create Teardown button
        self.teardown = Button(self.master, width=20, padx=3, pady=3, bg="#F1948A")
        self.teardown["text"] = "Teardown"
        self.teardown["command"] = self.exitClient
        self.teardown.grid(row=1, column=3, padx=2, pady=2)

        def onEnterTeardown(e):
            self.teardown["background"] = "#F5B7B1"

        def onLeaveTeardown(e):
            self.teardown["background"] = "#F1948A"

        self.teardown.bind("<Enter>", onEnterTeardown)
        self.teardown.bind("<Leave>", onLeaveTeardown)

        # Create a label to display the movie
        self.label = Label(self.master, height=19)
        self.label.grid(row=0, column=0, columnspan=4, sticky=W + E + N + S, padx=5, pady=5)

    def setupMovie(self):
        """Setup button handler."""
        # TODO
        if self.state == self.INIT:
            self.sendRtspRequest(self.SETUP)

    def exitClient(self):
        """Teardown button handler."""
        self.sendRtspRequest(self.TEARDOWN)
        self.master.destroy()
        try:
            os.remove(CACHE_FILE_NAME + str(self.sessionId) + CACHE_FILE_EXT)
        except:
            pass

    # TODO

    def pauseMovie(self):
        """Pause button handler."""

        # TODO
        if (self.state == self.PLAYING):
            self.sendRtspRequest(self.PAUSE)
            self.pause.grid_forget()
            self.pause.config(state=tkinter.DISABLED)

            self.start.grid(row=1, column=1, padx=2, pady=2)
            self.start.config(state=tkinter.NORMAL)
            self.start["text"] = "Resume"

    def playMovie(self):
        """Play button handler."""
        if self.state == self.INIT:
            print("SET UP RUN")
            self.setupMovie()
            self.frameNbr = 0

        if self.state == self.READY:
            threading.Thread(target=self.listenRtp).start()
            self.play_event = threading.Event()
            self.play_event.set()
            self.sendRtspRequest(self.PLAY)
            self.start.grid_forget()
            self.start.config(state=tkinter.DISABLED)
            self.pause.grid(row=1, column=1, padx=2, pady=2)
            self.pause.config(state=tkinter.NORMAL)
            self.startTime = time.perf_counter()

    def CalculateLossRate(self, newframeNum):
        loss_count = self.lossRate * self.frameNbr
        self.lossRate = (loss_count + (newframeNum - self.frameNbr - 1)) / newframeNum
        return self.lossRate

    def CalculateDataRate(self, data, lastTimeReceive):
        duration = time.perf_counter() - lastTimeReceive
        dataLength = len(data)
        self.dataRate = int(dataLength / duration)
        return self.dataRate

    def listenRtp(self):
        """Listen for RTP packets."""
        # TODO
        while True:
            try:
                rtpPacket = self.client_rptSocket.recv(20480)
                if rtpPacket:
                    packetResolver = RtpPacket()
                    packetResolver.decode(rtpPacket)
                    # Check if this is he last frame
                    if packetResolver.isLastData():
                        self.pauseMovie()
                        self.start["text"] = "Play"
                        self.state=self.INIT
                        self.sessionId = 0
                        self.client_rptSocket.close()
                    ###############
                    newframeNum = packetResolver.seqNum()
                    print("Loss rate:", self.CalculateLossRate(newframeNum))
                    data = packetResolver.getPayload()
                    print("Data rate:", self.CalculateDataRate(data, self.startTime))
                    self.startTime = time.perf_counter()
                    if newframeNum > self.frameNbr:
                        self.frameNbr = newframeNum
                        self.updateMovie(self.writeFrame(data))
            except:
                if self.play_event.isSet():
                    if self.teardownAcked == 1:
                        self.client_rptSocket.shutdown(socket.SHUT_RDWR)
                        self.client_rptSocket.close()
                else:
                    break

    def writeFrame(self, data):
        """Write the received frame to a temp image file. Return the image file."""
        cachename = CACHE_FILE_NAME + str(self.sessionId) + CACHE_FILE_EXT
        file = open(cachename, "wb")
        file.write(data)
        file.close()

        return cachename

    def updateMovie(self, imageFile):
        """Update the image file as video frame in the GUI."""
        view = ImageTk.PhotoImage(Image.open(imageFile))
        self.label.configure(image=view, height=288)
        self.label.image = view

    def connectToServer(self):
        """Connect to the Server. Start a new RTSP/TCP session."""
        self.client_rtspSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        ADDRESS = (self.serverAddr, self.serverPort)
        print("Server address", self.serverAddr)
        self.client_rtspSocket.connect(ADDRESS)
        print("connected")

    def sendRtspRequest(self, requestCode):
        """Send RTSP request to the server."""
        if requestCode == self.SETUP:
            if self.state != self.INIT:
                return
            threading.Thread(target=self.recvRtspReply).start()
            self.rtspSeq = 1
            setup_str = "SETUP " + str(self.fileName) + " RTSP/1.0"
            seq_str = "CSeq " + str(self.rtspSeq)
            transport_str = "Transport: RTP/UDP; client_port= " + str(self.rtpPort)
            request = setup_str + "\n" + seq_str + "\n" + transport_str
            self.requestSent = self.SETUP

        elif requestCode == self.PLAY:
            if self.state != self.READY:
                return
            self.rtspSeq = self.rtspSeq + 1
            setup_str = "PLAY " + str(self.fileName) + " RTSP/1.0"
            seq_str = "CSeq " + str(self.rtspSeq)
            session_str = "Session: " + str(self.sessionId)
            request = setup_str + "\n" + seq_str + "\n" + session_str
            self.requestSent = self.PLAY
        elif requestCode == self.PAUSE:
            if self.state != self.PLAYING:
                return
            self.rtspSeq = self.rtspSeq + 1
            setup_str = "PAUSE " + str(self.fileName) + " RTSP/1.0"
            seq_str = "CSeq " + str(self.rtspSeq)
            session_str = "Session: " + str(self.sessionId)
            request = setup_str + "\n" + seq_str + "\n" + session_str
            self.requestSent = self.PAUSE
        elif requestCode == self.TEARDOWN:
            self.rtspSeq = self.rtspSeq + 1
            setup_str = "TEARDOWN " + str(self.fileName) + " RTSP/1.0"
            seq_str = "CSeq " + str(self.rtspSeq)
            session_str = "Session: " + str(self.sessionId)
            request = setup_str + "\n" + seq_str + "\n" + session_str
            self.requestSent = self.TEARDOWN
        else:
            return
        self.client_rtspSocket.send(request.encode('utf-8'))

    def recvRtspReply(self):
        """Receive RTSP reply from the server."""
        while True:
            recv_mess = self.client_rtspSocket.recv(1024)
            if recv_mess:
                self.parseRtspReply(recv_mess.decode('utf-8'))

            if self.requestSent == self.TEARDOWN:
                try:
                    self.client_rtspSocket.shutdown()
                    self.client_rtspSocket.close()
                except:
                    pass
                break

    def parseRtspReply(self, data):
        """Parse the RTSP reply from the server."""

        lines = data.split('\n')
        seqNum = int(lines[1].split(' ')[1])
        if seqNum == self.rtspSeq:
            session = int(lines[2].split(' ')[1])
            # New RTSP session ID
            if self.sessionId == 0:
                self.sessionId = session
            # Process only if the session ID is the same
            if self.sessionId == session:
                if int(lines[0].split(' ')[1]) == 200:
                    if self.requestSent == self.SETUP:
                        self.state = self.READY
                        # Open RTP port.
                        self.openRtpPort()
                        self.playMovie()
                    elif self.requestSent == self.PLAY:
                        self.state = self.PLAYING
                    elif self.requestSent == self.PAUSE:
                        self.state = self.READY
                        self.play_event.clear()
                    elif self.requestSent == self.TEARDOWN:
                        self.state = self.INIT
                        # Flag the teardownAcked to close the socket.
                        self.teardownAcked = 1

    def openRtpPort(self):
        """Open RTP socket binded to a specified port."""
        self.client_rptSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        CLIENT_IP = socket.gethostbyname(socket.gethostname())
        ADDR = (CLIENT_IP, self.rtpPort)
        self.client_rptSocket.bind(ADDR)

    def handler(self):
        """Handler on explicitly closing the GUI window."""
        self.pauseMovie()
        if messageBox.askokcancel("Confirm", "Do you want to quit?"):
            self.exitClient()
        else:
            self.playMovie()
# TODO
