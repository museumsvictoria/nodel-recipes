# Copyright (c) 2014 Museum Victoria
# This software is released under the MIT license (see license.txt for details)

'''iBoot Original Node'''

### Libraries required by this Node
import socket
import struct



### Parameters used by this Node
PORT = 80
PASSWORD = "3000"
param_ipAddress = Parameter('{"title":"IP address","schema":{"type":"string"}}')

# every 10 mins
SLOW_GET_INTERVAL = 10*60

# the last time *anything* was sent to the unit
lastReceive = [0]



### Functions used by this Node
def main():
  print 'started'

def cmd(control):
  try:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(10)
    s.connect((param_ipAddress, PORT))
    s.sendall('\x1b'+PASSWORD+'\x1b'+control+'\x0d')
    data = s.recv(16)
    lastReceive[0] = system_clock()
    if(data=="OFF"):
      local_event_PowerOff.emit()
      local_event_Power.emit('Off')
    elif(data=="ON"):
      local_event_PowerOn.emit()
      local_event_Power.emit('On')
    else:
      raise Exception("Error: unexpected response")
  except Exception, e:
    local_event_Error.emit(e)
  finally:
    s.close()

def statusCheck():
  cmd("q")

  diff = (system_clock() - lastReceive[0])/1000.0 # (in secs)
  now = date_now()
  
  if diff > status_check_interval+15:
    previousContactValue = local_event_LastContactDetect.getArg()
    
    if previousContactValue == None:
      message = 'Always been missing.'
      
    else:
      previousContact = date_parse(previousContactValue)
      roughDiff = (now.getMillis() - previousContact.getMillis())/1000/60
      message = 'Missing for approx. %s minutes' % roughDiff
      
    local_event_Status.emit({'level': 2, 'message': message})
    
  else:
    local_event_LastContactDetect.emit(str(now))
    local_event_Status.emit({'level': 0, 'message': 'OK'})
    
status_check_interval = SLOW_GET_INTERVAL+15
status_timer = Timer(statusCheck, status_check_interval, 60)
status_timer.start()



### Local actions this Node provides
def local_action_Power(arg):
  '''{"title":"Power","schema":{"type":"string","enum":["On","Off"]},"group":"Outlet","order":-1}'''
  # support for group node remote action
  if type(arg) is not unicode:
    arg = arg['state']
  # support for local use  
  if arg == 'On':
    cmd("n")
    print 'Action PowerOn requested.'
  if arg == 'Off':
    cmd("f")
    print 'Action PowerOff requested.'

def local_action_PowerOn(arg):
  '''{"title":"PowerOn","desc":"PowerOn","group":"Outlet"}'''
  cmd("n")
  print 'Action PowerOn requested.'

def local_action_PowerOff(arg):
  '''{"title":"PowerOff","desc":"PowerOff","group":"Outlet"}'''
  cmd("f")
  print 'Action PowerOff requested.'

def local_action_GetPower(arg):
  '''{"title":"GetPower","desc":"GetPower","group":"Information"}'''
  cmd("q")
  print 'Action GetPower requested.'




### Local events this Node provides
local_event_PowerOn = LocalEvent({'group': 'Outlet', 'order': next_seq()})
local_event_PowerOff = LocalEvent({'group': 'Outlet', 'order': next_seq()})
local_event_Power = LocalEvent({'schema': {'type':'string','enum':['On','Off']}, 'group': 'Outlet', 'order': next_seq()})
local_event_Error = LocalEvent({'group': 'Status',' order': next_seq()})
local_event_LastContactDetect = LocalEvent({'order': next_seq(), 'group': 'Status', 'title': 'Last contact', 'schema': {'type': 'string'}})
local_event_Status = LocalEvent({'order': -100, 'schema': {'type': 'object', 'title': 'Status', 'properties': {
        'level': {'type': 'integer', 'title': 'Level'},
        'message': {'type': 'string', 'title': 'Message'}
      }}})



### Main
def main():
  # Start your script here.
  print 'Nodel script started.'
