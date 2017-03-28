# Copyright (c) 2014 Museum Victoria
# This software is released under the MIT license (see license.txt for details)

import pjlink
import socket
import sys

DEFAULT_PORT = 4352

param_ipAddress = Parameter({ "title": "IP address", "schema": {"type": "string"}})
param_port = Parameter({"schema": {"type": "integer", "hint": DEFAULT_PORT}})
param_password = Parameter({"schema": {"type": "string"}})

local_event_PowerState = LocalEvent({'title': 'Power State (legacy)', "group": "Power","schema": {"type": "string", "enum": ["off", "on", "cooling", "warm-up"]}})
local_event_InputState = LocalEvent({'title': 'Input State (legacy)', "group": "Inputs"})
local_event_Error = LocalEvent({"title": "Error", "schema": {"type": "string"}})

local_event_Power = LocalEvent({'group': 'Power', 'schema': {'type': 'string', 'enum': ['On', 'Off', 'Partially On', 'Partially Off']}})
local_event_DesiredPower = LocalEvent({'group': 'Power', 'schema': {'type': 'string', 'enum': ['On', 'Off']}})

local_event_Input = LocalEvent({'group': 'Inputs', 'schema': {'type': 'object', 'properties': { 
        'number': {'type': 'integer', 'order': 1}, 
        'source': { 'type': 'string', 'order': 2, 'enum': ['UNKNOWN', 'RGB', 'VIDEO', 'DIGITAL', 'STORAGE', 'NETWORK']} }}})

local_event_DesiredInput = LocalEvent({'group': 'Inputs', 'schema': {'type': 'object', 'properties': { 
        'number': {'type': 'integer', 'order': 1}, 
        'source': { 'type': 'string', 'order': 2, 'enum': ['RGB', 'VIDEO', 'DIGITAL', 'STORAGE', 'NETWORK']} }}})

local_event_LampHours = LocalEvent({'group': 'Information', 'desc': 'The lamps hours for each lamp (comma separated)', 'order': next_seq(), 'schema': {'type': 'string'}})

def main():
  if len((param_ipAddress or '').strip()) == 0:
    console.warn('No IP address configured; nothing to do')
    return
  
  console.info('Using network destination [%s:%s]' % (param_ipAddress, param_port or DEFAULT_PORT))
  console.info('Power state is polled every 5 minutes unless actively switching power or inputs.')
  console.info('Use "Power" and "Input" actions for reliable (managed) state transitions')

def local_action_RawPowerOn(arg=None):
  '''{"desc": "Turns projector on.", "group": "Power"}'''
  p = get_projector()
  if(p):
    try:
      p.set_power('on')
    except Exception, e:
      local_event_Error.emit(e)
    finally:
      p.f.close()

def local_action_RawPowerOff(arg=None):
  '''{"desc": "Turns the projector off.", "group": "Power" }'''
  p = get_projector()
  if(p):
    try:
      p.set_power('off')
    except Exception, e:
      local_event_Error.emit(e)
    finally:
      p.f.close()

def local_action_GetPower(arg=None):
  '''{"desc": "Get power state of projector.", "group": "Power" }'''
  p = get_projector()
  if(p):
    try:
      pwr = p.get_power()
      local_event_PowerState.emit(pwr)
      
      # for status reporting
      lastReceive[0] = system_clock()
      
    except Exception, e:
      local_event_Error.emit(e)
    finally:
      p.f.close()

def local_action_RawSetInput(arg):
  '''{"desc": "Set projector input.", "group": "Inputs", "schema": { "type":"object", "required":true, "title": "Input", "properties":{ 
          "number": { "type":"integer", "title": "Number", "required":true }, 
          "source": { "type":"string", "title": "Source", "required":true, "enum": ["RGB", "VIDEO", "DIGITAL", "STORAGE", "NETWORK"] } } } }'''
  p = get_projector()
  if(p):
    try:
      p.set_input(arg['source'], arg['number'])
    except Exception, e:
      local_event_Error.emit(e)
    finally:
      p.f.close()

def local_action_GetInput(arg=None):
  '''{"desc": "Get current input.", "group": "Inputs" }'''
  p = get_projector()
  if(p):
    try:
      inp = p.get_input()
      local_event_InputState.emit(inp) # legacy
      local_event_Input.emit({'source': inp[0], 'number': inp[1]}) # managed
      
    except Exception, e:
      local_event_Error.emit(e)
    finally:
      p.f.close()

def local_action_Mute(what):
  '''{"schema": { "title": "What", "type": "string", "required": true, "enum" : ["video", "audio", "all"] }, "group": "Mute" }'''
  p = get_projector()
  if(p):
    try:
      what = { 'video': 1, 'audio': 2, 'all': 3, }[what]
      p.set_mute(what, True)
    except Exception, e:
      local_event_Error.emit(e)
    finally:
      p.f.close()

def local_action_Unmute(what):
  '''{"schema": { "title": "What", "type": "string", "required": true, "enum" : ["video", "audio", "all"] }, "group": "Mute" }'''
  p = get_projector()
  if(p):
    try:
      what = { 'video': 1, 'audio': 2, 'all': 3, }[what]
      p.set_mute(what, False)
    except Exception, e:
      local_event_Error.emit(e)
    finally:
      p.f.close()

def local_action_Lamps(x = None):
  '''{"desc": "Get lamp info", "group": "Information" }'''
  p = get_projector()
  if(p):
    try:
      lampHours = list()
      for i, (time, state) in enumerate(p.get_lamps()):
          print 'Lamp %d: %s (%d hours)' % (i+1, 'on' if state else 'off', time)
          lampHours.append(str(time))
          
      local_event_LampHours.emit(', '.join(lampHours))
          
    except Exception, e:
      local_event_Error.emit(e)
    finally:
      p.f.close()

def local_action_Errors(arg=None):
  '''{"desc": "Get projector error info.", "group": "Information" }'''
  p = get_projector()
  if(p):
    try:
      for what, state in p.get_errors().items():
          print '%s: %s' % (what, state)
    except Exception, e:
      local_event_Error.emit(e)
    finally:
      p.f.close()

def get_projector():
  try:
    sock = socket.socket()
    sock.connect((param_ipAddress, param_port or DEFAULT_PORT))
    f = sock.makefile()
    proj = pjlink.Projector(f)
    rv = proj.authenticate(lambda: param_password)
    if(rv or rv is None):
      return proj
    else:
      local_event_Error.emit('authentication error')
      return False
  except:
    local_event_Error.emit('connection error')
    return False
  finally:
    sock.close()

# managed power and input select

ENFORCEMENT_TIME = 2 * 60 # (default 2 mins)

def syncPower():
  console.log('syncing power (if necessary)')
  
  # immediately check if the states match
  desiredPower = local_event_DesiredPower.getArg()
  actual = local_event_Power.getArg()
  
  if desiredPower == actual:
    console.info('Power matches desired state ("%s")' % desiredPower)
    timer_powerSyncer.stop()
    
    timer_powerRetriever.setInterval(5*60) # revert power poller
    
    return
  
  # should be expiring?
  lastPowerSet = local_event_DesiredPower.getTimestamp()
  
  if lastPowerSet != None and (date_now().getMillis() - lastPowerSet.getMillis() > ENFORCEMENT_TIME*1000):
    console.warn('Giving up syncing power; more than %s seconds elapsed' % ENFORCEMENT_TIME)
    timer_powerSyncer.stop()
    
    timer_powerRetriever.setInterval(5*60) # revert power poller
    
    return
  
  # otherwise, attempt to sync
  if desiredPower == 'On':
    lookup_local_action('RawPowerOn').call()
    
  elif desiredPower == 'Off':
    lookup_local_action('RawPowerOff').call()
    
  # (leave timer to re-fire...)
  
def syncInput():
  console.log('syncing input (if necessary)')
  
  # immediately check if the states match
  desired = local_event_DesiredInput.getArg()
  actual = local_event_Input.getArg()
  
  if same_value(desired, actual):
    console.info('Input matches desired state ("%s")' % desired)
    timer_inputSyncer.stop()
    timer_inputRetriever.setInterval(5*60) # revert poller
    return
  
  # should be expiring?
  lastSet = local_event_DesiredInput.getTimestamp()
  
  if lastSet != None and (date_now().getMillis() - lastSet.getMillis() > ENFORCEMENT_TIME*1000):
    console.warn('Giving up syncing input; more than %s seconds elapsed' % ENFORCEMENT_TIME)
    timer_inputSyncer.stop()
    timer_inputRetriever.setInterval(5*60) # revert poller
    return
  
  # otherwise, if power is on, attempt to sync
  if local_event_Power.getArg() != 'On':
    console.info('(power is off; will not sync input)')
    return
  
  lookup_local_action('RawSetInput').call(desired)
    
  # (leave timer to re-fire...)  
  
timer_powerSyncer = Timer(syncPower, 0, 0) # is only active when syncing power, self stopping
timer_powerRetriever = Timer(lambda: lookup_local_action('GetPower').call(), 5*60, 5) # retrieve the power every 5 minutes (unless syncing)
timer_inputSyncer = Timer(syncInput, 0, 0) # is only active when syncing input, self stopping

def retrieveInputIfOn():
  if local_event_Power.getArg() == 'On':
    lookup_local_action('GetInput').call()
    
timer_inputRetriever = Timer(retrieveInputIfOn, 5*60, 5) # retrieve the input every 5 minutes (unless syncing)

# power

def local_action_Power(arg=None):
  '''{"title": "Power (managed)", "group": "Power", "desc": "Enforces state for a period of time", "schema": {"type": "string", "enum": ["On", "Off"]}}'''
  console.info('Power %s' % arg)
  
  local_event_DesiredPower.emit(arg)
  
  if timer_powerSyncer.isStopped():
    console.info('Kicking off power syncer immediately (then every 10s) and power state retriever after 3 seconds (then every 10s)')
    timer_powerSyncer.setDelayAndInterval(0.001, 10)
    timer_powerSyncer.start()
    
    timer_powerRetriever.setDelayAndInterval(3, 10)
    
def local_action_PowerOn(arg=None):
  '''{"title": "On (managed)", "group": "Power"}'''
  lookup_local_action('Power').call('On')
  
def local_action_PowerOff(arg=None):
  '''{"title": "Off (managed)", "group": "Power"}'''
  lookup_local_action('Power').call('Off')  
    
def evaluatePowerState(arg=None):
  desired = local_event_DesiredPower.getArg()
  raw = local_event_PowerState.getArg()
  
  if desired == 'On':
    if raw == 'on':
      local_event_Power.emit('On')
      
    else: # all other states
      local_event_Power.emit('Partially On')
      
  elif desired == 'Off':
    if raw == 'off':
      local_event_Power.emit('Off')
      
    else: # all other states
      local_event_Power.emit('Partially Off')
  
def local_action_SetInput(arg=None):
  '''{"title": "Set Input (legacy)", "desc": "For legacy purposes only, chain-calls 'Input' action with same argument", "group": "Inputs"}'''
  lookup_local_action('Input').call(arg)
  
def local_action_Input(arg=None):
  '''{"title": "Input (managed)", "desc": "Set projector input, with attempts to enforcing over a period of time.", "group": "Inputs", "schema": { "type":"object", "required":true, "title": "Input", "properties":{ 
          "number": { "type":"integer", "required":true }, 
          "source": { "type":"string", "required":true, "enum": ["RGB", "VIDEO", "DIGITAL", "STORAGE", "NETWORK"] } } } }'''
  console.info('Input %s' % arg)
  
  local_event_DesiredInput.emit(arg)
  
  if timer_inputSyncer.isStopped():
    console.info('Kicking off input syncer immediately (then every 10s) and input state retriever after 3 seconds (then every 10s)')
    timer_inputSyncer.setDelayAndInterval(0.001, 10)
    timer_inputSyncer.start()
    
    timer_inputRetriever.setDelayAndInterval(3, 10)      

@after_main
def trapPowerSignals():
  lookup_local_event('PowerState').addEmitHandler(evaluatePowerState)  
  lookup_local_event('DesiredPower').addEmitHandler(evaluatePowerState)

  
# <!--- device status with PJLINK lamp hours

DEFAULT_LAMPHOURUSE = 1800
param_warningThresholds = Parameter({'title': 'Warning thresholds', 'schema': {'type': 'object', 'properties': {
           'lampUseHours': {'title': 'Lamp use (hours)', 'type': 'integer', 'hint': str(DEFAULT_LAMPHOURUSE), 'order': 1}
        }}})

lampUseHoursThreshold = DEFAULT_LAMPHOURUSE

@after_main
def init_lamp_hours_support():
  global lampUseHoursThreshold
  lampUseHoursThreshold = (param_warningThresholds or {}).get('lampUseHours') or lampUseHoursThreshold
  
# poll every 24 hours, 30s first time.
poller_lampHours = Timer(lambda: lookup_local_action('Lamps').call(), 24*3600, 30)

local_event_Status = LocalEvent({'title': 'Status', 'order': 9990, "schema": { 'title': 'Status', 'type': 'object', 'properties': {
        'level': {'title': 'Level', 'order': next_seq(), 'type': 'integer'},
        'message': {'title': 'Message', 'order': next_seq(), 'type': 'string'}
    } } })

lastReceive = [0]

# roughly, the last contact  
local_event_LastContactDetect = LocalEvent({'group': 'Status', 'title': 'Last contact detect', 'schema': {'type': 'string'}})
  
def statusCheck():
  lampUseHours = max([int(x) for x in (local_event_LampHours.getArg() or '0').split(',')])
  
  diff = (system_clock() - lastReceive[0])/1000.0 # (in secs)
  now = date_now()
  
  if diff > status_check_interval+15:
    previousContactValue = local_event_LastContactDetect.getArg()
    
    if previousContactValue == None:
      message = 'Always been missing.'
      
    else:
      previousContact = date_parse(previousContactValue)
      roughDiff = (now.getMillis() - previousContact.getMillis())/1000/60
      message = 'Off the network for approx. %s minutes' % roughDiff
      
    local_event_Status.emit({'level': 2, 'message': message})
    return
  
  elif lampUseHours > lampUseHoursThreshold:
    local_event_Status.emit({'level': 1, 
                             'message': 'Lamp usage is %s hours which is %s above the replacement threshold of %s. It may need replacement.' % 
                               (lampUseHours, lampUseHours-lampUseHoursThreshold, lampUseHoursThreshold)})
    
  else:
    local_event_Status.emit({'level': 0, 'message': 'OK'})
  
  local_event_LastContactDetect.emit(str(now))  
  
status_check_interval = 12*60 # check every 12 minutes
status_timer = Timer(statusCheck, status_check_interval, 30)

# device status --->