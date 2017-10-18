# Copyright (c) 2017 Museum Victoria
# This software is released under the MIT license (see license.txt for details)

'''iBoot G2 Node'''

### Libraries required by this Node
import socket
import struct



### Parameters used by this Node
PORT = 9100
param_ipAddress = Parameter('{"title":"IP address","schema":{"type":"string"}}')

# every 1 min(s)
SLOW_GET_INTERVAL = 60

# the last time *anything* was sent to the unit
lastReceive = [0]


### Functions used by this Node
def set_state(control):
  try:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(15)
    s.connect((param_ipAddress, PORT))
    s.sendall('hello-000')
    data = s.recv(16)
    seq = struct.unpack("<H",data)[0]
    seq = seq+1
    desc = 1
    data = struct.pack('<B21s21sBBHBB',3,'','',desc,0,seq,1,control)
    s.sendall(data)
    data = s.recv(16)
    if(struct.unpack('<B',data)[0]==0):
      print 'Success'
      if(control==0):
        local_event_PowerOff.emit()
        local_event_Power.emit('Off')
      if(control==1):
        local_event_PowerOn.emit()
        local_event_Power.emit('On')
    else:
      raise Exception("Error sending command")
    lastReceive[0] = system_clock()
  except Exception, e:
    local_event_Error.emit(e)
  finally:
    s.close()

def get_state():
  try:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(15)
    s.connect((param_ipAddress, PORT))
    s.sendall('hello-000')
    data = s.recv(16)
    seq = struct.unpack("<H",data)[0]
    seq = seq+1
    desc = 4
    data = struct.pack('<B21s21sBBH',3,'','',desc,0,seq)
    s.sendall(data)
    data = s.recv(16)
    state = struct.unpack('<BBBBBBBB',data)[0]
    if(state==0):
      local_event_PowerOff.emit()
      local_event_Power.emit('Off')
    if(state==1):
      local_event_PowerOn.emit()
      local_event_Power.emit('On')
    lastReceive[0] = system_clock()
    s.close()
  except Exception, e:
    local_event_Error.emit(e)
  finally:
    s.close()

def statusCheck():
  get_state()

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
  '''{"title":"State","schema":{"type":"string","enum":["On","Off"]},"group":"Outlet","order":-1}'''
  if arg == 'On':
    set_state(1)
    print 'Action PowerOn requested.'
  elif arg == 'Off':
    set_state(0)
    print 'Action PowerOff requested.'

def local_action_PowerOn(arg):
  '''{"title":"PowerOn","desc":"PowerOn","group":"Outlet"}'''
  lookup_local_action('Power').call('On')

def local_action_PowerOff(arg):
  '''{"title":"PowerOff","desc":"PowerOff","group":"Outlet"}'''
  lookup_local_action('Power').call('Off')

def local_action_GetPower(arg):
  '''{"title":"GetPower","desc":"GetPower","group":"Information","order":1}'''
  get_state()
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
