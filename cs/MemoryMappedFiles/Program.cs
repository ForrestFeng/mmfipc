using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using System.IO.MemoryMappedFiles;

namespace MmfIPC
{
    class Program
    {
        static void PushMessageTimely()
        {
            AsyncMessagePump msgpump = new AsyncMessagePump();

            int i = 0;
            while(true)
            {
                string msg = string.Format("New Message {0}", i);
                msgpump.OnNewMessage(msg);
                Thread.Sleep(1000);
                i += 1;
            }
        }

        static void Main(string[] args)
        {
            // push msg to client async way in anther thread
            Task t = new Task(PushMessageTimely);
            t.Start();

            // accetp client call in main thread
            CalcServer calcSvr = new CalcServer();
            calcSvr.IPCServer.run();
        }
    }
}
