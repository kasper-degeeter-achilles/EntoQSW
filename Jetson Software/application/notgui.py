import sys
import threading
from tkinter import ttk, messagebox
import logging

from application.serial import TooManyDevicesAvailableException, NoDeviceAvailableException, \
    UnableToOpenConnectionException, MessageTransportationException

class notUI:

    def __init__(self, main_service, async_loop):
        self._main_service = main_service
        self.async_loop = async_loop
        self.start_sorting()

    def start_sorting(self):
        self._main_service.activate_camera()
        logging.info('Sorting started')
        while True:
            try:
                self.async_loop.run_until_complete(self._async_acquire_images())
            except TooManyDevicesAvailableException as err:
                logging.error("Too many devices")
            except NoDeviceAvailableException:
                logging.error("No devices")
            except UnableToOpenConnectionException:
                logging.error("Cannot open serial connection")
            except MessageTransportationException:
                logging.error("An error occurred while communicating with the device")


    def _async_task(function):
        threading.Thread(target=function).start()

    async def _async_acquire_images(self):
        return self._main_service.acquire_images()

    async def _async_start_sorting(self):
        return self.start_sorting()