'''(de)multiplexing for the LG protocol'''

# Example transmissions taken from https://www.lg.com/us/commercial/documents/MAN_SE3B_SE3KB_SL5B.pdf page 74
#
# Transmission
# [Command1][Command2][ ][Set ID][ ][Data][Cr]
# * [Command1] Identifies the factory setting and the user setting modes.
# * [Command2] Controls monitors.
# * [Set ID] Used for selecting a set you want to control. A Set ID can be assigned to each set from 1
#            to 255 (from 01H to FFH), or from 1 to 1,000 (from 001H to 3e8H) in certain models, under
#            OPTION in the OSD menu. Selecting '00H' or '000H' for Set ID allows the simultaneous control
#            of all connected monitors. (It may not be supported depending on the model.)
# * [Data]   Transmits command data.
#            Data count may increase depending on the command.
# * [Cr]     Carriage Return. Corresponds to '0x0D' in ASCII code.
# * [ ]      White Space. Corresponds to '0x20' in ASCII code.
#
# Acknowledgement
# [Command2][ ][Set ID][ ][OK/NG][Data][x]
# * The Product transmits an ACK (acknowledgement) based on this format when receiving normal data. At this
#   time, if the data is FF, it indicates the present status data. If the data is in data write mode, it returns the data
#   of the PC computer.
# * If a command is sent with Set ID '00' (=0x00) or '000 (=0x000)', the data is reflected to all monitor sets and
#   they do send any acknowledgement (ACK).
# * If the data value 'FF' is sent in control mode via RS-232C, the current setting value of a function can be
#   checked (only for some functions).
# * Some commands may not be supported on some models

param_ipAddress = Parameter({'schema': {'type': 'string' }})

DEFAULT_PORT = 9999
param_port = Parameter({'schema': {'type': 'integer', 'hint': DEFAULT_PORT}})

param_setIDs = Parameter({'title': 'Set IDs (decimal)', 'desc': 'Comma delimited', 'schema': {'type': 'string'}})

setIDs = list()

# -->

def main():
  if is_blank(param_setIDs):
    raise Exception('No SetIDs specified')
    return
  
  setIDs.extend([int(x.strip()) for x in param_setIDs.split(',')])
  
  for setID in setIDs:
    bindSetID(setID)
    
def bindSetID(setID):
  def send(data):
    log(1, 'send set:%s [%s]' % (setID, data))
    call_safe(lambda: queueSend(data))
    
  sendAction = Action('Set %s Send' % setID, send, {'group': 'Set %s' % setID, 'order': next_seq(), 'schema': {'type': 'string'}})
  receiveEvent = Event('Set %s Receive' % setID, {'group': 'Set %s' % setID, 'order': next_seq(), 'schema': {'type': 'string'}})

def parseResp(data):
  # e.g. [Command1][Command2][ ][Set ID][ ][Data][Cr]
  
  log(2, 'parse [%s]' % data)
  
  # grab setID (but will relay the entire command as is)
  
  parts = data.split(' ')
  if len(parts) < 2:
    console.warn('not enough parts to response; ignoring [%s]' % data)
    return
  
  setIDpart = parts[1] # in hex
  
  try:
    setID = int(setIDpart, 16) # decimal
    
  except:
    console.warn('setID part was not understood: [%s]' % setIDpart)
    return
  
  receiveEvent = lookup_local_event('Set %s Receive' % setID)
  
  if receiveEvent == None:
    console.warn('set ID %s not found' % setID)
    return
  
  receiveEvent.emit(data)
  
  
# <!-- queueing

from collections import deque

out_buffer = deque() # holds the out buffer

processing = False # actually processing the queue?

# when last packet was sent (using system_clock)
lastSent = 0

MAX_SIZE = 100 # number of segments to queue

GAP = 20 # milliseconds

def queueSend(data):
  global processing
  
  size = len(out_buffer)
  if size > MAX_SIZE:
    console.warn('out buffer is %s; discarding' %  size)
    return
  
  out_buffer.appendleft(data)
  
  if processing:
    log(4, '(queued data; size is %s)' % size)
    return
  
  processing = True
  
  processBuffer()
  
def processBuffer():
  global lastSent, processing
  
  now = system_clock()
  timeDiff = now - lastSent
  
  if timeDiff <= GAP:
    call_safe(processBuffer, timeDiff/1000.0)
    return
  
  # has been more than GAP, process queue immediately
  
  if len(out_buffer) > 0:
    data = out_buffer.pop()
    tcp.send(data)
    
    lastSent = now
    
  if len(out_buffer) > 0:
    call_safe(processBuffer, GAP/1000.0)
    
  else:
    processing = False # clear flag

# -->


# <!-- TCP

def tcp_connected():
  log(0, 'TCP connected')

def tcp_disconnected():
  log(0, 'TCP disconnected')

def tcp_timeout():
  log(0, 'TCP disconnected')
  
def tcp_sent(data):
  log(3, "tcp_sent [%s]" % data)

def tcp_received(data):
  log(3, "tcp_received [%s]" % data)
  
  parseResp(data)
  
tcp = TCP(connected=tcp_connected, 
          disconnected=tcp_disconnected, 
          sent=tcp_sent,
          received=tcp_received,
          timeout=tcp_timeout, 
          sendDelimiters='\r',
          receiveDelimiters='\r\nx') # notice the 'x' at the end of all responses
                               
@after_main # another main entry-point
def setup_tcp():
  if not param_ipAddress:
    console.warn('IP address has not been specified')
    return

  dest = '%s:%s' % (param_ipAddress, param_port or DEFAULT_PORT)

  console.info('Will connect to TCP %s' % dest)

  tcp.setDest(dest)

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
