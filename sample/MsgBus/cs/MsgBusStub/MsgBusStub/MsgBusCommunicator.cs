using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading;
using System.Threading.Tasks;

namespace MsgBusStub
{
    public delegate void MessageEventHandler(string msgName, string message);

    
    // This class simulator your real business to send message to message bus 
    // and read message from message bus
    public class MsgBusCommunicator
    {

        public event MessageEventHandler OnMessageEvent;

        /// <summary>
        /// simulator send out messages from message bus
        /// </summary>
        private void PumpMessageOutForEver()
        {
            for (int i = 0; i < int.MaxValue; i++)
            {
                if (OnMessageEvent != null) 
                    OnMessageEvent(string.Format(".NETMsg_{0}", i), string.Format(".NETMsgBody_{0}", i));

                // sleep 1 seconds
                Thread.Sleep(1000 * 1);
            }
        }

        /// <summary>
        /// Fire the message with event type name and message to message bus.
        /// This funciton is invoked fromt the python world. see  MsgBusAgent.TestSendOutMessage in 
        /// smaple\MsgBus\py folder
        /// </summary>
        /// <param name="msgName"></param>
        /// <param name="message"></param>
        public void FireMessage(string msgName, string message)
        {
            Console.WriteLine(".NET world receive message from python: {0}", msgName);
        }

        /// <summary>
        /// Start to send out messages so that python world can receive the messages
        /// If you do not need to send message to python world actively you can skip this call.
        /// The MsgCollector.OnMessageEvent in the sample\MsgBus\MsgBus.py file will be invoked
        /// </summary>
        public void StartPumpMsgInBackground()
        {
            var t = new Task(PumpMessageOutForEver);
            t.Start();
        }}
}
