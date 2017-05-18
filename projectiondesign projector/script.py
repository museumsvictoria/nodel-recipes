# Copyright (c) 2017 Museum Victoria
# This software is released under the MIT license (see license.txt for details)

''''Projection Design Node'''

### Libraries required by this Node
import socket
import struct



### Parameters used by this Node
PORT = 1025
param_ipAddress = Parameter('{"title":"IP Address","schema":{"type":"string"}}')
param_debug = Parameter('{"title":"Debug Mode","schema":{"type":"boolean"}}')

param_f35 = Parameter('{"title":"F35 Support","schema":{"type":"boolean"}}')

inputs_f35 = ['VGA 1', 'VGA 2', 'DVI 1', '4', '5', '6', 'Component', 'HDMI 1', '9',
          'DVI 2', 'HDMI 2', 'Dual Head DVI', 'Dual Head HDMI', 'Dual Head XP2',
          'XP2 A', 'XP2 B']



### Local events this Node provides
local_event_Power = LocalEvent({'group': 'Power', 'schema': {'type': 'string', 'enum': ['On', 'Off', 'Partially On', 'Partially Off']}})
local_event_DesiredPower = LocalEvent({'group': 'Power', 'schema': {'type': 'string', 'enum': ['On', 'Off']}})

local_event_Error = LocalEvent('{ "title": "Error", "desc": "Error", "group": "General" }')

local_event_LampHours = LocalEvent({'group': 'Information', 'desc': 'The lamps hours for each lamp (comma separated)', 'order': next_seq(), 'schema': {'type': 'string'}})



### Main
def main(arg = None):
  if len((param_ipAddress or '').strip()) == 0:
    console.warn('No IP address configured; nothing to do')
    poller_lampHours.stop()
    status_timer.stop()
    timer_powerRetriever.stop()
    
    return


### Functions used by this Node
def send_cmd(cmd, arg=None):
  #open socket
  sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
  sock.settimeout(10)
  try:
    sock.connect((param_ipAddress, PORT))
    packet = ":"+cmd
    if(arg): packet += " "+arg
    packet+="\r"
    sock.send(packet)
    if(param_debug): print 'Sent', packet
    data = sock.recv(1024)
    if(param_debug): print 'Received', data
    rcvpack = struct.unpack("<xxxxx4sx6sx", data[0:17])
    assert cmd in rcvpack[0]
    # if(arg): assert arg in rcvpack[1] # packet 1 contains response code, not send arg
    return rcvpack[1]
  except socket.error, e:
    print "socket error: %s\n" % e
    local_event_Error.emit(e)
  except AssertionError, e:
    print "command error: %s\n" % e
    local_event_Error.emit(e)
  finally:
    lastReceive[0] = system_clock()
    sock.close()



### Local actions this Node provides
def local_action_Power(arg = None):
  '''{"title": "Power", "group": "Power", "desc": "Turns the projector on or off.", "schema": {"type": "string", "enum": ["On", "Off"]}}'''
  console.info('Power %s' % arg)
  local_event_DesiredPower.emit(arg)
  if arg == 'On':
    print 'Action PowerOn requested'
    send_cmd('POWR', '1')
  elif arg == 'Off':
    print 'Action PowerOff requested'
    send_cmd('POWR', '0')

def local_action_PowerOn(arg = None):
  """{"title":"PowerOn","desc":"PowerOn","group":"Power"}"""
  lookup_local_action('Power').call('On')

def local_action_PowerOff(arg = None):
  """{"title":"PowerOff","desc":"PowerOff","group":"Power"}"""
  lookup_local_action('Power').call('Off')

def local_action_GetPower(arg = None):
  """{"title":"GetPower","desc":"GetPower","group":"Information"}"""
  #print 'Action GetPower requested'
  result = send_cmd('POST', '?')
  if(result=='000005' or result=='000006'):
    print 'critical power off'
    local_event_Power.emit('Off')
  if(result=='000004'): print 'powering down'
  if(result=='000003'):
    #print 'power is on'
    local_event_Power.emit('On')
  if(result=='000002'): print 'powering up'
  if(result=='000000' or result=='000001'):
    #print 'power is off'
    local_event_Power.emit('Off')

def local_action_MuteOn(arg = None):
  """{"title":"MuteOn","desc":"MuteOn","group":"Picture"}"""
  print 'Action MuteOn requested'
  send_cmd('PMUT', '1')

def local_action_MuteOff(arg = None):
  """{"title":"MuteOff","desc":"MuteOff","group":"Picture"}"""
  print 'Action MuteOff requested'
  send_cmd('PMUT', '0')
  
def local_action_GetLampHours(x = None):
  """{ "title": "GetLampHours", "desc": "GetLampHours", "group": "Information" }"""
  print 'Action GetLampHours requested'

  lampHours = list()

  # Add lamp hours.
  lampHours.append(send_cmd('LTR1', '?').strip("0")) # Lamp 1
  lampHours.append(send_cmd('LTR2', '?').strip("0")) # Lamp 1

  # Announce hours.
  local_event_LampHours.emit(', '.join(lampHours))

# <!--- device status

DEFAULT_LAMPHOURUSE = 1800
param_warningThresholds = Parameter({'title': 'Warning thresholds', 'schema': {'type': 'object', 'properties': {
           'lampUseHours': {'title': 'Lamp use (hours)', 'type': 'integer', 'hint': str(DEFAULT_LAMPHOURUSE), 'order': 1}
        }}})

lampUseHoursThreshold = DEFAULT_LAMPHOURUSE

@after_main
def init_lamp_hours_support():
  global lampUseHoursThreshold
  lampUseHoursThreshold = (param_warningThresholds or {}).get('lampUseHours') or lampUseHoursThreshold
  
# poll every 4 hours, 30s first time.
poller_lampHours = Timer(lambda: lookup_local_action('GetLampHours').call(), 4*3600, 30)

local_event_Status = LocalEvent({'title': 'Status', 'group': 'Status', 'order': 9990, "schema": { 'title': 'Status', 'type': 'object', 'properties': {
        'level': {'title': 'Level', 'order': next_seq(), 'type': 'integer'},
        'message': {'title': 'Message', 'order': next_seq(), 'type': 'string'}
    } } })

lastReceive = [0]

# roughly, the last contact  
local_event_LastContactDetect = LocalEvent({'group': 'Status', 'title': 'Last contact detect', 'schema': {'type': 'string'}})

def statusCheck():
  lampUseHours = max([int(x) for x in (local_event_LampHours.getArg() or '0').split(',')])
  
  diff = (system_clock() - lastReceive[0])/1000.0 # (in secs)
  now = date_now()
  
  # the list of status items as (category, statusInfo) tuples
  statuses = list()
  
  if diff > status_check_interval+15:
    previousContactValue = local_event_LastContactDetect.getArg()
    
    if previousContactValue == None:
      message = 'Always been missing.'
      
    else:
      previousContact = date_parse(previousContactValue)
      roughDiff = (now.getMillis() - previousContact.getMillis())/1000/60
      if roughDiff < 60: # less than an hour, show just minutes
        message = 'Missing for approx. %s mins' % roughDiff
      elif roughDiff < (60*24): # less than a day, concise time is useful
        message = 'Missing since %s' % previousContact.toString('h:mm:ss a')
      else: # more than a day, concise date and time
        message = 'Missing since %s' % previousContact.toString('h:mm:ss a, E d-MMM')
      
    local_event_Status.emit({'level': 2, 'message': message})
    
    # (is offline so no point checking any other statuses)
    
    return 
  
  # check lamp hours
  if lampUseHours > lampUseHoursThreshold:
    statuses.append(('Lamp usage', 
                    {'level': 1, 'message': 'Lamp usage is %s hours which is %s above the replacement threshold of %s. It may need replacement.' % 
                                 (lampUseHours, lampUseHours-lampUseHoursThreshold, lampUseHoursThreshold)}))
    
  # aggregate the statuses
  aggregateLevel = 0
  aggregateMessage = 'OK'
  msgs = list()
  
  for key, status in statuses:
    level = status['level']
    if level > 0:
      if level > aggregateLevel:
        aggregateLevel = level # raise the level
        del msgs[:]  # clear message list because of a complete new (higher) level
        
      if level == aggregateLevel: # keep adding messages of equal status level
        msgs.append('%s: [%s]' % (key, status['message'])) # add the message
      
  if aggregateLevel > 0:
    aggregateMessage = ', '.join(msgs)
    
  local_event_Status.emit({'level': aggregateLevel, 'message': aggregateMessage})
  
  local_event_LastContactDetect.emit(str(now))  
  
status_check_interval = 12*60 # check every 12 minutes
status_timer = Timer(statusCheck, status_check_interval, 30)

# 10 minute power checker
timer_powerRetriever = Timer(lambda: lookup_local_action('GetPower').call(), 10*60, 20)

# device status --->

# <--- f35 support

@after_main
def init_F35_support():

  if param_f35:

    # Set Stereo Mode
    def handler_get_stereo(arg):
      print 'Action GetStereoMode requested'
      result = send_cmd('TDSM', '?')
      if(result=='000002'):
        print '3D stereo mode: side by side'
      if(result=='000001'):
        print '3D stereo mode: frame sequential'
      if(result=='000000'):
        print '3D stereo mode: off'

    meta_get_stereo = { "title": "GetStereoMode", "desc": "GetStereoMode", "group": "Information" }

    Action('GetStereoMode', handler_get_stereo, meta_get_stereo)

# Get Stereo Mode
    def handler_set_stereo(arg):
      print 'Action SetStereoMode requested'
      if arg == 'OFF':
        send_cmd('TDSM', '0')
      if arg == 'FRAME SEQUENTIAL':
        send_cmd('TDSM', '1')
      if arg == 'SIDE BY SIDE':
        send_cmd('TDSM', '2')

    meta_set_stereo = {"title":"Stereo Mode","required":'true',"schema":{"type":"string","enum": ['OFF', 'FRAME SEQUENTIAL', 'SIDE BY SIDE']}, 'group': '3D'}

    Action('SetStereoMode', handler_set_stereo, meta_set_stereo)

    # Dual Head On
    def handler_dualhead_on(arg):
      print 'Action DualHeadOn requested'
      send_cmd('DHED', '1')

    meta_dualhead_on = {"title":"DualHeadOn","desc":"DualHeadOn","group":"3D"}

    Action('DualHeadOn', handler_dualhead_on, meta_dualhead_on)

    # Dual Head Off
    def handler_dualhead_off(arg):
      print 'Action DualHeadOff requested'
      send_cmd('DHED', '0')

    meta_dualhead_off = {"title":"DualHeadOff","desc":"DualHeadOff","group":"3D"}

    Action('DualHeadOff', handler_dualhead_off, meta_dualhead_off)

    # Get Dual Head
    def handler_get_dualhead(arg):
      print 'Action GetDualHead requested'
      result = send_cmd('DHED', '?')
      if(result=='000001'):
        print 'dual head setup mode: on'
      if(result=='000000'):
        print 'dual head setup mode: off'

    meta_get_dualhead = {"title":"GetDualHead","desc":"GetDualHead","group":"Information"}

    Action('GetDualHead', handler_get_dualhead, meta_get_dualhead)

    # Set Input
    def handler_set_input(arg):
      print 'Action SetInput requested: '+arg
      if arg == 'HDMI 1':
        send_cmd('IABS', '8')
      if arg == 'HDMI 2':
        send_cmd('TDSM', '11')
      if arg == 'Dual Head HDMI':
        send_cmd('TDSM', '13')  
      send_cmd(arg)

    meta_set_input = {"title":"Set input","desc":"SetInput","group":"Input","schema":{"type":"string", "title": "Source", "required":"true",
      "enum": ['HDMI 1', 'HDMI 2', 'Dual Head HDMI'] } }

    Action('SetInput', handler_set_input, meta_set_input)

    # Get Input
    def handler_get_input(arg):
      result = int(send_cmd('IABS', '?').strip("0"))
      print 'source: ', inputs_f35[result - 1]

    meta_get_input = {"title":"GetInput","desc":"GetInput","group":"Information"}

    Action('GetInput', handler_get_input, meta_get_input)

# f35 support --->