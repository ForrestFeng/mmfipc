import re
import time
import MmfIPC
import json
import SDict
import uuid
import threading

class DimMsgSender(MmfIPC.MmfIpcClient):
    def FireMessage(self, msgName,  message):
        self.invoke("FireMessage", msgName, message)


class HardwareStateEvtMsgResolver():
    """
     hardStateEvt is the type of SortedDict
    """
    def __init__(self, hardStateEvt):
        self.hardStateEvt = hardStateEvt

    def __get_reptot_by_ReportType_LogicalName(self, reportType, logicalName):
        for rpt in self.hardStateEvt.Reports:
            if rpt.ReportType == reportType and rpt.Items.LogicalName == logicalName:
                return rpt
        return None

    def __get_report_by_ReportType_SerialNumber(self, reportType, serialNumber):
        for rpt in self.hardStateEvt.Reports:
            if rpt.ReportType == reportType and rpt.Items.SerialNumber == serialNumber:
                return rpt
        return None

    def __get_repport_by_Id(self, id):
        for rpt in self.hardStateEvt.Reports:
            if rpt.Id == id:
                return rpt
        return None

    def __get_reptot_by_ReportType(self, reportType):
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
        return self.__get_reptot_by_ReportType_LogicalName("Collimator", "")

    @property
    def WallBuckyRpt(self):
        """
        :return: coresponding report in the form of SortedDict or None if not find
        """
        return self.__get_reptot_by_ReportType_LogicalName("Bucky", "Wall")

    @property
    def TabletopBuckyRpt(self):
        """
        :return: coresponding report in the form of SortedDict or None if not find
        """
        return self.__get_reptot_by_ReportType_LogicalName("Bucky", "None")

    @property
    def TableBuckyRpt(self):
        """
        :return: coresponding report in the form of SortedDict or None if not find
        """
        return self.__get_reptot_by_ReportType_LogicalName("Bucky", "Table")

    @property
    def DrxDetector1Rpt(self):
        """
        :return: coresponding report in the form of SortedDict or None if not find
        """
        return self.__get_report_by_ReportType_SerialNumber("Detector", "000000000001")

    @property
    def DrxDetector2Rpt(self):
        """
        :return: coresponding report in the form of SortedDict or None if not find
        """
        return self.__get_report_by_ReportType_SerialNumber("Detector", "000000100002")

    @property
    def DrxDetector3Rpt(self):
        """
        :return: coresponding report in the form of SortedDict or None if not find
        """
        return self.__get_report_by_ReportType_SerialNumber("Detector", "000010100003")

    @property
    def UPSPCURpt(self):
        """
        :return: coresponding report in the form of SortedDict or None if not find
        """
        return self.__get_reptot_by_ReportType_LogicalName("UPSPCU", "")

    @property
    def SystemStatusRpt(self):
        """
        :return: coresponding report in the form of SortedDict or None if not find
        """
        return self.__get_reptot_by_ReportType("SystemStatus")

    @property
    def PositionerRpt(self):
        """
        :return: coresponding report in the form of SortedDict or None if not find
        """
        return self.__get_reptot_by_ReportType_LogicalName("Positioner", "")

    @property
    def TableAecRpt(self):
        """
        :return: coresponding report in the form of SortedDict or None if not find
        """
        return self.__get_reptot_by_ReportType_LogicalName("Aec", "Table")

    @property
    def WallAecRpt(self):
        """
        :return: coresponding report in the form of SortedDict or None if not find
        """
        return self.__get_reptot_by_ReportType_LogicalName("Aec", "Wall")

    @property
    def GeneratorRpt(self):
        """
        :return: coresponding report in the form of SortedDict or None if not find
        """
        return self.__get_reptot_by_ReportType_LogicalName("Generator", "")

    @property
    def AcquisitionRpt(self):
        """
        :return: coresponding report in the form of SortedDict or None if not find
        """
        return self.__get_reptot_by_ReportType("Acquisition")

    @property
    def SelectedDeviceContainerRpt(self):
        """
        :return: The selected device container (bucky)
        The returned value is one of self.WallBucky, self.TableBucky and self.TabletopBucky
        """
        return self.__get_repport_by_Id(self.AcquisitionRpt.Items.SelectedDeviceContainerId)

    @property
    def SelectedAcquisitionDeviceRpt(self):
        """
        Get the current acqusition device that is going to be used for next exposing. the acqusition device is
        associated with one device container(bucky) either in manual or auto mode.
        :return: current acqusition device that is going to be used for next exposing. It is one of the drx
        detector report or other detector report like Varian detector... TODO
        """
        receptorAssociation = self.SelectedReceptorAssociation
        return self.__get_repport_by_Id(receptorAssociation.Items.AssociatedImageAcquisitionDeviceId)

    @property
    def SelectedReceptorAssociation(self):
        """
        Get the current acqusition SortedDict which has two sub keys
        self.ReceptorAssociation.AssociatedImageAcquisitionDeviceId
        self.AssociatedImageAcquisitionDeviceId.IsManual
        :return: current acqusition SortedDict to be used for next exposing
        """
        return self.AcquisitionRpt.Items.ReceptorAssociations[self.AcquisitionRpt.Items.SelectedDeviceContainerId]


class DimMsgCollector(MmfIPC.MmfIpcServer):
    __FLAG_PRINT_BUCKY_CHANGE = True
    __FLAG_PRINT_SYSTEM_STATUS = True
    __FLAG_PRINT_MESSAGE_TYPE = False
    __FLAG_PRINT_LONG_BAR_ON_BCUCKY_CHANGE = True
    __Long_Bar = "-" * 100
    __FLAG_DUMP_HARDWAE_STATE = False


    def __init__(self, mmfName):
        self.msgDict = SDict.SortedDict()
        super(DimMsgCollector, self).__init__(mmfName)
        # current  HardwareStateEvtMsgResolver object for the hardware state message string
        self.HardwareState = None
        # current hardware state message string
        self.HardwareStateEvtMsg = None
        self.Expection = {}

    def __processDimReplyEvtMsg(self, shortMsgType):
        self.msgDict['HardwareStateEvtMsg'] = self.msgDict.DimReplyEvtMsg.HardwareStateEvtMsg
        self.__processHardwareStateEvtMsg("HardwareStateEvtMsg")

    def __processHardwareStateEvtMsg(self,  shortMsgType):
        self.HardwareState = HardwareStateEvtMsgResolver(self.msgDict.HardwareStateEvtMsg)

        if DimMsgCollector.__FLAG_DUMP_HARDWAE_STATE:
            self.DumpHardwareState()

        for k in self.Expection.keys():
            evalStr = 'self.{}'.format(k)
            expectedValue = self.Expection[k][1]
            result = eval(evalStr)
            self.Expection[k] = (result, expectedValue)

        if DimMsgCollector.__FLAG_PRINT_BUCKY_CHANGE:
            if self.HardwareState.WallBuckyRpt.Items.Selected:
                print "%30s: %s" % ('Update Bucky', 'Wall Selected')
            if self.HardwareState.TabletopBuckyRpt.Items.Selected:
                print "%30s: %s" % ('Update Bucky', 'None Selected')
            if self.HardwareState.TableBuckyRpt.Items.Selected:
                print "%30s: %s" % ('Update Bucky', 'Table Selected')

        if DimMsgCollector.__FLAG_PRINT_SYSTEM_STATUS:
            print "%30s: %s" % ("State", self.HardwareState.SystemStatusRpt.Items.State)
            print "%30s: %s" % ("OperationMode", self.HardwareState.SystemStatusRpt.Items.OperationMode)
            print "%30s: %s" % ("NotReadyReasons", self.HardwareState.SystemStatusRpt.Items.NotReadyReasons)

    def DumpHardwareState(self):
        tenbar = "-"*10
        r = self.HardwareState
        print tenbar, "DrxDetector1Rpt", tenbar
        print "DrxDetector1Rpt.Items.DetectorType=", self.HardwareState.DrxDetector1Rpt.Items.DetectorType
        print "DrxDetector1Rpt.Items.ImagingSystemType=", self.HardwareState.DrxDetector1Rpt.Items.ImagingSystemType
        print "DrxDetector1Rpt.Items.DetectorOrientation=", self.HardwareState.DrxDetector1Rpt.Items.DetectorOrientation
        print "DrxDetector1Rpt.Items.DetectorEnabled=", self.HardwareState.DrxDetector1Rpt.Items.DetectorEnabled
        print "DrxDetector1Rpt.Items.FirmwareUpToDate=", self.HardwareState.DrxDetector1Rpt.Items.FirmwareUpToDate
        print "DrxDetector1Rpt.Items.FirmwareUpdateRequired=", self.HardwareState.DrxDetector1Rpt.Items.FirmwareUpdateRequired
        print "DrxDetector1Rpt.Items.Model=", self.HardwareState.DrxDetector1Rpt.Items.Model
        print "DrxDetector1Rpt.Items.SerialNumber=", self.HardwareState.DrxDetector1Rpt.Items.SerialNumber
        print "DrxDetector1Rpt.Items.DeviceState=", self.HardwareState.DrxDetector1Rpt.Items.DeviceState
        print "DrxDetector1Rpt.Items.DeviceType=", self.HardwareState.DrxDetector1Rpt.Items.DeviceType
        print "DrxDetector1Rpt.Items.ActuationCount=", self.HardwareState.DrxDetector1Rpt.Items.ActuationCount
        print "DrxDetector1Rpt.Items.ConnectionType=", self.HardwareState.DrxDetector1Rpt.Items.ConnectionType
        print "DrxDetector1Rpt.Items.SignalStrength=", self.HardwareState.DrxDetector1Rpt.Items.SignalStrength
        print "DrxDetector1Rpt.Items.NetworkConnectionError=", self.HardwareState.DrxDetector1Rpt.Items.NetworkConnectionError
        print "DrxDetector1Rpt.Items.IPAddress=", self.HardwareState.DrxDetector1Rpt.Items.IPAddress
        print "DrxDetector1Rpt.Items.CommunicationStatus=", self.HardwareState.DrxDetector1Rpt.Items.CommunicationStatus
        print "DrxDetector1Rpt.Items.CurrentSleepState=", self.HardwareState.DrxDetector1Rpt.Items.CurrentSleepState
        print "DrxDetector1Rpt.Items.PreventSleep=", self.HardwareState.DrxDetector1Rpt.Items.PreventSleep
        if self.HardwareState.DrxDetector1Rpt.Items.NetworkConnectionError:
            print "!! BatteryInformation not valid because of NetworkConnectionError !!"
        print "DrxDetector1Rpt.Items.BatteryInformation.CurrentChargeLevel=", self.HardwareState.DrxDetector1Rpt.Items.BatteryInformation.CurrentChargeLevel
        print "DrxDetector1Rpt.Items.BatteryInformation.CurrentChargePercentage=", self.HardwareState.DrxDetector1Rpt.Items.BatteryInformation.CurrentChargePercentage
        print "DrxDetector1Rpt.Items.BatteryInformation.BatteryInError=", self.HardwareState.DrxDetector1Rpt.Items.BatteryInformation.BatteryInError
        print "DrxDetector1Rpt.Items.BatteryInformation.BatteryCharging=", self.HardwareState.DrxDetector1Rpt.Items.BatteryInformation.BatteryCharging
        print "DrxDetector1Rpt.Items.BatteryInformation.BatteryLow=", self.HardwareState.DrxDetector1Rpt.Items.BatteryInformation.BatteryLow
        print "DrxDetector1Rpt.Items.BatteryInformation.BatteryDrained=", self.HardwareState.DrxDetector1Rpt.Items.BatteryInformation.BatteryDrained
        print "DrxDetector1Rpt.Items.BatteryInformation.BatteryMaxChargeLevel=", self.HardwareState.DrxDetector1Rpt.Items.BatteryInformation.BatteryMaxChargeLevel
        print "DrxDetector1Rpt.Items.BatteryInformation.BatteryNumberOfCharges=", self.HardwareState.DrxDetector1Rpt.Items.BatteryInformation.BatteryNumberOfCharges
        print "DrxDetector1Rpt.Items.BatteryInformation.BatteryTemperature=", self.HardwareState.DrxDetector1Rpt.Items.BatteryInformation.BatteryTemperature

        print tenbar, "GeneratorRpt", tenbar
        print "GeneratorRpt.Items.Kvp=", self.HardwareState.GeneratorRpt.Items.Kvp
        print "GeneratorRpt.Items.Ma=", self.HardwareState.GeneratorRpt.Items.Ma
        print "GeneratorRpt.Items.Time=", self.HardwareState.GeneratorRpt.Items.Time
        print "GeneratorRpt.Items.Mas=", self.HardwareState.GeneratorRpt.Items.Mas
        print "GeneratorRpt.Items.FocalSpot=", self.HardwareState.GeneratorRpt.Items.FocalSpot
        print "GeneratorRpt.Items.ExposureMode=", self.HardwareState.GeneratorRpt.Items.ExposureMode
        print "GeneratorRpt.Items.ExposureTech=", self.HardwareState.GeneratorRpt.Items.ExposureTech
        print "GeneratorRpt.Items.AecAvailable=", self.HardwareState.GeneratorRpt.Items.AecAvailable
        print "GeneratorRpt.Items.IsFocalSpotEditable=", self.HardwareState.GeneratorRpt.Items.IsFocalSpotEditable
        print "GeneratorRpt.Items.AecBackupMode=", self.HardwareState.GeneratorRpt.Items.AecBackupMode
        print "GeneratorRpt.Items.AnodeHeat=", self.HardwareState.GeneratorRpt.Items.AnodeHeat
        print "GeneratorRpt.Items.Model=", self.HardwareState.GeneratorRpt.Items.Model
        print "GeneratorRpt.Items.SerialNumber=", self.HardwareState.GeneratorRpt.Items.SerialNumber
        print "GeneratorRpt.Items.DeviceState=", self.HardwareState.GeneratorRpt.Items.DeviceState
        print "GeneratorRpt.Items.DeviceType=", self.HardwareState.GeneratorRpt.Items.DeviceType
        print "GeneratorRpt.Items.ActuationCount=", self.HardwareState.GeneratorRpt.Items.ActuationCount


        print tenbar, "SystemStatus", tenbar
        print "SystemStatusRpt.Items.State=", self.HardwareState.SystemStatusRpt.Items.State
        print "SystemStatusRpt.Items.OperationMode=", self.HardwareState.SystemStatusRpt.Items.OperationMode
        print "SystemStatusRpt.Items.NotReadyReasons=", self.HardwareState.SystemStatusRpt.Items.NotReadyReasons


        print tenbar, "WallAecRpt", tenbar
        print "WallAecRpt.Items.Selected=", self.HardwareState.WallAecRpt.Items.Selected
        print "WallAecRpt.Items.ModeOn=", self.HardwareState.WallAecRpt.Items.ModeOn
        print "WallAecRpt.Items.AecTech=", self.HardwareState.WallAecRpt.Items.AecTech
        print "WallAecRpt.Items.Mode=", self.HardwareState.WallAecRpt.Items.Mode
        print "WallAecRpt.Items.Availability=", self.HardwareState.WallAecRpt.Items.Availability
        print "WallAecRpt.Items.Density=", self.HardwareState.WallAecRpt.Items.Density
        print "WallAecRpt.Items.Fields=", self.HardwareState.WallAecRpt.Items.Fields
        print "WallAecRpt.Items.IsAecEnableInWork=", self.HardwareState.WallAecRpt.Items.IsAecEnableInWork
        print "WallAecRpt.Items.Model=", self.HardwareState.WallAecRpt.Items.Model
        print "WallAecRpt.Items.LogicalName=", self.HardwareState.WallAecRpt.Items.LogicalName
        print "WallAecRpt.Items.DeviceState=", self.HardwareState.WallAecRpt.Items.DeviceState
        print "WallAecRpt.Items.FilmScreen=", self.HardwareState.WallAecRpt.Items.FilmScreen
        print "WallAecRpt.Items.DeviceType=", self.HardwareState.WallAecRpt.Items.DeviceType

        print tenbar, "WallBucky", tenbar
        print "WallBuckyRpt.Items.DeviceState=", self.HardwareState.WallBuckyRpt.Items.DeviceState
        print "WallBuckyRpt.Items.DeviceType=", self.HardwareState.WallBuckyRpt.Items.DeviceType
        print "WallBuckyRpt.Items.Selected=", self.HardwareState.WallBuckyRpt.Items.Selected
        print "WallBuckyRpt.Items.LogicalName=", self.HardwareState.WallBuckyRpt.Items.LogicalName
        print "WallBuckyRpt.Items.BuckyOrientation=", self.HardwareState.WallBuckyRpt.Items.BuckyOrientation
        print "WallBuckyRpt.Items.ConsoleOrientation=", self.HardwareState.WallBuckyRpt.Items.ConsoleOrientation
        print "WallBuckyRpt.Items.Extension=", self.HardwareState.WallBuckyRpt.Items.Extension
        print "WallBuckyRpt.Items.AECInstallationOrientation=", self.HardwareState.WallBuckyRpt.Items.AECInstallationOrientation
        print "WallBuckyRpt.Items.AECDeviceExtends=", self.HardwareState.WallBuckyRpt.Items.AECDeviceExtends
        print "WallBuckyRpt.Items.GridDeviceExtends=", self.HardwareState.WallBuckyRpt.Items.GridDeviceExtends
        print "WallBuckyRpt.Items.CanRotate=", self.HardwareState.WallBuckyRpt.Items.CanRotate
        print "WallBuckyRpt.Items.CanTilt=", self.HardwareState.WallBuckyRpt.Items.CanTilt
        print "WallBuckyRpt.Items.CanInvert=", self.HardwareState.WallBuckyRpt.Items.CanInvert
        print "WallBuckyRpt.Items.SupportsAEC=", self.HardwareState.WallBuckyRpt.Items.SupportsAEC
        print "WallBuckyRpt.Items.SupportsGridTypeDetection=", self.HardwareState.WallBuckyRpt.Items.SupportsGridTypeDetection
        print "WallBuckyRpt.Items.DetectorResultOrientation=", self.HardwareState.WallBuckyRpt.Items.DetectorResultOrientation
        print "WallBuckyRpt.Items.GridMagnetNumber=", self.HardwareState.WallBuckyRpt.Items.GridMagnetNumber
        print "WallBuckyRpt.Items.Model=", self.HardwareState.WallBuckyRpt.Items.Model


        print tenbar, "AcquisitionRpt", tenbar
        print "AcquisitionRpt.Items.ReceptorAssociations=", self.HardwareState.AcquisitionRpt.Items.ReceptorAssociations
        print "AcquisitionRpt.Items.SelectedDeviceContainerId=", self.HardwareState.AcquisitionRpt.Items.SelectedDeviceContainerId
        print "AcquisitionRpt.Items.SelectedDeviceIds=", self.HardwareState.AcquisitionRpt.Items.SelectedDeviceIds
        print "SelectedReceptorAssociation.IsManual=", self.HardwareState.SelectedReceptorAssociation.IsManual
        print "SelectedReceptorAssociation.AssociatedImageAcquisitionDeviceId=", self.HardwareState.SelectedReceptorAssociation.AssociatedImageAcquisitionDeviceId

        print "GeneratorRpt.Items.Kvp=", self.HardwareState.GeneratorRpt.Items.Kvp

    def OnMessageEvent(self, rawMsg):
        # Csh.Devices.Messages.OperationModeReqMsg long key must use eg. msgDict["Csh.Devices.Messages.OperationModeReqMsg"] to access
        longMsgType = rawMsg[0:rawMsg.find(" - ")]
        # simple key can use eg. msgDict.OperationModeReqMsg to access
        shortMsgType = longMsgType[longMsgType.rfind(".")+1:]
        msgTime = rawMsg[rawMsg.find(" - ")+3:rawMsg.find("\r\n")]
        msgContent = rawMsg[rawMsg.find("\r\n")+2:]

        if DimMsgCollector.__FLAG_PRINT_LONG_BAR_ON_BCUCKY_CHANGE:
            if shortMsgType == "BuckySelectionReqMsg":
                print DimMsgCollector.__Long_Bar
        if DimMsgCollector.__FLAG_PRINT_MESSAGE_TYPE:
            print "%30s: %s" % ("MsgType", shortMsgType)

        # convert to sorted dict
        js = json.loads(msgContent)
        conetDict = SDict.SortedDict(js)

        # store messages
        self.msgDict[shortMsgType] = conetDict
        self.msgDict[shortMsgType+"_Time"] = msgTime
        self.msgDict[shortMsgType+"_Body"] = msgTime

        # process messages
        if shortMsgType == 'DimReplyEvtMsg':
            self.__processDimReplyEvtMsg('DimReplyEvtMsg')
        elif shortMsgType == 'HardwareStateEvtMsg':
            self.__processHardwareStateEvtMsg('HardwareStateEvtMsg')

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

    def Expect(self, expressionString, expectValue):
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
