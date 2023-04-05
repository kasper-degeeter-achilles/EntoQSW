import logging
from typing import Optional

import serial
from retry.api import retry_call
from serial import PortNotOpenError, SerialTimeoutException, SerialException
import serial.tools.list_ports
import time

from application.exceptions import MessageTransportationException, UnableToOpenConnectionException, \
    NoDeviceAvailableException, TooManyDevicesAvailableException


class SerialCommunicator:
    _READ_TIMEOUT_SECONDS = 6
    _WRITE_TIMEOUT_SECONDS = 6
    _RETRIES = 5

    def __init__(self) -> None:
        self.connection: Optional[serial.Serial] = None
        self.device: Optional[str] = None

    def __del__(self):
        self._disconnect()

    def write(self, data: bytes):
        """"
        :raises MessageTransportationException, UnableToOpenConnection, NoDeviceAvailable or TooManyDevicesAvailable
        """
        try:
            self._connect_if_necessary()
            retry_call(self._try_writing, fargs=[data], delay=2, backoff=1, tries=self._RETRIES, logger=None)
        except MessageTransportationException as err:
            self._disconnect()
            raise err

    def _disconnect(self):
        logging.debug(f'{self.__class__.__name__.upper()}: Closing connection')
        if self.connection is not None:
            self.connection.close()
        self.connection = None

    def _try_writing(self, data: bytes):
        """"
        :raises MessageTransportationException, UnableToOpenConnection
        """
        try:
            logging.debug(f'{self.__class__.__name__.upper()}: Trying to write data to connected device...')
            self.connection.write(data)
            logging.debug(f'{self.__class__.__name__.upper()}: Trying to read acknowledgement...')
            time.sleep(0.2)
            acknowledgment = self.connection.readline()
            assert (data.strip() == acknowledgment.strip())
        except (PortNotOpenError, SerialException, SerialTimeoutException) as err:
            logging.warning(f'{self.__class__.__name__.upper()}: {err.args[0]}')
            self._disconnect()
            self._try_connecting()
            raise MessageTransportationException()
        except AssertionError:
            logging.warning(f'{self.__class__.__name__.upper()}: Send and received data ar not the same! '
                            f'Sent {data} - received {acknowledgment}')
            self._disconnect()
            self._connect_if_necessary()
            raise MessageTransportationException()
        except AttributeError:
            logging.warning(f'{self.__class__.__name__.upper()}: Connection not open')
            self._connect_if_necessary()
            raise UnableToOpenConnectionException()
        logging.debug(f'{self.__class__.__name__.upper()}: Successfully communicated')

    def _connect_if_necessary(self):
        """"
        :raises UnableToOpenConnection, NoDeviceAvailable or TooManyDevicesAvailable
        """
        if self.connection is None:
            logging.debug(f'{self.__class__.__name__.upper()}: No connection, will try to connect first')
            self._get_serial_device_if_needed()

            logging.debug(f'{self.__class__.__name__.upper()}: Trying to connect to: {self.device}')
            try:
                self._try_connecting()
            except SerialException as err:
                logging.warning(f'{self.__class__.__name__.upper()}: Failed to open connection to device')
                raise UnableToOpenConnectionException(err)

            logging.debug(f'{self.__class__.__name__.upper()}: Successfully connected to device')
            self.connection.reset_input_buffer()
            self.connection.reset_output_buffer()

    def _try_connecting(self):
        """"
        :raises SerialException
        """
        try:
            self.connection = serial.Serial(self.device, 115200, timeout=self._READ_TIMEOUT_SECONDS,
                                            write_timeout=self._WRITE_TIMEOUT_SECONDS)
            time.sleep(5.5)
            self.connection.readline()
        except SerialException as err:
            logging.warning(f'{self.__class__.__name__.upper()}: {err.args[0]}')
            raise err

    def _get_serial_device_if_needed(self):
        """"
        :raises NoDeviceAvailable or TooManyDevicesAvailable
        """
        if self.device is None:
            port_list = serial.tools.list_ports.comports()
            if len(port_list) == 0:
                logging.debug(f'{self.__class__.__name__.upper()}: No serial device available to connect to')
                raise NoDeviceAvailableException()
            if len(port_list) > 1:
                logging.debug(f'{self.__class__.__name__.upper()}: Multiple COM ports appear to be populated')
                raise TooManyDevicesAvailableException([port.device for port in port_list])
            else:
                self.device = port_list[0].device
