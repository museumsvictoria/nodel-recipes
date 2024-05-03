'''BrightSign UDP Node'''

### Libraries required by this Node
import socket



### Parameters used by this Node
param_ipAddress = Parameter('{"title":"IP Address","desc":"The IP address","schema":{"type":"string"}}')
PORT = 1010



### Functions used by this Node
def send_udp_string(msg):
  #open socket
  sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
  try:
    sock.sendto(msg, (param_ipAddress, PORT))
  except socket.error, msg:
    print "error: %s\n" % msg
    local_event_Error.emit(msg)
  finally:
    if sock:
      sock.close()



### Local actions this Node provides
def local_action_Start(arg = None):
  """{"title":"Start","desc":"Start","group":"Content"}"""
  print 'Action Start requested.'
  send_udp_string('Start')

def local_action_Stop(arg = None):
  """{"title":"Stop","desc":"Stop","group":"Content"}"""
  print 'Action Stop requested.'
  send_udp_string('Stop')

def local_action_PlayClip01(arg = None):
  """{"title":"PlayClip01","desc":"PlayClip01","group":"Content"}"""
  print 'Action PlayClip01 requested.'
  send_udp_string('PlayClip01')

def local_action_Mute(arg = None):
  """{"title":"Mute","group":"Volume","schema":{"type":"string","enum": ['On', 'Off'], "required": True}}"""
  print 'Action Mute%s requested' % arg
  send_udp_string('MuteOn') if arg == 'On' else send_udp_string('MuteOff')

def local_action_MuteOn(arg = None):
  """{"title":"MuteOn","desc":"MuteOn","group":"Volume"}"""
  print 'Action MuteOn requested.'
  send_udp_string('MuteOn')

def local_action_MuteOff(arg = None):
  """{"title":"MuteOff","desc":"MuteOff","group":"Volume"}"""
  print 'Action MuteOff requested.'
  send_udp_string('MuteOff')



### Local events this Node provides
local_event_Error = LocalEvent('{"title":"Error","desc":"Error","group":"General"}')



### Main
def main(arg = None):
  # Start your script here.
  print 'Nodel script started.'
