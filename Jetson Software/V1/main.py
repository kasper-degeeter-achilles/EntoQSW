import asyncio
import sys

import nest_asyncio
import logging



from ttkthemes import ThemedTk

from application.application import Application
from application.gui import UI
from application.serial import SerialCommunicator

nest_asyncio.apply()

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

stdout_handler = logging.StreamHandler(sys.stdout)
stdout_handler.setLevel(logging.DEBUG)
stdout_handler.setFormatter(formatter)

logging.getLogger().addHandler(stdout_handler)

def main(async_loop):
    window = ThemedTk(theme='arc')
    window.title('ENTOQ Fly Monitoring')
    window.geometry('1000x700')

    logging.debug('Instantiating services')
    serial_service = SerialCommunicator()
    main_service = Application(serial_service, 'settings.xml', async_loop)
    UI(window, main_service, async_loop)
    logging.debug('Starting Tkinter mainloop')
    window.mainloop()


if __name__ == '__main__':
    async_loop = asyncio.get_event_loop()
    main(async_loop)