'''Basic Samsung serial driver - manual http://www.samsung.com/us/pdf/UX_DX.pdf'''

TCP_PORT = 1515

param_ipAddress = Parameter({"value":"192.168.100.1","title":"IP address","order":0, "schema":{"type":"string"}})
param_id = Parameter({"value":"1","title":"ID","order":0, "schema":{"type":"integer"}})

local_event_DebugShowLogging = LocalEvent({'group': 'Debug', 'schema': {'type': 'boolean'}})

# general device status
local_event_Status = LocalEvent({'order': -100, 'group': 'Status', 'schema': {'type': 'object', 'title': 'Status', 'properties': {
        'level': {'type': 'integer', 'title': 'Value'},
        'message': {'type': 'string', 'title': 'String'}
      }}})

local_event_Power = LocalEvent({'order': 0, 'schema': {'type': 'string', 'enum': ['On', 'Off']}})
local_event_Volume = LocalEvent({'schema': {'type': 'integer'}})
local_event_Mute = LocalEvent({'schema': {'type': 'string', 'enum': ['Mute', 'Unmute']}})
# this table is incomplete
INPUT_CODE_TABLE = [ ('1F', 'PC'),
                     ('1E', 'BNC'),
                     ('18', 'DVI'),
                     ('0C', 'AV'),
                     ('04', 'S-Video'),
                     ('08', 'Component'),
                     ('20', 'MagicNet'),
                     ('1f', 'DVI_VIDEO'),
                     ('30', 'RF(TV)'),
                     ('40', 'DTV'),
                     ('21', 'HDMI') ]
local_event_InputCode = LocalEvent({'schema': {'type': 'string'}})

def handle_displayStatusTimer():
  lookup_local_action('GetDisplayStatus').call()

# poll every 30s
timer_deviceStatus = Timer(handle_displayStatusTimer, 30)


def main(arg = None):
  print 'Nodel script started.'
  
  tcp.setDest('%s:%s' % (param_ipAddress, TCP_PORT))

local_event_TCPStatus = LocalEvent({'schema': {'type': 'string', 'enum': ['Connected', 'Disconnected', 'Timeout']}})  
  
def connected():
  local_event_TCPStatus.emitIfDifferent('Connected')
  
  # wait a second and poll
  timer_deviceStatus.setDelay(1.0)
  
def received(data):
  lastReceive[0] = system_clock()
  if local_event_DebugShowLogging.getArg():
    print 'RECV: [%s]' % data.encode('hex')
  
def sent(data):
  if local_event_DebugShowLogging.getArg():
    print 'SENT: [%s]' % data.encode('hex')
  
def disconnected():
  local_event_TCPStatus.emitIfDifferent('Disconnected')
  
def timeout():
  local_event_TCPStatus.emitIfDifferent('Timeout')
  
tcp = TCP(connected=connected, received=received, sent=sent, disconnected=disconnected, 
          timeout=timeout, 
          sendDelimiters=None, receiveDelimiters=None, binaryStartStopFlags=None)

def setPower(arg):
  state = True if arg != 'Off' else False
  msg = '\x11%s\x01%s' % (chr(int(param_id)), '\x01' if state else '\x00')
  checksum = sum([ord(c) for c in msg]) & 0xff
  tcp.request('\xaa%s%s' % (msg, chr(checksum)), checkHeader)

def local_action_TurnOn(arg=None):
  """{"title":"On","desc":"Turns this node on.","group":"Power","caution":"Ensure hardware is in a state to be turned on.","order":1}"""
  setPower('On')
  
def local_action_TurnOff(arg=None):
  """{"title":"Off","desc":"Turns this node on.","group":"Power","caution":"Ensure hardware is in a state to be turned on.","order":2}"""
  # example response after off: aa ff 00 03 41 11 00 54
  setPower('Off')
  
def local_action_Power(arg=None):
  """{"title": "Set", "group": "Power", "order": 3,
      "desc":"Turns this node on or off.", 
      "caution": "Ensure hardware is in a state to be turned on.",
      "schema": { "type": "string", "enum": ["On", "Off"] }}"""
  setPower(arg)

def local_action_GetDisplayStatus(arg=None):
  # example response: aaff00094100010000141000006e

  # aa   ff   00   09      41 ('A')    00
  # HDR  CMD  ID   length  ACK         R->Cmd
  # +0   1    2    3       4           5

  # 1:01   2:00    3:00     4:14     5:10     6:00    7:00          6e
  # PRW    VOL     MUTE     INPUT    ASPECT   NTimeNF FTimeNF       CSUM
  # +6     +7      +8       +9       +10      +11     +12           +13
  msg = '\x00%s\x00' % chr(int(param_id))
  checksum = sum([ord(c) for c in msg]) & 0xff
  
  def handleResp(arg):
    checkHeader(arg)
    
    local_event_Power.emit('On' if ord(arg[6]) == 1 else 'Off')
    local_event_Volume.emit(ord(arg[7]))
    local_event_Mute.emit('Mute' if ord(arg[8]) == 1 else 'Unmute')
    local_event_InputCode.emit(arg[9].encode('hex'))
  
  tcp.request('\xaa%s%s' % (msg, chr(checksum)), handleResp)
  
  
def local_action_ClearMenu(arg=None):
  """{"desc": "Clears the OSD menu"}"""
  msg = '\x34%s\x01\x00' % chr(int(param_id))
  checksum = sum([ord(c) for c in msg]) & 0xff
  tcp.request('\xaa%s%s' % (msg, chr(checksum)), checkHeader)
  
  
def getIRRemoteControl(arg):
  # eg. 'aa ff 00 03 41 36 01 7a
  
  msg = '\x36%s\x00' % chr(int(param_id))
  checksum = sum([ord(c) for c in msg]) & 0xff
  tcp.request('\xaa%s%s' % (msg, chr(checksum)), lambda resp: checkHeader(resp, lambda: irRemoteControlEvent.emit('Enabled' if resp[6] == '\x01' else 'Disabled')))
  
Action('Get IR Remote Control', getIRRemoteControl, {'title': 'Get', 'group': 'IR Remote Control'})
  
def setIRRemoteControl(arg):
  if arg != 'Disabled':
    state = True
  else:
    state = False
  
  msg = '\x36%s\x01%s' % (chr(int(param_id)), '\x01' if state else '\x00')
  checksum = sum([ord(c) for c in msg]) & 0xff
  tcp.request('\xaa%s%s' % (msg, chr(checksum)), lambda resp: checkHeader(resp, lambda: irRemoteControlEvent.emit(arg)))

irRemoteControlEvent = Event('IR Remote Control', {'group': 'IR Remote Control', 'schema': {'type': 'string', 'enum': ['Enabled', 'Disabled']}})
Action('IR Remote Control', setIRRemoteControl, {'title': 'Set', 'group': 'IR Remote Control', 'caution': 'Are you sure you want to enable/disable IR remote control?', 'schema': {'type': 'string', 'enum': ['Enabled', 'Disabled']}})
  

  
def checkHeader(arg, onSuccess=None):
  if arg[0] != '\xaa' or arg[1] != '\xff':
    raise Exception('Bad message structure')
    
  if arg[4] != 'A':
    raise Exception('Bad acknowledgement')
    
  if onSuccess:
    onSuccess()
    
# for status checks
lastReceive = [0]

# roughly, the last contact  
local_event_LastContactDetect = LocalEvent({'group': 'Status', 'title': 'Last contact detect', 'schema': {'type': 'string'}})
  
def statusCheck():
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
    
status_check_interval = 75
status_timer = Timer(statusCheck, status_check_interval)
