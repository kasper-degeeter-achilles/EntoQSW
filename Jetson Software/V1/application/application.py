import logging
import time
from datetime import datetime
import os
import pathlib
import xml.etree.ElementTree as ElementTree
import gxipy as gx

import threading

from application.gui import MINI_WIDTH, MINI_HEIGHT
from PIL import Image

CLOSE_ALL_VALVES = bytes(str(0) + '\n', 'utf-8')

class Cage:

    def __init__(self, index: int):
        self.ID = index
        self.name = None
        self.capacity = 20000
        self.numberMales: int = 0
        self.numberFemales: int = 0
        self.requiredMales = 5
        self.requiredFemales = 20000
        self.malesComplete = False
        self.femalesComplete = False
        self.relais = None

    def add_male(self):
        if self.numberMales >= self.requiredMales:
            self.malesComplete = True
        else:
            self.numberMales += 1

    def add_female(self):
        if self.numberFemales >= self.requiredFemales:
            self.femalesComplete = True
        else:
            self.numberFemales += 1

    def setmalepercentage(self, percentage: float):
        self.requiredMales = round(self.capacity * percentage)
        self.requiredFemales = round(self.capacity * (1 - percentage))
        if self.numberMales > self.requiredMales:
            self.malesComplete = True
            logging.warning("Too many males present already")
        if self.numberFemales > self.requiredFemales:
            self.femalesComplete = True
            logging.warning("Too many females present already")

    def fire(self):
        #TODO: send message to PLC to close relais
        i = 0

class Camera:

    def __init__(self, camera_index: int) -> None:
        self.name: str = f'cam{camera_index}'
        self.serial_number: str = ''
        self.gain: float = 10.0
        self.exposure: float = 100000
        self.awb: float = 1
        self.wbr: float = 1
        self.wbb: float = 1
        self.data = None
        self.image = None

class Application:

    def __init__(self, serial_service, file_name: str, async_loop):
        self.serial_service = serial_service
        self.cameras = []
        self.cages = []
        self.capture_time = None
        self.save_directory = "/media/entoq/41DB-88AA/Output"
        self.idregex = ''
        self._load_settings(file_name)
        self.progress=0.0
        self.progressMin=0.0
        self.progressMax=100.0
        self.stopped = False
        self.rawImage = None
        self.processedImg = None
        self.async_loop = async_loop

    def stop_acquire_images(self):
        self.stopped = True

        logging.info("Stopped sorting")

    def set_ui(self, ui):
        self.ui = ui

    def set_communication_device(self, device):
        self.serial_service.device = device

    def acquire_images(self):
        self.stopped = False
        try:
            device_manager = gx.DeviceManager()
            dev_num, dev_info_list = device_manager.update_device_list()
            camera = self.cameras[0]
            if dev_num == 0:
                raise RuntimeError('No camera connected?')
   
            cam = device_manager.open_device_by_index(1)
            cam.TriggerMode.set(gx.GxSwitchEntry.ON)  # set trigger mode ON
            cam.TriggerSource.set(gx.GxTriggerSourceEntry.LINE0)  # Hardware trigger on Line 0 of camera
            # cam.TriggerDelay.set(0) #No additional trigger delay required. Take picture as fast as possible
            cam.ExposureTime.set(camera.exposure)  # set exposure

            cam.PixelFormat.set(17301505)  # TODO: check pixel format

            cam.Gain.set(camera.gain)  # sensor gain

            if camera.awb == 1:  # set auto white balance
                cam.BalanceWhiteAuto.set(1)
            else:
                cam.BalanceWhiteAuto.set(0)
                cam.BalanceRatioSelector.set(0)
                cam.BalanceRatio.set(camera.wbr)
                cam.BalanceRatioSelector.set(2)
                cam.BalanceRatio.set(camera.wbb)
        except Exception as err:
            logging.warning(f'{self.__class__.__name__.upper()}: An error occured while communicating with '
                                f'device "{camera.name}" with serial number {camera.serial_number} due to: '
                                f'{err.args[0]}')
            raise RuntimeError(f'An error occurred while trying to communicate with camera "{camera.name}" with '
                                   'serial number {camera.serial_number}')

        while not self.stopped:
            try:
                cam.stream_on() # start data acquisition
                # acquire image
                self.raw_image = cam.data_stream[0].get_image()
                self.capture_time = datetime.now().strftime('%Y-%m-%d_%Hh%Mm%Ss')
            except Exception as err:
                logging.warning(f'{self.__class__.__name__.upper()}: An error occured while communicating with '
                                f'device "{camera.name}" with serial number {camera.serial_number} due to: '
                                f'{err.args[0]}')
                raise RuntimeError(f'An error occurred while trying to communicate with camera "{camera.name}" with '
                                   'serial number {camera.serial_number}')

            # create numpy array with data from raw image
            if self.raw_image is not None:
                numpy_image = self.raw_image.get_numpy_array()
                self.processedImg = Image.fromarray(numpy_image, 'L')

                self.async_loop.run_until_complete(self._async_save_images(self.processedImg))  # TODO: for now store the image, later determine sex and send to cage


        try:
            # stop data acquisition
            cam.stream_off()
            # close device
            cam.close_device()
        except Exception as err:
            logging.warning(f'{self.__class__.__name__.upper()}: Could not communicate with device "{camera.name}" '
                            f'with serial number {camera.serial_number} due to: {err.args[0]} \n Camera not '
                            f'switched off')
            raise RuntimeError(f'An error occurred while trying to communicate with camera "{camera.name}" with '
                               'serial number {camera.serial_number}. Camera potentially not switched off. ')
        time.sleep(0.01)




    def test(self):
        self.acquire_images()
        flySex = self.determine_sex()
        self.determine_destination(flySex)
        self.ui.update()

    def fire_to_cage(self, cage):
        i = 0
        MESSAGE = bytes(str(cage.ID) + '\n', 'utf-8')
        # self.serial_service.write(MESSAGE)

    def save_image(self, img):

        sep = os.path.sep
        directory = "/media/entoq/41DB-88AA/Output"
        logging.info("Write to director {}".format(directory))
        path = pathlib.Path(directory)
        path.mkdir(parents=True, exist_ok=True)

        outfile = directory + sep + self.capture_time + ".png"
        logging.info("Writing file to {}".format(outfile))
        img.save(outfile, compress_level=3)

    def determine_sex(self):
        #TODO: send image to AI and get feedback
        i = 0
        logging.info("Male fly detected")
        return 1

    def determine_destination(self, sex: int):
        # TODO: decide which cage to send fly to
        cageSelected = False
        for cage in self.cages:
            if sex == 1 and not cage.malesComplete: #TODO: what with flies with low probability of being correct?
                self.fire_to_cage(cage)
                cageSelected = True
                cage.add_male()
                logging.info("Male fly added to Cage {}".format(cage.ID))
                logging.info("Total number of male flies in cage {} is {}".format(cage.ID, cage.numberMales))
                break
            elif sex == 0 and not cage.femalesComplete:
                self.fire_to_cage(cage)
                cageSelected = True
                cage.add_female()
                logging.info("Female fly added to Cage {}", cage.ID)
                break

            if not cageSelected and cage.ID == len(self.cages):
                cage.fire()
                logging.info("Fly added to Cage {}", cage.ID)

    def _load_settings(self, file_name: str):
        logging.debug(f'{self.__class__.__name__.upper()}: Start loading settings')
        camera_index = 0
        cage_index = 0
        try:
            settings_tree = ElementTree.parse(file_name)
            settings_root = settings_tree.getroot()

            for child in settings_root:
                if child.tag == 'camera':
                    camera_index = camera_index + 1
                    camera = Camera(camera_index)

                    for childchild in child:
                        if childchild.tag == 'name':
                            camera.name = childchild.text
                        elif childchild.tag == 'serial':
                            camera.serial_number = childchild.text
                        elif childchild.tag == 'gain':
                            camera.gain = float(childchild.text)
                        elif childchild.tag == 'exposure':
                            camera.exposure = float(childchild.text)
                        elif childchild.tag == 'rotation':
                            camera.rotation = float(childchild.text)
                        elif childchild.tag == 'awb':
                            camera.awb = float(childchild.text)
                        elif childchild.tag == 'wbr':
                            camera.wbr = float(childchild.text)
                        elif childchild.tag == 'wbb':
                            camera.wbb = float(childchild.text)

                    if camera.serial_number != '':
                        self.cameras.append(camera)
                elif child.tag == 'savedirectory':
                    self.save_directory = child.text
                elif child.tag == 'logdirectory':
                    self.log_directory = child.text
                    sep = os.path.sep
                    pathlib.Path(self.log_directory).mkdir(parents=True, exist_ok=True)
                    file_handler = logging.FileHandler(self.log_directory + sep + 'logs.log')
                    file_handler.setLevel(logging.DEBUG)
                    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
                    logging.getLogger().addHandler(file_handler)
                elif child.tag == 'idregex':
                    self.idregex = child.text
                elif child.tag == 'cage':
                    cage_index +=1
                    cage = Cage(cage_index)
                    for childinchild in child:
                        if childinchild.tag == 'name':
                            cage.name = childinchild.text
                        elif childinchild.tag == 'relais':
                            cage.relais = int(childinchild.text)
                        elif childinchild.tag == 'capacity':
                            cage.capacity = int(childinchild.text)
                    self.cages.append(cage)



        except ElementTree.ParseError as err:
            logging.critical(f'{self.__class__.__name__.upper()}: An error occurred while trying to load {file_name}: {err.msg}')
            exit()
        except FileNotFoundError as err:
            logging.critical(f'{self.__class__.__name__.upper()}: An error occurred while trying to load {file_name}: {err.strerror}')
            exit()

        logging.debug(f'{self.__class__.__name__.upper()}: Settings loaded')

    def _async_task(function):
        threading.Thread(target=function).start()

    async def _async_save_images(self,img):
        return self.save_image(img)