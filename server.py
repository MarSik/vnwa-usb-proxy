"""USB proxy for D8SAQ's VNWA running in wine.

Usage:
  server.py [options]

Options:
  -d --debug  Enable debugging information
"""

import asyncio
from docopt import docopt
import logging

# Using https://github.com/pyusb/pyusb
import usb.core
import usb.util

LOG = logging.getLogger("VNWA")
LOG_IO = logging.getLogger("VNWA.io")

class VNWA(object):
    def __init__(self):
        self.usb = None

    def detect_vnwa(self):
        # find our device
        dev = usb.core.find(idVendor=0x20a0, idProduct=0x4118)

        # was it found?
        if dev is None:
            LOG.info('Device not found')
            return

        LOG.info(f"Connected to {dev.product} by {dev.manufacturer}")

        # set the active configuration. With no arguments, the first
        # configuration will be the active one
        dev.set_configuration()
        self.usb = dev

    def respond(self, writer, reply):
        LOG_IO.debug(f"< {reply}")
        writer.write(reply)

    def process_hellolinux(self, writer, cmd_num, *args):
        self.respond(writer, f"{cmd_num} imhere\x00".encode("ascii"))

    def process_init(self, writer, cmd_num, *args):
        self.respond(writer, "{cmd_num} {ready} {manufacturer} {product} {address}\x00".format(
            cmd_num=cmd_num,
            ready="1" if self.usb else "0",
            manufacturer=self.usb.iManufacturer if self.usb else 0,
            product=self.usb.iProduct if self.usb else 0,
            address=self.usb.address if self.usb else 0).encode("ascii"))

    def process_open(self, writer, cmd_num, *args):
        self.respond(writer, f"{cmd_num}\x00".encode("ascii"))

    def process_ctrlmsg(self, writer, cmd_num, *args):
        reqtype, request, value, index, timeout, size = [int(f) for f in args[:6]]
        data = bytes(int(b) for b in args[6:])
        dataorsize = data if len(data) == size else size
        ret = self.usb.ctrl_transfer(reqtype, request, value, index, dataorsize, timeout=timeout)

        # The VNWA tool requires this, no idea why
        if reqtype == 64:
            asciized = " ".join(f"{d}" for d in data)
            self.respond(writer, f"{cmd_num} {size} {asciized}\x00".encode("ascii"))
        # No response from usb write, return number of written bytes
        elif isinstance(ret, int):
            self.respond(writer, f"{cmd_num} {ret}\x00".encode("ascii"))

        # usb read, return data
        else: # list
            asciized = " ".join(f"{d}" for d in ret)
            self.respond(writer, f"{cmd_num} {len(ret)} {asciized}\x00".encode("ascii"))

    def process_close(self, writer, cmd_num, *args):
        self.respond(writer, f"{cmd_num} 0\x00".encode("ascii"))
        # TODO close usb

    def process_quit(self, writer, cmd_num, *args):
        self.respond(writer, f"{cmd_num} quit\x00".encode("ascii"))
        #loop.stop()

    def process_getstrsmp(self, writer, cmd_num, req_type, *args):
        if req_type == '1':
            data = self.usb.manufacturer
        elif req_type == '2':
            data = self.usb.product

        self.respond(writer, "{no} 16 {value}\x00".format(
            no=cmd_num,
            value=" ".join(str(ord(c)) for c in data)).encode("ascii"))

    async def __call__(self, reader, writer):
        LOG_IO.info("Client connected")
        while True:
            # Read command
            data = await reader.readuntil(b"\x00")
            LOG_IO.debug(f"> {data}")
            if not data or data[-1] != 0x00:
                break

            # Remove the tailing \x00
            data = data[:-1]

            # Parse command
            # cmd_num, cmd, reqtype, request, value, index (int), timeout, size, data (int)...
            cmd_num, cmd, *parts = data.decode("ascii").split()
            getattr(self, "process_" + cmd)(writer, cmd_num, *parts)

            await writer.drain()  # Flush

        # Close connection
        writer.close()
        LOG_IO.info("Connection closed.")

async def main(vnwa):
    coro = await asyncio.start_server(vnwa, '127.0.0.1', 56789)

    # Serve requests until Ctrl+C is pressed
    addrs = ', '.join(str(sock.getsockname()) for sock in coro.sockets)
    LOG.info(f'Serving on {addrs}')
    try:
        async with coro:
            await coro.serve_forever()
    except KeyboardInterrupt:
        pass

    # Close the server and collect the result
    coro.close()
    await coro.wait_closed()


if __name__ == "__main__":
    args = docopt(__doc__)
    if args["--debug"]:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)
    logging.getLogger("asyncio").setLevel(logging.WARN)

    vnwa = VNWA()
    vnwa.detect_vnwa()
    asyncio.run(main(vnwa))


