Download and install software for cameras:
https://www.get-cameras.com/customerdownloads
This installs the required dlls used by gxipy

In the gxwrapper.py change
    dll = ctypes.WinDLL('GxIAPI.dll', winmode=0)
to:
    dll = ctypes.WinDLL('GxIAPI.dll', winmode=1)