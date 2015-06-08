from time import ctime
from DimMsg import *


class DimAgent():
    # const vaiable
    WALL = 'Wall'
    TABLE = "Table"
    TABLE_TOP = "None"

    # private object
    __dimMsgCollector = DimMsgCollector("DIMTestWithIPCMsgPump")
    __collectorThread = CollectorThread(__dimMsgCollector)
    __dimMsgSender = DimMsgSender("DIMTestWithIPCReqHandler")


    def __init__(self):
        DimAgent.__collectorThread.start()

    def ChangeBucy(self, logicalName, sync=False):
        container = '{"DeviceContainerName": "%s", "CorrelationId": "%s"}' % (logicalName, uuid.uuid1())
        DimAgent.__dimMsgSender.FireMessage("BuckySelectionReqMsg", container)


def main():
    print('Start at:', ctime())
    agent = DimAgent()

    while True:
        agent.ChangeBucy(DimAgent.WALL)
        time.sleep(2)
        agent.ChangeBucy(DimAgent.TABLE)
        time.sleep(2)
        agent.ChangeBucy(DimAgent.TABLE_TOP)
        time.sleep(2)

    print('End at:', ctime())

















if __name__ == '__main__':
    main()