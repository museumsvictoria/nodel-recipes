# -*- coding: utf-8 -*-

'''Epson (see script for links to manual, and considerations for special models, etc.)'''

# -  http://download.epson.com.sg/manuals/User%20manual-EB-GG6170-G6070W-G6270W-G6450WU-G6570WU-G6770WU.pdf

def dump_message():
  console.info('''
  
  > NOTE:
  > Some models do not natively support "Signal Presence" polling via this VP21 protocol recipe.
  >
  > A clunky work-around action is used instead called 'Poll Signal Presence Fallback Via Web' which will
  > require the WebPassword to be specified if it's not "admin".
  > 
  > It is not guarenteed to work on all models. Please ensure the "Signal Presence" signal is accurate when
  > Power is On and signal is definitely present.
  >
  > If serial control is in use, there the web-fallback is obviously not available.
  
''')

SOURCES_BY_CODE = { 
  '1F': 'Computer (Auto)',
  '11': 'Computer (RGB)',
  '14': 'Computer (Component)',
  'BF': 'BNC (Auto)',
  'B1': 'BNC (RGB)',
  'B4': 'BNC (Component)',
  '30': 'HDMI',
  '41': 'Video',
  '42': 'S-Video',
  '53': 'LAN',
  '70': 'DisplayPort',
  '80': 'HDBaseT'
}

TCP_PORT = 3629

MAX_VOL = 243

param_disabled = Parameter({ "title":"Disabled?", "order": next_seq(), "schema": { "type":"boolean" }})
param_ipAddress = Parameter({ "title":"IP address", "order": next_seq(), "schema": { "type":"string", "hint": "(overrides bindings use)" }})
param_TCPPortForSerial = Parameter({'title': 'TCP Port if using Serial Bridge', 'schema': {'type': 'integer', 'hint': u'0 (default not in use or e.g. 4999 for Global Caché)'}})

local_event_IPAddress = LocalEvent({ "schema": { "type": "string" }})

def remote_event_IPAddress(ipAddr):
  if is_blank(param_ipAddress):
    old = local_event_IPAddress.getArg()
    if old != ipAddr:
      console.info('IP address updated to %s (was %s)' % (ipAddr, old))
      local_event_IPAddress.emit(ipAddr)
      dest = '%s:%s' % (ipAddr, param_TCPPortForSerial or TCP_PORT)
      console.info('Will connect to [%s]' % dest)
      tcp.setDest(dest)

DEFAULT_LAMPHOURUSE = 1800
param_warningThresholds = Parameter({'title': 'Warning thresholds', 'schema': {'type': 'object', 'properties': {
           'lampUseHours': {'title': 'Lamp use (hours)', 'type': 'integer', 'hint': str(DEFAULT_LAMPHOURUSE), 'order': 1}
        }}})

lampUseHoursThreshold = DEFAULT_LAMPHOURUSE


GREETING = 'ESC/VP.net\x10\x03\x00\x00\x00\x00'

local_event_ShowLog = LocalEvent({'title': 'Show log', 'order': 9998, 'group': 'Debug', 'schema': {'type': 'boolean'}})

def main(arg = None):
  if param_disabled:
    console.warn('Disabled=true; not starting')
    return
  
  # 'combine' raw and desired power signals for feedback
  local_event_RawPower.addEmitHandler(handlePowerSignals)
  local_event_DesiredPower.addEmitHandler(handlePowerSignals)
  
  # clear state
  local_event_DesiredPower.emit(None)
  
  # set up warning
  global lampUseHoursThreshold
  lampUseHoursThreshold = (param_warningThresholds or {}).get('lampUseHours') or lampUseHoursThreshold
  
  dump_message()

  if is_blank(param_ipAddress):
    ipAddr = local_event_IPAddress.getArg()
  else:
    ipAddr = param_ipAddress
    local_event_IPAddress.emit(ipAddr)

  if is_blank(ipAddr):
    console.warn('No IP address update received or configured; will wait...')

  else:
    if param_TCPPortForSerial: # using Serial Bridge?
      dest = '%s:%s'% (ipAddr, param_TCPPortForSerial)
      console.info('Will connect via Serial Bridge on [%s]' % dest)
    else:                      # direct
      dest = '%s:%s'% (ipAddr, TCP_PORT)
      console.info('Will connect directly to projector at [%s]' % dest)
    
    tcp.setDest(dest)

# [ desired power ----

local_event_DesiredPower = LocalEvent({"group": "Power", "order": next_seq(), "schema": {"type": "string", 'enum': ['On', 'Off']}})

def ensurePower():
  console.info('Ensuring power...')
  
  current = local_event_Power.getArg()
  desired = local_event_DesiredPower.getArg()
  
  if current == desired or desired == None:
    local_event_DesiredPower.emit(None)
    power_timer.stop()
    power_giveup.stop()
    
    # ensure source too
    setSource()
    
  elif desired == 'On':
    lookup_local_action('Force On').call()
    
  elif desired == 'Off':
    lookup_local_action('Force Off').call()
    
def powerGiveUp():
  console.info('Giving up')
  
  local_event_DesiredPower.emit(None)
  
  power_timer.stop()
  power_poller.setInterval(30) # poll every 30s
  power_poller.start()

power_timer = Timer(ensurePower, 0)
power_poller = Timer(lambda: lookup_local_action('Poll Power').call(), 30, 5)
power_giveup = Timer(powerGiveUp, 0)

def local_action_Power(arg=None):
  '''{"group": "Power", "order": 1.1, "schema": {"type": "string"}}'''
  console.info('Power(%s)' % arg)
  
  local_event_DesiredPower.emit(arg)
  
  if arg == None:
    return
  
  # workaround: starting here before setting delay and interval because of 
  #             timer behaviour
  console.info('Starting power timer!')
  power_timer.setInterval(16) # force every 16s
  power_timer.start()
  power_timer.setDelay(0.001) 
  
  power_giveup.setInterval(3*60) # give 3 mins before giving up
  power_giveup.start()
  
# 'Raw Power' and 'Desired Power' handlers
def handlePowerSignals(ignore):
  desired = local_event_DesiredPower.getArg()
  raw = local_event_RawPower.getArg()
  
  local_event_Power.emit(raw if raw == desired or desired == None else 'Partially %s' % desired)
      
@local_action({'title': 'On', 'group': 'Power', 'order': next_seq()})
def PowerOn():
  lookup_local_action('Power').call('On')
  
@local_action({'title': 'Off', 'group': 'Power', 'order': next_seq()})
def PowerOff():
  lookup_local_action('Power').call('Off')

# ---- desired power ]  

# [ desired source ----

local_event_DesiredSource = LocalEvent({"group": "Input", "order": 1.1, "schema": {"type": "string"}})

def ensureSource():
  console.info('Ensuring source...')
  
  # don't bother if not on
  if local_event_Power.getArg() != 'On':
    if local_event_ShowLog.getArg():
      print 'Power is not on, not ensuring source'
    return
  
  current = local_event_Source.getArg()
  desired = local_event_DesiredSource.getArg()
  
  if current == desired or desired == None:
    source_timer.stop()
    source_giveup.stop()
    
  lookup_local_action('Force Source').call(desired)
    
def sourceGiveUp():
  console.info('Giving up source')
  source_timer.stop()
  source_poller.setInterval(30) # poll every 30s
  source_poller.start()
  
def pollSource():
  # don't bother polling if not on
  if local_event_Power.getArg() != 'On':
    if local_event_ShowLog.getArg():
      print 'Power is not on, not polling source'
    return
  
  lookup_local_action('Poll Source').call()

source_timer = Timer(ensureSource, 0)
source_poller = Timer(pollSource, 30, 5)
source_giveup = Timer(sourceGiveUp, 0)

def setSource():
  arg = local_event_DesiredSource.getArg()
  
  if arg == None:
    return
  
  source_poller.setInterval(8) # poll every 8s
  source_poller.start()
  
  # workaround: starting here before setting delay and interval because of 
  #             timer behaviour  
  source_timer.start()
  source_timer.setDelayAndInterval(0.1, 16) # force every 16s
  
  source_giveup.start()
  source_giveup.setDelay(90) # give 1.5 mins before giving up on source

def local_action_Source(arg=None):
  '''{"group": "Source", "order": 1.1, "schema": {"type": "string"}}'''
  console.info('Source(%s)' % arg)
  
  local_event_DesiredSource.emit(arg)      
      
  setSource()

# ---- desired source ]


# [ power ----    
    
POWER_MODES = { 0: 'Off',    # Standby Network OFF
                1: 'On',     # Lamp On
                2: 'Warmup',
                3: 'Cooldown',
                4: 'Off',    # Standby Mode (Network ON)
                5: 'Fault' } # Abnormality standby
  
local_event_Power = LocalEvent({'group': 'Power', 'order': next_seq(), 'schema': {'type': 'string'}})

local_event_RawPower = LocalEvent({"group": "Raw", "desc": "The raw power status from the projector.", "order": next_seq(), "schema": {"type": "string"}})

def local_action_PollPower(ignore=None):
  '''{"group": "Raw", "order": 1}'''
  tcp.request('PWR?', lambda resp: handleValueReq(resp, 'PWR', lambda arg: local_event_RawPower.emit(POWER_MODES[int(arg)])))
  
def local_action_ForceOn(ignore=None):
  '''{"group": "Raw", "order": 1.1}'''
  console.info('ForceOn()')
  tcp.send('PWR ON')

def local_action_ForceOff(ignore=None):
  '''{"group": "Raw", "order": 1.2}'''
  console.info('ForceOff()')
  tcp.send('PWR OFF')
  

# ---- power ]

# [ source ----

local_event_Source = LocalEvent({'group': 'Source', 'order': next_seq(), 'schema': {'type': 'string'}})

def local_action_PollSource(ignore=None):
  '''{"group": "Raw", "order": 2.1}'''
  tcp.request('SOURCE?', lambda resp: handleValueReq(resp, 'SOURCE', lambda value: local_event_Source.emit(value)))
  
def local_action_ForceSource(source):
  '''{"group": "Raw", "order": 2.2, "schema": {"type": "string"}}'''
  console.info('ForceSource(%s)' % source)
  tcp.send('SOURCE %s' % source)
  local_action_PollSource()

# ---- power ]


# [ vol ----

# - only work when power is on



local_event_Vol = LocalEvent({'group': 'Volume', 'order': next_seq(), 'schema': {'type': 'integer'}})

# faking 0 - 100%
local_event_XVol = LocalEvent({'group': 'Volume', 'order': next_seq(), 'schema': {'type': 'integer'}})

# faking mute
local_event_XVolMuting = LocalEvent({'group': 'Volume', 'order': next_seq(), 'schema': {'type': 'boolean'}})
local_event_XLastMutingVol = LocalEvent({'group': 'Volume', 'order': next_seq(), 'schema': {'type': 'integer'}})


  
def local_action_PollVol(ignore=None):
  '''{"group": "Volume", "order": 3.1}'''
  def handleValue(value):
    i = int(value)
    local_event_Vol.emit(i)
    
    if local_event_XVolMuting.getArg() != True: # muting state is faked so don't emit this
      local_event_XVol.emit(i * 100 / MAX_VOL) 
    
  queue(lambda: tcp.request('VOL?', lambda resp: handleValueReq(resp, 'VOL', handleValue)))
  
def local_action_ForceVol(level):
  '''{"group": "Volume", "order": 3.2, "schema": {"type": "integer"}}'''
  queue(lambda: tcp.send('VOL %s' % level), 200)
  
  local_action_PollVol()
  
def local_action_ForceVolIncr(ignore=None):
  '''{"group": "Volume", "order": 3.3}'''
  queue(lambda: tcp.send('VOL INC'), 200)
  local_action_PollVol()
  
def local_action_ForceVolDecr(ignore=None):
  '''{"group": "Volume", "order": 3.4}'''
  queue(lambda: tcp.send('VOL DEC'), 200)
  local_action_PollVol()
  
def local_action_XVol(perc):
  '''{"group": "Volume", "order": 3.5, "schema": {"type": "integer"}}'''
  lookup_local_action('Force Vol').call(int(perc / 100.0 * MAX_VOL))
  

def local_action_XVolMuting(state):
  '''{"group": "Volume", "order": 3.6, "schema": {"type": "boolean"}}'''
  if state:
    local_event_XLastMutingVol.emit(local_event_Vol.getArg())
    lookup_local_action('Force Vol').call(0)
    local_event_XVolMuting.emit(True)
    
  else:
    last = local_event_XLastMutingVol.getArg()
    lookup_local_action('Force Vol').call(last if last != None else 36)
    local_event_XVolMuting.emit(False)

def local_action_XVolMutingToggle(ignore=None):
  '''{"group": "Volume", "order": 3.7}'''
  lookup_local_action('XVolMuting').call(not local_event_XVolMuting.getArg())
    
  
# ---- vol ]
  
# [ error status

local_event_ErrorState = LocalEvent({'group': 'Raw', 'schema': {'type': 'string'}})

def local_action_PollErrorState(ignore=None):
  '''{"group": "Raw", "order": 2.1}'''
  tcp.request('ERR?', lambda resp: handleValueReq(resp, 'ERR', lambda value: local_event_ErrorState.emit(value)))

# --- error status ]

# [ lamp hours status

local_event_LampUseHours = LocalEvent({'group': 'Info', 'desc': 'In hours (space separated for multiple lamps)', 'schema': {'type': 'string'}})

def local_action_PollLampUseHours(ignore=None):
  '''{"group": "Info", "order": 2.1}'''
  def handleResp(value):
    local_event_LampUseHours.emit(value)
    
  tcp.request('LAMP?', lambda resp: handleValueReq(resp, 'LAMP', handleResp))
  
# poll every 24 hours, 30s first time.
poller_lampHours = Timer(lambda: lookup_local_action('PollLampUseHours').call(), 24*3600, 30)

  
# --- lamp hours status ]


# [ general info

# signal presence

DEFAULT_WEBPASSWORD = 'admin'

local_event_SignalPresence = LocalEvent({'group': 'Info', 'schema': {'type': 'boolean', 'order': next_seq()}})

def local_action_PollSignalPresence(ignore=None):
  '''{"group": "Info", "order": 2.1}'''
  def errorHandler():
    if param_TCPPortForSerial:
      if local_event_ShowLog.getArg():
        print 'Using serial bridge, cannot use SignalPresence-fallback-via-web'
        return
      
    lookup_local_action('PollSignalPresenceFallbackViaWeb').call()
    
  tcp.request('SIGNAL?', lambda resp: handleValueReq(resp, 'SIGNAL', lambda value: local_event_SignalPresence.emit(value == '01'), errorHandler))

param_WebPassword = Parameter({'title': 'Web Password (optional, for Signal Presence workaround for some models)', 'schema': {'type': 'string', 'hint': '%s (default)' % DEFAULT_WEBPASSWORD}})  


# signal presence 'HACK' by polling the HTML website
def local_action_PollSignalPresenceFallbackViaWeb():
  '''{"title": "Poll Signal Presence (fallback via Web)", "group": "Info", "order": 2.2, "desc": "Fallback used when model does not support function via VP21 protocol"}'''
  # only poll if power is on
  if lookup_local_event('Power').getArg() != 'On':
    return
  
  URL = 'http://%s/cgi-bin/webconf.exe?page=05'
  
  if local_event_ShowLog.getArg():
    print 'HTTP: polling URL [%s]' % URL
  
  ipAddr = local_event_IPAddress.getArg()
  infoHTMLPage = get_url(URL % ipAddr, username='EPSONWEB', password=param_WebPassword or DEFAULT_WEBPASSWORD,
                         headers={'Cookie': 'value=971F9C4BAB285D19B7F8437D6AB01B61A9083BDE1F2F4643',
                           'Referer': 'http://%s/webconf/index2.html' % ipAddr})
  
  if '&#45;&nbsp;x' in infoHTMLPage:
    signalPresence = False
    
  elif 'The projector is currently on standby.' in infoHTMLPage:
    signalPresence = False
    
  else:
    signalPresence = True
    
  if local_event_ShowLog.getArg():    
    print 'signal presence parsed was [%s]' % signalPresence
    
  local_event_SignalPresence.emit(signalPresence)
  
  
# poll every 10 seconds, 30s first time.
Timer(lambda: lookup_local_action('PollSignalPresence').call(), 10, 10)


# serial number

local_event_SerialNumber = LocalEvent({'group': 'Info', 'schema': {'type': 'string', 'order': next_seq()}})

def local_action_PollSerialNumber(ignore=None):
  '''{"group": "Info", "order": 2.1}'''
  tcp.request('SNO?', lambda resp: handleValueReq(resp, 'SNO', lambda value: local_event_SerialNumber.emit(value)))
  
# poll every 24 hours, 30s first time.
Timer(lambda: lookup_local_action('PollSerialNumber').call(), 24*3600, 30)



# --- general info ]

  
# [ TCP ----

def connected():
  console.info('TCP connected')
  
  tcp.send(GREETING)
  
def received(data):
  lastReceive[0] = system_clock()
  if local_event_ShowLog.getArg():
    print 'RECV: [%s]' % data
  
def sent(data):
  if local_event_ShowLog.getArg():
    print 'SENT: [%s]' % data
  
def disconnected():
  console.warn('TCP disconnected')
  
def timeout():
  console.warn('TCP timeout!')
  
  tcp.clearQueue()
  tcp.drop()

tcp = TCP(connected=connected, 
          received=received, 
          sent=sent, 
          disconnected=disconnected, 
          timeout=timeout,
          sendDelimiters='\r', 
          receiveDelimiters='\r\n:') # NOTE ':' AS ANOTHER DELIMETER

earliestAllowed = system_clock()
tcpOps = list() # e.g. (tcpOp, 200ms)

def processQueue():
  global earliestAllowed
 
  diff = earliestAllowed - system_clock()
  
  # are we allowed to send yet?
  if diff > 0: 
    call_safe(processQueue, diff/1000.0)
    return
  
  # is okay to send....
  
  # check length
  if len(tcpOps) <= 0:
    console.log('Q: is empty. Nothing to do')
    return
  
  # pop next op
  tcpOp, minDelay = tcpOps.pop(0)
  
  earliestAllowed = system_clock() + minDelay
  
  tcpOp()


def queue(tcpOp, minPostDelay=200):
  if len(tcpOps) > 10:
    console.warn('Request was too long, dropping this request')
    return
  
  tcpOps.append((tcpOp, minPostDelay))
  processQueue()

# ---- TCP ]

# convenience functions

# given a response, splits out the value ensuring the name is a match
# e.g. 'PWR=01'
#      handleValueReq(resp, 'PWR', lambda value: console.info(value))
def handleValueReq(resp, name, handler, errorHandler=None):
  # if optional 
  if errorHandler != None and resp == 'ERR':
    errorHandler()
    return
  
  parts = resp.split('=')
  if len(parts) != 2:
    return
  
  if parts[0] != name:
    return
  
  if handler:
    handler(parts[1])

# status ---

local_event_Status = LocalEvent({'title': 'Status', 'order': 9990, "schema": { 'title': 'Status', 'type': 'object', 'properties': {
        'level': {'title': 'Level', 'order': next_seq(), 'type': 'integer'},
        'message': {'title': 'Message', 'order': next_seq(), 'type': 'string'}
    } } })

# for status checks

lastReceive = [0]

# roughly, the last contact  
local_event_LastContactDetect = LocalEvent({'group': 'Status', 'title': 'Last contact detect', 'schema': {'type': 'string'}})
  
def statusCheck():
  # determine lamp hours as a number, may start as a pair e.g. "2132 2133"
  allLampsUse = str(local_event_LampUseHours.getArg() or '') # (as string)
  multipleLamps = False
  
  # dealing with multiple lamps?
  if ' ' in allLampsUse:
    # find the max out of multiple lamps    
    lampUseHours = max([int(x) for x in allLampsUse.split(' ')])
    multipleLamps = True
    
  else:
    lampUseHours = int(allLampsUse or 0)
  
  diff = (system_clock() - lastReceive[0])/1000.0 # (in secs)
  now = date_now()
  
  if diff > status_check_interval+15:
    previousContactValue = local_event_LastContactDetect.getArg()
    
    if previousContactValue == None:
      message = 'Always been missing.'
      
    else:
      previousContact = date_parse(previousContactValue)
      roughDiff = (now.getMillis() - previousContact.getMillis())/1000/60
      if roughDiff < 60:
        message = 'Missing for approx. %s mins' % roughDiff
      elif roughDiff < (60*24):
        message = 'Missing since %s' % previousContact.toString('h:mm:ss a')
      else:
        message = 'Missing since %s' % previousContact.toString('h:mm:ss a, E d-MMM')
      
    local_event_Status.emit({'level': 2, 'message': message})
    return

  elif local_event_Power.getArg() == 'On' and local_event_SignalPresence.getArg() != True:
    local_event_Status.emit({'level': 1, 'message': 'Is on but no video signal detected'})  
  
  elif lampUseHours >= lampUseHoursThreshold:
    local_event_Status.emit({'level': 1, 
                             'message': 'Lamp usage is high (%s hours above threshold of %s). It may need replacement soon.' % 
                             (1+lampUseHours-lampUseHoursThreshold, lampUseHoursThreshold)})
    
  else:
    local_event_Status.emit({'level': 0, 'message': 'OK'})
  
  local_event_LastContactDetect.emit(str(now))  
  
status_check_interval = 75
status_timer = Timer(statusCheck, status_check_interval)

# for slave operation
def remote_event_PowerSlave(arg=None):
  lookup_local_action('Power').call(arg)