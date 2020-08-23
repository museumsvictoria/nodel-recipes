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


def get_command_string(cmd_type, visca_addr, seq_number, data=None):

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

    def payload_len_to_hex(payload):
        payload_len = len(payload)
        hex_str = ''
        hex_str += chr(payload_len >> 8 & 0xff)
        hex_str += chr(payload_len & 0xff)
        return hex_str

    msg_header = None
    msg_payload = None

    pan_speed = get_pan_speed()
    tilt_speed = get_tilt_speed()

    if cmd_type == 'up':
        msg_payload = address_to_hex(visca_addr) + '\x01\x06\x01' + chr(pan_speed) + chr(tilt_speed) + '\x03\x01' + '\xff'
        msg_header = '\x01\x00' + payload_len_to_hex(msg_payload) + seq_to_hex(seq_number)
    elif cmd_type == 'down':
        msg_payload = address_to_hex(visca_addr) + '\x01\x06\x01' + chr(pan_speed) + chr(tilt_speed) + '\x03\x02' + '\xff'
        msg_header = '\x01\x00' + payload_len_to_hex(msg_payload) + seq_to_hex(seq_number)
    elif cmd_type == 'left':
        msg_payload = address_to_hex(visca_addr) + '\x01\x06\x01' + chr(pan_speed) + chr(tilt_speed) + '\x01\x03' + '\xff'
        msg_header = '\x01\x00' + payload_len_to_hex(msg_payload) + seq_to_hex(seq_number)
    elif cmd_type == 'right':
        msg_payload = address_to_hex(visca_addr) + '\x01\x06\x01' + chr(pan_speed) + chr(tilt_speed) + '\x02\x03' + '\xff'
        msg_header = '\x01\x00' + payload_len_to_hex(msg_payload) + seq_to_hex(seq_number)
    elif cmd_type == 'home':
        msg_payload = address_to_hex(visca_addr) + '\x01\x06\x04' + '\xff'
        msg_header = '\x01\x00' + payload_len_to_hex(msg_payload) + seq_to_hex(seq_number)
    elif cmd_type == 'stop':
        msg_payload = address_to_hex(visca_addr) + '\x01\x06\x01\x05\x05\x03\x03' + '\xff'
        msg_header = '\x01\x00' + payload_len_to_hex(msg_payload) + seq_to_hex(seq_number)
    elif cmd_type == 'reset_seq':
        msg_payload = '\x01'
        msg_header = '\x02\x00' + payload_len_to_hex(msg_payload) + seq_to_hex(seq_number)
    elif cmd_type == 'preset_reset':
        msg_payload = address_to_hex(visca_addr) + '\x01\x04\x3f\x00' + number_to_hex(data) + '\xff'
        msg_header = '\x01\x00' + payload_len_to_hex(msg_payload) + seq_to_hex(seq_number)
    elif cmd_type == 'preset_set':
        msg_payload = address_to_hex(visca_addr) + '\x01\x04\x3f\x01' + number_to_hex(data) + '\xff'
        msg_header = '\x01\x00' + payload_len_to_hex(msg_payload) + seq_to_hex(seq_number)
    elif cmd_type == 'preset_recall':
        msg_payload = address_to_hex(visca_addr) + '\x01\x04\x3f\x02' + number_to_hex(data) + '\xff'
        msg_header = '\x01\x00' + payload_len_to_hex(msg_payload) + seq_to_hex(seq_number)
    elif cmd_type == 'zoom_stop':
        msg_payload = address_to_hex(visca_addr) + '\x01\x04\x07\x00' + '\xff'
        msg_header = '\x01\x00' + payload_len_to_hex(msg_payload) + seq_to_hex(seq_number)
    elif cmd_type == 'zoom_tele':  # Standard
        msg_payload = address_to_hex(visca_addr) + '\x01\x04\x07\x02' + '\xff'
        msg_header = '\x01\x00' + payload_len_to_hex(msg_payload) + seq_to_hex(seq_number)
    elif cmd_type == 'zoom_wide':  # Standard
        msg_payload = address_to_hex(visca_addr) + '\x01\x04\x07\x03' + '\xff'
        msg_header = '\x01\x00' + payload_len_to_hex(msg_payload) + seq_to_hex(seq_number)
    elif cmd_type == 'focus_auto':
        msg_payload = address_to_hex(visca_addr) + '\x01\x04\x38\x02' + '\xff'
        msg_header = '\x01\x00' + payload_len_to_hex(msg_payload) + seq_to_hex(seq_number)
    elif cmd_type == 'focus_manual':
        msg_payload = address_to_hex(visca_addr) + '\x01\x04\x38\x03' + '\xff'
        msg_header = '\x01\x00' + payload_len_to_hex(msg_payload) + seq_to_hex(seq_number)
    elif cmd_type == 'focus_stop':
        msg_payload = address_to_hex(visca_addr) + '\x01\x04\x08\x00' + '\xff'
        msg_header = '\x01\x00' + payload_len_to_hex(msg_payload) + seq_to_hex(seq_number)
    elif cmd_type == 'focus_far':  # Standard
        msg_payload = address_to_hex(visca_addr) + '\x01\x04\x08\x02' + '\xff'
        msg_header = '\x01\x00' + payload_len_to_hex(msg_payload) + seq_to_hex(seq_number)
    elif cmd_type == 'focus_near':  # Standard
        msg_payload = address_to_hex(visca_addr) + '\x01\x04\x08\x03' + '\xff'
        msg_header = '\x01\x00' + payload_len_to_hex(msg_payload) + seq_to_hex(seq_number)
    else:
        raise Exception('Unsupported command type')

    return msg_header + msg_payload


# -->

# <!-- actions

def resetSequenceNo():
    console.log('[resetSequenceNo] called')
    ctrlCmd_reset_seq = get_command_string('reset_seq', _viscaAddress, next_seq() + 20000)
    udp.send(ctrlCmd_reset_seq)

    
# -- drive related --

PAN_SPEED = 5
TILT_SPEED = 5

def get_pan_speed():
    global PAN_SPEED
    if PAN_SPEED < 1 or PAN_SPEED > 24:
        return 5
    return PAN_SPEED
    
def get_tilt_speed():
    global TILT_SPEED
    if TILT_SPEED < 1 or TILT_SPEED > 24:
        return 5
    return TILT_SPEED

@local_action({'group': 'PTZ Drive', 'title': 'Set Pan Speed', 'schema': {'title': 'Pan Speed (default: 5, Min: 1, Max: 24)', 'type': 'integer', 'format': 'range', 'min':1, 'max':24}, 'order': next_seq()})
def set_pan_speed(arg):
    console.log('[set_pan_speed] %d' % arg)
    global PAN_SPEED
    PAN_SPEED = arg;
    
@local_action({'group': 'PTZ Drive', 'title': 'Set Tilt Speed', 'schema': {'title': 'Tilt Speed (default: 5, Min: 1, Max: 24)', 'type': 'integer', 'format': 'range', 'min':1, 'max':24}, 'order': next_seq()})
def set_tilt_speed(arg):
    console.log('[set_tilt_speed] %d' % arg)
    global TILT_SPEED
    TILT_SPEED = arg;

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
    inquery_presetRecall = get_command_string('preset_recall', _viscaAddress, next_seq() + 20000, arg)
    udp.send(inquery_presetRecall)


# -- Zoom related --
@local_action({'group': 'PTZ Zoom', 'title': 'Zoom Stop', 'order': next_seq()})
def ptz_zoom_stop(arg):
    console.log('[ptz_zoom_stop] called')
    inquery_zoomStop = get_command_string('zoom_stop', _viscaAddress, next_seq() + 20000)
    udp.send(inquery_zoomStop)

@local_action({'group': 'PTZ Zoom', 'title': 'Zoom Tele', 'order': next_seq()})
def ptz_zoom_tele(arg):
    console.log('[ptz_zoom_tele] called')
    inquery_zoomTele = get_command_string('zoom_tele', _viscaAddress, next_seq() + 20000)
    udp.send(inquery_zoomTele)

@local_action({'group': 'PTZ Zoom', 'title': 'Zoom Wide', 'order': next_seq()})
def ptz_zoom_wide(arg):
    console.log('[ptz_zoom_wide] called')
    inquery_zoomWide = get_command_string('zoom_wide', _viscaAddress, next_seq() + 20000)
    udp.send(inquery_zoomWide)

# -- Focus related --
le_Focus_Mode = create_local_event(
            'Focus Mode',
            metadata={
                'title': 'Focus Mode',
                'group': 'PTZ Focus',
                'order': next_seq(),
                'schema': {
                    'type': 'string'
                }
            }
        )

@local_action({'group': 'PTZ Focus', 'title': 'Focus Mode - Auto', 'order': next_seq()})
def ptz_focus_mode_auto(arg):
    console.log('[ptz_focus_mode_auto] called')
    inquery_focusModeAuto = get_command_string('focus_auto', _viscaAddress, next_seq() + 20000)
    udp.send(inquery_focusModeAuto)
    le_Focus_Mode.emit('AUTO')

@local_action({'group': 'PTZ Focus', 'title': 'Focus Mode - Manual', 'order': next_seq()})
def ptz_focus_mode_manual(arg):
    console.log('[ptz_focus_mode_manual] called')
    inquery_focusModeManual = get_command_string('focus_manual', _viscaAddress, next_seq() + 20000)
    udp.send(inquery_focusModeManual)
    le_Focus_Mode.emit('MANUAL')

@local_action({'group': 'PTZ Focus', 'title': 'Focus - Stop', 'order': next_seq()})
def ptz_focus_stop(arg):
    console.log('[ptz_focus_stop] called')
    inquery_focusStop = get_command_string('focus_stop', _viscaAddress, next_seq() + 20000)
    udp.send(inquery_focusStop)

@local_action({'group': 'PTZ Focus', 'title': 'Focus - Far', 'order': next_seq()})
def ptz_focus_far(arg):
    console.log('[ptz_focus_far] called')
    inquery_focusFar = get_command_string('focus_far', _viscaAddress, next_seq() + 20000)
    udp.send(inquery_focusFar)

@local_action({'group': 'PTZ Focus', 'title': 'Focus - Near', 'order': next_seq()})
def ptz_focus_near(arg):
    console.log('[ptz_focus_near] called')
    inquery_focusNear = get_command_string('focus_near', _viscaAddress, next_seq() + 20000)
    udp.send(inquery_focusNear)

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
