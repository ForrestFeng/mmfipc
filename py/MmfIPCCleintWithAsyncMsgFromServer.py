import MmfIPC
from threading import Thread
import time

class IPCClient (MmfIPC.MmfIpcClient):
    def Add(self, a, b):
        result = self.invoke('Add', a, b)
        return result

    def SetName(self, name):
        result = self.invoke('SetName', name)

        return result
    def Hello(self, a, b, c):
        return self.invoke('Hello', a, b, c)


class IPCServerEvt (MmfIPC.MmfIpcServer):
    def OnNewMessage(self, msg):
        print msg


client = IPCClient("ICalc")

class ServerEvtThread(Thread):
    def run(self):
        serverEvt = IPCServerEvt("ServerEvt")
        serverEvt.run()

# start server in background thread
serverEvtThread = ServerEvtThread()
serverEvtThread.start()

i  = 0
while True:
    time.sleep(1)
    #client.Add(i, i)
    client.SetName("new name")
    i = i + 1

print 'Done'
