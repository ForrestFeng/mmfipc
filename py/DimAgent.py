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
        msg = '{"DeviceContainerName": "%s", "CorrelationId": "%s"}' % (logicalName, uuid.uuid1())
        DimAgent.__dimMsgSender.FireMessage("BuckySelectionReqMsg", msg)


    def VerifyHardwareState(self, property_name, expect_value, timeout=3):
        return DimAgent.__dimMsgCollector.VerifyHardwareState(property_name, expect_value, timeout)


    @property
    def HardwareStateEvtMsg(self):
        return DimAgent.__dimMsgCollector.HardwareStateEvtMsg

    @property
    def HardwareStateEvtMsgRaw(self):
        return DimAgent.__dimMsgCollector.HardwareStateEvtMsgRaw


def main():
    print('Start at:', ctime())
    agent = DimAgent()

    # do something to get the DimHardwareState first
    agent.ChangeBucy(DimAgent.WALL)
    agent.ChangeBucy(DimAgent.TABLE)
    time.sleep(3)

    while True:
        agent.ChangeBucy(DimAgent.WALL)
        wait_result, real_value, raw_msg = agent.VerifyHardwareState("WallBuckyRpt.Items.Selected", True, 4)
        print wait_result, real_value

        agent.ChangeBucy(DimAgent.TABLE)
        wait_result, real_value, raw_msg = agent.VerifyHardwareState("TableBuckyRpt.Items.Selected", True, 4)
        print wait_result, real_value

        agent.ChangeBucy(DimAgent.TABLE_TOP)
        wait_result, real_value, raw_msg = agent.VerifyHardwareState("TabletopBuckyRpt.Items.Selected", True, 4)
        print wait_result, real_value
        print raw_msg

    print('End at:', ctime())

















if __name__ == '__main__':
    main()