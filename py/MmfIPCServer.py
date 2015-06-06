import MmfIPC


class IPCServer (MmfIPC.MmfIpcServer):
    def Add(self, a, b):
        return a + b

    def Hello(self, a, b, c):
        return a + b + c


server = IPCServer('ICalc')
server.run()
