'''
**QSC Q-SYS Core**

`rev 7`

 * drag-drop **External Controls.xml** into the node root and restart node
 * supports Core redundancy via a third instance
   * e.g. create 3 node for "DSP 1", "DSP 2" and "DSPs" where the latter has the Core 1 and Core 2 remote events filled in and External Controls.
 
_changelog_

* _rev. 7: tidyup_
* _rev. 6b: add CoreState for redundant operation_
* _rev. 4.230215: JP added "level" and "message" for Status backwards support_
* _rev. 3.201015: JP added to repo_

'''

QSC_PORT = 1710

disable_autoPoll = False

param_disabled = Parameter({"order": 0, "title":"Disable communication", "group":"Comms", "schema":{"type":"boolean"}})
param_ipAddress = Parameter({"order": 1, "title": "IP address", "desc": "The IP address to connect to.", "schema": {"type": "string" }, "value": "192.168.100.1", "order": 0})
param_logon = Parameter({"order": 2, "title": "Logon", "schema": { "type": "object", "properties": { 
                                                           "user": {"order": 1, "title": "User", "type": "string"},
                                                           "password": {"order": 2, "title": "Password", "type": "string"}}}})
param_qscBinding = Parameter({"order": 3, "title": "QSC binding (if no 'External Controls.xml')", "schema": { "type": "object", "properties": { 
                                                           "namedControlsXML": {"order": 1, "title": "Named controls XML", "type": "string", "format": "long"}}}})

param_includeMetersOnly = Parameter({ 'order': 4, 'schema': { 'type': 'boolean' }})
param_excludeMeters = Parameter({ 'order': 5, 'schema': { 'type': 'boolean' }})

# <!-- related to redundancy

local_event_CoreState = LocalEvent({ 'desc': 'Relates to redundant operation', 'schema': { 'type': 'string' }})

local_event_IPAddress = LocalEvent({ 'schema': { 'type': 'string' }})

def remote_event_IPAddress(arg):
  doSetIPAddress(arg)

@local_action({ 'schema': { 'type': 'string' }})
def SetIPAddress(arg):
  doSetIPAddress(arg)
  
def doSetIPAddress(arg):
  if not is_blank(param_ipAddress):
    console.info('Set IP Address: ignoring - IP address parameter is fixed')
    return
  
  ipAddr = local_event_IPAddress.getArg()
  if arg != ipAddr:
    console.info('IP address changed to %s! (was %s)' % (arg, ipAddr))
    local_event_IPAddress.emit(arg)
    dest = '%s:%s' % (arg, QSC_PORT)
    console.info('Setting dest to [%s]' % dest)
    tcp.setDest(dest)
    tcp.drop()

# -->
    
import xml.etree.ElementTree as ET

QSC_NAMED_CONTROLS = ["Station1_PushToTalk_Input"]
qscNamedControls = list()

# how often to poll when rapid is needed
QSC_RAPID_POLL = 0.3

# General signals ---

local_event_EngineStatus = LocalEvent({'group': 'System information', 'order': 1, 'schema': {
      'type': 'object',
      'title': 'Engine status',
      'properties': {
        'Platform':    { 'order': 1, 'title': 'Platform', 'type': 'string' },
        'State':       { 'order': 2, 'title': 'State', 'type': 'string' },
        'DesignName':  { 'order': 3, 'title': 'Design name', 'type': 'string' },
        'DesignCode':  { 'order': 4, 'title': 'Design code', 'type': 'string' },
        'IsRedundant': { 'order': 5, 'title': 'Is redundant?', 'type': 'boolean' },
        'IsEmulator':  { 'order': 6, 'title': 'Is emulator?', 'type': 'boolean' },
        'Status':      { 'order': 7, 'title': 'Status', 'type': 'object', 'properties': {
            'Code':  { 'order': 1, 'title': 'Code', 'type': 'integer'},
            'String':{ 'order': 2, 'title': 'String', 'type': 'string'}
          }}
        }
    }})

# stores signals by control ID
externalControlSignalsByControlID = {}
    
# Comms section ---
local_event_Connected = LocalEvent({'group': 'Comms', 'order': 1})
# LEAVING THIS TO LOGGING INSTEAD: local_event_Received = LocalEvent({'group': 'Comms', 'order': 2})
# LEAVING THIS TO LOGGING INSTEAD: local_event_Sent = LocalEvent({'group': 'Comms', 'order': 3})
local_event_Disconnected = LocalEvent({'group': 'Comms', 'order': 4})
local_event_Timeout = LocalEvent({'group': 'Comms', 'order': 5})

local_event_Error = LocalEvent({'group': 'Error', 'order': 1})


# main() ---

def main(arg = None):
    if param_disabled == True:
        print 'Not running; node is manually disabled.'
        return
      
    bindStaticFeedbackFunctions()
    
    # try parameter first
    externalControlsText = (param_qscBinding or EMPTY).get('namedControlsXML')
    
    # then try 'External Controls.xml' file.
    if not externalControlsText:
      f = None
      try:
        f = open('External Controls.xml')
        externalControlsText = f.read().decode('utf8')
      except:
        pass
      finally:
        if f != None:
          f.close()
    
    if externalControlsText:
      extractQSCcontrols(externalControlsText)
      bindNamedControls()
      
    else:
      console.info("No 'External Controls.xml' file found or QSC Binding parameter; not binding to any controls")
    
    if is_blank(param_ipAddress):
      ipAddr = local_event_IPAddress.getArg()
    else:
      ipAddr = param_ipAddress
    
    if is_blank(ipAddr):
      console.warn('IP Address has never been used')
      return
    
    dest = '%s:%s' % (ipAddr, QSC_PORT)
    console.info('Will connect to %s' % dest)
    tcp.setDest(dest)
    
# Direct control of QSC control
def local_action_SetControlValue(arg):
    '''{"group": "QSC direct", "order" : 0, "title" : "Set control value", "schema": { "type": "integer" } }'''
    control = arg['control']
    value = arg['value']
    
    qscControlSet(control, value)
    
def local_action_InvalidateGlobalChangeGroup(arg):
    '''{"group": "QSC direct", "order" : 1, "title" : "Invalidate global change group", "desc": "Resyncs ALL values."}'''
    tcp.send(json_encode(newJSONrpc('ChangeGroup.Invalidate', params={"Id": "global"})))
    
def refreshState():
    print 'Refreshing feedback.'
    
# A keep-alive must be sent within 60s otherwise the server shutsdown the socket
# a NoOp is good enough
def keepAlive():
    request_noOp()

# this arrives immediately on connect
def handleEngineStatusFeedback(obj):
    params = obj.get('params')
    if params is None:
      params = obj.get('result')
      
    local_event_EngineStatus.emit(params)
    state = params.get('State')
    if state == None:
      state = 'Unknown'
    local_event_CoreState.emit(state)
    
    global _coreStateUpdated # update timestamp so that on silence, it fails over
    _coreStateUpdated = system_clock()

# feedback functions by name
FEEDBACK_FUNCS = {}

# (stored as { 'timeIn': 42345234, 'func': func })
dynamicFeedbackFunctions = {}

def bindStaticFeedbackFunctions():
    FEEDBACK_FUNCS['EngineStatus'] = handleEngineStatusFeedback
    FEEDBACK_FUNCS['StatusGet'] = handleEngineStatusFeedback    
    FEEDBACK_FUNCS['NoOp'] = False #- deliberately commented out (NoOp doesn't need anything)
    FEEDBACK_FUNCS['ChangeGroup.Poll'] = handleChangeGroupPollFeedback

def extractQSCcontrols(rootXML):
    rootXML = rootXML.strip()
    
    doParse(rootXML)

      
def doParse(rootXML):
  root = ET.fromstring(rootXML.encode('utf-8'))

  # don't care where they exist, just extract all the <Control> elements
  controls = list()

  def explore(element):
      for child in element:
          if child.tag == 'Control':
              controls.append(child)
          else:
              explore(child)

  explore(root)

  for control in controls:
      controlID = control.attrib.get('Id')
      if controlID is None:
          continue

      qscNamedControls.append((controlID, control.attrib))

  # sort by controlID
  qscNamedControls.sort()
  
    
# binds all the named control based on config
# (only done once)
def bindNamedControls():
    console.info('qscNamedControls=[%s]' % qscNamedControls)
  
    for controlID, properties in qscNamedControls:
        bindNamedControlAction(controlID, properties)
        
        # TODO LOG console.info('Bound signal and event to QSC control %s' % controlID)
        
def bindNamedControlAction(controlID, properties):
    # e.g.
    # <Control Id="D1SpecialAreaMixer:MicMute" ControlId="input_1_mute" ControlName="Input 1 Mute" 
    #          ComponentId="dXMO'+bU&quot;bV_P?YK^piI" ComponentName="D1 Special Area Mixer : Mixer 2x1" 
    #          ComponentLabel="D1 Special Area Mixer" Type="Boolean" Mode="RW" Size="1" />
    #
    componentName = properties.get('ComponentName') # e.g. D1 Special Area Mixer : Mixer 2x1
    
    componentNameLower = componentName.lower()
    if param_includeMetersOnly and 'meter' not in componentNameLower:
      return
    
    if param_excludeMeters and 'meter' in componentNameLower:
      return
    
    controlType = properties.get('Type') # e.g. "Boolean", "Integer", "Float", "Trigger"

    minValue = properties.get('MinimumValue')
    maxValue = properties.get('MaximumValue')
    
    nodelGroup = 'QSC - "%s"' % componentName
    
    isString = False
    statelessAction = False
    isBool = False
    
    if controlType == 'Boolean':
      schema = { 'type': 'boolean' }
      isBool = True
      
    elif controlType == 'String':
      schema = { 'type': 'string' }
      isString = True

    elif controlType == 'Float':
      schema = { 'type': 'number' }
      
      # only use sliders on Floats
      if minValue != None:
        schema['format'] = 'range'
      
    elif controlType == 'Integer':
      schema = { 'type': 'integer' }
      
    elif controlType == 'None' and 'Preamp' in controlID:
      # have to do this because of a bug in the QSYS where it doesn't assign a type
      # for "Preamp" controls :-(
      schema = { 'type': 'number' }
      
    elif controlType == 'Status':
      schema = { 'type': 'object', 'title': 'Arg', 'properties': {
              'value': {'title': 'Value', 'type': 'integer'},
              'string': {'title': 'String', 'type': 'string'},
              'level': { 'type': 'integer', 'order': 2 },
              'message': { 'type': 'string', 'order': 3 }
      } }
    
    elif controlType == 'Trigger':
      schema = { 'type': 'boolean' }
      statelessAction = True
      
    else:
      console.warn('Unknown QSC data type detected; using string (type was "%s" for control %s)' % (controlType, controlID))
      schema = { 'type': 'string' }
      
    # specify max and min anyway regardless of slider use
    if minValue != None:
      schema['min'] = minValue
      schema['max'] = maxValue
      
  
    signal = Signal('QSC %s' % controlID, {'group': nodelGroup, 'order': next_seq(), 'title': controlID, 
                                           'schema' : schema})
    externalControlSignalsByControlID[controlID] = signal  
  
    def handler(arg=None):
        # support some other boolean type for convenience
        if isBool:
          if arg in [ 'On', 'on', 'ON' ]: arg = True
          elif arg in [ 'Off', 'off', 'OFF' ]: arg = False
            
        qscControlSet(controlID, arg if statelessAction == False else 1, isString)  
    
    name = 'QSC %s' % controlID
    action = Action(name, handler, {'group': nodelGroup, 'order': next_seq(),  
                                    'title': controlID, 'schema': schema if not statelessAction else None})
    
# first level of feedback handling
def parseFeedback(obj):
    # print 'got feedback:%s' % obj
    
    context = obj.get('id')
    
    if context is None:
        # no 'id' so try 'method' as context (which arrives as first packet on connection)
        context = obj.get('method')
        
    # check for errors first
    error = obj.get('error')
    if error is not None:
        msg = { 'error': error }
        if context is not None:
           msg['context'] = context

        local_event_Error.emit(msg)
    
    # lookup feedback function (saves having a whole bunch of "ifs")
    feedbackFunc = FEEDBACK_FUNCS.get(context)
    
    if feedbackFunc is False:
        # deliberate blind function
        return

    if feedbackFunc is not None:
        feedbackFunc(obj)
        return
    
    # try the dynamic lookups
    feedbackFuncInfo = dynamicFeedbackFunctions.get(context)
    if feedbackFuncInfo is not None:
        # clean up immediately
        del(dynamicFeedbackFunctions[context])
      
        func = feedbackFuncInfo['func']
        data = feedbackFuncInfo.get('data')
        
        # call the function
        func(obj, data)
        
        return
      
    # don't have a feedback function set up, so ignore
    
    # (dump if some context was available)
    if context is not None:
    	print '(ignoring) %s' % obj

def connected():
    console.info('TCP CONNECTED')
    local_event_Connected.emit()
    timer.start()
    coreStatusPoll_timer.start()
    
    request_setUpControlChangeGroupPolling(externalControlSignalsByControlID)
  
def received(data):
    log(2, 'RECV: [%s]' % data)
    
    lastReceive[0] = system_clock()
      
    obj = json_decode(data)
    
    # LEAVING THIS TO LOGGING INSTEAD: local_event_Received.emit(obj)
    
    parseFeedback(obj)

def sent(data):
    log(2, 'SENT: [%s]' % data)
      
    obj = json_decode(data)
    
    # LEAVING THIS TO LOGGING INSTEAD: local_event_Sent.emit(obj)
    
def disconnected():
    console.warn('TCP DISCONNECTED')

    local_event_Disconnected.emit()
    timer.stop()
    coreStatusPoll_timer.stop()
    
def timeout():
    local_event_Timeout.emit()
    
# a timer that enables when TCP is connected
timer = Timer(keepAlive, 45, stopped=True)
   
# the main TCP connection that stays open  
tcp = TCP(connected=connected, received=received, sent=sent, disconnected=disconnected, sendDelimiters='\x00', receiveDelimiters='\x00', timeout=timeout)

# QRC protocol methods --------------

# sends a NoOp request
def request_noOp():
    tcp.send(json_encode(newJSONrpc('NoOp', id='NoOp')))

# Change group controlling -----------
def request_setUpControlChangeGroupPolling(controls):
    controlsList = [controlID for controlID in controls]
  
    # instruct the controls that need polling
    tcp.send(json_encode(newJSONrpc('ChangeGroup.AddControl', params={"Id": "global", "Controls": controlsList})))
    
    # TODO: check response
    
    # set up an auto-poll
    if not disable_autoPoll:
        tcp.send(json_encode(newJSONrpc('ChangeGroup.AutoPoll', params={"Id": "global", "Rate": QSC_RAPID_POLL})))
    
    # ... changes start flying in!

# e.g. {jsonrpc=2.0, method=ChangeGroup.Poll, 
#      params={Id=global, Changes=[{Name=Station1_PushToTalk_Input, String=true, Value=1}]}}
def handleChangeGroupPollFeedback(packet):
    params = packet['params']
    
    # go through the changes
    changes = params['Changes']
    if changes is None:
        return
    
    for change in changes:
        name = change['Name']
        string = change['String']
        value = change['Value']
        
        # look up the signal
        signal = externalControlSignalsByControlID.get(name)
        if signal is None:
            return
          
        signalType = signal.getArgSchema().get('type')
        if signalType == 'string':
          signal.emit(string)

        elif signalType == 'boolean':
          signal.emit(value == 1)
        
        # using 'object' to be native QSC type with 'value' and 'string' attributes
        elif signalType == 'object':
          signal.emit({'string': string, 'value': value, 'level': value, 'message': string }) # TODO: limit to ONLY status
        
        else:
          signal.emit(value)

# Sets a control's value
# (value can be bool of number)
# e.g. {"jsonrpc":"2.0","id":1234,"method":"Control.Set","params":{"Name": "10Station56ZonePARouterZone1BGMSelect", "Value": 0}}\x00        
def qscControlSet(controlID, valueOrString, isString=False):
    if isString:
      params = {"Name": controlID, "String": valueOrString}
    else:
      params = {"Name": controlID, "Value": valueOrString}
      
    tcp.send(json_encode(newJSONrpc('Control.Set', params=params)))

@local_action({})
def request_CoreStatus():
  doRequestCoreStatus()
  
def doRequestCoreStatus():
    tcp.send(json_encode(newJSONrpc('StatusGet', id='StatusGet')))
    
coreStatusPoll_timer = Timer(doRequestCoreStatus, 10, stopped=True) # starts and stop according to TCP connection, 10s period

_coreStateUpdated = system_clock() - 60000 # safe initialisation

def clearCoreStateOnTimeout():
  if (system_clock() - _coreStateUpdated) > 15000:
    console.warn('No response from core, failing Core state to NODEL_NO_RESPONSE')
    
    local_event_CoreState.emit("NODEL_NO_RESPONSE")
    
Timer(clearCoreStateOnTimeout, 15, 5) # 15s period, first after 5

# <!-- redundancy

local_event_Core1IPAddress = LocalEvent({ 'group': 'Redundancy', 'order': next_seq(), 'schema': { 'type': 'string' }})

def remote_event_Core1IPAddress(arg):
  local_event_Core1IPAddress.emit(arg)

local_event_Core2IPAddress = LocalEvent({ 'group': 'Redundancy', 'order': next_seq(), 'schema': { 'type': 'string' }})

def remote_event_Core2IPAddress(arg):
  local_event_Core2IPAddress.emit(arg)
  
local_event_LastActiveCore = LocalEvent({ 'group': 'Redundancy', 'order': next_seq(), 'schema': { 'type': 'integer' }})

local_event_Core1State = LocalEvent({ 'group': 'Redundancy', 'order': next_seq(), 'schema': { 'type': 'string' }})

def remote_event_Core1State(arg):
  local_event_Core1State.emit(arg)
  checkRedundancy()
  
local_event_Core2State = LocalEvent({ 'group': 'Redundancy', 'order': next_seq(), 'schema': { 'type': 'string' }})

def remote_event_Core2State(arg):
  local_event_Core2State.emit(arg)
  checkRedundancy()

def checkRedundancy():
  active = None
  
  if local_event_Core1State.getArg() == 'Active':
    active = 1
    
  else:
    if local_event_Core2State.getArg() == 'Active':
      active = 2
      
  if active == None:
    console.warn('No Core is actively claiming to be Active; not going to change anything...')
    return
  
  if active == local_event_LastActiveCore.getArg():
    # nothing to do!
    return
  
  # otherwise, a change occurred!
  
  local_event_LastActiveCore.emit(active)
  newAddr = lookup_local_event('Core %s IPAddress' % active).getArg()
  console.info('Active Core has swapped to %s; changing address to %s' % (active, newAddr))
  
  SetIPAddress.call(newAddr)

# -->


# <!-- JSON-RPC functions
    
NO_OBJ = {}

# prepares a JSON-RPC packet to be sent
def newJSONrpc(method, params=NO_OBJ, id=None):
    packet = {'jsonrpc': '2.0', 'method': method, 'params': params}
    
    if id is not None:
        packet['id'] = id
  
    return packet
  
# Error related -------------------------  
  
ERROR_CODES = {
    -32700: 'Parse error. Invalid JSON was received by the server.',
    -32600: 'Invalid request. The JSON sent is not a valid Request object.',
    -32601: 'Method not found.',
    -32602: 'Invalid params.',
    -32603: 'Server error.',
    1:      'Bad Parameters - one or more of the parameters is bogus',
    2:      'Invalid Page Request ID',
    3:      'Bad Page Request - could not create the requested Page Request',
    4:      'Missing file',
    5:      'Change Groups exhausted',
    6:      'Unknown change croup',
    7:      'Unknown component name',
    8:      'Unknown control',
    9:      'Illegal mixer channel index',
    10:     'Logon required'}

# returns an error message
def get_error_message(code):
    message = ERROR_CODES.get(code)
    if message is None:
        message = "Unknown error code, '%s' returned." % code
        
    return message

# --!>

  
# <status and error reporting ---

# for comms drop-out
lastReceive = [0]

# roughly, the last contact  
local_event_LastContactDetect = LocalEvent({'group': 'Status', 'order': 99999+next_seq(), 'title': 'Last contact detect', 'schema': {'type': 'string'}})

# node status
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
    # device is online and good
    local_event_LastContactDetect.emit(str(now))
    local_event_Status.emit({'level': 0, 'message': 'OK'})
    
status_check_interval = 75
status_timer = Timer(statusCheck, status_check_interval)

# --->  
  
  
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
