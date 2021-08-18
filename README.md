# userdefaults3

[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
![PyPI - Python Version](https://img.shields.io/pypi/pyversions/userdefaults3)
![PyPI - Wheel](https://img.shields.io/pypi/wheel/userdefaults3)

Python 3 rewrite of userdefaults, a pure-Python interface to NSUserDefaults.

The singular 'UserDefaults' class provides the main interface, which should be used
as a regular dictionary.
Python types are converted to their Obj-C equivlents on writing to UserDefaults.

## Usage

```python
>>> with UserDefaults() as ud:
>>>     ud["key"] = value
>>>
```

Or, for more flexible access to the UserDefaults class:

```python
>>> ud = UserDefaults()
>>> ud["key"] = value
>>> ...  # other operations here
>>> ud.sync()  # write back to plist file, does nothing on Obj-C backend
```

On supported platforms that have a Obj-C backend, the UserDefaults class acts as a
shim for NSUserDefaults. Otherwise, a naive file handle is used to modify
UserDefaults using plistlib.

Supported backends:
- pyobjc (MacOS)
- rubicon-objc (Darwin/Pyto)
- objc_util (Pythonista)

If your platform does not have a Obj-C backend (unless you are on Libterm/a-Shell),
you problably should **not** use this as directly writing to the plist file itself is
discouraged (as quoted from Apple's docstring):

> Don’t try to access the preferences subsystem directly. Modifying preference
> property list files may result in loss of changes, delay of reflecting changes,
> and app crashes.

The naive file method is kept to support platforms which do not have/cannot install
a Obj-C backend (i.e Libterm, a-Shell).

Known bugs:
- On Pyto, writing to the inputHistory key using the Obj-C backend results in a `SIGKILL` (crashes).

## Building

Use flit to build/install:

```bash
$ flit build
```
