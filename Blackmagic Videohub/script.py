'''
**BlackMagic** Videohub 10x10 and others.

Actions and signals are dynamically created when a connection is first made. The "Route" actions and signals are simply named "Output X" where X is the output number starting from 1. The signal's value 
is the input it's routed to, starting from 1.

Protocol reference - [VideohubDeveloperInformation.pdf](https://documents.blackmagicdesign.com/DeveloperManuals/VideohubDeveloperInformation.pdf)

`rev 1`

 * _r1.250109 created._
 * _TODO: discrete cross-point switching_

'''

TCP_PORT = 9990

param_IPAddress = Parameter({ "schema": { "type": "string", "hint": "(overrides bindings)" }})

local_event_IPAddress = LocalEvent({ "schema": { "type": "string" }})

def remote_event_IPAddress(arg):
  if not is_blank(param_IPAddress):
    prev = local_event_IPAddress.getArg()
    if prev != arg:
      local_event_IPAddress.emit(arg)
      console.info("IP address updated to %s!, was %s" % (arg, prev))
      dest = "%s:%s" % (arg, TCP_PORT)
      _tcp.setDest(dest)
      
def main():
  ipAddr = param_IPAddress
  
  if is_blank(ipAddr):
    ipAddr = local_event_IPAddress.getArg()
    
  if is_blank(ipAddr):
    console.warn("No IP address configured or updated (yet?), will keep waiting...")
  else:
    local_event_IPAddress.emit(ipAddr)
    
    dest = "%s:%s" % (ipAddr, TCP_PORT)
    console.info("Will connect to %s..." % dest)
    _tcp.setDest(dest)
    
# <!-- protocol -->
  
# the last section denoted by the ":", e.g. CONFIGURATION:  
_lastSection = None
  
def parseLine(line):
  global _lastSection
  
  if line.endswith(":"):
    _lastSection = line[:-1]
    console.info("Retrieving %s..." % _lastSection)
    
    if _lastSection == "END PRELUDE":
      console.info("Done.")
    
    return
  
  if line == "ACK":
    # heartbeat and keep-alive
    global _lastReceive
    _lastReceive = system_clock()
    return
  
  elif line == "NAK":
    console.warn("!! Negative acknowledgement received !!")
    return

  if _lastSection == "VIDEO OUTPUT ROUTING":
    # e.g. > VIDEO OUTPUT ROUTING:
    #      > 0 0
    #      > 1 0
    parts = line.split(" ")
    if len(parts) == 2:
      o = int(parts[0]) + 1
      i = int(parts[1]) + 1
      oE = lookup_local_event("Output %s" % o)
      if oE != None:
        oE.emit(i)
      
  elif _lastSection == "INPUT LABELS":
    # e.g. > INPUT LABELS:
    #      > 0 Input 01
    #      > 1 Input 02
    firstSpace = line.index(" ")
    
    i = int(line[:firstSpace]) + 1 # adjust for base-1 numbering for this node
    label = line[firstSpace+1:].strip()
    
    tryInitInput(i, label)
    
  elif _lastSection == "OUTPUT LABELS":
    firstSpace = line.index(" ")
    
    o = int(line[:firstSpace]) + 1 # adjust for base-1 numbering for this node
    label = line[firstSpace+1:].strip()
    
    tryInitOutput(o, label)
    
def tryInitInput(num, label):
  eLabel = lookup_local_event("Input %s Label" % num)
  
  if eLabel == None:
    title = "Input %s Label" % num
    
    eLabel = create_local_event("Input %s Label" % num, { "title": title, "group": "Input Labels", "schema": { "type": "string", "order": next_seq()+9000}})
    
    aLabel = create_local_action("Input %s Label" % num, lambda arg: doSetInputLabel(num, arg), { "title": title, "group": "Input Labels", "schema": { "type": "string", "order": next_seq()+9000 }})
    
  eLabel.emit(label)
  
def tryInitOutput(num, label):
  eLabel = lookup_local_event("Output %s Label" % num)
  
  if eLabel == None:
    title = "Output %s Label" % num
    group = "Output %s - %s" % (num, label)
    
    eLabel = create_local_event("Output %s Label" % num, { "title": title, "group": "Output Labels", "schema": { "type": "string", "order": next_seq()+9000 }})
    
    aLabel = create_local_action("Output %s Label" % num, lambda arg: doSetOutputLabel(num, arg), { "title": title, "group": "Output Labels", "schema": { "type": "string", "order": next_seq()+9000 }})
    
    eRoute = create_local_event("Output %s" % num, { "title": '"%s"' % label, "group": group, "schema": { "type": "integer", "order": next_seq() }})
    
    aRoute = create_local_action("Output %s" % num, lambda arg: doRoute(num, arg), { "title": '"%s"' % label, "group": group, "schema": { "type": "integer", "order": next_seq() }})
    
  eLabel.emit(label)
  
def sendPing():
  _tcp.send("PING:\n\n")
  # < ACK
  
_pinger = Timer(sendPing, 30, stopped=True) # ping every 30s, will only start after connection
  
def doRoute(o, i):
  console.info("VIDEO OUTPUT ROUTING: %s %s" % (o, i))
  _tcp.send("VIDEO OUTPUT ROUTING:\n%s %s\n\n" % (o-1, i-1))
  
def doSetOutputLabel(o, label):
  if is_blank(label):
    return console.warn("label missing")
  
  console.info("OUTPUT LABELS: %s %s" % (o, label))
  _tcp.send("OUTPUT LABELS:\n%s %s\n\n" % (o-1, label))
  
def doSetInputLabel(i, label):
  if is_blank(label):
    return console.warn("label missing")
  
  console.info("INPUT LABELS: %s %s" % (i, label))
  _tcp.send("INPUT LABELS:\n%s %s\n\n" % (i-1, label))  
    
def tcp_connected():
  console.info("CONNECTED")
  _pinger.start()
  
  # give it a little bit of time to receive but then update the status soonish
  call(statusCheck, 5)
  
def tcp_recv(line):
  log(1, "RECV: %s" % line)
  
  parseLine(line)
  
def tcp_send(line):
  log(1, "SENT: %s" % line)
  
def tcp_disconnected():
  console.warn("DISCONNECTED")
  _pinger.stop()
  
_tcp = TCP(connected=tcp_connected, received=tcp_recv, sent=tcp_send, disconnected=tcp_disconnected, receiveDelimiters="\n")

# example response:
# > PROTOCOL PREAMBLE:
# > Version: 2.8
# >
# > VIDEOHUB DEVICE:
# > Device present: true
# > Model name: Blackmagic Videohub 10x10 12G
# > Friendly name: Blackmagic Videohub 10x10 12G
# > Unique ID: BC694413A0EA480395097B34D1E0B96C
# > Video inputs: 10
# > Video outputs: 10
# >
# > NETWORK:
# > Interface Count: 1
# > Default Interface: 0
# >
# > NETWORK INTERFACE 0:
# > Name: 1GbE
# > Priority: 1
# > MAC Address: 7c:2e:0d:a7:d4:25
# > Dynamic IP: true
# > Current Addresses: 10.78.0.155/255.255.255.0
# > Current Gateway: 10.78.0.1
# > Static Addresses: 10.0.0.2/255.255.255.0
# > Static Gateway: 10.0.0.1
# >
# > INPUT LABELS:
# > 0 Input 01
# > 1 Input 02
# > ...
# > 8 Input 09
# > 9 Input 10
# >
# > OUTPUT LABELS:
# > 0 Output 01
# > 1 Output 02
# > 2 Output 03
# > ...
# > 8 Output 09
# > 9 Output 10
# >
# > VIDEO OUTPUT LOCKS:
# > 0 U
# > 1 U
# > ...
# > 8 U
# > 9 U
# >
# > VIDEO OUTPUT ROUTING:
# > 0 0
# > 1 0
# > ...
# > 8 0
# > 9 0
# >
# > CONFIGURATION:
# > Take Mode: true
# > TAKE MODE:
# > 0 true
# > 1 true
# > 2 true
# > 3 true
# > ...
# > 7 true
# > 8 true
# > 9 true
# >
# > END PRELUDE:

# <!-- logging

local_event_LogLevel = LocalEvent({'group': 'Debug', 'order': 10000+next_seq(), 'desc': 'Use this to ramp up the logging (with indentation)', 'schema': {'type': 'integer'}})

def warn(level, msg):
  if (local_event_LogLevel.getArg() or 0) >= level:
    console.warn(('  ' * level) + msg)

def log(level, msg):
  if (local_event_LogLevel.getArg() or 0) >= level:
    console.log(('  ' * level) + msg)

# --!>

# <status and error reporting ---

# for comms drop-out
_lastReceive = system_clock() - 999999

# roughly, the last contact  
local_event_LastContactDetect = LocalEvent({'group': 'Status', 'order': 99999+next_seq(), 'title': 'Last contact detect', 'schema': {'type': 'string'}})

# node status
local_event_Status = LocalEvent({'group': 'Status', 'order': 99999+next_seq(), 'schema': { 'type': 'object', 'properties': {
        'level': { 'type': 'integer', 'order': 1 },
        'message': { 'type': 'string', 'order': 2 }}}})
  
def statusCheck():
  diff = (system_clock() - _lastReceive)/1000.0 # (in secs)
  now = date_now()
  
  if diff > (status_check_interval*2):
    previousContactValue = local_event_LastContactDetect.getArg()
    
    if previousContactValue == None:
      message = 'Always been missing'
      
    else:
      previousContact = date_parse(previousContactValue)
      message = 'Missing %s' % formatPeriod(previousContact)
      
    local_event_Status.emit({'level': 2, 'message': message})
    
  else:
    # update contact info
    local_event_LastContactDetect.emit(str(now))
    local_event_Status.emit({'level': 0, 'message': 'OK'})
    
status_check_interval = 75
status_timer = Timer(statusCheck, status_check_interval)

def formatPeriod(dateObj):
  if dateObj == None:       return 'for unknown period'
  
  now = date_now()
  diff = (now.getMillis() - dateObj.getMillis()) / 1000 / 60 # in mins
  
  if diff <= 1:             return 'for <1 min'
  elif diff < 60:           return 'for <%s mins' % diff
  elif diff < 60*24:        return 'since %s' % dateObj.toString('h:mm a')
  elif diff < 365*60*24:    return 'since %s' % dateObj.toString('E d-MMM h:mm a')
  else:                     return 'for more than a year'

# --->
