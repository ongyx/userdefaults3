# coding: utf8
"""Python 3 rewrite of userdefaults, a pure-Python interface to NSUserDefaults.

The singular 'UserDefaults' class provides the main interface, which should be used
as a regular dictionary.
Python types are converted to their Obj-C equivlents on writing to UserDefaults.

Usage:

>>> with UserDefaults() as ud:
>>>     ud["key"] = value
>>>

Or, for more flexible access to the UserDefaults class:

>>> ud = UserDefaults()
>>> ud["key"] = value
>>> ...  # other operations here
>>> ud.sync()  # write back to plist file, does nothing on Obj-C backend

On supported platforms that have a Obj-C backend, the UserDefaults class acts as a
shim for NSUserDefaults. Otherwise, a naive file handle is used to modify
UserDefaults using plistlib.

Supported backends:
rubicon-objc (Darwin/Pyto)
objc_util (Pythonista)

If your platform does not have a Obj-C backend (unless you are on Libterm/a-Shell),
you problably should not use this as directly writing to the plist file itself is
discouraged (as quoted from Apple's docstring):

> Don’t try to access the preferences subsystem directly. Modifying preference
> property list files may result in loss of changes, delay of reflecting changes,
> and app crashes.

The naive file method is kept to support platforms which do not have/cannot install
a Obj-C backend (i.e Libterm, a-Shell).

Known bugs:
- On Pyto, writing to the inputHistory key using the Obj-C backend results in a
SIGKILL (crashes).

Copyright (c) 2020 Ong Yong Xin

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

from collections.abc import MutableMapping
import os
import pathlib
import plistlib
import sys

__author__ = "Ong Yong Xin"
__copyright__ = "Copyright 2020, Ong Yong Xin"
__credits__ = ["Ong Yong Xin"]
__license__ = "MIT"
__version__ = "1.0.1"
__maintainer__ = "Ong Yong Xin"
__email__ = "ongyongxin2020+github@gmail.com"
__status__ = "Production"

DEFAULT_PLIST_FORMAT = plistlib.FMT_BINARY
INFO_PLIST_PATH = pathlib.Path(sys.executable).parent / "Info.plist"
USERHOME = pathlib.Path("~").expanduser()


try:
    with open(INFO_PLIST_PATH, mode="rb") as f:
        BUNDLE_ID = plistlib.load(f)["CFBundleIdentifier"]

except (FileNotFoundError, plistlib.InvalidFileException):
    BUNDLE_ID = ""


try:
    if "Pythonista" in BUNDLE_ID:
        # map as rubicon.objc does, specific to Pythonista
        from objc_util import ns as at, ObjCClass

    elif "LibTerm" in BUNDLE_ID or "a-Shell" in BUNDLE_ID:
        # rubicon-objc on LibTerm/a-Shell results in a SIGBUS,
        # problably something to do with ctypes
        raise NotImplementedError()

    else:
        # default to rubicon-objc
        # TODO: add pyobjc support
        from rubicon.objc import at, ObjCClass

except (ImportError, NotImplementedError):
    _NSUserDefaults = None

else:
    # enable faulthandler to trace SIGBUS
    import faulthandler

    faulthandler.enable()
    _NSUserDefaults = ObjCClass("NSUserDefaults").alloc().init()
    faulthandler.disable()
    del faulthandler


class UserDefaultsError(Exception):
    pass


def get_userdefaults_path() -> pathlib.Path:
    """Get the path to the UserDefaults plist.

    Returns:
        A pathlib.Path object representing the path,
        othwerwise None if the bundle ID is invalid.
    """

    bundle_id = get_bundle_id()
    if bundle_id is None:
        return None

    if bundle_id == "AsheKube.app.a-Shell":
        # UserDefaults plist is in SyncedPreferences instead
        plist_folder = "SyncedPreferences"
    else:
        plist_folder = "Preferences"

    return USERHOME / "Library" / plist_folder / f"{bundle_id}.plist"


class BaseUserDefaults(MutableMapping):
    """Base class for UserDefault interfaces.
    
    Interfaces which inherit from BaseUserDefaults should call
    super().__init__(data) if you override __init__().
    
    Args:
        data (default: {}): The UserDefaults data, as a dictionary.
    
    Attributes:
        data (dict): See above
    """

    def __init__(self):
        pass

    def __getitem__(self, key):
        return self.data[key]

    def __setitem__(self, key, value):
        self.data[key] = value

    def __delitem__(self, key):
        del self.data[key]

    def __iter__(self):
        return iter(self.data)

    def __len__(self):
        return len(self.data)

    def __repr__(self):
        return f"{type(self).__name__}({self.data})"


class FileUserDefaults(BaseUserDefaults):
    """Naive file-based UserDefaults context manager.
    You problably should _not_ use this, unless you are on Libterm/a-Shell.
    
    Args:
        writeback: Whether or not to write back changes to UserDefaults at the end of
                   the "with" block.
                   Does not affect .sync().
    
    Attributes:
        data (dict): The deserialised UserDefaults data.
        path (pathlib.Path): The path to the UserDefaults plist.
    
    Raises:
        UserDefaultsError, if the plist file could not be found.
        NotImplementedError, if the platform is not supported.
    """

    def __init__(self, writeback: bool = False, suitename: str = ""):
        if suitename:
            raise NotImplementedError("suitenams not supported by FileUserDefaults")

        del suitename

        self._writeback = writeback
        self.path = get_userdefaults_path()

        if self.path is None:
            raise NotImplementedError("platform not supported: bundle ID is invalid")

        try:
            with self.path.open(mode="rb") as f:
                self.data = plistlib.load(f, fmt=DEFAULT_PLIST_FORMAT)

        except (FileNotFoundError, plistlib.InvalidFileException) as e:
            raise UserDefaultsError(f"could not parse UserDefaults plist: {e}")

    def sync(self):
        """Write changes back to the UserDefaults plist file.
        
        Raises:
            UserDefaultsError, if changes were already written.
        """

        if self._writeback:
            with self.path.open(mode="wb") as f:
                plistlib.dump(self.data, f, fmt=DEFAULT_PLIST_FORMAT)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.sync()


class ObjCUserDefaults(BaseUserDefaults):
    """Public Obj-C interface to UserDefaults.
    Args:
        writeback: Whether or not to write back changes to UserDefaults (ignored here).
        suitename: The domain ID for NSUserDefaults to access.
    
    Atrributes:
        suitename (str): The suite name that NSUserDefaults was initalized with.
        objcclass (rubicon.objc.api.ObjCInstance): Raw interface to NSUserDefaults.
    
    Raises:
        NotImplementedError, if an Obj-C backend is not found.
        UserDefaultsError, if self.data tries to be set (it is read-only).
    """

    def __init__(self, writeback: bool = False, suitename: str = ""):
        del writeback
        self.suitename = suitename

        if _NSUserDefaults is None:
            raise NotImplementedError("platform not supported: Obj-C backend not found")

        if suitename:
            # create a custom instance
            self.objcclass = (
                ObjCClass("NSUserDefaults").alloc().initWithSuiteName_(suitename)
            )

        else:
            # use default instance
            self.objcclass = _NSUserDefaults

    def __getitem__(self, key):
        return self.objcclass.objectForKey_(key)

    def __setitem__(self, key, value):
        self.objcclass.setObject_forKey_(key, at(value))

    def __delitem__(self, key):
        self.objcclass.removeObjectForKey_(key)

    @property
    def data(self):
        return self.objcclass.dictionaryRepresentation()

    @data.setter
    def data(self):
        raise UserDefaultsError(
            "cannot assign directly to UserDefaults: use .update() instead"
        )

    def sync(self):
        """Dummy method for compatibility with FileUserDefaults."""
        # synchonize method depreciated - see https://developer.apple.com/documentation/foundation/nsuserdefaults/1414005-synchronize?language=objc
        # self._userdefaults.synchronize()
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        pass


if _NSUserDefaults is None:
    # use file-based backend
    UserDefaults = FileUserDefaults
else:
    UserDefaults = ObjCUserDefaults


if __name__ == "__main__":
    pass
