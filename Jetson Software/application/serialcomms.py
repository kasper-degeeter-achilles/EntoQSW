import logging

import serial
import serial.tools.list_ports
import time
import json

from application.exceptions import MessageTransportationException, UnableToOpenConnectionException, \
    NoDeviceAvailableException, TooManyDevicesAvailableException


class SerialJSON:
    _READ_TIMEOUT_SECONDS = 6
    _WRITE_TIMEOUT_SECONDS = 6
    _RETRIES = 5

    def __init__(self, baudrate) -> None:
        self.port = None
        self.baudrate=baudrate
        self.dtrEnable=False
        self.s=None

    def __del__(self):
        self.close()

    def openserial(self, port, baudrate, dtrEnable):
        if(port is None):
            self.openAutoPort(baudrate, dtrEnable)
        else:
            attempt=0
            looping=True
            self.port=port
            self.baudrate=baudrate
            self.s=None
            self.parsestream=bytearray()
            self.dtrEnable=dtrEnable

            while(looping):
                try:
                    print("trying to open serial port")
                    self.close()
                    self.s = serial.Serial(port, baudrate, timeout=self._READ_TIMEOUT_SECONDS, write_timeout=self._WRITE_TIMEOUT_SECONDS, dsrdtr=dtrEnable)
                    if(self.s is not None):
                        looping=False
                except:
                    print("failed to open serial port")
                    time.sleep(1)
                attempt=attempt+1
                if(attempt==self._RETRIES):
                    looping=False
    
    def openAutoPort(self, baudrate, dtrEnable):
        port=self.autoGetPort()
        if(port is not None):
            self.openserial(port, baudrate, dtrEnable)

    def close(self):
        if self.s is not None:
            self.s.close()
        self.s = None

    def writeJSON(self, data: dict):
        d=json.dumps(data).encode()
        print(d)
        attempt=0
        looping=True
        while(looping):
            try:
                self.s.write(d)
                self.s.write(b'\x00') #our terminator
                if(self.s is not None):
                    looping=False
                print("written")
            except:
                self.openserial(self.port, self.baudrate, self.dtrEnable)
            attempt=attempt+1
            if(attempt==self._RETRIES):
                looping=False

    def readJSON(self):
        attempt=0
        looping=True
        while(looping):
            try:
                if not self.s.in_waiting:
                    looping=False
                else:
                    c = s.read(1)
                    if(c == b'\x00'):
                        j = json.loads(parsestream)
                        parsestream.clear()
                        return j
                    else:
                        parsestream.extend(c)
            except:
                self.openserial(self.port, self.baudrate, self.dtrEnable)
                attempt=attempt+1
            if(attempt==self._RETRIES):
                looping=False
        return None

    def waitandreadJSON(self):
        attempt=0
        looping=True
        while(looping):
            try:
                if not self.s.in_waiting:
                    tile.sleep(0.1)
                else:
                    c = s.read(1)
                    if(c == b'\x00'):
                        j = json.loads(parsestream)
                        parsestream.clear()
                        return j
                    else:
                        parsestream.extend(c)
            except:
                self.openserial(self.port, self.baudrate, self.dtrEnable)
                attempt=attempt+1
            if(attempt==self._RETRIES):
                looping=False
        return None

    def autoGetPort(self):
        print("searching COM ports");
        port_list = serial.tools.list_ports.comports()
        print(port_list)
        if len(port_list) == 0:
            logging.debug(f'{self.__class__.__name__.upper()}: No serial device available to connect to')
            raise NoDeviceAvailableException()
        if len(port_list) > 1:
            print(len(port_list), " serial ports present")
            logging.debug(f'{self.__class__.__name__.upper()}: Multiple COM ports appear to be populated')
            raise TooManyDevicesAvailableException([port.device for port in port_list])
        else:
            return port_list[0].device