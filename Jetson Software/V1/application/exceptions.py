from serial import SerialException


class NoDeviceAvailableException(Exception):
    pass


class TooManyDevicesAvailableException(Exception):
    def __init__(self, devices, *args: object) -> None:
        self.devices = devices
        super().__init__(*args)


class UnableToOpenConnectionException(SerialException):
    pass


class MessageTransportationException(Exception):
    pass
