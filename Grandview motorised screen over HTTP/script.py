'''
_(rev 1)_

Recipe for Grandview motorised screen makes use of HTTP calls for monitoring and control.

Note that the screens have quite a pritive webserver so blocked calls can be expected. 
'''

param_disabled = Parameter({ 'schema': { 'type': 'boolean' }, 'desc': 'Disables this node' })

param_ipAddress = Parameter({ 'schema': { 'type': 'string', 'hint': '(overrides binding method)' }})


local_event_RawStatus = LocalEvent({ 'group': 'Operation', 'order': next_seq(), 'schema': { 'type': 'string' } }) # e.g. opening, closing, etc.

local_event_DesiredStatus = LocalEvent({ 'group': 'Operation', 'order': next_seq(), 'schema': { 'type': 'string', 'enum': [ 'Opened', 'Closed' ] } })

local_event_Power = LocalEvent({ 'group': 'Power', 'order': next_seq(), 'schema': { 'type': 'string', 'enum': [ 'On', 'Partially On', 'Off', 'Partially Off' ] } }) # 'On' means Up or Closed, 'Off' means Down or Open

local_event_Opened = LocalEvent({ 'group': 'Operation', 'order': next_seq(), 'schema': { 'type': 'boolean' }})

local_event_Closed = LocalEvent({ 'group': 'Operation', 'order': next_seq(), 'schema': { 'type': 'boolean' }})


LONG_POLL = 30        # when just polling
QUICK_POLL = 5        # when actively syncing
SYNC_PERSISTENCE = 90 # how long to persist for when syncing desired states

import sys            # for stacktrace summary


def main():
  if param_disabled:
    return console.warn('Disabled! nothing to do')
  
  if is_blank(param_ipAddress):
    _timer_sync.stop()
    return console.warn('IP address not specified!')
  
  console.info('Polling will start in %ss; major operations are always logged; for finer logging adjust LogLevel signal' % _timer_sync.getDelay())
  _timer_sync.start() # start polling
  
_busy = False

_lastSuccessfulOperation = system_clock() - 10000 # for staggering major operations (system_clock() based)



@local_action({ 'group': 'Power', 'schema': { 'type': 'string', 'enum': [ 'On', 'Off' ] } })
def Power(arg):
  if arg in [ 'On', 'on', 'ON', 1, True ]:
    desired = 'Opened'
  elif arg in [ 'Off', 'off', 'OFF', 0, False ]:
    desired = 'Closed'
  else:
    return console.warn('state: unknown arg "%s"' % arg)
  
  console.info('Power: %s (meaning "%s")' % (arg, desired))
  local_event_DesiredStatus.emit(desired)
  
  log(1, 'nudging sync timer now')
  _timer_sync.setDelayAndInterval(0.001, QUICK_POLL) # sync NOW, and every 5 seconds

@local_action({ 'group': 'Power', 'order': next_seq() })
def PowerOn(arg):
  Power.call('On')
  
@local_action({ 'group': 'Power', 'order': next_seq() })
def PowerOff(arg):
  Power.call('Off')  
  
@after_main
def combine_feedback():
  def handler(arg):
    desiredStatus = local_event_DesiredStatus.getArg()
    rawStatus = local_event_RawStatus.getArg()

    desiredAsPower = 'On' if desiredStatus == 'Opened' else 'Off' if desiredStatus == 'Closed' else 'Unknown' # desired is controlled so should never be Unknown but keeping for completeness
    rawAsPower = 'On' if rawStatus == 'Opened' else ('Off' if rawStatus == 'Closed' else 'Unknown')
        
    if desiredStatus == None:         power = rawAsPower                      # will be Unknown
    elif desiredStatus == rawStatus:  power = rawAsPower                      # will be On or Off
    else:                             power = 'Partially %s' % desiredAsPower # should always be either Partially On or Partially Off
      
    local_event_Power.emit(power)
    
    local_event_Opened.emit(rawStatus == 'Opened')
    local_event_Closed.emit(rawStatus == 'Closed')
    
  local_event_DesiredStatus.addEmitHandler(handler)
  local_event_RawStatus.addEmitHandler(handler)
  
    
@local_action({ 'group': 'Operation' })
def syncNow():
  result = call('GetDevInfoList.js') # e.g. { currentIp: "172.16.80.102", devInfo": [ {
                                     #          ver: "1.0", id: "3449710912", ip: "172.16.80.102", sub: "255.255.248.0", gw: "172.16.80.1", name: "FSF-SCN", pass: "admin",pass2: "config", 
                                     #          status: "Opened" } ] }
  
  if result == False: # bad result, timeout, etc.
    return
  
  raw = result['devInfo'][0]['status']
  local_event_RawStatus.emit(raw)
  
  desired = local_event_DesiredStatus.getArg()
      
  # check if it's been more than 1.5 minutes since action request so polling can simmer down if necessary
  lastAction = (Power.getTimestamp() or date_parse('1990'))
  if (date_now().getMillis() - lastAction.getMillis()) > SYNC_PERSISTENCE*1000:
    if _timer_sync.getInterval() != LONG_POLL:
      # adjust polling period and log
      log(1, 'has been more than %s mins since action or just restarted, long polling now' % (SYNC_PERSISTENCE / 60.0))
      _timer_sync.setInterval(LONG_POLL)
      
      # don't sync, all done for this cycle
      return
  
  if desired == None:
    return log(1, 'desired state is blank, nothing to do')
  
  if desired == raw:
    return log(1, 'desired and raw are same i.e. "%s", so nothing to do right now' % (desired))
  
  # they're different and not blank so sync
  
  global _lastSuccessfulOperation
  
  if (system_clock() - _lastSuccessfulOperation) < 10000:
    console.log('want to change status to "%s", but has been less than 10 seconds since last successful operation; will stagger' % desired)
    return 
  
  if desired == 'Opened':
    result = call('Open.js', query={ 'a': '100' }) # not sure what the query is; taking from reverse engineering the webpage
    if result == False:
      return
    
    _lastSuccessfulOperation = system_clock()
    
  elif desired == 'Closed':
    result = call('Close.js', query={ 'a': '100' }) # not sure what the query is; taking from reverse engineering the webpage
    if result == False:
      return
    
    _lastSuccessfulOperation = system_clock()  
  
_timer_sync = Timer(lambda: syncNow.call(), LONG_POLL, 5, stopped=True) # every 30s, first after 5  

def call(suffix, query=None, forceLog=False):
  # this web server is very primative and struggles with overlapping calls so need to respect a busy flag
  global _busy
  
  if _busy:
    return False
  
  _busy = True
  
  try:
    url = 'http://%s/%s' % (param_ipAddress, suffix)

    if forceLog: console.info('req: url:%s' % url)
    else: log(1, 'req: url:%s' % url)
      
    try:
      timestamp = system_clock()
      resp = get_url(url, connectTimeout=5, readTimeout=5, query=query)
    except:
      e = sys.exc_info()[1] # tuple order is excType, value, trace
      msg = 'get_url: failed (took %0.1f) with "%s"' % ((system_clock()-timestamp)/1000.0, e)
      
      if forceLog: console.warn(msg)
      else:        warn(1, msg)
        
      return False

    log(1, 'resp: %s' % resp)
    result = json_decode(resp)

    global _lastReceive
    _lastReceive = system_clock()

    return result
  
  finally:
    _busy = False

# -->

  
# <status and error reporting ---

# for comms drop-out
_lastReceive = 0

# roughly, the last contact  
local_event_LastContactDetect = LocalEvent({'group': 'Status', 'order': 99999+next_seq(), 'title': 'Last contact detect', 'schema': {'type': 'string'}})

# node status
local_event_Status = LocalEvent({'group': 'Status', 'order': 99999+next_seq(), 'schema': {'type': 'object', 'properties': {
        'level': {'type': 'integer', 'order': 1},
        'message': {'type': 'string', 'order': 2}}}})
  
def statusCheck():
  diff = (system_clock() - _lastReceive)/1000.0 # (in secs)
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
        message = 'Missing since %s' % previousContact.toString('h:mm a')
      else:
        message = 'Missing since %s' % previousContact.toString('h:mm a, E d-MMM')
      
    local_event_Status.emit({'level': 2, 'message': message})
    
  else:
    # update contact info
    local_event_LastContactDetect.emit(str(now))
    
    # TODO: check internal device status if possible

    local_event_LastContactDetect.emit(str(now))
    local_event_Status.emit({'level': 0, 'message': 'OK'})
    
status_check_interval = 75
status_timer = Timer(statusCheck, status_check_interval)

# --->

  

# <!-- logging

local_event_LogLevel = LocalEvent({'group': 'Debug', 'order': 10000+next_seq(), 'desc': 'Use this to ramp up the logging (with indentation)',  
                                   'schema': {'type': 'integer'}})

def warn(level, msg):
  if (local_event_LogLevel.getArg() or 0) >= level:
    console.warn(('  ' * level) + msg)

def log(level, msg):
  if (local_event_LogLevel.getArg() or 0) >= level:
    console.log(('  ' * level) + msg)

# --!>
