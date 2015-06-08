using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;

namespace MmfIPC
{
   
    internal class CalcServer 
    {
        public MmfIpcServer IPCServer = null;

        public CalcServer()
        {
            IPCServer = new MmfIpcServer("ICalc", this);
        }

        public string Add(string a, string b)
        {
            int result = Convert.ToInt32(a) + Convert.ToInt32(b);
            return result.ToString();
        }

        // this method returns nothing to test if the C# server can handle it correctly
        public void SetName(string name)
        {
            return;
        }
    }

    internal class AsyncMessagePump : MmfIpcClinet
    {
        public AsyncMessagePump()
            : base("ServerEvt")
        {
            
        }

        public string OnNewMessage(string msg)
        {
            this.invoke("OnNewMessage", new string[]{msg});
            return "";
        }
    }
}
