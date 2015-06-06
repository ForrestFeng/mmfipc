import MmfIPC


class IPCClient (MmfIPC.MmfIpcClient):
    def Add(self, a, b):
        result = self.invoke('Add', a, b)
        return result

    def Hello(self, a, b, c):
        return self.invoke('Hello', a, b, c)


client = IPCClient("ICalc")

#print client.Add(1, 6)
for i in range(100000):
    #print client.Add('"{}"'.format(i), '"{}"'.format(i))
    print i, '+', i , '=', client.Add(i, i)
    #print client.Hello(i, i, i)
    pass

print 'Done'
