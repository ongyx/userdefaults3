# coding: utf8
"""Python 3 rewrite of userdefaults, a pure-Python interface to NSUserDefaults.

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
import platform
import plistlib
import re
import sys
import warnings

__author__ = "Ong Yong Xin"
__copyright__ = "Copyright 2020, Ong Yong Xin"
__credits__ = ["Ong Yong Xin"]
__license__ = "MIT"
__version__ = "1.1.5"
__maintainer__ = "Ong Yong Xin"
__email__ = "ongyongxin2020+github@gmail.com"
__status__ = "Production"

DEFAULT_PLIST_FORMAT = plistlib.FMT_BINARY
USERHOME = pathlib.Path("~").expanduser()
# XPC service names should follow this format
RE_XPC_SERVICE = re.compile(r"UIKitApplication:([a-zA-Z0-9\-\.]+)\[([0-9a-fA-F]+)\]")

try:
    _INFO_PLIST = pathlib.Path(sys.executable).parent / "Info.plist"
    with _INFO_PLIST.open(mode="rb") as f:
        BUNDLE_ID = plistlib.load(f)["CFBundleIdentifier"]

except (FileNotFoundError, plistlib.InvalidFileException):
    # try harder
    try:
        match = RE_XPC_SERVICE.match(os.getenv("XPC_SERVICE_NAME"))
        if match is None:
            raise TypeError

    except TypeError:
        BUNDLE_ID = ""

    else:
        BUNDLE_ID = match.group(1)


try:
    if "Pythonista" in BUNDLE_ID:
        # map as rubicon.objc does, specific to Pythonista
        from objc_util import ns as at, ObjCClass

    elif "LibTerm" in BUNDLE_ID or "a-Shell" in BUNDLE_ID:
        # rubicon-objc on LibTerm/a-Shell results in a SIGBUS,
        # problably something to do with ctypes
        raise NotImplementedError()

    elif "Pyto" in BUNDLE_ID:
        from rubicon.objc import at, ObjCClass

    else:
        # default to pyobjc as preinstalled bridge
        import Foundation

        # define shims for compatibility with rubicon-objc/objc_util

        def ObjCClass(ns_object_name):
            return getattr(Foundation, ns_object_name)

        def at(object):
            return object


except (ImportError, NotImplementedError):
    BACKEND = "file"
    _NSUserDefaults = None

else:
    BACKEND = "objc"
    # enable nicer traceback
    try:
        import faulthandler

        faulthandler.enable()
    except AttributeError:
        # on Pyto, faulthandler raises this for some reason
        pass
    _NSUserDefaults = ObjCClass("NSUserDefaults").standardUserDefaults
    faulthandler.disable()


class UserDefaultsError(Exception):
    pass


def get_userdefaults_path() -> pathlib.Path:
    """Get the path to the UserDefaults plist.

    Returns:
        A pathlib.Path object representing the path,
        othwerwise None if the bundle ID is invalid.
    """

    if BUNDLE_ID is None:
        return None

    if BUNDLE_ID == "AsheKube.app.a-Shell":
        # UserDefaults plist is in SyncedPreferences instead
        plist_folder = "SyncedPreferences"
    else:
        plist_folder = "Preferences"

    return USERHOME / "Library" / plist_folder / f"{BUNDLE_ID}.plist"


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

        with self.path.open(mode="wb") as f:
            plistlib.dump(self.data, f, fmt=DEFAULT_PLIST_FORMAT)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if self._writeback:
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
