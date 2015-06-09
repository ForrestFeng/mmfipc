using System;
using System.Collections.Generic;
using System.Linq;
using System.Security.Cryptography;
using System.Text;
using System.Threading.Tasks;
using MmfIPC;

namespace MsgBusStub
{

    class MsgBusStub
    {
        /// <summary>
        /// IPC communicate stub for python .NET IPC
        /// </summary>
        private MmfIpcServer _IPCReqHandler;
        private MmfIpcClinet _IPCMsgPump;

        public MsgBusStub(MsgBusCommunicator communicator)
        {
            communicator.OnMessageEvent += CommunicatorOnOnMessageEvent;
            _IPCMsgPump = new MmfIpcClinet("DIMTestWithIPCMsgPump");
            // _IPCReqHandler will handler the msg invoked from the python world
            _IPCReqHandler = new MmfIpcServer("DIMTestWithIPCReqHandler", communicator);
            
        }

        /// <summary>
        /// publish the message to python world with _IPCMsgPump
        /// </summary>
        /// <param name="msgName"></param>
        /// <param name="message"></param>
        private void CommunicatorOnOnMessageEvent(string msgName, string message)
        {
            _IPCMsgPump.invoke("OnMessageEvent", new string[] { msgName, message });
        }

        public void HandlePythonWorldInvokeForEver()
        {
            _IPCReqHandler.run();
        }
    }


    class Program
    {
        /// <summary>
        /// This console application simulator a MsgBus stub for the C# world.
        /// </summary>
        /// <param name="args"></param>
        static void Main(string[] args)
        {
            Console.WriteLine("MsgBusStub start to communicate with Python...");
            var communicator = new MsgBusCommunicator();
            var stub = new MsgBusStub(communicator);

            communicator.StartPumpMsgInBackground();
            stub.HandlePythonWorldInvokeForEver();

            Console.ReadLine();
        }
    }
}
