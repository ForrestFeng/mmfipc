import time
import MmfIPC
import json
import threading

class MsgSender(MmfIPC.MmfIpcClient):
    def __init__(self, mmfName):
        super(MsgSender, self).__init__(mmfName)

    def FireMessage(self, msgName,  message):
        self.invoke("FireMessage", msgName, message)


class MsgCollector(MmfIPC.MmfIpcServer):
    def __init__(self, mmfName):
        super(MsgCollector, self).__init__(mmfName)

    def OnMessageEvent(self,msgName, message):
        print "Python world receive %s from .NET" % msgName
\


class CollectorThread(threading.Thread):
    def __init__(self, msgCollector):
        super(CollectorThread, self).__init__()
        self.messageCollector = msgCollector

    def run(self):
        self.messageCollector.run()
