import sys
import threading
import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk
import logging

from application.serial import TooManyDevicesAvailableException, NoDeviceAvailableException, \
    UnableToOpenConnectionException, MessageTransportationException


class SelectSerialPortDialog(tk.Toplevel):

    def __init__(self, parent, devices):
        tk.Toplevel.__init__(self, parent)

        self.parent = parent
        self.cancelled = False
        self.result = None

        body = tk.Frame(self)

        self._selected_device = tk.StringVar()
        label = tk.Label(body, text='Selected port')
        dropdown = tk.OptionMenu(body, self._selected_device, *devices)
        label.pack(side="top", fill="x")
        dropdown.pack(padx=5, pady=5, fill=tk.X, side=tk.LEFT, expand=True)
        body.pack(padx=5, pady=5)

        box = tk.Frame(self)
        w = tk.Button(box, text="OK", width=10, command=self.ok, default=tk.ACTIVE)
        w.pack(side=tk.LEFT, padx=5, pady=5)
        w = tk.Button(box, text="Cancel", width=10, command=self.cancel)
        w.pack(side=tk.LEFT, padx=5, pady=5)
        self.bind("<Return>", self.ok)
        self.bind("<Escape>", self.cancel)
        box.pack()

        self.deiconify()
        dropdown.focus_force()
        self.wait_window()

    def ok(self, event=None):
        self.result = self._selected_device.get()
        self.cancelled = False
        self.destroy()

    def cancel(self, event=None):
        self.cancelled = True
        if self.parent is not None:
            self.parent.focus_set()
        self.destroy()


class UI:

    def __init__(self, window, main_service, async_loop) -> None:
        self._window = window
        self._main_service = main_service
        self._main_service.update_function = lambda: self.update_latest_image()
        self.async_loop = async_loop

        self._sideFrame = tk.Frame(master=self._window)
        self._previewFrame = tk.Frame(master=self._window)

        self.image = None
        self.stopped = False

        self._window.columnconfigure(0, weight=0)
        self._window.columnconfigure(1, weight=1)
        self._sideFrame.grid(column=0, row=0)
        self._previewFrame.grid(column=1, row=0, sticky="NSEW")
        self._previewFrame.columnconfigure(0, weight=1)

        for cage in self._main_service.cages:
            self._cageFrame = ttk.Frame(master=self._sideFrame)
            self._cageLabel = ttk.Label(master=self._cageFrame, text=cage.name)
            self._cageLabel.grid(column=0, row=0)
            self._cageMaleLabel = ttk.Label(master=self._cageFrame, text='Males: ')
            self._cageMaleLabel.grid(column=0, row=1)
            self.maleLabel = tk.StringVar()
            cage.maleLabel = self.maleLabel
            self._cageMaleCount = ttk.Label(master=self._cageFrame, textvariable=self.maleLabel)
            self._cageMaleCount.grid(column=1, row=1)
            self._cageFemaleLabel = ttk.Label(master=self._cageFrame, text='Females: ')
            self.femaleLabel = tk.StringVar()
            cage.femaleLabel = self.femaleLabel
            self._cageFemaleCount = ttk.Label(master=self._cageFrame, textvariable=self.femaleLabel)
            self._cageFemaleLabel.grid(column=0, row=2)
            self._cageFemaleCount.grid(column=1, row=2)
            self._cageFrame.grid(column=0, row=cage.ID)

        self._startButton = ttk.Button(master=self._sideFrame, text='Start Sorting',
                                       command=lambda: self._async_task(self.start_sorting))
        self._startButton.grid(column=0, row=5)
        self._stopButton = ttk.Button(master=self._sideFrame, text='Stop Sorting',
                                      command=lambda: self._async_task(self.stop_sorting))
        self._stopButton.grid(column=0, row=6)

        self.runningStatus = tk.StringVar()
        self._statusField = ttk.Label(master=self._sideFrame, textvariable=self.runningStatus)
        self._statusField.grid(column=0, row=7)

        self._settingsFrame = tk.Frame(master=self._sideFrame)
        self._settingsFrame.grid(column=0, row=8)

        self._malePercentageLabel = ttk.Label(master=self._settingsFrame, text='Desired male %')
        self._malePercentageLabel.grid(column=0, row=0)
        self._malePercentage = ttk.Entry(master=self._settingsFrame, text="30")
        self._malePercentage.insert(0, '30')
        self._malePercentage.grid(column=1, row=0)
        self._malePercentageButton = ttk.Button(master=self._settingsFrame, text='Set',
                                                command=lambda: self.set_percentage())
        self._malePercentageButton.grid(column=0, row=2, columnspan=2)

        self._manualTriggerButton = ttk.Button(master=self._settingsFrame, text='Trigger',
                                               command=lambda: self._async_task(self.trigger))
        self._manualTriggerButton.grid(column=0, row=3, columnspan=2)

        self.image = Image.open("EntoQ_Symbol_main.png")
        self.processed_image = ImageTk.PhotoImage(self.image.resize((500, 500)))

        self._imageLabel = ttk.Label(master=self._previewFrame, image=self.processed_image, text='no image')
        self._imageLabel = ttk.Label(master=self._previewFrame, image=self.processed_image, text='no image')
        self._imageLabel['image'] = self.processed_image
        self._imageLabel.grid(column=0, row=0)

    ######################################
    # Drawing methods
    ######################################
    def update_latest_image(self):
        logging.info('Inside update latest image')
        self.image = self._main_service.processedImg
        self.image = self.image.resize((549, 367))
        self.processed_image = ImageTk.PhotoImage(self.image)
        self._imageLabel['image'] = self.processed_image
        self._imageLabel.pack(expand=True)

        logging.info('Reached end of update latest image')

    def update(self):
        self._window.update()

    ######################################
    # UI functionality
    ######################################
    @staticmethod
    def _async_task(function):
        threading.Thread(target=function).start()

    def start_sorting(self):
        self.stopped = False
        self.runningStatus.set('Sorting active')
        self._main_service.activate_camera()
        self._main_service.newImage = False
        logging.info('Sorting started')
        while not self.stopped:
            try:
                self.async_loop.run_until_complete(self._async_acquire_images())
            except TooManyDevicesAvailableException as err:
                dialog = SelectSerialPortDialog(self._window, err.devices)
                if not dialog.cancelled:
                    self._main_service.set_communication_device(dialog.result)
                    self.async_loop.run_until_complete(self._async_acquire_images())
            except NoDeviceAvailableException:
                messagebox.showerror('Error', 'No serial devices available to connect to')
            except UnableToOpenConnectionException:
                messagebox.showerror('Error', 'Could not open connection to serial device')
            except MessageTransportationException:
                messagebox.showerror('Error', 'An error occurred while communicating with the device')
            except RuntimeError as err:
                messagebox.showerror('Error', err.args[0])
        self._main_service.stop_camera()

    def stop_sorting(self):
        self.stopped = True
        self.runningStatus.set('Sorting stopped')
        logging.info("Sorting stopped")

    def set_percentage(self):
        logging.info("here")
        self._main_service.update_male_percentage(int(self._malePercentage.get()))

    def trigger(self):
        self.stop_sorting()
        logging.info("Sorting stopped, manual trigger")
        self._main_service.trigger()

    ######################################
    # Async / Service methods
    ######################################
    async def _async_acquire_images(self):
        return self._main_service.acquire_images()

    async def _async_start_sorting(self):
        return self.start_sorting()