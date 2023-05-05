""""
:summary: class representing bidirectional asynchronous (UART) serial communication 
          with json strings 
:Date: 2023-04-28
:Authors:
    - Victor Coucke
 """


import logging
import serial
import serial.tools.list_ports
import time
import json

from application.exceptions import *

class SerialJSON:
    _READ_TIMEOUT_SECONDS = 5
    _WRITE_TIMEOUT_SECONDS = 1
    _RETRIES = 5
    _TERMINATOR = b'\n'

    def __init__(self, baudrate) -> None:
        self.port = None
        self.baudrate = baudrate
        self.dtrEnable=False
        self.s=None
        self.counter = 0
        self.parsestream = bytearray()
        self.parselength = 0
        self.parsebegin = 0
        self.parseend = 0
        self.received_serial_data = None

    def __del__(self):
        self.close()

    def openserial(self, port=None, baudrate=None, dtrEnable=False):
        if(port is None):
            self.openAutoPort(baudrate, dtrEnable)
        else:
            attempt=0
            looping=True
            self.port=port
            self.baudrate=baudrate
            self.s=None
            self.dtrEnable=dtrEnable

            while(looping):
                try:
                    logging.debug("Trying to open serial port")
                    self.close()
                    self.s = serial.Serial(port, baudrate, timeout=self._READ_TIMEOUT_SECONDS, write_timeout=self._WRITE_TIMEOUT_SECONDS, dsrdtr=dtrEnable)
                    self.s.flush()
                    if(self.s is not None):
                        looping=False
                except (NameError, serial.SerialException):
                    logging.exception("An exception was thrown!")
                    logging.warning("reconnecting ...")
                    self.openserial(self.port, self.baudrate, self.dtrEnable)
                    attempt=attempt+1
                except Exception as e:
                    logging.exception("An exception was thrown!")
                    logging.warning("possible fatal serial error , reconnecting ...")
                    self.openserial(self.port, self.baudrate, self.dtrEnable)
                    attempt=attempt+1
   
            if(attempt==self._RETRIES):
                looping=False
                logging.error("retried to open serial port 5 times after fatal error")
                raise UnableToOpenConnectionException
    
    def openAutoPort(self, baudrate, dtrEnable):
        port=self.autoGetPort()
        if(port is not None):
            self.openserial(port, baudrate, dtrEnable)

    def close(self):
        if self.s is not None:
            self.s.close()
        self.s = None

    def writeandreadJSON(self, data: dict):
        data = self.addcounter(data)
        attempt = 0
        self.writeJSON(data)
        j = self.waitandreadJSON()
        logging.debug(j)

        
    def addcounter(self, data: dict):
        self.counter+=1
        if self.counter == 128:
            self.counter = 0
        message={
            "count": self.counter
        }
        data.update(message)
        return data

    def writeJSON(self, data: dict):
        data = self.addcounter(data)
        d=json.dumps(data).encode()
        logging.info(d)
        attempt=0
        looping=True
        while(looping):
            try:
                self.s.write(d)
                self.s.write(self._TERMINATOR) #our terminator
                if(self.s is not None):
                    looping=False
                logging.debug("Serial message written")
            except (NameError, serial.SerialException):
                logging.exception("An exception was thrown!")
                logging.warning("reconnecting ...")
                self.openserial(self.port, self.baudrate, self.dtrEnable)
                attempt=attempt+1
            except Exception as e:
                logging.exception("An exception was thrown!")
                logging.warning("possible fatal serial error , reconnecting ...")
                self.openserial(self.port, self.baudrate, self.dtrEnable)
                attempt=attempt+1
            if(attempt==self._RETRIES):
                looping=False
                logging.error("retried to open serial port 5 times after fatal error")
                raise UnableToOpenConnectionException

    def readJSON(self):
        attempt=0
        looping=True
        while(looping):
            try:
                if not self.s.in_waiting:
                    looping=False
                else:
                    c = self.s.read(1)
                    if(c == self._TERMINATOR):
                        j = json.loads(self.parsestream)
                        self.parsestream.clear()
                        return j
                    else:
                        self.parsestream.extend(c)
            except (NameError, serial.SerialException):
                logging.exception("An exception was thrown!")
                logging.warning("reconnecting ...")
                self.openserial(self.port, self.baudrate, self.dtrEnable)
                attempt=attempt+1

            except (json.JSONDecodeError):
                logging.error("Json Decode Error")
                self.parsestream.clear()

            except (UnicodeDecodeError):
                logging.error("unicode decode error")
                self.parsestream.clear()

            except Exception as e:
                logging.exception("An exception was thrown!")
                logging.warning("possible fatal serial error , reconnecting ...")
                self.openserial(self.port, self.baudrate, self.dtrEnable)
                attempt=attempt+1
   
            if(attempt==self._RETRIES):
                looping=False
                logging.error("retried to open serial port 5 times after fatal error")
                raise UnableToOpenConnectionException

        return None

    def waitandreadJSON(self):
        start_time = time.monotonic()
        attempt=0
        looping=True
        while(looping) and (time.monotonic() - start_time < self._READ_TIMEOUT_SECONDS):
            try:
                if not self.s.in_waiting:
                    time.sleep(0.1)
                    logging.debug('waiting for reply')
                else:
                    logging.debug("Something was received")
                    c = self.s.read(1)
                    if(c == self._TERMINATOR):
                        j = json.loads(self.parsestream)
                        self.parsestream.clear()
                        return j
                    else:
                        self.parsestream.extend(c)
            except (NameError, serial.SerialException):
                logging.exception("An exception was thrown!")
                logging.warning("reconnecting ...")
                self.openserial(self.port, self.baudrate, self.dtrEnable)
                attempt=attempt+1

            except (json.JSONDecodeError):
                logging.error("Json Decode Error")
                self.parsestream.clear()

            except (UnicodeDecodeError):
                logging.error("unicode decode error")
                self.parsestream.clear()

            except Exception as e:
                logging.exception("An exception was thrown!")
                logging.warning("possible fatal serial error , reconnecting ...")
                self.openserial(self.port, self.baudrate, self.dtrEnable)
                attempt=attempt+1
   
            if(attempt==self._RETRIES):
                looping=False
                logging.error("retried to open serial port 5 times after fatal error")
                raise UnableToOpenConnectionException

        return None


    def autoGetPort(self):
        logging.debug("Searching COM ports");
        port_list = serial.tools.list_ports.comports()
        (port_list)
        if len(port_list) == 0:
            logging.debug(f'{self.__class__.__name__.upper()}: No serial device available to connect to')
            raise NoDeviceAvailableException()
        if len(port_list) > 1:
            logging.debug(len(port_list), " serial ports present")
            logging.debug(f'{self.__class__.__name__.upper()}: Multiple COM ports appear to be populated')
            raise TooManyDevicesAvailableException([port.device for port in port_list])
        else:
            return port_list[0].device
        

    def update(self):
        j = self.readJSON()
        if j is not None:
            logging.info(j)
            self.received_serial_data = j