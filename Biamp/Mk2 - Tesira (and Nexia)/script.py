# -*- coding: utf-8 -*-
u'''
**Biamp Tesira Text Protocol** (TTP) - Works with Tesira models using the Tesira Text Protocol.

Make sure TELNET is turned on.

`rev 10.20240319`

_changelog_
 
   * r10: added Logic Meter
   * r9: general faults raise warning and automatic connection drop
   * r8: activeFaults
   * r7: firmware version, start/stop pollers
   * r6: added Router block
   * r5: parse **ObjectIDs.csv** file, added Presets via Preset Recall
   * r4: logic selector block, Parlé mic block
   
'''

# TODO:
# - For Maxtrix Mixer blocks, only cross-point muting is done.
# - named source select
# - mute with source select

TELNET_TCPPORT = 23

param_Disabled = Parameter({'schema': {'type': 'boolean'}})
param_IPAddress = Parameter({'title': 'IP address', 'schema': {'type': 'string'}})

# this is the general error count used to determine errors p. minute
_errorCount = 0

# TODO REMOVE DEFAULT_DEVICE = 1

param_InputBlocks = Parameter({'title': 'Input blocks', 'schema': {'type': 'array', 'items': {'type': 'object', 'properties': {
          'instance': {'type': 'string', 'desc': 'Instance ID or tag', 'order': 1},
          'inputNames': {'type': 'string', 'desc': 'Comma separated list of simple labels starting at input #1; use "ignore" to ignore an input', 'order': 2}}}}})

param_LevelBlocks = Parameter({'title': 'Level blocks', 'schema': {'type': 'array', 'items': {'type': 'object', 'properties': {
          'instance': {'type': 'string', 'desc': 'Instance ID or tag', 'order': 1},
          'names': {'type': 'string', 'desc': 'Comma separated list of simple labels starting at #1; use "ignore" to ignore', 'order': 2}}}}})

param_MuteBlocks = Parameter({'title': 'Mute blocks', 'schema': {'type': 'array', 'items': {'type': 'object', 'properties': {
          'instance': {'type': 'string', 'desc': 'Instance ID or tag', 'order': 1},
          'names': {'type': 'string', 'desc': 'Comma separated list of simple labels starting at #1; use "ignore" to ignore', 'order': 2}}}}})

param_LogicSelectorBlocks = Parameter({'title': 'Logic Selector blocks', 'schema': {'type': 'array', 'items': {'type': 'object', 'properties': {
          'instance': {'type': 'string', 'desc': 'Instance ID or tag', 'order': 1},
          'names': {'type': 'string', 'desc': 'Comma separated list of simple labels starting at #1; use "ignore" to ignore', 'order': 2}}}}})

param_SourceSelectBlocks = Parameter({'title': 'Source-Select blocks', 'schema': {'type': 'array', 'items': {'type': 'object', 'properties': {
          'instance': {'type': 'string', 'desc': 'Instance ID or tag', 'order': 3},
          'sourceCount': {'type': 'integer', 'desc': 'The number of sources being routed', 'order': 4},
          'names': {'type': 'string', 'desc': 'Comma separated list of simple labels starting at #1; use "ignore" to ignore', 'order': 5}}}}})

param_MeterBlocks = Parameter({'title': 'Meter blocks', 'schema': {'type': 'array', 'items': {'type': 'object', 'properties': {
          'type': {'type': 'string', 'enum': ['Peak', 'RMS', 'Presence', 'Logic'], 'order': 1},
          'instance': {'type': 'string', 'desc': 'Instance ID or tag', 'order': 2},
          'names': {'type': 'string', 'desc': 'Comma separated list of simple labels starting at #1; use "ignore" to ignore', 'order': 3}}}}})

param_MatrixMixerBlocks = Parameter({'title': 'Matrix Mixer blocks', 'schema': {'type': 'array', 'items': {'type': 'object', 'properties': {
          'label': {'type': 'string', 'order': 1},
          'instance': {'type': 'string', 'desc': 'Instance ID or tag', 'order': 4},
          'inputNames': {'type': 'string', 'desc': 'Comma separated list of simple labels', 'order': 5},
          'outputNames': {'type': 'string', 'desc': 'Comma separated list of simple labels', 'order': 6}}}}})

param_StandardMixerBlocks = Parameter({'title': 'Standard Mixer blocks', 'schema': {'type': 'array', 'items': {'type': 'object', 'properties': {
          'label': {'type': 'string', 'order': 1},
          'instance': {'type': 'string', 'desc': 'Instance ID or tag', 'order': 4},
          'inputNames': {'type': 'string', 'desc': 'Comma separated list of simple labels', 'order': 5},
          'outputNames': {'type': 'string', 'desc': 'Comma separated list of simple labels', 'order': 6},
          'ignoreCrossPoints': {'type': 'boolean', 'desc': 'Ignore cross-point states to reduce number of controls', 'order': 7}
        }}}})

param_ParleMicBlocks = Parameter({'title': u'Parlé Microphone blocks', 'schema': {'type': 'array', 'items': {'type': 'object', 'properties': {
          'instance': { 'type': 'string', 'order': 1, 'desc': 'Instance ID or tag' },
          'label': { 'type': 'string', 'order': 2 },          
          'names': { 'type': 'string', 'order': 3, 'desc': 'Comma separated list of simple labels' }
        }}}})

param_Presets = Parameter({ 'schema': { 'type': 'array', 'items': { 'type': 'object', 'properties': {
          'presetID': { 'type': 'integer', 'hint': '(starts at 1000)', 'order': 1 },
          'label': { 'type': 'string' }}}}})

param_Routers = Parameter({'title': 'Router blocks', 'schema': {'type': 'array', 'items': {'type': 'object', 'properties': {
          'label': {'type': 'string', 'order': 1},
          'instance': {'type': 'string', 'desc': 'Instance ID or tag', 'order': 4},
          'inputNames': {'type': 'string', 'desc': 'Comma separated list of simple labels', 'order': 5},
          'outputNames': {'type': 'string', 'desc': 'Comma separated list of simple labels', 'order': 6}}}}})

# <main ---

_pollers = list()
  
def main():
  if param_Disabled:
    console.warn('Disabled! nothing to do')
    return
  
  if is_blank(param_IPAddress):
    console.warn('No IP address set; nothing to do')
    return
  
  dest = '%s:%s' % (param_IPAddress, TELNET_TCPPORT)
  
  console.info('Will connect to [%s]' % dest)
  tcp.setDest(dest)

# --- main>

# <protocol ---

def parseResp(rawResp, onSuccess):
  # e.g: [+OK "value":-64.697762]

  resp = rawResp.strip()
  
  global _errorCount
  
  if resp == '+OK':
    onSuccess(None)
    
  elif '-ERR' in resp:
    _errorCount += 1
    console.warn('Got bad resp: %s' % resp)
    
    if "address not found" in resp:
      console.error("Device reported ADDRESS NOT FOUND which means the name of control is wrong or it does not exist. This node needs to be reconfigured or controls need to be added to the design.")
    
    return
  
  else:
    # any successful resp has its callback called
    valuePos = resp.find('"value":')
  
    if valuePos > 0:
      onSuccess(resp[valuePos+8:])
    else:            
      _errorCount += 1
      console.warn('no value in resp; was [%s]' % resp)
    
# <!-- active fault list

# > DEVICE get activeFaultList
# < +OK "value":[{"id":INDICATOR_MAJOR_IN_DEVICE "name":"Major Fault in Device" "faults":[{"id":FAULT_DANTE_FLOW_INACTIVE "name":"one or more Dante flows inactive"}] "serialNumber":"04870642"} {"id":INDICATOR_MAJOR_IN_SYSTEM "name":"Major Fault in System" "faults":[] "serialNumber":"04870642"}]
# OR
# [+OK "value":[{"id":INDICATOR_NONE_IN_DEVICE "name":"No fault in device" "faults":[] "serialNumber":"04758197"} {"id":INDICATOR_NONE_IN_DEVICE "name":"No fault in device" "faults":[] "serialNumber":"05416569"} {"id":INDICATOR_NONE_IN_DEVICE "name":"No fault in device" "faults":[] "serialNumber":"05022765"}]]
# NEED TO SOMEHOW PARSE THIS:
# [
#    {"id":INDICATOR_MAJOR_IN_DEVICE "name":"Major Fault in Device" "faults": [ 
#        { "id":FAULT_DANTE_FLOW_INACTIVE "name":"one or more Dante flows inactive"}
#        ] "serialNumber":"04870642"
#    } 
#    {"id":INDICATOR_MAJOR_IN_SYSTEM "name":"Major Fault in System" "faults":[] "serialNumber":"04870642"
#    }
#]

local_event_ActiveFaults = LocalEvent({ "schema": { "type": "string" }}) # comma delimited or "NONE"

local_event_LastNoFaults = ({ "schema": { "type": "string" }}) # last time no faults existed

def parse_activeFaults(resp):
  # e.g. [{"id":INDICATOR_NONE_IN_DEVICE "name":"No fault in device" "faults":[] "serialNumber":"04758197"} {"id":INDICATOR_NONE_IN_DEVICE "name":"No fault in device" "faults":[] "serialNumber":"05416569"} {"id":INDICATOR_NONE_IN_DEVICE "name":"No fault in device" "faults":[] "serialNumber":"05022765"}]
  # going to treat MINOR and MAJOR faults as the same
  
  # grab only words starting with INDICATOR or FAULT
  # might end up with INDICATOR_NONE_IN_DEVICE name no fault in device
  
  tokenWords = list() # starting with INDICATOR or FAULT
  word = list()
  
  atLeastOneFault = False
  
  # split into words
  for c in resp:
    if c.isalnum() or c == "_": # treat underscore as part of word
      word.append(c)
    else:
      if len(word) > 0:
        newWord = ''.join(word)
        if newWord.startswith("INDICATOR_") or newWord.startswith("FAULT_"):
          tokenWords.append(newWord)
          if newWord.startswith("FAULT_"):
            atLeastOneFault = True
        del word[:]
  
  if len(word)>0: # deal with last
    newWord = ''.join(word)
    if newWord.startswith("INDICATOR_") or newWord.startswith("FAULT_"):
      tokenWords.append(newWord)
      if newWord.startswith("FAULT_"):
        atLeastOneFault = True      
    
  if atLeastOneFault:
    local_event_ActiveFaults.emit(' '.join(tokenWords))
  else:
    local_event_ActiveFaults.emit("NONE")
    local_event_LastNoFaults.emit(str(date_now()))
  
def pollActiveFaults():
  # see https://support.biamp.com/Tesira/Control/Tesira_TTP_Fault_Responses for full listing
  tcp_request("DEVICE get activeFaultList\n", lambda resp: parseResp(resp, parse_activeFaults))
  
_pollers.append(Timer(pollActiveFaults, 60, 10, stopped=True)) # every minute, first after 10

# -->


# <!-- firmware

local_event_Firmware = LocalEvent({ "schema": { "type": "string" }})

def pollFirmware():
  tcp_request("DEVICE get version\n", lambda resp: parseResp(resp, lambda arg: local_event_Firmware.emit(arg)))
  
_pollers.append(Timer(pollFirmware, 300, 5, stopped=True)) # every 5 mins, first after 5

# -->


INPUTGAIN_SCHEMA = {'type': 'integer', 'desc': '0, 6, 12, 18, 24, 30, 36, 42, 48, 54, 60, 66'}
  
@after_main
def bindInputs():
  for info in param_InputBlocks or []:
    for inputNum, inputName in enumerate(info['inputNames'].split(',')):
      if inputName == 'ignore':
        continue
        
      initNumberValue('Input', 'gain', inputName, info['instance'], inputNum+1, isInteger=True)
    
@after_main
def bindLevels():
  for info in param_LevelBlocks or []:
    levelInstance = info['instance']
    for num, name in enumerate(info['names'].split(',')):
      initNumberValue('Level', 'level', name, levelInstance, num+1, group=levelInstance)
      initBoolValue('Level Muting', 'mute', name, levelInstance, num+1, group=levelInstance)
      
@after_main
def bindMutes():
  for info in param_MuteBlocks or []:
    instance = info['instance']
    
    names = (info['names'] or '').strip()
    if len(names) > 0:
      for num, name in enumerate([x.strip() for x in names.split(',')]):
        initBoolValue('Mute', 'mute', name, instance, num+1)
        
    else:
      initBoolValue('Mute', 'mute', 'All', instance, 1)
      
@after_main
def bindLogicSelectorBlocks():
  for info in param_LogicSelectorBlocks or []:
    instance = info['instance']
    
    names = (info['names'] or '').strip()
    if len(names) > 0:
      for num, name in enumerate([x.strip() for x in names.split(',')]):
        initBoolValue('LogicSelect', 'state', name, instance, num+1)
      

@after_main
def bindMatrixMixers():
  for info in param_MatrixMixerBlocks or []:
    instance = info['instance']
    label = info['label']
    
    for inputNum, inputName in enumerate(info['inputNames'].split(',')):
      inputName = inputName.strip()
      
      for outputNum, outputName in enumerate(info['outputNames'].split(',')):
        outputName = outputName.strip()
        
        initBoolValue('Crosspoint State', 'crosspointLevelState', 
                          '%s - %s - %s' % (label, inputName.strip(), outputName),
                          instance, inputNum+1, index2=outputNum+1)
        
        initNumberValue('Crosspoint Level', 'crosspointLevel', 
                          inputName,
                          instance, inputNum+1, index2=outputNum+1, 
                          group='"%s %s"' % (label, outputName))
        
        
@after_main
def bindStandardMixers():
  for info in param_StandardMixerBlocks or []:
    instance = info['instance']
    
    if not info.get('ignoreCrossPoints'): # skip cross-points
      for inputNum, inputName in enumerate(info['inputNames'].split(',')):
        inputName = inputName.strip()
      
        for outputNum, outputName in enumerate(info['outputNames'].split(',')):
          outputName = outputName.strip()
          initBoolValue('Crosspoint State', 'crosspoint', 
                            inputName,
                            instance, inputNum+1, index2=outputNum+1, 
                            group='"%s %s"' % (info['label'], outputName))
        
    # output levels
    for outputNum, outputName in enumerate(info['outputNames'].split(',')):
        outputName = outputName.strip()
        initNumberValue('Output Level', 'outputLevel', 
                          outputName,
                          instance, outputNum+1,
                          group='"%s %s"' % (info['label'], outputName))
        
        initBoolValue('Output Mute', 'outputMute', 
                          outputName,
                          instance, outputNum+1,
                          group='"%s %s"' % (info['label'], outputName))        
        
    # TODO: also expose input levels
    
  
@after_main
def processParleMicBlocks():
  for info in param_ParleMicBlocks or []:
    instance = info['instance']
    label = info['label'] or instance
    
    names = (info['names'] or '').strip()
    if len(names) > 0:
      for num, name in enumerate([x.strip() for x in names.split(',')]):
        initBoolValue('Mute', 'mute', name, instance, num+1)

        
@after_main
def bindPresets():
  def preset_handler(presetID):
    # e.g. DEVICE recallPreset 1011
    tcp_request('DEVICE recallPreset %s\n' % presetID, lambda resp: parseResp(resp, lambda ignore: e_presetRecall.emit(presetID)))  

  if param_Presets:
    e_presetRecall = create_local_event('Preset Recall', { 'group': 'Presets', 'order': next_seq(), 'schema':  { 'type': 'integer' }})
    a_presetRecall = create_local_action('Preset Recall', preset_handler, { 'group': 'Presets', 'order': next_seq(), 'schema':  { 'type': 'integer' }})  
    
  for info in param_Presets or EMPTY:
    presetID = info['presetID']
    label = info['label']
    
    initPreset(e_presetRecall, a_presetRecall, presetID, label)
    
def initPreset(e_presetRecall, a_presetRecall, presetID, label):
  e = create_local_event('Preset %s' % presetID, { 'title': '%s "%s"' % (presetID, label), 'group': 'Presets', 'order': next_seq(), 'schema':  { 'type': 'boolean' }})
  e_presetRecall.addEmitHandler(lambda arg: e.emit(arg == presetID))
  
  def action_handler(ignore):
    console.info('Preset %s "%s" called' % (presetID, label))
    a_presetRecall.call(presetID)
  
  a = create_local_action('Preset %s' % presetID, action_handler, { 'title': '%s "%s"' % (presetID, label), 'group': 'Presets', 'order': next_seq() })
  
@after_main
def bindRouters():
  for info in param_Routers or []:
    instance = info['instance']
    
    # Router1 get input 1 +OK "value":0     OR     
    # Router1 set input 1 1 +OK    
      
    for outputNum, outputName in enumerate(info['outputNames'].split(',')):
      outputName = outputName.strip()
      initNumberValue('Router', 'input', outputName, instance, outputNum+1, isInteger=True)
      # e.g. name ends up as "AreaCombiningRouter 1 Router"
      
      # discrete selections
      for inputNum, inputName in enumerate(info['inputNames'].split(',')):
        inputName = inputName.strip()
        initRouterPoint(instance, outputNum+1, outputName, inputNum+1, inputName)
        
def initRouterPoint(inst, oNum, oName, iNum, iName): # required to avoid variable capture bugs
  name = '%s %s %s' % (inst, oNum, iNum)
  
  e = create_local_event(name, { 'title': '"%s"' % iName, 'group': 'Router %s' % inst, 'order': next_seq(), 'schema': { 'type': 'boolean' }})

  lookup_local_event('%s %s Router' % (inst, oNum)).addEmitHandler(lambda arg: e.emit(iNum == arg))

  a = create_local_action(name, lambda ignore: lookup_local_action('%s %s Router' % (inst, oNum)).call(iNum), { 'title': '"%s"' % iName, 'group': 'Router %s' % inst, 'order': next_seq() })
        

def initBoolValue(controlType, cmd, label, inst, index1, index2=None, group=None):
  if index2 == None:
    name = '%s %s %s' % (inst, index1, controlType)
  else:
    # name collision will occur if dealing with more than 10 in a list
    # so add in a forced delimeter 'x', e.g. '1 11' is same as '11 1' but not '1x11'
    delimeter = ' ' if index1 < 10 and index2 < 10 else ' x ' 
    
    name = '%s %s%s%s %s' % (inst, index1, delimeter, index2, controlType)
    
  title = '"%s" (#%s)' % (label, index1)
  
  if group == None:
    group = inst
    
  schema = {'type': 'boolean'}
  
  signal = Event(name, {'title': title, 'group': group, 'order': next_seq(), 'schema': schema})
  
  # some cmds take in index1 and index2
  index = index1 if index2 == None else '%s %s' % (index1, index2)

  # e.g. Mixer1 get crosspointLevelState 1 1
    
  getter = Action('Get ' + name, lambda arg: tcp_request('%s get %s %s\n' % (inst, cmd, index), 
                          lambda resp: parseResp(resp, lambda arg: signal.emit(arg == '1' or arg == 'true'))),
                 {'title': 'Get', 'group': group, 'order': next_seq()})
  
  setter = Action(name, lambda arg: tcp_request('%s set %s %s %s\n' % (inst, cmd, index, '1' if arg == True else '0'), 
                          lambda resp: parseResp(resp, 
                            lambda result: signal.emit(arg))), # NOTE: uses the original 'arg' here
                  {'title': title, 'group': group, 'order': next_seq(), 'schema': schema})
  
  _pollers.append(Timer(lambda: getter.call(), random(120,150), random(5,10), stopped=True))
  
  # and come conveniece derivatives
  
  toggle = Action(name + " Toggle", lambda arg: setter.call(not signal.getArg()), {'title': 'Toggle', 'group': group, 'order': next_seq()})
  
  inverted = Event(name + " Inverted", {'title': '(inverted)', 'group': group, 'order': next_seq(), 'schema': schema})
  signal.addEmitHandler(lambda arg: inverted.emit(not arg))

def initNumberValue(controlType, cmd, label, inst, index1, isInteger=False, index2=None, group=None):
  if index2 == None:
    name = '%s %s %s' % (inst, index1, controlType)
  else:
    # name collision will occur if dealing with more than 10 in a list
    # so add in a forced delimeter 'x', e.g. '1 11' is same as '11 1' but not '1x11'
    delimeter = ' ' if index1 < 10 and index2 < 10 else ' x ' 
    
    name = '%s %s%s%s %s' % (inst, index1, delimeter, index2, controlType)
    
  title = '%s ("%s")' % (name, label)
  
  if group == None:
    group = '%s %s' % (controlType, inst)
    
  schema = {'type': 'integer' if isInteger else 'number'}
  
  signal = Event(name, {'title': title, 'group': group, 'order': next_seq(), 'schema': schema})
  
  # some cmds take in index1 and index2
  index = index1 if index2 == None else '%s %s' % (index1, index2)
    
  getter = Action('Get ' + name, lambda arg: tcp_request('%s get %s %s\n' % (inst, cmd, index), 
                          lambda resp: parseResp(resp, lambda arg: signal.emit(int(float(arg)) if isInteger else float(arg)))),
                 {'title': 'Get', 'group': group, 'order': next_seq()})
  
  setter = Action(name, lambda arg: tcp_request('%s set %s %s %s\n' % (inst, cmd, index, arg), 
                          lambda resp: parseResp(resp, 
                            lambda result: signal.emit(arg))), # NOTE: uses the original 'arg' here
                  {'title': title, 'group': group, 'order': next_seq(), 'schema': schema})
  
  _pollers.append(Timer(lambda: getter.call(), random(120,150), random(5,10), stopped=True))
  
@after_main
def bindSourceSelects():
  for info in param_SourceSelectBlocks or []:
    initSourceSelect(info['instance'], info['sourceCount'], info['names'])
                                                                 
  
def initSourceSelect(inst, sourceCount, names):
  name = inst
  title = inst
  group = inst
    
  signal = Event(name, {'title': title, 'group': group, 'order': next_seq(), 'schema': {'type': 'integer'}})
  
  getter = Action('Get ' + name, lambda arg: tcp_request('%s get sourceSelection\n' % (inst), 
                          lambda resp: parseResp(resp, lambda result: signal.emit(int(result)))),
                 {'title': 'Get', 'group': group, 'order': next_seq()})
  
  # safe to use title here remembering within brackets is extraneous
  setter = Action(name, lambda arg: tcp_request('%s set sourceSelection %s\n' % (inst, int(arg)), 
                          lambda resp: parseResp(resp, 
                            lambda result: signal.emit(int(arg)))), # NOTE: uses the original 'arg' here
                  {'title': title, 'group': group, 'schema': {'type': 'integer'}})
  
  bindSourceItem(inst, 0, None, setter, signal)
  
  for i, label in zip(range(1, sourceCount+1), [x.strip() for x in names.split(',')]):
    bindSourceItem(inst, i, label, setter, signal)
  
  _pollers.append(Timer(lambda: getter.call(), random(120,150), random(5,10), stopped=True))
  
def bindSourceItem(inst, i, label, setter, signal):
  name = '%s %s Selected' % (inst, i)
  if label: title = '"%s"' % (label)
  else:     title = 'Source %s' % i
  group = inst
  
  selectedSignal = Event(name, {'title': title, 'group': inst, 'order': next_seq(), 'schema': {'type': 'boolean'}})
  
  signal.addEmitHandler(lambda arg: selectedSignal.emitIfDifferent(arg == i))

  def handler(arg):
    if arg == None: # toggle if no arg is given
      setter.call(0 if selectedSignal.getArg() else i)
      
    else:           # set the state
      setter.call(i if arg == True else 0)
    
  togglerOrSetter = Action(name, handler, {'title': title, 'group': inst, 'order': next_seq()})

@after_main
def bindMeterBlocks():
  for info in param_MeterBlocks or []:
    meterType = info['type']
    meterInstance = info['instance']
    for num, name in enumerate(info['names'].split(',')):
      initMeters(meterType, name, meterInstance, num+1)
    
def initMeters(meterType, label, inst, index):
  name = '%s %s' % (inst, index)
  title = '"%s"' % label
  
  if meterType == 'Presence':
    cmd = 'present'
    schema = {'type': 'boolean'}
    
  elif meterType == 'Logic':
    cmd = 'state'
    schema = {'type': 'boolean'}    
    
  else:
    cmd = 'level'
    schema = {'type': 'number'}
    
  group = inst

  signal = Event(name, {'title': title, 'group': group, 'order': next_seq(), 'schema': schema})
  
  def handleResult(result):
    if meterType == 'Presence':
      signal.emitIfDifferent(result=='true')
      
    elif meterType == 'Logic':
      signal.emitIfDifferent(result=='true')      
      
    else:
      signal.emit(float(result))
  
  def poll():
    tcp_request('%s get %s %s\n' % (inst, cmd, index), 
                lambda resp: parseResp(resp, handleResult))
  
  # start meters much later to avoid being overwhelmed with feedback
  _pollers.append(Timer(poll, 0.5, random(30,45), stopped=True))

# only requests *if ready*
def tcp_request(req, onResp):
    if receivedTelnetOptions:
      # tcp.request(req, onResp)
      queue.request(lambda: tcp.send(req), onResp)
      
# --- protocol>

from org.nodel.io import Stream # for reading ObjectIDs.csv
from java.io import File        #          ditto 
import csv

@after_main
def bindObjectFileExport():
  f = File(_node.getRoot(), 'ObjectIDs.txt')
  if not f.exists():
    return
  
  console.info("import: ObjectIDs.txt exists...")
  
  header = None
  
  for row in csv.reader(Stream.readFully(f).splitlines()):
    if header is None:
      header = dict([(name.lower(), i) for i, name in enumerate(row) ])
      continue
          
    parseRow(row[header['type']], row[header['label']], row[header['partition name']], row[header['instance tag']])

def parseRow(objType, objLabel, objPartName, objTag):
  if objType == 'AudioMeter':
    # Object Code,  Type,       Label,     Partition Name,         Partition ID, Unit, Instance Tag
    # AudioMeter24, AudioMeter, RMS Meter, LVL 25 Combining Space, 1,            1,    AudioMeter24
        
    console.log('import: RMS Meter "%s" - will only use first channel. Override if necessary' % objTag)
    initMeters('RMS', 'main', objTag, 1)
        
  elif objType == 'Level':
    # Object Code, Type,  Label,  Partition Name,         Partition ID, Unit, Instance Tag
    # Level31,     Level, TR1 PS, LVL 25 Combining Space, 1,            1,    TR1PSLVL
        
    initNumberValue('Level', 'level', 'Main', objTag, 1, group=objPartName)
    initBoolValue('Level Muting', 'level', 'Main', objTag, 1, group=objPartName)
    
  else:                
    console.log('import: %s "%s" - unknown type, skipping' % (objType, objTag))

# <tcp ---

# taken from Tesira help file

receivedTelnetOptions = False
  
def tcp_connected():
  console.info('tcp_connected')
  
  global receivedTelnetOptions
  receivedTelnetOptions = False
  
  tcp.clearQueue()
  
def tcp_received(data):
  # UNCOMMENT TO SHOW HEX TOO:
  # log(3, 'tcp_recv [%s] -- [%s]' % (data, data.encode('hex')))
  log(3, 'tcp_recv [%s]' % data)
  for c in data:
    handleByte(c)

telnetBuffer = list()
recvBuffer = list()
    
def handleByte(c):
  if len(telnetBuffer) > 0:
    # goes into a TELNET frame
    telnetBuffer.append(c)
    
    if len(telnetBuffer) == 3:
      frame = ''.join(telnetBuffer)
      del telnetBuffer[:]
      telnet_frame_received(frame)

    
  elif c == '\xff':
    # start of TELNET FRAME
    telnetBuffer.append(c)
      
  elif c in ['\r', '\n']:
    # end of a NORMAL msg
    msg = ''.join(recvBuffer).strip()
    del recvBuffer[:]
    
    if len(msg) > 0:
      queue.handle(msg)
    
  else:
    # put all other characters into NORMAL msg
    recvBuffer.append(c)
    
    if len(recvBuffer) > 1024:
      console.warn('buffer too big; dropped; was "%s"' % ''.join(recvBuffer))
      del recvBuffer[:]
      global _errorCount
      _errorCount += 1
    
def telnet_frame_received(data):
  log(2, 'telnet_recv [%s]' % (data.encode('hex')))
  
  # reject all telnet options
  if data[0] == '\xFF':
    if data[1] == '\xFB':  # WILL
      tcp.send('\xFF\xFE%s' % data[2]) # send DON'T
      
    elif data[1] == '\xFD': # DO
      tcp.send('\xFF\xFC%s' % data[2]) # send WON'T
      
def msg_received(data):
  log(2, 'msg_recv [%s]' % (data.strip()))
  
  global _lastReceive
  _lastReceive = system_clock()

  if 'Welcome to the Tesira Text Protocol Server...' in data:
    global receivedTelnetOptions
    receivedTelnetOptions = True
    
    [ p.start() for p in _pollers ]
  
def tcp_sent(data):
  log(3, 'tcp_sent [%s] -- [%s]' % (data, data.encode('hex')))
  
def tcp_disconnected():
  console.warn('tcp_disconnected')

  global receivedTelnetOptions
  receivedTelnetOptions = False
  
  [ p.stop() for p in _pollers ]  
  
def tcp_timeout():
  console.warn('tcp_timeout; dropping (if connected)')
  
  global _errorCount
  _errorCount += 1
  
  tcp.drop()
  
def protocolTimeout():
  console.log('protocol timeout; flushing buffer; dropping connection (if connected)')
  queue.clearQueue()
  del recvBuffer[:]
  del telnetBuffer[:]

  global receivedTelnetOptions
  receivedTelnetOptions = False
  
  tcp.drop()

tcp = TCP(connected=tcp_connected, received=tcp_received, sent=tcp_sent, disconnected=tcp_disconnected, timeout=tcp_timeout,
          receiveDelimiters='', sendDelimiters='')

queue = request_queue(timeout=protocolTimeout, received=msg_received)

# --- tcp>


# <logging ---

local_event_LogLevel = LocalEvent({'group': 'Debug', 'order': 10000+next_seq(), 'schema': {'type': 'integer'}})

def warn(level, msg):
  if local_event_LogLevel.getArg() >= level:
    console.warn(('  ' * level) + msg)

def log(level, msg):
  if local_event_LogLevel.getArg() >= level:
    console.log(('  ' * level) + msg)    

# --->


# <!-- status

local_event_Status = LocalEvent({ 'group': 'Status', 'order': 9990, 'schema': { 'type': 'object', 'properties': {
        'level': { 'order': 1, 'type': 'integer'},
        'message': { 'order': 2, 'type': 'string'}}}})

_lastReceive = 0 # system_clock base

# roughly, the last contact  
local_event_LastContactDetect = LocalEvent({'group': 'Status', 'title': 'Last contact detect', 'schema': {'type': 'string'}})

_lastErrorCount, _lastErrorCountTimestamp = 0, system_clock()
_lastConnectionRecycle = system_clock()
  
def statusCheck():
  nowClock = system_clock()
  diff = (nowClock - _lastReceive)/1000.0 # (in secs)
  now = date_now()
  
  if diff > status_check_interval+15:
    previousContactValue = local_event_LastContactDetect.getArg()
    
    if previousContactValue == None:
      message = 'Never been monitored'
      
    else:
      message = 'Unmonitorable %s' % formatPeriod(previousContactValue)
      
    local_event_Status.emit({'level': 2, 'message': message})
    return
  
  local_event_LastContactDetect.emit(str(now))
  
  # check general protocol faults
  global _lastErrorCount, _lastErrorCountTimestamp
  errorCount = _errorCount
  errorDiff = errorCount - _lastErrorCount
  timeDiff = nowClock - _lastErrorCountTimestamp
  
  _lastErrorCount, _lastErrorCountTimestamp = errorCount, nowClock
  
  errorsPerMin = errorDiff * 60000 / timeDiff
  
  if errorsPerMin > 0: # if more than 10 general errors per minute, show the warning
    local_event_Status.emit({ "level": 1, "message": "Protocol is reporting more than %s device faults per minute; will recycle connection after 5 mins." % errorsPerMin })
    
    global _lastConnectionRecycle
    if nowClock - _lastConnectionRecycle > (5 * 60000):
      console.error("Has been more than 5 mins with a high fault rate, dropping connection")
      tcp.drop()
      _lastConnectionRecycle = nowClock
      
    return
  
  activeFaults = local_event_ActiveFaults.getArg()
  if local_event_ActiveFaults.getArg() != "NONE":
    local_event_Status.emit({ "level": 2, "message": "Device(s) report faults and likely need attention - %s, %s" % (activeFaults, formatPeriod(local_event_LastNoFaults.getArg())) })
    return
  
  local_event_Status.emit({'level': 0, 'message': 'OK'})
  
status_check_interval = 75
status_timer = Timer(statusCheck, status_check_interval)

def formatPeriod(dateStr, asInstant=False):
  if dateStr == None:       return 'for unknown period'

  dateObj = date_parse(dateStr)

  now = date_now()
  diff = (now.getMillis() - dateObj.getMillis()) / 1000 / 60 # in mins
  
  if diff < 0:              return 'never ever'
  elif diff == 0:           return 'for <1 min' if not asInstant else '<1 min ago'
  elif diff < 60:           return ('for <%s mins' if not asInstant else '<%s mins ago') % diff
  elif diff < 60*24:        return ('since %s' if not asInstant else 'at %s') % dateObj.toString('h:mm a')
  else:                     return ('since %s' if not asInstant else 'on %s') % dateObj.toString('E d-MMM h:mm a')

# --->


# <convenience methods ---

def getOrDefault(value, default):
  return default if value == None or is_blank(value) else value

from java.util import Random
_rand = Random()

# returns a random number between an interval
def random(fromm, to):
  return fromm + _rand.nextDouble()*(to - fromm)

# --->
