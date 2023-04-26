import asyncio
import sys

import nest_asyncio
import logging

from ttkthemes import ThemedTk

from application.application import Application
from application.gui import UI
from application.serial import SerialCommunicator
from application.notgui import notUI

nest_asyncio.apply()

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

stdout_handler = logging.StreamHandler(sys.stdout)
stdout_handler.setLevel(logging.DEBUG)
stdout_handler.setFormatter(formatter)

logging.getLogger().addHandler(stdout_handler)


def main(async_loop):
    try:
        window = ThemedTk(theme='arc')
        window.title('ENTOQ Fly Monitoring')
        window.geometry()
        logging.debug('Instantiating services')
        display = True
    except:
        logging.warning("Could not open a display")
        display = False


    serial_service = SerialCommunicator()
    main_service = Application(serial_service, '/home/entoq/Documents/EntoQSW/P-02894-ENT-Insect-selector/Jetson Software/settings.xml', async_loop)
    if display:
        UI(window, main_service, async_loop)
        logging.debug('Starting Tkinter mainloop')
        window.mainloop()
    else:
        notUI(main_service,async_loop)





if __name__ == '__main__':
    async_loop = asyncio.get_event_loop()
    main(async_loop)
