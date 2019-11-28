import asyncio

# Using https://github.com/pyusb/pyusb
import usb.core
import usb.util

class VNWA(object):
    def __init__(self):
        self.usb = None

    def detect_vnwa(self):
        # find our device
        dev = usb.core.find(idVendor=0x20a0, idProduct=0x4118)

        # was it found?
        if dev is None:
            print('Device not found')
            return

        print(f"Connected to {dev.product} by {dev.manufacturer}")

        # set the active configuration. With no arguments, the first
        # configuration will be the active one
        dev.set_configuration()
        self.usb = dev

    def respond(self, writer, reply):
        print(f"< {reply}")
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

        if reqtype == 64:
            asciized = " ".join(f"{d}" for d in data)
            self.respond(writer, f"{cmd_num} {size} {asciized}\x00".encode("ascii"))
        elif isinstance(ret, int):
            self.respond(writer, f"{cmd_num} {ret}\x00".encode("ascii"))
        else: # list
            asciized = " ".join(f"{d}" for d in ret)
            self.respond(writer, f"{cmd_num} {len(ret)} {asciized}\x00".encode("ascii"))

    def process_close(self, writer, cmd_num, *args):
        self.respond(writer, f"{cmd_num} 0\x00".encode("ascii"))
        # TODO close usb

    def process_quit(self, writer, cmd_num, *args):
        self.respond(writer, f"{cmd_num} quit\x00".encode("ascii"))
        loop.stop()

    def process_getstrsmp(self, writer, cmd_num, req_type, *args):
        if req_type == '1':
            data = self.usb.manufacturer
        elif req_type == '2':
            data = self.usb.product

        self.respond(writer, "{no} 16 {value}\x00".format(
            no=cmd_num,
            value=" ".join(str(ord(c)) for c in data)).encode("ascii"))

    async def __call__(self, reader, writer):
        print("Client connected")
        while True:
            # Read command
            data = await reader.readuntil(b"\x00")
            print(f"> {data}")
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
        print("Connection closed.")


if __name__ == "__main__":
    vnwa = VNWA()
    vnwa.detect_vnwa()
    loop = asyncio.get_event_loop()
    coro = asyncio.start_server(vnwa, '127.0.0.1', 56789, loop=loop)
    server = loop.run_until_complete(coro)

    # Serve requests until Ctrl+C is pressed
    print('Serving on {}'.format(server.sockets[0].getsockname()))
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass

    # Close the server and collect the result
    server.close()
    loop.run_until_complete(server.wait_closed())
    
    # Leave python to handle cleanup and loop.close()

