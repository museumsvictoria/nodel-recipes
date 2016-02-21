'''Basic Samsung serial driver'''

TCP_PORT = 1515

param_ipAddress = Parameter({"value":"192.168.100.1","title":"IP address","order":0, "schema":{"type":"string"}})
param_id = Parameter({"value":"1","title":"ID","order":0, "schema":{"type":"integer"}})


def main(arg = None):
  print 'Nodel script started.'
  
  tcp.setDest('%s:%s' % (param_ipAddress, TCP_PORT))
  
def connected():
  print 'connected'
  
def received(data):
  print 'received ' + data.encode('hex')
  
def sent(data):
  print 'sent ' + data.encode('hex')
  
def disconnected():
  print 'disconnected'
  
def timeout():
  console.warn("TCP timeout")

  
tcp = TCP(dest=None, connected=connected, received=received, sent=sent, disconnected=disconnected, timeout=timeout, sendDelimiters=None, receiveDelimiters=None, binaryStartStopFlags=None)
  
def local_action_TurnOn(arg = None):
  """{"title":"Turns on","desc":"Turns this node on.","group":"Power","caution":"Ensure hardware is in a state to be turned on.","order":2}"""
  msg = '\x11%s\x01\x01' % chr(int(param_id))
  
  checksum = sum([ord(c) for c in msg]) & 0xff
  
  tcp.request('\xaa%s%s' % (msg, chr(checksum)), lambda resp: console.log('Got response [%s] to power on request.' % resp.encode('hex')))
  
def local_action_TurnOff(arg = None):
  """{"title":"Turns off","desc":"Turns this node on.","group":"Power","caution":"Ensure hardware is in a state to be turned on.","order":2}"""
  msg = '\x11%s\x01\x00' % chr(int(param_id))
  
  checksum = sum([ord(c) for c in msg]) & 0xff
  
  tcp.request('\xaa%s%s' % (msg, chr(checksum)), lambda resp: console.log('Got response [%s] to power off request.' % resp.encode('hex')))  
