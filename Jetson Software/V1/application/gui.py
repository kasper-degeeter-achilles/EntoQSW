import sys
import threading
import tkinter as tk
from tkinter import ttk, messagebox

import PIL.ImageShow
import numpy as np
from PIL import Image, ImageTk

from application.serial import TooManyDevicesAvailableException, NoDeviceAvailableException, \
    UnableToOpenConnectionException, MessageTransportationException

MINI_WIDTH = 140
MINI_HEIGHT = 140
BORDER_THICKNESS = 5


class ScrollableFrame(ttk.Frame):

    def __init__(self, container, *args, **kwargs):
        super().__init__(container, *args, **kwargs)
        self.canvas = tk.Canvas(self, height=MINI_HEIGHT + 2 * BORDER_THICKNESS, bd=0)
        self.scrollbar = ttk.Scrollbar(self, orient='horizontal', command=self.canvas.xview)
        self.scrollable_frame = ttk.Frame(self.canvas)

        self.scrollable_frame.bind('<Configure>', lambda e: self.canvas.configure(scrollregion=self.canvas.bbox('all')))

        if sys.platform.startswith('linux'):
            self.canvas.bind('<4>', lambda event: self.canvas.xview('scroll', -1, 'units'))
            self.canvas.bind('<5>', lambda event: self.canvas.xview('scroll', 1, 'units'))
        else:
            self.canvas.bind_all('<MouseWheel>', lambda event: self._mouse_wheeled(event))
            self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor='nw')

            self.canvas.configure(xscrollcommand=self.scrollbar.set)

            self.scrollbar.pack(side='bottom', fill='x', expand=False)
            self.canvas.pack(side='top', fill='both', expand=False)

    def _mouse_wheeled(self, event):
        # for OSX, don't divide by 120, I've been told
        self.canvas.xview('scroll', int(-event.delta / 120), 'units')


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
        self._main_service.set_ui(self)
        self.async_loop = async_loop

        self._sideFrame = tk.Frame(master=self._window, width=512, relief='raised')
        self._previewFrame = tk.Frame(master=self._window, bg="black")

        self._currentImage = 0
        self.ignoreInput = False

        self._sideFrame.pack(side=tk.LEFT, expand=False)
        self._previewFrame.pack(side=tk.RIGHT, expand=True)

        for cage in self._main_service.cages:
            self._cageFrame = ttk.Frame(master=self._sideFrame, relief=tk.RAISED)
            self._cageLabel = ttk.Label(master=self._cageFrame, text=cage.name)
            self._cageLabel.pack(side=tk.TOP, anchor="w")
            self._cageMaleLabel = ttk.Label(master=self._cageFrame, text='Males: ')
            self.malelabel = tk.StringVar()
            self._cageMaleCount = ttk.Label(master=self._cageFrame, textvariable=self.malelabel)
            self._cageMaleLabel.pack(side=tk.TOP, anchor="w")
            self._cageMaleCount.pack(side=tk.TOP, anchor="e")
            self._cageFemaleLabel = ttk.Label(master=self._cageFrame, text='Females: ')
            self._cageFemaleCount = ttk.Label(master=self._cageFrame, text=cage.numberFemales)
            self._cageFemaleLabel.pack(side=tk.TOP, anchor="w")
            self._cageFemaleCount.pack(side=tk.TOP, anchor="e")
            self._cageFrame.pack(fill=tk.X, side=tk.TOP, padx=6, pady=5)

        self._startButton = ttk.Button(master=self._sideFrame, text='Start Sorting',
                                       command=lambda: self._async_task(self._test)) #TODO: link naar juiste functie
        self._startButton.pack(fill=tk.X, side=tk.TOP, padx=5, pady=5)
        self._stopButton = ttk.Button(master=self._sideFrame, text='Stop Sorting',
                                      command=lambda: self._async_task(self.stop_sorting()))  #TDDO:  link naar juiste functie
        self._stopButton.pack(fill=tk.X, side=tk.TOP, padx=5, pady=5)
        self._saveButton = ttk.Button(master=self._sideFrame, text='Save Settings',
                                      command=lambda: self._async_task(self._save_images)) #TODO: Create save settings function
        self._saveButton.pack(fill=tk.X, side=tk.TOP, padx=5, pady=5)
        self._malePercentageLabel = ttk.Label(master=self._sideFrame, text='Desired male %')
        self._malePercentageLabel.pack()
        self._malePercentage = ttk.Entry(master=self._sideFrame, text="30")
        self._malePercentage.pack()
        self._malePercentageButton = ttk.Button(master=self._sideFrame, text='Set')
        self._malePercentageButton.pack()

        # img = ImageTk.PhotoImage(Image.open("ball.png"))
        # self._imageLabel = ttk.Label(master=self._sideFrame, image=img, width=500)
        # self._imageLabel.pack()

        img = Image.open("ball.png")
        img = img.resize((300,300))
        imglab = ImageTk.PhotoImage(img)

        self._imageLabel = ttk.Label(master=self._previewFrame, image=imglab, text='noimage')
        self._imageLabel.photo = imglab
        self._imageLabel.pack()


        self._sideFrame.pack(side=tk.LEFT, expand=False)
        self._previewFrame.pack(side=tk.RIGHT, expand=True)
        ######################################
    # Drawing methods
    ######################################
    def update_latest_image(self):

        img = self._main_service.processedImg
        img = img.resize((300, 300))
        imglab = ImageTk.PhotoImage(img)

        self._imageLabel = ttk.Label(master=self._previewFrame, image=imglab, text='noimage')
        self._imageLabel['image'] = imglab
        self._imageLabel.pack()

    def update_progress(self):
        p=  self._main_service.progress
        self._progress['value'] = p
        self._window.update()

    def stop_sorting(self):
        self._main_service.stop_acquire_images()

    def update(self):
        self._window.update()

    ######################################
    # UI functionality
    ######################################
    @staticmethod
    def _async_task(function):
        threading.Thread(target=function).start()

    def _acquire_images(self):
        if not self.ignoreInput:
            self.ignoreInput = True
            try:
                self.async_loop.run_until_complete(self._async_acquire_images())
            except TooManyDevicesAvailableException as err:
                dialog = SelectSerialPortDialog(self._window, err.devices)
                if not dialog.cancelled:
                    self._main_service.set_communication_device(dialog.result)
                    self._acquire_images()
            except NoDeviceAvailableException:
                messagebox.showerror('Error', 'No serial devices available to connect to')
            except UnableToOpenConnectionException:
                messagebox.showerror('Error', 'Could not open connection to serial device')
            except MessageTransportationException:
                messagebox.showerror('Error', 'An error occurred while communicating with the device')
            except RuntimeError as err:
                messagebox.showerror('Error', err.args[0])
            self._update_latest_image()
            self.ignoreInput = False


    def _test(self):
        try:
            self.async_loop.run_until_complete(self._async_test())
        except TooManyDevicesAvailableException as err:
            dialog = SelectSerialPortDialog(self._window, err.devices)
            if not dialog.cancelled:
                self._main_service.set_communication_device(dialog.result)
                self._test()
        except NoDeviceAvailableException:
            messagebox.showerror('Error', 'No serial devices available to connect to')
        except UnableToOpenConnectionException:
            messagebox.showerror('Error', 'Could not open connection to serial device')
        except MessageTransportationException:
            messagebox.showerror('Error', 'An error occurred while communicating with the device')
        except RuntimeError as err:
            messagebox.showerror('Error', err.args[0])
        self.update_latest_image()


    ######################################
    # Async / Service methods
    ######################################
    async def _async_acquire_images(self):
        return self._main_service.acquire_images()

    async def _async_test(self):
        return self._main_service.test()

