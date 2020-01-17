'''
With this recipe, you can control pan/tilt and preset of Sony VISCA Color Video Camera.
'''


# <!-- parameters

param_disabled = Parameter({'desc': 'Disables this node?', 'schema': {'type': 'boolean'}})
param_ipAddress = Parameter({'schema': {'type': 'string'}})

_port = 52381
param_port = Parameter({'schema': {'type': 'integer', 'hint': '(default is %s)' % _port}})

_viscaAddress = 1
param_viscaAddress = Parameter({'schema': {'type': 'integer', 'hint': '(default is %s)' % _viscaAddress}})


def main():
    if not param_ipAddress:
      console.warn('IP address not configured')
      return
    
    if param_port: # 0 is not allowed here
      global _port
      _port = param_port

    if param_viscaAddress != None: # 0 is allowed here
      global _viscaAddress
      _viscaAddress = param_viscaAddress
      
    target = "%s:%s" % (param_ipAddress, _port)
    console.info('Will connect to [%s]' % target)
    
    udp.setDest(target)

    resetSequenceNo()
    

def udp_received(src, data):
    log(2, 'udp_recv %s (from %s)' % (':'.join([b.encode('hex') for b in data]), src))

def udp_sent(data):
    log(1, 'udp_sent %s' % ':'.join([b.encode('hex') for b in data]))


udp = UDP(sent=udp_sent,
          ready=lambda: console.info('udp_ready'),
          received=udp_received)

def address_to_hex(addr_number):
    return chr(0x80 + addr_number)

def seq_to_hex(seq_number):
    hex_str = ''
    hex_str += chr(seq_number >> 24 & 0xff)
    hex_str += chr(seq_number >> 16 & 0xff)
    hex_str += chr(seq_number >> 8 & 0xff)
    hex_str += chr(seq_number & 0xff)
    return hex_str


def number_to_hex(number):
    return chr(int(number))


def get_command_string(cmd_type, visca_addr, seq_number, data=None):
    msg_header = None
    msg_payload = None

    if cmd_type == 'up':
        msg_header = '\x01\x00' + '\x00\x09' + seq_to_hex(seq_number)
        msg_payload = address_to_hex(visca_addr) + '\x01\x06\x01\x05\x05\x03\x01' + '\xff'
    elif cmd_type == 'down':
        msg_header = '\x01\x00' + '\x00\x09' + seq_to_hex(seq_number)
        msg_payload = address_to_hex(visca_addr) + '\x01\x06\x01\x05\x05\x03\x02' + '\xff'
    elif cmd_type == 'left':
        msg_header = '\x01\x00' + '\x00\x09' + seq_to_hex(seq_number)
        msg_payload = address_to_hex(visca_addr) + '\x01\x06\x01\x05\x05\x01\x03' + '\xff'
    elif cmd_type == 'right':
        msg_header = '\x01\x00' + '\x00\x09' + seq_to_hex(seq_number)
        msg_payload = address_to_hex(visca_addr) + '\x01\x06\x01\x05\x05\x02\x03' + '\xff'
    elif cmd_type == 'home':
        msg_header = '\x01\x00' + '\x00\x05' + seq_to_hex(seq_number)
        msg_payload = address_to_hex(visca_addr) + '\x01\x06\x04' + '\xff'
    elif cmd_type == 'stop':
        msg_header = '\x01\x00' + '\x00\x09' + seq_to_hex(seq_number)
        msg_payload = address_to_hex(visca_addr) + '\x01\x06\x01\x05\x05\x03\x03' + '\xff'
    elif cmd_type == 'reset_seq':
        msg_header = '\x02\x00' + '\x00\x01' + seq_to_hex(seq_number)
        msg_payload = '\x01'
    elif cmd_type == 'preset_reset':
        msg_header = '\x01\x00' + '\x00\x07' + seq_to_hex(seq_number)
        msg_payload = address_to_hex(visca_addr) + '\x01\x04\x3f\x00' + number_to_hex(data) + '\xff'
    elif cmd_type == 'preset_set':
        msg_header = '\x01\x00' + '\x00\x07' + seq_to_hex(seq_number)
        msg_payload = address_to_hex(visca_addr) + '\x01\x04\x3f\x01' + number_to_hex(data) + '\xff'
    elif cmd_type == 'preset_recall':
        msg_header = '\x01\x00' + '\x00\x07' + seq_to_hex(seq_number)
        msg_payload = address_to_hex(visca_addr) + '\x01\x04\x3f\x02' + number_to_hex(data) + '\xff'
    else:
        raise Exception('Unsupported command type')

    return msg_header + msg_payload


# save preset

# recall preset

# -->

# <!-- actions

def resetSequenceNo():
    console.log('[resetSequenceNo] called')
    ctrlCmd_reset_seq = get_command_string('reset_seq', _viscaAddress, next_seq() + 20000)
    udp.send(ctrlCmd_reset_seq)

    
# -- drive related --

@local_action({'group': 'PTZ Drive', 'title': 'Home', 'order': next_seq()})
def ptz_home(ignore):
    console.log('[ptz_home] called')
    inquery_ptdHome = get_command_string('home', _viscaAddress, next_seq() + 20000)
    udp.send(inquery_ptdHome)

@local_action({'group': 'PTZ Drive', 'title': 'Up', 'order': next_seq()})
def ptz_up(data):
    console.log('[ptz_up] called')
    inquery_ptdUp = get_command_string('up', _viscaAddress, next_seq() + 20000)
    udp.send(inquery_ptdUp)

@local_action({'group': 'PTZ Drive', 'title': 'Down', 'order': next_seq()})
def ptz_down(data):
    console.log('[ptz_down] called')
    inquery_ptdDown = get_command_string('down', _viscaAddress, next_seq() + 20000)
    udp.send(inquery_ptdDown)

@local_action({'group': 'PTZ Drive', 'title': 'Left', 'order': next_seq()})
def ptz_left(data):
    console.log('[ptz_left] called')
    inquery_ptdLeft = get_command_string('left', _viscaAddress, next_seq() + 20000)
    udp.send(inquery_ptdLeft)

@local_action({'group': 'PTZ Drive', 'title': 'Right', 'order': next_seq()})
def ptz_right(data):
    console.log('[ptz_right] called')
    inquery_ptdRight = get_command_string('right', _viscaAddress, next_seq() + 20000)
    udp.send(inquery_ptdRight)

@local_action({'group': 'PTZ Drive', 'title': 'Stop', 'order': next_seq()})
def ptz_stop(data):
    console.log('[ptz_stop] called')
    inquery_ptdStop = get_command_string('stop', _viscaAddress, next_seq() + 20000)
    udp.send(inquery_ptdStop)

    
# -- preset related --
    
@local_action({'group': 'PTZ Preset', 'title': 'Preset Reset', 'order': next_seq(), 'schema': {'type': 'integer'}})
def ptz_preset_reset(data):
    console.log('[ptz_preset_reset] called')
    inquery_presetReset = get_command_string('preset_reset', _viscaAddress, next_seq() + 20000, data)
    udp.send(inquery_presetReset)

@local_action({'group': 'PTZ Preset', 'title': 'Preset Set', 'order': next_seq(), 'schema': {'type': 'integer'}})
def ptz_preset_set(data):
    console.log('[ptz_preset_set] called')
    inquery_presetSet = get_command_string('preset_set', _viscaAddress, next_seq() + 20000, data)
    udp.send(inquery_presetSet)

@local_action({'group': 'PTZ Preset', 'title': 'Preset Recall', 'order': next_seq(), 'schema': {'type': 'integer'}})
def ptz_preset_recall(arg):
    console.log('[ptz_preset_recall] called')
    
    msg_header = '\x01\x00' + '\x00\x07' + seq_to_hex(next_seq() + 20000)
    msg_payload = address_to_hex(_viscaAddress) + '\x01\x04\x3f\x02' + number_to_hex(arg) + '\xff'    
    
    udp.send(msg_header + msg_payload)

@local_action({'group': 'Status', 'order': next_seq()})
def httpPoll():
  # look for this token if result to be sure
  TOKEN = 'birddog_p200.png'
  
  url = 'http://%s/login' % param_ipAddress

  try:
    log(2, 'httpPoll %s' % url)
    resp = get_url(url, connectTimeout=5)
    
    if TOKEN not in resp:
      console.warn('unexpected response! did not find token [%s] in response from %s' % (TOKEN, url))
      return
    
    global _lastReceive
    _lastReceive = system_clock()
   
  except:
    log(1, 'problem polling %s' % url)

timer_poller = Timer(lambda: httpPoll.call(), 30, 5) # every 30s, first after 5    

# -->

# <!-- status

local_event_Status = LocalEvent({'title': 'Status', 'group': 'Status', 'order': 9990, "schema": { 'title': 'Status', 'type': 'object', 'properties': {
        'level': {'title': 'Level', 'order': 1, 'type': 'integer'},
        'message': {'title': 'Message', 'order': 2, 'type': 'string'}
    } } })

_lastReceive = 0 # last valid comms, system_clock() based

# roughly, the last contact  
local_event_LastContactDetect = LocalEvent({'group': 'Status', 'title': 'Last contact detect', 'schema': {'type': 'string'}})
  
def statusCheck():
  diff = (system_clock() - _lastReceive)/1000.0 # (in secs)
  now = date_now()
  
  if diff > status_check_interval+15:
    previousContactValue = local_event_LastContactDetect.getArg()
    
    if previousContactValue == None: message = 'Never seen'
    else:
      previousContact = date_parse(previousContactValue)
      message = 'Missing %s' % formatPeriod(previousContact)
      
    local_event_Status.emit({'level': 2, 'message': message})
    return
    
  local_event_Status.emit({'level': 0, 'message': 'OK'})
  
  local_event_LastContactDetect.emit(str(now))
  
status_check_interval = 75
timer_statusCheck = Timer(statusCheck, status_check_interval)

def formatPeriod(dateObj):
  if dateObj == None:      return 'for unknown period'
  
  now = date_now()
  diff = (now.getMillis() - dateObj.getMillis()) / 1000 / 60 # in mins
  
  if diff == 0:             return 'for <1 min'
  elif diff < 60:           return 'for <%s mins' % diff
  elif diff < 60*24:        return 'since %s' % dateObj.toString('h:mm:ss a')
  else:                     return 'since %s' % dateObj.toString('E d-MMM h:mm:ss a')
  
# status -->


# <!-- logging

local_event_LogLevel = LocalEvent({
    'group': 'Debug',
    'order': 10000 + next_seq(),
    'desc': 'Use this to ramp up the logging (with indentation)',
    'schema': {'type': 'integer'}
})


def warn(level, msg):
    if local_event_LogLevel.getArg() >= level:
        console.warn(('  ' * level) + msg)


def log(level, msg):
    if local_event_LogLevel.getArg() >= level:
        console.log(('  ' * level) + msg)

# --!>
