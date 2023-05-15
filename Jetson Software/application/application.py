import logging
import time
from datetime import datetime
import os
import pathlib
import xml.etree.ElementTree as ElementTree
import gxipy as gx
from PIL import Image
from random import randint

CLOSE_ALL_VALVES = bytes(str(0) + '\n', 'utf-8')
BAUD_RATE=115200

class Cage:

    def __init__(self, index: int):
        self.ID = index
        self.fireAction=""
        self.name = None
        self.capacity = 20000
        self.numberMales: int = 0
        self.numberFemales: int = 0
        self.requiredMales = 5
        self.requiredFemales = 20000
        self.malesComplete = False
        self.femalesComplete = False
        self.relais = None
        self.male_percentage = 30
        self.maleLabel = None
        self.femaleLabel = None

    def add_male(self):
        self.numberMales += 1
        if self.numberMales >= self.requiredMales:
            self.malesComplete = True
        if self.maleLabel is not None:
            self.maleLabel.set(self.numberMales)

    def add_female(self):
        self.numberFemales += 1
        if self.numberFemales >= self.requiredFemales:
            self.femalesComplete = True
        if self.femaleLabel is not None:
            self.femaleLabel.set(self.numberFemales)

    def set_required_numbers(self):
        self.requiredMales = round(self.capacity * self.male_percentage / 100)
        self.requiredFemales = round(self.capacity * (1 - self.male_percentage / 100))
        logging.info(
            'Cage {} now requires {} males and {} females'.format(self.name, self.requiredMales, self.requiredFemales))
        if self.numberMales > self.requiredMales:
            self.malesComplete = True
            logging.warning("Too many males present already")
        if self.numberFemales > self.requiredFemales:
            self.femalesComplete = True
            logging.warning("Too many females present already")


class Camera:

    def __init__(self) -> None:
        self.serial_number: str = ''
        self.gain: float = 24.0
        self.exposure: float = 100000
        self.awb: float = 1
        self.wbr: float = 1
        self.wbb: float = 1
        self.data = None
        self.image = None
        self.cam = None
        self.roix: int = 1
        self.roiy: int = 1
        self.roiwidth: int = 5000 #TODO: check maximum width
        self.roiheight: int = 3000 #TODO: check maximum heigth


class Application:

    def __init__(self, serial_service, file_name: str, async_loop):
        self.serial_service = serial_service
        self.camera = Camera()
        self.cam = None
        self.cages = []
        self.capture_time = None
        self.save_directory = "/media/entoq/41DB-88AA/Output"
        self._load_settings(file_name)
        self.rawImage = None
        self.processedImg = None
        self.newImage = False
        self.async_loop = async_loop
        self.ui = None
        self.device_manager = None
        self.update_function = None

    def set_ui(self, ui):
        self.ui = ui

    def set_communication_device(self, device):
        self.serial_service.open(device, BAUD_RATE, False)

    def trigger(self):
        try:
            self.device_manager = gx.DeviceManager()
            dev_num, dev_info_list = self.device_manager.update_device_list()
            if dev_num == 0:
                raise RuntimeError('No camera connected?')

            self.cam = self.device_manager.open_device_by_index(1)
            self.cam.TriggerMode.set(gx.GxSwitchEntry.ON)  # set trigger mode ON
            self.cam.TriggerSource.set(gx.GxTriggerSourceEntry.SOFTWARE)  # Software trigger
            # cam.TriggerDelay.set(0) #No additional trigger delay required. Take picture as fast as possible
            self.cam.ExposureTime.set(self.camera.exposure)  # set exposure
            logging.debug(self.cam.ExposureTime.get())
            logging.debug(self.camera.exposure)
            
            self.cam.PixelFormat.set(17301505)  # TODO: check pixel format
            self.cam.Gain.set(self.camera.gain)  # sensor gain
            #self.cam.RegionMode.set(gx.GxRegionSendModeEntry.SINGLE_ROI)
            #self.cam.RegionSelector.set(gx.GxRegionSelectorEntry.REGION0)
            self.cam.stream_on()
            self.cam.TriggerSoftware.send_command()
            self.acquire_images()
            self.stop_camera()

        except Exception as err:
            logging.warning(f'{self.__class__.__name__.upper()}: An error occured while communicating with camera '
                            f'due to: '
                            f'{err.args[0]}')
            raise RuntimeError(f'An error occurred while trying to communicate with camera')

    def activate_camera(self):
        try:
            self.device_manager = gx.DeviceManager()
            dev_num, dev_info_list = self.device_manager.update_device_list()

            self.cam = self.device_manager.open_device_by_index(1)
            self.cam.TriggerMode.set(gx.GxSwitchEntry.ON)  # set trigger mode ON
            self.cam.TriggerSource.set(gx.GxTriggerSourceEntry.LINE0)  # Hardware trigger on Line 0 of camera
            # cam.TriggerDelay.set(0) #No additional trigger delay required. Take picture as fast as possible
            self.cam.ExposureTime.set(self.camera.exposure)  # set exposure
            logging.debug(self.camera.exposure)
            logging.debug(self.cam.ExposureTime.get())
            self.cam.PixelFormat.set(17301505)  # TODO: Mono8 17301505 Mono12 17825797
            self.cam.Gain.set(self.camera.gain)  # sensor gain
            

        except Exception as err:
            logging.warning(f'{self.__class__.__name__.upper()}: An error occured while communicating with camera '
                            f'due to: '
                            f'{err.args[0]}')
            raise RuntimeError(f'An error occurred while trying to communicate with camera')

    def acquire_images(self):
        try:
            if self.cam is None:
                logging.error('Camera does not exist')
            self.cam.stream_on()
            self.rawImage = self.cam.data_stream[0].get_image()  # acquire image
            self.capture_time = datetime.now().strftime('%Y-%m-%d_%Hh%Mm%Ss')
        except Exception as err:
            logging.warning(f'{self.__class__.__name__.upper()}: An error occured while trying to take a picture '
                            f'due to: '
                            f'{err.args[0]}')
            raise RuntimeError(f'An error occurred while trying to communicate with camera')
        # create numpy array with data from raw image
        if self.rawImage is not None:
            numpy_image = self.rawImage.get_numpy_array()
            self.processedImg = Image.fromarray(numpy_image, 'L')
            self.async_loop.run_until_complete(self._async_save_images(
                self.processedImg))  # TODO: for now store the image, later determine sex and send to cage
            logging.debug('Reached update function')
            fly_sex = self.determine_sex()
            self.determine_destination(fly_sex)
            if self.acquire_images is not None and self.update_function is not None:
                self.update_function()
            self.newImage = True
        else:
            self.newImage = False
            logging.debug('No picture taken')

    def stop_camera(self):
        try:
            # stop data acquisition
            self.cam.stream_off()
            # close device
            self.cam.close_device()
        except Exception as err:
            logging.warning(f'{self.__class__.__name__.upper()}: An error occured while communicating with camera '
                            f'due to: '
                            f'{err.args[0]}')
            raise RuntimeError(f'An error occurred while trying to communicate with camera')
        time.sleep(0.01)

    def save_image(self, img):
        sep = os.path.sep
        logging.info("Write to director {}".format(self.save_directory))
        path = pathlib.Path(self.save_directory)
        path.mkdir(parents=True, exist_ok=True)

        outfile = self.save_directory + sep + self.capture_time + ".jpg"
        logging.info("Writing file to {}".format(outfile))
        img.save(outfile, compress_level=3)

    def fire_to_cage(self, cage):
        message={
            "id": "fire",
            "action": cage.fireAction
        }
        logging.info(f'Fired to cage {cage.ID}')
        self.serial_service.writeandreadJSON(message)

    def update_male_percentage(self, percentage):
        if percentage > 100:
            i = 0
            logging.warning("percentage larger than 100%")
        elif percentage < 1:
            i = 0
            logging.warning('percentage smaller than 0%')
        else:
            for cage in self.cages:
                logging.info("Updating required numbers for cage {}".format(cage.name))
                cage.male_percentage = percentage
                cage.set_required_numbers()

    def update_ROI(self, x, y, w, h):
        logging.debug("%s, %s, %s, %s", x, y, w, h)
        self.camera.roix = self.round_to_multiple(x, 8)
        self.camera.roiy = self.round_to_multiple(y, 2)
        w = self.round_to_multiple(w, 8)
        h = self.round_to_multiple(h, 2)
        if self.camera.roix + w >= 5496:
            self.camera.roiwidth = 5496 - self.camera.roix
            logging.warning("width was too big")
        elif w == 0:
            self.camera.roiwidth = 5496 - self.camera.roix
        else:
            self.camera.roiwidth = w
        if self.camera.roiy + h >= 3672:
            self.camera.roiheight = 3672 - self.camera.roiy
            logging.warning("width was too big")
        elif h == 0:
            self.camera.roiheight = 3672 - self.camera.roiy
        else:
            self.camera.roiheight = h

        logging.debug("Setting ROI:")
        logging.debug("%s, %s, %s, %s", self.camera.roix, self.camera.roiy, self.camera.roiwidth, self.camera.roiheight)
        self.activate_camera()
        try:
            self.cam.Width.set(16)
            self.cam.Height.set(2)
            self.cam.OffsetX.set(0)
            self.cam.OffsetY.set(0)
            self.cam.OffsetX.set(int(self.camera.roix))
            self.cam.OffsetY.set(int(self.camera.roiy))
            self.cam.Width.set(int(self.camera.roiwidth))
            self.cam.Height.set(int(self.camera.roiheight))
            logging.debug(self.cam.OffsetX)
        except Exception as err:
            logging.warning(f'{self.__class__.__name__.upper()}: An error occured while communicating with camera '
                            f'due to: '
                            f'{err.args[0]}')
            raise RuntimeError(f'An error occurred while trying to communicate with camera')
        self.stop_camera()

    @staticmethod
    def round_to_multiple(number, multiple):
        return multiple * round(number / multiple)

    @staticmethod
    def determine_sex():
        # TODO: send image to AI and get feedback
        sex = randint(0, 1)
        return sex

    def determine_destination(self, sex: int):
        cage_selected = False
        for cage in self.cages:
            if sex == 1 and not cage.malesComplete:  # TODO: what with flies with low probability of being correct?
                self.fire_to_cage(cage)
                cage_selected = True
                cage.add_male()
                logging.info("Male fly added to Cage {}".format(cage.ID))
                logging.info("Total number of male flies in cage {} is {}".format(cage.ID, cage.numberMales))
                break
            elif sex == 0 and not cage.femalesComplete:
                self.fire_to_cage(cage)
                cage_selected = True
                cage.add_female()
                logging.info("Female fly added to Cage {}".format(cage.ID))
                logging.info("Total number of female flies in cage {} is {}".format(cage.ID, cage.numberFemales))
                break

            if not cage_selected and cage.ID == len(self.cages):
                self.fire_to_cage(cage)
                logging.info("All full, firing to trash")

    def _load_settings(self, file_name: str):
        logging.debug(f'{self.__class__.__name__.upper()}: Start loading settings')
        camera_index = 0
        cage_index = 0
        try:
            settings_tree = ElementTree.parse(file_name)
            settings_root = settings_tree.getroot()

            for child in settings_root:
                if child.tag == 'camera':
                    for childchild in child:
                        if childchild.tag == 'name':
                            self.camera.name = childchild.text
                        elif childchild.tag == 'serial':
                            self.camera.serial_number = childchild.text
                        elif childchild.tag == 'gain':
                            self.camera.gain = float(childchild.text)
                        elif childchild.tag == 'exposure':
                            self.camera.exposure = float(childchild.text)
                        elif childchild.tag == 'awb':
                            self.camera.awb = float(childchild.text)
                        elif childchild.tag == 'wbr':
                            self.camera.wbr = float(childchild.text)
                        elif childchild.tag == 'wbb':
                            self.camera.wbb = float(childchild.text)
                        elif childchild.tag == 'roix':
                            self.camera.roix = float(childchild.text)
                        elif childchild.tag == 'roiy':
                            self.camera.roiy = float(childchild.text)
                        elif childchild.tag == 'roiwidth':
                            self.camera.roiwidth = float(childchild.text)
                        elif childchild.tag == 'roiheight':
                            self.camera.roiheight = float(childchild.text)

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
                elif child.tag == 'cage':
                    cage_index += 1
                    cage = Cage(cage_index)
                    for childinchild in child:
                        if childinchild.tag == 'name':
                            cage.name = childinchild.text
                        elif childinchild.tag == 'capacity':
                            cage.capacity = int(childinchild.text)
                        elif childinchild.tag == 'male_percentage':
                            cage.male_percentage = int(childinchild.text)
                            cage.set_required_numbers()
                        elif childinchild.tag == 'action':
                            cage.fireAction = childinchild.text
                    self.cages.append(cage)
        except ElementTree.ParseError as err:
            logging.critical(
                f'{self.__class__.__name__.upper()}: An error occurred while trying to load {file_name}: {err.msg}')
            exit()
        except FileNotFoundError as err:
            logging.critical(
                f'{self.__class__.__name__.upper()}: An error occurred while trying to load {file_name}:'
                f' {err.strerror}')
            exit()

        logging.debug(f'{self.__class__.__name__.upper()}: Settings loaded')

    async def _async_save_images(self, img):
        return self.save_image(img)
