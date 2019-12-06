'''Lutron GRX-CI-NWK-E interface - see script for default IP, etc.'''

# [from protocol doc](http://www.lutron.com/TechnicalDocumentLibrary/RS232ProtocolCommandSet.040196d.pdf)
# make sure DIP6 and DIP7 switches ON for full feedback
#
# default login: nwk
# default ip: 192.168.250.1   port: 23 TELNET

# example comms while watching button presses:
# C0     - Off pressed
# c0
# C1     - Full On pressed
# c1

# rev. 1:   2019/12/06
#
# TODO   :   status monitoring

# <!-- parameters

param_Disabled = Parameter({'desc': 'Disables this node', 'schema': {'type': 'boolean'}})

param_IPAddress = Parameter({'schema': {'type': 'string' }})

DEFAULT_PORT = 23
param_Port = Parameter({'schema': {'type': 'integer', 'hint': '(default %s)' % DEFAULT_PORT}})

DEFAULT_LOGIN = 'nwk'
param_Login = Parameter({'schema': {'type': 'string', 'hint': '(default "%s")' % DEFAULT_LOGIN}})

# -->


# <!-- main entry-point

def main():
  console.info("Started!")

# -->


# <!-- operations

# holds callback functions
_callbacks = {} # e.g. { ':V': function(parts) }


local_event_Version = LocalEvent({'group': 'Device Info', 'order': next_seq(), 'schema': {'type': 'string'}})

@local_action({'group': 'Device Info', 'order': next_seq()})
def RequestVersion():
  def handleResp(parts):
    # e.g. response [~:v 5 3 0 1 OK] (:v high_rev low_rev model)
    local_event_Version.emit('.'.join(parts[1:-1]))
  
  _callbacks['~:v'] = handleResp
  tcp.send(':V')
  
def poll():
  RequestVersion.call()
  RequestSceneStatus.call()
  
timer_poller = Timer(poll, 60, 5, stopped=True)

SCENES = { '0': 0, '1': 1,  '2': 2,  '3': 3,  '4': 4,
                   '5': 5,  '6': 6,  '7': 7,  '8': 8,
                   '9': 9,  'A': 10, 'B': 11, 'C': 12,
                   'D': 13, 'E': 14, 'F': 15, 'G': 16 }

SCENES_REV = dict([(SCENES[x], x) for x in SCENES])


# REQUEST SCENE status
@local_action({'group': 'Scene Status', 'order': next_seq()})
def RequestSceneStatus():
  def handleResp(parts):
    # ~:ss [S1][S2][S3][S4][S5][S6][S7][S8]
    # [Sx]: scene currently selected on Control Unit at address x
    # e.g ~:ss 1AMMMMMM  means: - Control Unit at address 1 is in scene 1, 
    #                           - Control Unit at address 2 is in scene 10,
    #                           - Control Units at addresses 3 to 8 are missing (M)
    for i, code in enumerate(parts[1]):
      # e.g. i=0, value=1
      if code == 'M': # missing, so ignore
        continue
        
      initAndSetControlUnit(i+1, SCENES[code])
    
  _callbacks['~:ss'] = handleResp
  _callbacks[':ss'] = handleResp   # async feedback when scenes are changed outside nodel
  
  tcp.send(':G')
  
def initAndSetControlUnit(i, scene):
  controlUnitSceneName = 'ControlUnit %s Scene' % i
  
  controlUnitSignal = lookup_local_event(controlUnitSceneName)
      
  if not controlUnitSignal:
    # create once
    
    # main control unit signal
    controlUnitSignal = Event(controlUnitSceneName, {'group': 'Scenes', 'title': '"%s"' % (i+1), 'order': next_seq(), 'schema': {'type': 'integer'}})
    
    cuAction = Action(controlUnitSceneName, lambda arg: SelectScene(i, arg), {'group': 'Scenes', 'title': '"%s"' % (i+1), 'order': next_seq(), 
                                                              'schema': {'type': 'integer'}})
    
    # the 16 others
    for s in range(16):
      cuSceneSignal = Event('ControlUnit %s Scene %s' % (i, s+1), {'group': 'Control Unit %s' % i, 'title': 'Scene %s' % (s+1), 'order': next_seq(), 
                                                                   'schema': {'type': 'boolean'}})
      initControlUnitScene(cuAction, i, s) # need as separate method because of variable capture issues
      
  # emit the main one
  controlUnitSignal.emit(scene)
  
  # and emit the scene boolean ones
  for s in range(16):
    lookup_local_event('ControlUnit %s Scene %s' % (i, s+1)).emitIfDifferent(scene == (s+1))  
    
def initControlUnitScene(cuAction, cu, scene):
  Action('ControlUnit %s Scene %s' % (cu, scene), 
         lambda ignore: cuAction.call(scene),
         {'group': 'Control Unit %s' % cu, 'title': 'Scene %s' % scene, 'order': next_seq()})
    
def SelectScene(cu, scene): # NOT EXPOSING AS ACTION
  def handleResp(parts):
    # if parts[-1:] == 'OK':
    #  lookup_local_event('ControlUnit %s Scene' % cu).emit(scene)
      
    # feedback will be completed by direct scene change feedback
    # clear callback
    # _callbacks['~1'] = None
    pass
  
  # SELECT SCENE Command Name A : Description Selects any scene on the specified GRAFIK Eye Control Units.
  # Syntax :A[scene][control units]<CR>
  # Allowed Values Scene is from 0 to G
  # Control Unit 1-8 (Control Units on link)
  # Examples :A21<CR> Select scene 2 on Control Unit A1
  # :AG78<CR> Select scene 16 on Control Units A7 and A8    for i, code in enumerate(parts[1]):
  
  # will rely on scene change feedback
  # example resp: ~1 OK (this actually means 1 cmd processed so need to be careful)
  # _callbacks['~1'] = handleResp
  
  log(1, 'SelectScene cu:%s scene:%s' % (cu, scene))
  tcpData = ':A%s%s' % (SCENES_REV[scene], cu)
  # log(1, 'tcp will be: [%s]' % tcpData)
  tcp.send(tcpData)

# -->


# <!-- TCP

def tcp_connected():
  console.info('tcp_connected')

def tcp_disconnected():
  console.warn('tcp_disconnected')
  
  timer_poller.stop()
  
  tcp.setReceiveDelimeters(' ') # use space to trap login
  tcp.drop() # start new session

def tcp_timeout():
  console.warn('TCP/protocol timeout')
  
  tcp.drop() # start new session

def tcp_sent(data):
  log(1, "tcp_sent [%s]" % data)

def tcp_received(data):
  log(1, "tcp_received [%s]" % data)
  
  if data == 'login:':
    timer_poller.start()
    tcp.setReceiveDelimeters('\r\n')
    tcp.send(param_Login or DEFAULT_LOGIN)
  
  else: # assume a callback
    parts = data.split() # e.g. ['~:v', '5', '3', '0', '1', 'OK'] 
    
    # lookup callback and call with parts as arg
    fn = _callbacks.get(parts[0])
    if fn:
      fn(parts)
  

tcp = TCP(connected=tcp_connected, 
          disconnected=tcp_disconnected, 
          sent=tcp_sent,
          received=tcp_received,
          timeout=tcp_timeout, 
          sendDelimiters='\r', 
          receiveDelimiters=' ') # using space to trap first login
                               
@after_main # another main entry-point
def setup_tcp():
  if param_Disabled:
    console.warn('Node is disabled; will not connect TCP')
    return
  
  if not param_IPAddress:
    console.warn('IP address has not been specified')
    return

  dest = '%s:%s' % (param_IPAddress, param_Port or DEFAULT_PORT)

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
