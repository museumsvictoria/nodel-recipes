# -*- coding: utf-8 -*-

'''
ATEN USB Industrial Hub switcher via serial.

* normally connected with an RS-232 to RS-485 adapter/converter, example [here](https://www.ebay.com.au/itm/232544689234).
* baud **38400**, 8, None 1.
* this recipe supports direct IP address config or via an alternative IP addressing method e.g. AMX Beacons

**NOTE**: at time of writing with firmware V1.0.062, the current active port cannot be retrieved from the device. Newer firmware is 
      being released in the future by ATEN which will allow for that and this recipe will be updated. For now, pseudo feedback is used based
      on the last selected port.

Example manual - [link](https://assets.aten.com/product/manual/us3344i_um_w_2018-11-13.pdf).

Example wiring diagram:

      ATEN             GENERIC
     US3344i        RS485 - RS232   
    --------------------------------
     GND : Green -|- Blue  : 485+
      T- :       -|- Red   : 485-
      T+ :       -|- Green : GND
      R+ : Blue  -|-       : 5-12V
      R- : Red   -|-
    --------------------------------

_rev 2_
'''

param_PortsInUse = Parameter({ 'title': 'Ports in use', 'schema': { 'type': 'array', 'items': { 'type': 'object', 'properties': {
  'num':  { 'type': 'string', 'order': 1 },
  'label': { 'type': 'string', 'order': 2 }}}}})

# allow for static IP config or an alternative IP addressing method e.g. AMX node

param_IPAddress = Parameter({ 'schema':  { 'type': 'string', 'hint': '(override discovery method using bindings)' }})

local_event_IPAddress = LocalEvent({ 'group': 'Discovery / Addressing', 'schema':  { 'type': 'string' }})

def remote_event_IPAddress(arg):
  if not is_blank(param_IPAddress): return
    
  ipAddress = local_event_IPAddress.getArg()
  if arg != ipAddress:
    console.info('IP address changed to %s (originally %s)' % (arg, ipAddress))
    local_event_IPAddress.emit(arg)
    dest = '%s:%s' % (ipAddress, param_Port or DEFAULT_PORT)
    console.info('Will connect to %s...' % dest)
    _tcp.setDest(dest)
    _tcp.drop()

DEFAULT_PORT = 4999
param_Port = Parameter({ 'schema': { 'type': 'integer', 'hint': u'(default Global Caché "4999")' }})

local_event_SelectedPort = LocalEvent({ 'schema': { 'type': 'string' }})

def main():
  ipAddress = None
  port = DEFAULT_PORT
  
  if not is_blank(param_IPAddress):
    ipAddress = param_IPAddress
  else:
    ipAddress = local_event_IPAddress.getArg()
  
  if is_blank(ipAddress):
    return console.info('IP address not specified nor known previously available')
  
  if param_Port: # > 0
    port = int(param_Port)
  
  dest = '%s:%s' % (ipAddress, port)
  console.info('Will connect to [%s]' % dest)
  
  _tcp.setDest(dest)
  
  if not param_PortsInUse:
    return console.warn('No Ports in use have been configured')
  
  # init used ports
  for info in param_PortsInUse:
    initPort(info['num'], info['label'])
    
def initPort(num, label):
  e = create_local_event('Port %s Selected' % num, { 'title': 'Selected', 'group': 'Port %s "%s"' % (num, label), 'schema':  { 'type': 'boolean' }})
  
  def handler(ignore):
    console.info('Port %s Selected called' % num)
    
    def resp_handler(resp):
      if 'Command OK' in resp: local_event_SelectedPort.emit(num)
      else:                    console.warn('Port %s Selected failure - resp was %s' % (num, resp))
    
    _tcp.request('SW P0%s' % num, resp_handler)
    
  a = create_local_action('Port %s Selected' % num, handler, { 'title': 'Selected', 'group': 'Port %s "%s"' % (num, label) })
  
  local_event_SelectedPort.addEmitHandler(lambda arg: e.emit(arg == num))
  
@local_action({ 'group': 'Info' })
def PollFirmware():
  _tcp.send('INFO')
  
timer_Poller = Timer(lambda: PollFirmware.call(), 60, 5, stopped=True) # every minute, first after 5 seconds, enabled on TCP connection
             
local_event_Firmware = LocalEvent({ 'group': 'Info', 'schema': { 'type': 'string' }})
    
# Protocol examples:
#  > info
#  < Command OK
#  < F/W: V1.0.062
#
# > SW P03\r\n
# < Command OK

def parseMsg(msg):
  global _lastReceive
  
  if 'F/W' in msg:
    local_event_Firmware.emit(' '.join(msg.split(' ')[1:]))
    _lastReceive = system_clock()
    
  elif 'Command OK' in msg:
    _lastReceive = system_clock()
    
# <!-- TCP

def tcp_connected():
  console.info('tcp_connected')
  _tcp.clearQueue()
  timer_Poller.start()
  
def tcp_received(raw):
  xRaw = raw.encode('hex')
  log(3, 'tcp_received - %s' % ':'.join([ xRaw[i*2:i*2+2] for i in range(len(xRaw)/2) ]))
  
  parseMsg(raw)
  
def tcp_sent(raw):
  xRaw = raw.encode('hex')
  log(3, 'tcp_sent - %s' % ':'.join([ xRaw[i*2:i*2+2] for i in range(len(xRaw)/2)]))

def tcp_disconnected():
  console.warn('tcp_disconnected')
  timer_Poller.stop()

def tcp_timeout():
  console.warn('tcp_timeout - dropping connection if present')
  _tcp.drop()

_tcp = TCP(connected=tcp_connected, received=tcp_received, sent=tcp_sent, disconnected=tcp_disconnected, timeout=tcp_timeout, 
           sendDelimiters='\r\n', receiveDelimiters='\r\n')

# -->

  
# <!-- logging and status

local_event_Status = LocalEvent({ 'group': 'Status', 'order': 1, 'schema': { 'type': 'object', 'properties': {
  'level': { 'type': 'integer', 'order': 1 },
  'message': { 'type': 'string', 'order': 2 }}}})

_lastReceive = 0

# roughly, the last contact  
local_event_LastContactDetect = LocalEvent({'group': 'Status', 'title': 'Last contact detect', 'schema': {'type': 'string'}})
  
def statusCheck():
  diff = (system_clock() - _lastReceive)/1000.0 # (in secs)
  now = date_now()
  
  if diff > status_check_interval+15:
    previousContactValue = local_event_LastContactDetect.getArg()
    
    if previousContactValue == None: 
      message = 'Never been monitored'
    else:
      message = 'Unmonitorable %s' % formatPeriod(date_parse(previousContactValue))
      
    local_event_Status.emit({ 'level': 2, 'message': message })
    return
    
  local_event_Status.emit({'level': 0, 'message': 'OK (f/w %s)' % local_event_Firmware.getArg() })
  
  local_event_LastContactDetect.emit(str(now))
  
status_check_interval = 60 # was 75

status_timer = Timer(statusCheck, status_check_interval)

def formatPeriod(dateObj, asInstant=False):
  if dateObj == None:       return 'for unknown period'

  now = date_now()
  diff = (now.getMillis() - dateObj.getMillis()) / 1000 / 60 # in mins
  
  if diff < 0:              return 'never ever'
  elif diff == 0:           return 'for <1 min' if not asInstant else '<1 min ago'
  elif diff < 60:           return ('for <%s mins' if not asInstant else '<%s mins ago') % diff
  elif diff < 60*24:        return ('since %s' if not asInstant else 'at %s') % dateObj.toString('h:mm a')
  else:                     return ('since %s' if not asInstant else 'on %s') % dateObj.toString('E d-MMM h:mm a')

local_event_LogLevel = LocalEvent({ 'group': 'Debug', 'order': 10000+next_seq(), 'desc': 'Use this to ramp up the logging (with indentation)',
                                    'schema': { 'type': 'integer' }})

@local_action({ 'group': 'Debug', 'order': 10000+next_seq() })
def RaiseLogLevel():
  local_event_LogLevel.emit((local_event_LogLevel.getArg() or 0) + 1)

@local_action({ 'group': 'Debug', 'order': 10000+next_seq() })
def LowerLogLevel():
  local_event_LogLevel.emit(max((local_event_LogLevel.getArg() or 0) - 1, 0))

def warn(level, msg):
  if (local_event_LogLevel.getArg() or 0) >= level:
    console.warn(('  ' * level) + msg)

def log(level, msg):
  if (local_event_LogLevel.getArg() or 0) >= level:
    console.log(('  ' * level) + msg)

# --!>
