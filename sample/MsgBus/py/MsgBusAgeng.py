from time import ctime
from MsgBus import *
import uuid


class MsgBusAgent():

    # private object
    # this object defined as class variables to avoid too many message sender or collector are created
    # in case you create many instance of MsgBusAgent
    __dimMsgCollector = MsgCollector("DIMTestWithIPCMsgPump")
    __collectorThread = CollectorThread(__dimMsgCollector)
    __dimMsgSender = MsgSender("DIMTestWithIPCReqHandler")

    def __init__(self):
        MsgBusAgent.__collectorThread.start()

    def TestSendOutMessage(self, containter_id):
        MsgBusAgent.__dimMsgSender.FireMessage("PythonMessage_%s" % containter_id, "")


def main():
    print('Start at:', ctime())
    agent = MsgBusAgent()

    for containter_id in range(1000):
        agent.TestSendOutMessage(containter_id)
        time.sleep(2)

    print('End at:', ctime())

if __name__ == '__main__':
    main()