import re
import time
import MmfIPC
import json
import SDict
import uuid
import threading

class DimTestMsgSender(MmfIPC.MmfIpcClient):
    def FireMessage(self, msgName,  message):
        self.invoke("FireMessage", msgName, message)

class HardwareStateEvtMsgResolver():
    """
     hardStateEvt is the type of SortedDict
    """
    def __init__(self, hardStateEvt):
        self.hardStateEvt = hardStateEvt

    def _get_reptot_by_ReportType_LogicalName(self, reportType, logicalName):
        for rpt in self.hardStateEvt.Reports:
            if rpt.ReportType == reportType and rpt.Items.LogicalName == logicalName:
                return rpt
        return None

    def _get_report_by_ReportType_SerialNumber(self, reportType, serialNumber):
        for rpt in self.hardStateEvt.Reports:
            if rpt.ReportType == reportType and rpt.Items.SerialNumber == serialNumber:
                return rpt
        return None

    def _get_repport_by_Id(self, id):
        for rpt in self.hardStateEvt.Reports:
            if rpt.Id == id:
                return rpt
        return None

    def _get_reptot_by_ReportType(self, reportType):
        for rpt in self.hardStateEvt.Reports:
            if rpt.ReportType == reportType:
                return rpt
        return None

    @property
    def HardwareStateEvtMsg(self):
        """
        get the HardwareStateEvtMsg back from the r
        :return:
        """
        return self.hardStateEvt

    @property
    def CollimatorRpt(self):
        """
        :return: coresponding report in the form of SortedDict or None if not find
        """
        return self._get_reptot_by_ReportType_LogicalName("Collimator", "")

    @property
    def WallBuckyRpt(self):
        """
        :return: coresponding report in the form of SortedDict or None if not find
        """
        return self._get_reptot_by_ReportType_LogicalName("Bucky", "Wall")

    @property
    def TabletopBuckyRpt(self):
        """
        :return: coresponding report in the form of SortedDict or None if not find
        """
        return self._get_reptot_by_ReportType_LogicalName("Bucky", "None")

    @property
    def TableBucyRpt(self):
        """
        :return: coresponding report in the form of SortedDict or None if not find
        """
        return self._get_reptot_by_ReportType_LogicalName("Bucky", "Table")

    @property
    def DrxDetector1Rpt(self):
        """
        :return: coresponding report in the form of SortedDict or None if not find
        """
        return self._get_report_by_ReportType_SerialNumber("Detector", "000000000001")

    @property
    def DrxDetector2Rpt(self):
        """
        :return: coresponding report in the form of SortedDict or None if not find
        """
        return self._get_report_by_ReportType_SerialNumber("Detector", "000000100002")

    @property
    def DrxDetector3Rpt(self):
        """
        :return: coresponding report in the form of SortedDict or None if not find
        """
        return self._get_report_by_ReportType_SerialNumber("Detector", "000010100003")

    @property
    def UPSPCURpt(self):
        """
        :return: coresponding report in the form of SortedDict or None if not find
        """
        return self._get_reptot_by_ReportType_LogicalName("UPSPCU", "")

    @property
    def SystemStatusRpt(self):
        """
        :return: coresponding report in the form of SortedDict or None if not find
        """
        return self._get_reptot_by_ReportType("SystemStatus")

    @property
    def PositionerRpt(self):
        """
        :return: coresponding report in the form of SortedDict or None if not find
        """
        return self._get_reptot_by_ReportType_LogicalName("Positioner", "")

    @property
    def TableAecRpt(self):
        """
        :return: coresponding report in the form of SortedDict or None if not find
        """
        return self._get_reptot_by_ReportType_LogicalName("Aec", "Table")

    @property
    def WallAecRpt(self):
        """
        :return: coresponding report in the form of SortedDict or None if not find
        """
        return self._get_reptot_by_ReportType_LogicalName("Aec", "Wall")

    @property
    def GeneratorRpt(self):
        """
        :return: coresponding report in the form of SortedDict or None if not find
        """
        return self._get_reptot_by_ReportType_LogicalName("Generator", "")

    @property
    def AcquisitionRpt(self):
        """
        :return: coresponding report in the form of SortedDict or None if not find
        """
        return self._get_reptot_by_ReportType("Acquisition")
    
    @property
    def SelectedDeviceContainerRpt(self):
        """
        :return: The selected device container (bucky)
        The returned value is one of self.WallBucky, self.TableBucky and self.TabletopBucky
        """
        return self._get_repport_by_Id(self.AcquisitionRpt.Items.SelectedDeviceContainerId)
    
    @property
    def SelectedAcquisitionDeviceRpt(self):
        """
        Get the current acqusition device that is going to be used for next exposing. the acqusition device is
        associated with one device container(bucky) either in manual or auto mode.
        :return: current acqusition device that is going to be used for next exposing. It is one of the drx
        detector report or other detector report like Varian detector... TODO
        """
        receptorAssociation = self.SelectedReceptorAssociation
        return self._get_repport_by_Id(receptorAssociation.Items.AssociatedImageAcquisitionDeviceId)

    @property
    def SelectedReceptorAssociation(self):
        """
        Get the current acqusition SortedDict which has two sub keys
        self.ReceptorAssociation.AssociatedImageAcquisitionDeviceId
        self.AssociatedImageAcquisitionDeviceId.IsManual
        :return: current acqusition SortedDict to be used for next exposing
        """
        return self.AcquisitionRpt.Items.ReceptorAssociations[self.AcquisitionRpt.Items.SelectedDeviceContainerId]


class DimTestMsgCollector(MmfIPC.MmfIpcServer):

    msgDict = SDict.SortedDict()

    def __init__(self, mmfName):
        super(DimTestMsgCollector, self).__init__(mmfName)
        # current  HardwareStateEvtMsgResolver object for the hardware state message string
        self.HardwareState = None
        # current hardware state message string
        self.HardwareStateEvtMsg = None
        self.Expection = {}

    def _processDimReplyEvtMsg(self, shortMsgType):
        self.msgDict['HardwareStateEvtMsg'] = self.msgDict.DimReplyEvtMsg.HardwareStateEvtMsg
        self._processHardwareStateEvtMsg("HardwareStateEvtMsg")

    def _processHardwareStateEvtMsg(self,  shortMsgType):
        self.HardwareState = HardwareStateEvtMsgResolver(self.msgDict.HardwareStateEvtMsg)
        for k in self.Expection.keys():
            evalStr = 'self.{}'.format(k)
            expectedValue = self.Expection[k][1]
            result = eval(evalStr)
            self.Expection[k] = (result, expectedValue)
        if self.HardwareState.WallBuckyRpt.Items.Selected:
            print 'Update Expectation WallBucky                  Wall Selected'
        if self.HardwareState.TabletopBuckyRpt.Items.Selected:
            print 'Update Expectation TabletopBucky              None Selected'


    def DumpHardwareStateEvtMsg(self, shortMsgType, msgContent):
        tenbar = "-"*10
        if shortMsgType == "HardwareStateEvtMsg":
            r = HardwareStateEvtMsgResolver(self.msgDict.HardwareStateEvtMsg)
            print tenbar, "DrxDetector1Rpt", tenbar
            print "DrxDetector1Rpt.Items.DetectorType=", r.DrxDetector1Rpt.Items.DetectorType
            print "DrxDetector1Rpt.Items.ImagingSystemType=", r.DrxDetector1Rpt.Items.ImagingSystemType
            print "DrxDetector1Rpt.Items.DetectorOrientation=", r.DrxDetector1Rpt.Items.DetectorOrientation
            print "DrxDetector1Rpt.Items.DetectorEnabled=", r.DrxDetector1Rpt.Items.DetectorEnabled
            print "DrxDetector1Rpt.Items.FirmwareUpToDate=", r.DrxDetector1Rpt.Items.FirmwareUpToDate
            print "DrxDetector1Rpt.Items.FirmwareUpdateRequired=", r.DrxDetector1Rpt.Items.FirmwareUpdateRequired
            print "DrxDetector1Rpt.Items.Model=", r.DrxDetector1Rpt.Items.Model
            print "DrxDetector1Rpt.Items.SerialNumber=", r.DrxDetector1Rpt.Items.SerialNumber
            print "DrxDetector1Rpt.Items.DeviceState=", r.DrxDetector1Rpt.Items.DeviceState
            print "DrxDetector1Rpt.Items.DeviceType=", r.DrxDetector1Rpt.Items.DeviceType
            print "DrxDetector1Rpt.Items.ActuationCount=", r.DrxDetector1Rpt.Items.ActuationCount
            print "DrxDetector1Rpt.Items.ConnectionType=", r.DrxDetector1Rpt.Items.ConnectionType
            print "DrxDetector1Rpt.Items.SignalStrength=", r.DrxDetector1Rpt.Items.SignalStrength
            print "DrxDetector1Rpt.Items.NetworkConnectionError=", r.DrxDetector1Rpt.Items.NetworkConnectionError
            print "DrxDetector1Rpt.Items.IPAddress=", r.DrxDetector1Rpt.Items.IPAddress
            print "DrxDetector1Rpt.Items.CommunicationStatus=", r.DrxDetector1Rpt.Items.CommunicationStatus
            print "DrxDetector1Rpt.Items.CurrentSleepState=", r.DrxDetector1Rpt.Items.CurrentSleepState
            print "DrxDetector1Rpt.Items.PreventSleep=", r.DrxDetector1Rpt.Items.PreventSleep
            if r.DrxDetector1Rpt.Items.NetworkConnectionError:
                print "!! BatteryInformation not valid because of NetworkConnectionError !!"
            print "DrxDetector1Rpt.Items.BatteryInformation.CurrentChargeLevel=", r.DrxDetector1Rpt.Items.BatteryInformation.CurrentChargeLevel
            print "DrxDetector1Rpt.Items.BatteryInformation.CurrentChargePercentage=", r.DrxDetector1Rpt.Items.BatteryInformation.CurrentChargePercentage
            print "DrxDetector1Rpt.Items.BatteryInformation.BatteryInError=", r.DrxDetector1Rpt.Items.BatteryInformation.BatteryInError
            print "DrxDetector1Rpt.Items.BatteryInformation.BatteryCharging=", r.DrxDetector1Rpt.Items.BatteryInformation.BatteryCharging
            print "DrxDetector1Rpt.Items.BatteryInformation.BatteryLow=", r.DrxDetector1Rpt.Items.BatteryInformation.BatteryLow
            print "DrxDetector1Rpt.Items.BatteryInformation.BatteryDrained=", r.DrxDetector1Rpt.Items.BatteryInformation.BatteryDrained
            print "DrxDetector1Rpt.Items.BatteryInformation.BatteryMaxChargeLevel=", r.DrxDetector1Rpt.Items.BatteryInformation.BatteryMaxChargeLevel
            print "DrxDetector1Rpt.Items.BatteryInformation.BatteryNumberOfCharges=", r.DrxDetector1Rpt.Items.BatteryInformation.BatteryNumberOfCharges
            print "DrxDetector1Rpt.Items.BatteryInformation.BatteryTemperature=", r.DrxDetector1Rpt.Items.BatteryInformation.BatteryTemperature

            print tenbar, "GeneratorRpt", tenbar
            print "GeneratorRpt.Items.Kvp=", r.GeneratorRpt.Items.Kvp
            print "GeneratorRpt.Items.Ma=", r.GeneratorRpt.Items.Ma
            print "GeneratorRpt.Items.Time=", r.GeneratorRpt.Items.Time
            print "GeneratorRpt.Items.Mas=", r.GeneratorRpt.Items.Mas
            print "GeneratorRpt.Items.FocalSpot=", r.GeneratorRpt.Items.FocalSpot
            print "GeneratorRpt.Items.ExposureMode=", r.GeneratorRpt.Items.ExposureMode
            print "GeneratorRpt.Items.ExposureTech=", r.GeneratorRpt.Items.ExposureTech
            print "GeneratorRpt.Items.AecAvailable=", r.GeneratorRpt.Items.AecAvailable
            print "GeneratorRpt.Items.IsFocalSpotEditable=", r.GeneratorRpt.Items.IsFocalSpotEditable
            print "GeneratorRpt.Items.AecBackupMode=", r.GeneratorRpt.Items.AecBackupMode
            print "GeneratorRpt.Items.AnodeHeat=", r.GeneratorRpt.Items.AnodeHeat
            print "GeneratorRpt.Items.Model=", r.GeneratorRpt.Items.Model
            print "GeneratorRpt.Items.SerialNumber=", r.GeneratorRpt.Items.SerialNumber
            print "GeneratorRpt.Items.DeviceState=", r.GeneratorRpt.Items.DeviceState
            print "GeneratorRpt.Items.DeviceType=", r.GeneratorRpt.Items.DeviceType
            print "GeneratorRpt.Items.ActuationCount=", r.GeneratorRpt.Items.ActuationCount


            print tenbar, "SystemStatus", tenbar
            print "SystemStatusRpt.Items.State=", r.SystemStatusRpt.Items.State
            print "SystemStatusRpt.Items.OperationMode=", r.SystemStatusRpt.Items.OperationMode
            print "SystemStatusRpt.Items.NotReadyReasons=", r.SystemStatusRpt.Items.NotReadyReasons


            print tenbar, "WallAecRpt", tenbar
            print "WallAecRpt.Items.Selected=", r.WallAecRpt.Items.Selected
            print "WallAecRpt.Items.ModeOn=", r.WallAecRpt.Items.ModeOn
            print "WallAecRpt.Items.AecTech=", r.WallAecRpt.Items.AecTech
            print "WallAecRpt.Items.Mode=", r.WallAecRpt.Items.Mode
            print "WallAecRpt.Items.Availability=", r.WallAecRpt.Items.Availability
            print "WallAecRpt.Items.Density=", r.WallAecRpt.Items.Density
            print "WallAecRpt.Items.Fields=", r.WallAecRpt.Items.Fields
            print "WallAecRpt.Items.IsAecEnableInWork=", r.WallAecRpt.Items.IsAecEnableInWork
            print "WallAecRpt.Items.Model=", r.WallAecRpt.Items.Model
            print "WallAecRpt.Items.LogicalName=", r.WallAecRpt.Items.LogicalName
            print "WallAecRpt.Items.DeviceState=", r.WallAecRpt.Items.DeviceState
            print "WallAecRpt.Items.FilmScreen=", r.WallAecRpt.Items.FilmScreen
            print "WallAecRpt.Items.DeviceType=", r.WallAecRpt.Items.DeviceType

            print tenbar, "WallBucky", tenbar
            print "WallBuckyRpt.Items.DeviceState=", r.WallBuckyRpt.Items.DeviceState
            print "WallBuckyRpt.Items.DeviceType=", r.WallBuckyRpt.Items.DeviceType
            print "WallBuckyRpt.Items.Selected=", r.WallBuckyRpt.Items.Selected
            print "WallBuckyRpt.Items.LogicalName=", r.WallBuckyRpt.Items.LogicalName
            print "WallBuckyRpt.Items.BuckyOrientation=", r.WallBuckyRpt.Items.BuckyOrientation
            print "WallBuckyRpt.Items.ConsoleOrientation=", r.WallBuckyRpt.Items.ConsoleOrientation
            print "WallBuckyRpt.Items.Extension=", r.WallBuckyRpt.Items.Extension
            print "WallBuckyRpt.Items.AECInstallationOrientation=", r.WallBuckyRpt.Items.AECInstallationOrientation
            print "WallBuckyRpt.Items.AECDeviceExtends=", r.WallBuckyRpt.Items.AECDeviceExtends
            print "WallBuckyRpt.Items.GridDeviceExtends=", r.WallBuckyRpt.Items.GridDeviceExtends
            print "WallBuckyRpt.Items.CanRotate=", r.WallBuckyRpt.Items.CanRotate
            print "WallBuckyRpt.Items.CanTilt=", r.WallBuckyRpt.Items.CanTilt
            print "WallBuckyRpt.Items.CanInvert=", r.WallBuckyRpt.Items.CanInvert
            print "WallBuckyRpt.Items.SupportsAEC=", r.WallBuckyRpt.Items.SupportsAEC
            print "WallBuckyRpt.Items.SupportsGridTypeDetection=", r.WallBuckyRpt.Items.SupportsGridTypeDetection
            print "WallBuckyRpt.Items.DetectorResultOrientation=", r.WallBuckyRpt.Items.DetectorResultOrientation
            print "WallBuckyRpt.Items.GridMagnetNumber=", r.WallBuckyRpt.Items.GridMagnetNumber
            print "WallBuckyRpt.Items.Model=", r.WallBuckyRpt.Items.Model


            print tenbar, "AcquisitionRpt", tenbar
            print "AcquisitionRpt.Items.ReceptorAssociations=", r.AcquisitionRpt.Items.ReceptorAssociations
            print "AcquisitionRpt.Items.SelectedDeviceContainerId=", r.AcquisitionRpt.Items.SelectedDeviceContainerId
            print "AcquisitionRpt.Items.SelectedDeviceIds=", r.AcquisitionRpt.Items.SelectedDeviceIds
            print "SelectedReceptorAssociation.IsManual=", r.SelectedReceptorAssociation.IsManual
            print "SelectedReceptorAssociation.AssociatedImageAcquisitionDeviceId=", r.SelectedReceptorAssociation.AssociatedImageAcquisitionDeviceId

            print "GeneratorRpt.Items.Kvp=", r.GeneratorRpt.Items.Kvp

    def OnMessageEvent(self, rawMsg):
        # Csh.Devices.Messages.OperationModeReqMsg long key must use eg. msgDict["Csh.Devices.Messages.OperationModeReqMsg"] to access
        longMsgType = rawMsg[0:rawMsg.find(" - ")]
        # simple key can use eg. msgDict.OperationModeReqMsg to access
        shortMsgType = longMsgType[longMsgType.rfind(".")+1:]
        msgTime = rawMsg[rawMsg.find(" - ")+3:rawMsg.find("\r\n")]
        msgContent = rawMsg[rawMsg.find("\r\n")+2:]

        js = json.loads(msgContent)
        conetDict = SDict.SortedDict(js)

        self.msgDict[shortMsgType] = conetDict
        self.msgDict[shortMsgType+"_Time"] = msgTime
        self.msgDict[shortMsgType+"_Body"] = msgTime
        #self.DumpHardwareStateEvtMsg(shortMsgType, msgContent)

        # process messages
        if shortMsgType == 'DimReplyEvtMsg':
            self._processDimReplyEvtMsg('DimReplyEvtMsg')
        elif shortMsgType == 'HardwareStateEvtMsg':
            self._processHardwareStateEvtMsg('HardwareStateEvtMsg')

        return shortMsgType

    def WaitExpressionMatch(self, expressionString, expectValue, timeoutInSeconds):
        """
        eg. Wait("HardwareState.WallBuckyRpt.Items.Selected", True, 2)
        :param
        :return: True if expectValue equal to expressionString within timeOutInSeconds else return False
        """
        timeTaken = 0
        waitString = 'self.{}'.format(expressionString)
        while timeTaken < timeoutInSeconds:
            result = eval(waitString)
            logmsg = waitString,  '| result:{} | expected:{}'.format(result, expectValue)
            #print logmsg
            if result == expectValue:
                return True
            else:
                timeTaken += 0.2
                time.sleep(0.2)
        print logmsg
        return False

    def Expect(self,expressionString, expectValue):
        # tuple contains (real result, expected value)
        self.Expection[expressionString] = (None, expectValue)

    def Verify(self, expressionString, timeoutInSeconds):
        timeTaken = 0
        while timeTaken < timeoutInSeconds:
            if self.Expection[expressionString][0] == self.Expection[expressionString][1]:
                return True
            else:
                timeTaken += 0.5
                time.sleep(0.5)
        del self.Expection[expressionString]
        return False

    def WaitRegexMatch(self, shortMsgType, patternToSearch, timeoutInSeconds):
        """
        :param shortMsgType:string
        :param patternToSearch:string
        :return: True if the pattern is found in shortMsgType else return False
        """
        timeTaken = 0

        msgContent = None
        try:
            msgContent = eval("self.{}".format(shortMsgType))
        except Exception as e:
            return False

        while timeTaken < timeoutInSeconds:
            result = re.match(patternToSearch, msgContent,  re.DOTALL)
            logmsg = "self.HardwareStateEvtMsg match | {} | {}".format(patternToSearch, result is not None)
            #print logmsg
            if result is not None:
                return True
            else:
                timeTaken += 0.2
                time.sleep(0.2)
        print logmsg
        return False

class CollectorThread(threading.Thread):
    def __init__(self, dimMsgCollector):
        super(CollectorThread, self).__init__()
        self.dimMessageCollector = dimMsgCollector
    def run(self):
        self.dimMessageCollector.run()

# background thread to collect dim message
dimMsgCollector = DimTestMsgCollector("DIMTestWithIPCMsgPump")
collectorThread = CollectorThread(dimMsgCollector)
collectorThread.start()

# main thread opration to change bucky
dimTestMsgSender = DimTestMsgSender("DIMTestWithIPCReqHandler")


while True:


    time.sleep(2)
    print '-'*30
    print 'Change bucky                          to Wall'
    bucky = '{"DeviceContainerName": "%s", "CorrelationId": "%s"}' % ('Wall', uuid.uuid1())


    if dimMsgCollector.HardwareState:
        dimMsgCollector.Expect("HardwareState.WallBuckyRpt.Items.Selected", True)
    dimTestMsgSender.FireMessage("BuckySelectionReqMsg", bucky)
    # wait till the WallBuckyRpt.Items.Selected is Ture
    if dimMsgCollector.HardwareState:
        print dimMsgCollector.Verify("HardwareState.WallBuckyRpt.Items.Selected", 5)
        print '                  WallBuckySelected=                       ', dimMsgCollector.HardwareState.WallBuckyRpt.Items.Selected

        #dimMsgCollector.WaitExpressionMatch("HardwareState.WallBuckyRpt.Items.Selected", True, 5)
    # if dimMsgCollector.HardwareStateEvtMsg:
    #     dimMsgCollector.WaitRegexMatch("HardwareStateEvtMsg", ".*Selected.*", 3)

    time.sleep(2)
    print '-'*30
    print 'Change bucky                          to None'
    bucky = '{"DeviceContainerName": "%s", "CorrelationId": "%s"}' % ('None', uuid.uuid1())
    if dimMsgCollector.HardwareState:
        dimMsgCollector.Expect("HardwareState.TabletopBuckyRpt.Items.Selected", True)

    dimTestMsgSender.FireMessage("BuckySelectionReqMsg", bucky)
    if dimMsgCollector.HardwareState:
        print dimMsgCollector.Verify("HardwareState.TabletopBuckyRpt.Items.Selected", 5)
        print '                  TabletopBuckySelected=                   ', dimMsgCollector.HardwareState.TabletopBuckyRpt.Items.Selected
    # wait till the TabletopBuckyRpt.Items.Selected is Ture
    # if dimMsgCollector.HardwareState:
    #     dimMsgCollector.WaitExpressionMatch("HardwareState.TabletopBuckyRpt.Items.Selected", True, 5)




# sample message process
def convert_messsage_to_sorted_dict_sample(rawMsg):
    rawMsg = 'Csh.Devices.Messages.OperationModeReqMsg - 6/4/2015 1:05:28 PM\r\n{\r\n  "Mode": "Acquisition",\r\n  "CorrelationId": "e8a61b60-8439-44ad-b9fc-c2372c3a323a"\r\n}'
    # Csh.Devices.Messages.Operatself.msgDict.HardwareStateEvtMsgionModeReqMsg long key must use msgDict["Csh.Devices.Messages.OperationModeReqMsg"] to access
    msgType = rawMsg[0:rawMsg.find(" - ")]
    # simple key can use msgDict.OperationModeReqMsg to access
    msgTypeS = msgType[msgType.rfind(".")+1:]
    msgTime = rawMsg[rawMsg.find(" - ")+3:rawMsg.find("\r\n")]
    msgContent = rawMsg[rawMsg.find("\r\n")+2:]

    # print msgType
    # print '-' * 33
    # print msgTime
    # print '-' * 33
    # print msgContent
    # jd = json.JSONDecoder(msgContent)
    # print type(jd)
    # print dir(jd)
    # js = json.loads(msgContent)
    # print js
    # print type(js)

    js = json.loads(msgContent)
    msgDict = SDict.SortedDict()
    conetDict = SDict.SortedDict(js)

    msgDict[msgType] = conetDict
    msgDict[msgTypeS] = conetDict
    msgDict[msgTypeS+"_Time"] = msgTime

    print msgDict["Csh.Devices.Messages.OperationModeReqMsg"].Mode
    print msgDict.OperationModeReqMsg.Mode
    print msgDict.OperationModeReqMsg_Time

#convert_messsage_to_sorted_dict("")