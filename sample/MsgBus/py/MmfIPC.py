import win32event
import codecs
import mmap


class Mmf():
    """
    The MMF lay out
    It has at leat 2 blocks each block has a fixed size of 4096 + 32 (preceeding length) bytes.
    0. MMF Version, Config Blcok eg. The global string format for all the blocks.
    1. Return value block
    2. Function name block
    3. Argument number block
    4. First argument value from left to right
    5. Second argument value from left to right
    6. ... (up to 128 blocks)

    All blocks are used to store string with predfined format defined in the block 0.
    The first version of MMF stores all string in utf-8 format preceding with a 32 bytes
    leading number indicate how long the string it is.

    If a string for example the return string is too long, it will be truncted now. In the future
    define a negtive value of the preceeding length as a pointer to the new location in the MMF for
    the returned string.
    """

    def __init__(self, mmfName, stackSize = 1024*1024*8):
        self.mmfName = mmfName
        self.stackSize = stackSize
        self.headerSize = 32

        self.mmf = mmap.mmap(-1, self.stackSize, mmfName)
        self.emptyHeader = ' ' * self.headerSize
        self.encoding = 'utf8'

    def offset(self, index):
        if index == 0:
            return 0
        offset = 0
        while index > 0:
            self.mmf.seek(offset)
            length = self.mmf.read(self.headerSize)
            offset = offset + self.headerSize + int(length)
            index = index - 1

        return offset

    def _put_str_to_block(self, blockIdex, string):
        offset = self.offset(blockIdex)
        offsetStr = offset + self.headerSize
        self.mmf.seek(offset)
        self.mmf.write(codecs.encode(self.emptyHeader, self.encoding))
        self.mmf.seek(offset)
        self.mmf.write(codecs.encode(str(len(string)), self.encoding))
        self.mmf.seek(offsetStr)
        self.mmf.write(codecs.encode(string, self.encoding))

    def _get_str_from_block(self, blockIdx):
        offset = self.offset(blockIdx)
        self.mmf.seek(offset)
        length = self.mmf.read(self.headerSize)
        string = self.mmf.read(int(length))
        return string

    def put_func_and_args(self, funcName, *args):
        self._put_str_to_block(0, funcName)

        index = 1
        self._put_str_to_block(index, str(len(list(args))))

        for arg in list(args):
            index = index + 1
            self._put_str_to_block(index, str(arg))


    def get_func_and_args(self):
        """
        Return the func name, num of args and args as a tuple
        """
        funcName = self._get_str_from_block(0)
        argCnt = self._get_str_from_block(1)
        arglist = []
        index = 2
        for i in range(int(argCnt)):
            arglist.append(self._get_str_from_block(index))
            index = index + 1

        return funcName, argCnt, arglist

    def put_return_value(self, retValue):
        """
        Put the return value on to the MMF
        """
        self._put_str_to_block(0, str(retValue))

    def get_return_value(self):
        """
        Put the return value on to the MMF
        """
        return self._get_str_from_block(0)

class MmfIpcClient(object):
    DEBUG = False
    def __init__(self, mmfName):
        self.mmf = Mmf(mmfName)
        self.callingEvt = win32event.CreateEvent(None, False, False, mmfName + "CallingEvt")
        self.completeEvt = win32event.CreateEvent(None, False, False, mmfName + "CompleteEvt")
        self.mmfMutex = win32event.CreateMutex(None, False, mmfName + "MmfMutex")
        self.invokeMutex = win32event.CreateMutex(None, False, mmfName + "InvokeMutex")


    def invoke(self, funcName, *args):
        """
        Call me one by one
        Lock invokeMutex to ensure only one invoke is processed in multi-thread or multi-process client running
        Lock Mmf Mutex,
        1. Put data on mmf
        2. signal call start\
        Unlock Mutex
        3. wait on the cll completed signal
        4. retrive the return data
        5. Release invokeMutex
        6. return
        """
        try:
            win32event.WaitForSingleObject(self.invokeMutex, win32event.INFINITE)

            try:
                win32event.WaitForSingleObject(self.mmfMutex, win32event.INFINITE)
                self.mmf.put_func_and_args(funcName, *args)
                win32event.SetEvent(self.callingEvt)
            finally:
                win32event.ReleaseMutex(self.mmfMutex)

            # if callingEvt is consumed by server side it will be auto reset to no signal
            offlineInfo = ""
            if win32event.WaitForSingleObject(self.callingEvt, 0) == 0:
                # not consumed by server side
                offlineInfo = "{} Server is Offline!".format(self.mmf.mmfName)

            if self.DEBUG:
                argList = "";
                for i in range(len(args)):
                    if i + 1 < len(args):
                        argList += "{}, ".format(args[i])
                    else:
                        argList += "{0}".format(args[i])

                if offlineInfo != "":
                    print "{0}({1}) - Skiped as {2}".format(funcName, argList, offlineInfo)
                else:
                    print "{0}({1}) - Ivoked".format(funcName, argList)


            if offlineInfo != "":
                return "{0} - Skiped as {1}".format(funcName, offlineInfo)

            if win32event.WaitForSingleObject(self.completeEvt, 1000*5) == 0:
                return self.mmf.get_return_value()
            else:
                return "Ivoke timeout, {} Server may Offline or Dead!".format(self.mmf.mmfName)

        finally:
            win32event.ReleaseMutex(self.invokeMutex)

class MmfIpcServer(object):
    DEBUG = False
    def __init__(self, mmfName):
        self.mmf = Mmf(mmfName)
        self.callingEvt = win32event.CreateEvent(None, False, False, mmfName + "CallingEvt")
        self.completeEvt = win32event.CreateEvent(None, False, False, mmfName + "CompleteEvt")
        self.mmfMutex = win32event.CreateMutex(None, False, mmfName + "MmfMutex")



    def run(self):
        """
        Run with a dedicated thread
        1. Wait on calling signal
        Enter MMF Mutex
        2. Read func name and args
        3. Call implemention methods
        4. Put return value on to MMF
        Leave MMF Mutex
        Singal complete signal
        """
        print "Start to monitor and run functions from mmf..."
        while True:
            try:
                win32event.WaitForSingleObject(self.callingEvt, win32event.INFINITE)
                win32event.WaitForSingleObject(self.mmfMutex, win32event.INFINITE)
                func, argc, args = self.mmf.get_func_and_args()
                args = tuple(args)
                s = 'self.{}(*args)'.format(func)

                if self.DEBUG:
                    argList = ""
                    for i in range(len(args)):
                        if i + 1 < len(args):
                            argList += "{0}, ".format(args[i])
                        else:
                            argList += "{0}".format(args[i])
                    print "{0}({1})".format(func, argList)


                result = eval(s)
                #print s, result
                # do not set return value if return value is null (the method return nothing)
                if result is not None:
                    self.mmf.put_return_value(result)
            finally:
                win32event.ReleaseMutex(self.mmfMutex)
                win32event.SetEvent(self.completeEvt)

        input('please input')


