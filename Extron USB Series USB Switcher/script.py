'''Extron USB Switcher - see https://www.extron.com/download/files/userman/68-1517-01_F_SW_USB_UG_f.pdf'''

# <!-- parameters

param_disabled = Parameter({'desc': 'Disables this node', 'schema': {'type': 'boolean'}})

param_ipAddress = Parameter({ 'title': 'IP Address (normally of serial bridge)', 'schema': {'type': 'string' }})

DEFAULT_PORT = 4999
param_port = Parameter({'schema': {'type': 'integer', 'hint': '%s (default)' % DEFAULT_PORT}})

# -->


# <!-- main entry-point

def main():
  console.info("Recipe has started!")

# -->

# <!-- Extron protocol

def checkForErrors(resp, onSuccess):
  if resp.startswith('E'):
    raise Exception('Got error code [%s]' % resp)
    
  lastReceive[0] = system_clock()
    
  onSuccess(resp)
  

local_event_Firmware = LocalEvent({'group': 'Device Info', 'order': next_seq(), 'schema': {'type': 'string'}})

@local_action({'group': 'Device Info', 'order': next_seq()})
def pollFirmware():
  tcp.request('q', lambda raw: checkForErrors(raw, lambda resp: local_event_Firmware.emit(resp)))
  
  
# e.g. select input
#      >> 2!
#      << Chn2
local_event_Input = LocalEvent({'group': 'Switching', 'order': next_seq(), 'schema': {'type': 'integer'}})

def handleSwitchResp(resp):
  # e.g. "Chn2" or "Chn3" OR
  #      "Chn4 InACT0110 OutACT0000 Emul11" from poll input
  if not resp.startswith('Chn'):
    raise Warning('Unexpected switch resp [%s]' % resp)
    
  i = int(resp[3])
  
  local_event_Input.emit(i)

@local_action({'group': 'Switching', 'order': next_seq(), 'schema': {'type': 'integer'}})
def selectInput(arg):
  tcp.request('%s!' % arg, lambda raw: checkForErrors(raw, handleSwitchResp))


# e.g. request information:
#      >> I
#      << Chn4 InACT0110 OutACT0000 Emul11

@local_action({'group': 'Switching', 'order': next_seq()})
def pollInput():
  tcp.request('I', lambda raw: checkForErrors(raw, handleSwitchResp))
  
poller = Timer(lambda: pollInput.call(), 10, 5)
  
# -->



# <!-- TCP: this section demonstrates some TCP functions

def tcp_connected():
  console.info('tcp_connected')
  tcp.clearQueue()

def tcp_disconnected():
  console.warn('tcp_disconnected')

def tcp_timeout():
  console.warn('tcp_timeout')

def tcp_sent(data):
  log(1, "tcp_sent [%s]" % data)

def tcp_received(data):
  log(1, "tcp_received [%s]" % data)

tcp = TCP(connected=tcp_connected, 
          disconnected=tcp_disconnected, 
          sent=tcp_sent,
          received=tcp_received,
          timeout=tcp_timeout, 
          sendDelimiters=None, 
          receiveDelimiters='\r\n')
                               
@after_main # another main entry-point
def setup_tcp():
  if param_disabled:
    console.warn('Node is disabled; will not connect TCP')
    return
  
  if not param_ipAddress:
    console.warn('IP address has not been specified')
    return

  dest = '%s:%s' % (param_ipAddress, param_port or DEFAULT_PORT)

  console.info('Will connect to TCP %s' % dest)

  tcp.setDest(dest)
  
# <status and error reporting ---

# for comms drop-out
lastReceive = [0]

# roughly, the last contact  
local_event_LastContactDetect = LocalEvent({'group': 'Status', 'order': 99999+next_seq(), 'title': 'Last contact detect', 'schema': {'type': 'string'}})

local_event_Status = LocalEvent({'group': 'Status', 'order': 99999+next_seq(), 'schema': {'type': 'object', 'properties': {
        'level': {'type': 'integer', 'order': 1},
        'message': {'type': 'string', 'order': 2}}}})
  
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
      if roughDiff < 60:
        message = 'Missing for approx. %s mins' % roughDiff
      elif roughDiff < (60*24):
        message = 'Missing since %s' % previousContact.toString('h:mm:ss a')
      else:
        message = 'Missing since %s' % previousContact.toString('h:mm:ss a, E d-MMM')
      
    local_event_Status.emit({'level': 2, 'message': message})
    
  else:
    # update contact info
    local_event_LastContactDetect.emit(str(now))
    
    # TODO: check internal device status if possible

    local_event_LastContactDetect.emit(str(now))
    local_event_Status.emit({'level': 0, 'message': 'OK'})
    
status_check_interval = 75
status_timer = Timer(statusCheck, status_check_interval)

# --!>

# <!-- logging

local_event_LogLevel = LocalEvent({'group': 'Debug', 'order': 10000+next_seq(), 'desc': 'Use this to ramp up the logging (with indentation)',  
                                   'schema': {'type': 'integer'}})

def warn(level, msg):
  if local_event_LogLevel.getArg() >= level:
    console.warn(('  ' * level) + msg)

def log(level, msg):
  if local_event_LogLevel.getArg() >= level:
    console.log(('  ' * level) + msg)

# --!>