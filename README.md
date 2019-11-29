# USB proxy for VNWA running in wine

The [VNWA analyzer software](https://www.sdr-kits.net/DG8SAQ-VNWA-software-documentation-user-guide) is Windows only. However it is possible to use wine and start it in linux. The steps to configure it for such case are part of the installed program (Linux/VNWA\_Linux\_wine\_LAN.pdf). There is also an usb proxy included (usb\_lan\_server). Unfortunately that program was crashing for me on Fedora 30 and I decided to write a replacement.

## Prerequisites

- Python 3.6
- docopt (https://github.com/docopt/docopt)
- pyusb (https://github.com/pyusb/pyusb)
- usb backend library (libusb0.1 or libusb1.0)

## Usage

The preferred way to run the proxy is via [pipenv](https://github.com/pypa/pipenv):

```
pipenv install
pipenv run python3 server.py
```

## Author

Martin Sivak, OK7MS

## License

The code is published under the [Apache 2 license](https://www.apache.org/licenses/LICENSE-2.0).
