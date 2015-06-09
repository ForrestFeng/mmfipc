using System;
using System.Collections.Generic;
using System.IO;
using System.IO.MemoryMappedFiles;
using System.Linq;
using System.Text;
using System.Runtime.InteropServices;

//#define DEBUG_PRINT

namespace MmfIPC
{
    internal class mmap
    {
        private Encoding codecs = new UTF8Encoding(true, true);
        private MemoryMappedFile mmf;
        private MemoryMappedViewStream stream;
        private BinaryReader reader;
        private BinaryWriter writer;
        public mmap(int fileno, int length, string tagname)
        {
            // create a memory-mapped file of length 1000 bytes and give it a 'map name' of 'test'
            mmf = MemoryMappedFile.CreateOrOpen(tagname, length);
            stream = mmf.CreateViewStream();
            reader = new BinaryReader(stream);
            writer = new BinaryWriter(stream);
        }

        ~mmap()
        {
            stream.Dispose();
            mmf.Dispose();
        }

        public string read(int length)
        {
            string ret;
            ret = codecs.GetString(reader.ReadBytes(length));
            
            return ret;
        }

        public void seek(int pos)
        {
            stream.Seek(pos, SeekOrigin.Begin);
        }

        public void write(byte[] bytes)
        {
            writer.Write(bytes);
        }

        public void write(string s)
        {
            write(codecs.GetBytes(s));
        }
    }

    internal class Mmf
    {
        //"""
        // The MMF lay out
        // It has at several blocs 
        // 0. Function name block (and the return value also put here)
        // 1. Argument number block
        // 2. Function name block
        // 3. First argument value from left to right
        // 4. Second argument value from left to right
        // 5. ... (up to 128 blocks)

        // All blocks are used to store string with predfined format defined in the block 0.
        // The first version of MMF stores all string in utf-8 format preceding with a 32 bytes
        // leading number indicate how long the string it is.

        // If a string for example the return string is too long, it will be truncted now. In the future
        // define a negtive value of the preceeding length as a pointer to the new location in the MMF for
        // the returned string.
        // """

        public string mmfName;
        private int headerSize;
        private int stackSize;
        private string emptyHeader;

        private mmap mmf;

        public Mmf(string mmfName, int stackSize = 1024*1024*8)
        {
            this.mmfName = mmfName;
            this.stackSize = stackSize;
            this.headerSize = 32;

            this.mmf = new mmap(-1, this.stackSize, this.mmfName);
            this.emptyHeader = "".PadRight(this.headerSize);
        }

        private int offset(int index)
        {
            if (index == 0)
                return 0;
            int offset = 0;
            while (index > 0)
            {
                this.mmf.seek(offset);
                string length = this.mmf.read(this.headerSize);
                offset = offset + this.headerSize + Convert.ToInt32(length);
                index = index - 1;
            }
            return offset;
        }

        private void _put_str_to_block(int blockIdex, string s)
        {
            int offset = this.offset(blockIdex);
            int offsetStr = offset + this.headerSize;
            this.mmf.seek(offset);
            this.mmf.write(this.emptyHeader);
            this.mmf.seek(offset);
            this.mmf.write(s.Length.ToString());
            this.mmf.seek(offsetStr);
            this.mmf.write(s);
        }


        private string _get_str_from_block(int blockIdx)
        {
            int offset = this.offset(blockIdx);
            this.mmf.seek(offset);
            var length = this.mmf.read(this.headerSize);
            string s = this.mmf.read(Convert.ToInt32(length));
            return s;
        }

        public void put_func_and_args(string funcName, string[] args)
        {
            this._put_str_to_block(0, funcName);

            int index = 1;
            this._put_str_to_block(index, args.Count().ToString());

            foreach (var arg in args)
            {
                index = index + 1;
                this._put_str_to_block(index, arg);
            }
        }

        public string get_func_and_args(ref int argc, ref object[] args)
        {
            var funcName = this._get_str_from_block(0);
            argc = Convert.ToInt32(this._get_str_from_block(1));
            var arglist = new List<object>();

            var index = 2;
            for (int i = 0; i < argc; i++)
            {
                arglist.Add(this._get_str_from_block(index));
                index = index + 1;
            }
            args = arglist.ToArray();
            return funcName;
        }


        public void put_return_value(string retValue)
        {
            this._put_str_to_block(0, retValue);
        }

        public string get_return_value()
        {
            return this._get_str_from_block(0);
        }
    }

    public class MmfIpcClinet
    {
        private Mmf mmf;
        private CLRProfiler.NamedAutoResetEvent callingEvt;
        private CLRProfiler.NamedAutoResetEvent completeEvt;
        private CLRProfiler.NameMutex mmfMutex;
        private CLRProfiler.NameMutex invokeMutext;

        /// <summary>
        /// The mmf ipc server
        /// </summary>
        /// <param name="mmfName">mmf name</param>
        /// <param name="stackSize">default mmf size</param>
        public MmfIpcClinet(string mmfName)
        {
            mmf = new Mmf(mmfName);
            // create events
            callingEvt = new CLRProfiler.NamedAutoResetEvent(mmfName + "CallingEvt", false);
            completeEvt = new CLRProfiler.NamedAutoResetEvent(mmfName + "CompleteEvt", false);
            mmfMutex = new CLRProfiler.NameMutex(mmfName + "MmfMutex", false);
            invokeMutext = new CLRProfiler.NameMutex(mmfName + "MmfMutex", false);
        }

        /// <summary>
        /// monitor and call function from mmf
        /// 
        /// </summary>
        public string invoke(string funcName, string[] args)
        {
            //Call me one by one
            //Lock invokeMutex to ensure only one invoke is processed in multi-thread or multi-process client running
            //Lock Mmf Mutex,
            //1. Put data on mmf
            //2. signal call start
            //Unlock Mutex
            //3. wait on the cll completed signal
            //4. retrive the return data
            //5. Release invokeMutex
            //6. return

            try
            {
                invokeMutext.Wait();

                try
                {
                    mmfMutex.Wait();
                    this.mmf.put_func_and_args(funcName, args);
                    callingEvt.Set();
                }
                finally
                {
                    mmfMutex.Release();
                }
               
                //if callingEvt is consumed by server side it will be auto reset to no signal
                string offlineInfo = null;
                if (callingEvt.Wait(0))
                {
                    // signale not consumed by server side  
                    offlineInfo = string.Format("{0} Server is Offline!", mmf.mmfName);
                }

#if DEBUG_PRINT
                string argList = "";
                for (int i = 0; i < args.Length; i++)
                {
                    if (i + 1 < args.Length)
                        argList += string.Format("{0}, ", args[i]);
                    else
                        argList += string.Format("{0}", args[i]);
                }
                if (offlineInfo != null)
                    Console.WriteLine("{0}({1}) - Skiped as {2}", funcName, argList, offlineInfo);
                else
                    Console.WriteLine("{0}({1}) - Ivoked", funcName, argList);
#endif

                if (offlineInfo != null)
                    return string.Format("{0} - Skiped as {1}", funcName, offlineInfo);

                // Server side might exit abnormally without complete the func processing. 
                // So we have to wait for 5 seconds at most 
                if (completeEvt.Wait(1000 * 5))
                {
                    return this.mmf.get_return_value();
                }
                else
                {
                    return string.Format("Ivoke timeout, {0} Server may Offline or Dead!", mmf.mmfName);
                }

            }
            finally
            {
                invokeMutext.Release();
            }
            
            
        }
    }

    public class MmfIpcServer
    {
        private Mmf mmf;
        private CLRProfiler.NamedAutoResetEvent callingEvt;
        private CLRProfiler.NamedAutoResetEvent completeEvt;
        private CLRProfiler.NameMutex mmfMutex;
        private object serverImp = null;

        /// <summary>
        /// The mmf ipc server
        /// </summary>
        /// <param name="mmfName">mmf name</param>
        /// <param name="serverImp">the real server implement server functions</param>
        public MmfIpcServer(string mmfName, object serverImp = null)
        {
            if (serverImp == null)
                this.serverImp = this;
            else
                this.serverImp = serverImp;
            
            mmf = new Mmf(mmfName);
            // create events
            callingEvt = new CLRProfiler.NamedAutoResetEvent(mmfName + "CallingEvt", false);
            completeEvt = new CLRProfiler.NamedAutoResetEvent(mmfName + "CompleteEvt", false);
            mmfMutex = new CLRProfiler.NameMutex(mmfName + "MmfMutex", false);

        }

        /// <summary>
        /// monitor and call function from mmf
        /// 
        /// </summary>
        public void run()
        {
            //Run with a dedicated thread
            //1. Wait on calling signal
            //Enter MMF Mutex
            //2. Read func name and args
            //3. Call implemention methods
            //4. Put return value on to MMF
            //Leave MMF Mutex
            //Singal complete signal

            while (true)
            {
                try
                {
                    callingEvt.Wait();
                    mmfMutex.Wait();

                    int argc = 0;
                    object[] args = null;

                    string func = this.mmf.get_func_and_args(ref argc, ref args);

                    var meth = serverImp.GetType().GetMethod(func);
#if DEBUG_PRINT
                    string argList = "";
                    for (int i = 0; i < args.Length; i++)
                    {
                        if (i + 1 < args.Length)
                            argList += string.Format("{0}, ", args[i]);
                        else
                            argList += string.Format("{0}", args[i]);
                    }
                    Console.WriteLine("{0}({1})", func, argList);
#endif
                    // do not set return value if return value is null (the method return type is void)
                    var result = meth.Invoke(serverImp, args);
                    if (result != null)
                        this.mmf.put_return_value(result as string);
                }
                finally
                {
                    mmfMutex.Release();
                    completeEvt.Set();
                }
                

            }
        }
    }

   
}




namespace CLRProfiler
{
    /// <summary>
    /// Summary description for NamedManualResetEvent.
    /// </summary>
    public class NamedManualResetEvent : NamedAutoResetEvent
    {
        public NamedManualResetEvent(string eventName, bool initialState, bool manualReset=true):base(eventName,initialState,manualReset)
        {
        }
       
        public bool Reset()
        {
            return ResetEvent(eventHandle);
        }
    }

    public class NamedAutoResetEvent
    {
        protected IntPtr eventHandle;

        struct SECURITY_ATTRIBUTES
        {
            public uint nLength;
            public IntPtr lpSecurityDescriptor;
            public int bInheritHandle;
        };

        public NamedAutoResetEvent(string eventName, bool initialState, bool manualReset = false)
        {
            SECURITY_ATTRIBUTES sa;
            sa.nLength = 12;
            sa.bInheritHandle = 0;
            if (!ConvertStringSecurityDescriptorToSecurityDescriptor("D: (A;OICI;GRGWGXSDWDWO;;;AU)", 1, out sa.lpSecurityDescriptor, IntPtr.Zero))
                throw new Exception("ConvertStringSecurityDescriptorToSecurityDescriptor returned error");
            eventHandle = CreateEvent(ref sa, manualReset, initialState, eventName);
            LocalFree(sa.lpSecurityDescriptor);
            if (eventHandle == IntPtr.Zero)
            {
                eventHandle = OpenEvent(0x00100002, false, eventName);
                if (eventHandle == IntPtr.Zero)
                    throw new Exception(string.Format("Couldn't create or open event {0}", eventName));
            }
        }

        ~NamedAutoResetEvent()
        {
            CloseHandle(eventHandle);
        }


        public bool Set()
        {
            return SetEvent(eventHandle);
        }

        // default wait for INFINITE(-1) time
        public bool Wait(int timeOut = -1)
        {
            return WaitForSingleObject(eventHandle, timeOut) == 0;
        }

        [DllImport("Advapi32.dll")]
        private static extern bool ConvertStringSecurityDescriptorToSecurityDescriptor(
            string StringSecurityDescriptor,
            uint StringSDRevision,
            out IntPtr SecurityDescriptor,
            IntPtr SecurityDescriptorSize
            );

        [DllImport("Kernel32.dll")]
        private static extern bool LocalFree(IntPtr ptr);

        [DllImport("Kernel32.dll", CharSet = CharSet.Auto)]
        private static extern IntPtr CreateEvent(ref SECURITY_ATTRIBUTES eventAttributes, bool manualReset, bool initialState, string eventName);

        [DllImport("Kernel32.dll", CharSet = CharSet.Auto)]
        private static extern IntPtr OpenEvent(uint desiredAccess, bool inheritHandle, string eventName);

        [DllImport("Kernel32.dll")]
        protected static extern bool ResetEvent(IntPtr eventHandle);

        [DllImport("Kernel32.dll")]
        private static extern bool SetEvent(IntPtr eventHandle);

        [DllImport("Kernel32.dll")]
        private static extern bool CloseHandle(IntPtr eventHandle);

        [DllImport("Kernel32.dll")]
        private static extern int WaitForSingleObject(IntPtr handle, int milliseconds);
    }

    class NameMutex
    {

        // Use interop to call the CreateMutex function. 
        // For more information about CreateMutex, 
        // see the unmanaged MSDN reference library.
        [DllImport("kernel32.dll", CharSet = CharSet.Auto)]
        static extern IntPtr CreateMutex(IntPtr lpMutexAttributes, bool bInitialOwner,string lpName);


        [DllImport("kernel32.dll")]
        public static extern bool ReleaseMutex(IntPtr hMutex);


        [DllImport("Kernel32.dll")]
        private static extern int WaitForSingleObject(IntPtr handle, int milliseconds);


        private IntPtr mutexHandle = IntPtr.Zero;
        private IntPtr mutexAttrValue = IntPtr.Zero;
 

        public NameMutex(string Name, bool initialState)
        {
            mutexHandle = CreateMutex(mutexAttrValue, initialState, Name);
        }
        

        public void Release()
        {
            ReleaseMutex(mutexHandle);
        }

        // default wait for INFINITE(-1) time
        public bool Wait(int timeOut = -1)
        {
            return WaitForSingleObject(mutexHandle, timeOut) == 0;
        }
    }

}

