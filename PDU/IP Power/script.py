'''
**IP Power 9255 Pro PDU** using HTTP control

`REV 1`

**MANUAL**

* [IP Power 9255 Pro User Manual](https://s6aae352bbf6a48e4.jimcontent.com/download/version/1698733519/module/12331169760/name/9255Pro-manual.pdf)

**REVISION HISTORY**


'''

param_disabled = Parameter({'schema': {'type': 'boolean'}, 'desc': 'Disables this node' })

param_ipAddress = Parameter({'schema': {'type': 'string', 'hint': '(overrides binding method)'}})

param_username = Parameter({'schema': {'type': 'string', 'hint': 'user'}})

param_password = Parameter({'schema': {'type': 'string', 'hint': 'password'}})


local_event_RawStatus = LocalEvent({'group': 'Operation', 'order': next_seq(), 'schema': {'type': 'string'}}) # e.g. opening, closing, etc.

local_event_DesiredStatus = LocalEvent({'group': 'Operation', 'order': next_seq(), 'schema': {'type': 'string', 'enum': ['Opened', 'Closed']}})

local_event_Power = LocalEvent({'group': 'Power', 'order': next_seq(), 'schema': {'type': 'string', 'enum': ['On', 'Partially On', 'Off', 'Partially Off']}}) # 'On' means Up or Closed, 'Off' means Down or Open

local_event_Opened = LocalEvent({'group': 'Operation', 'order': next_seq(), 'schema': {'type': 'boolean'}})

local_event_Closed = LocalEvent({'group': 'Operation', 'order': next_seq(), 'schema': {'type': 'boolean'}})


LONG_POLL = 30
QUICK_POLL = 5
SYNC_PERSISTENCE = 90

import sys
import re

def main():
    if param_disabled:
        return console.warn('Disabled! Nothing to do')

    if is_blank(param_ipAddress):
        _timer_sync.stop()
        return console.warn('IP address not specified!')
    
    console.info('Polling will start in %ss' % _timer_sync.getDelay())
    _timer_sync.start()
_busy = False

_lastSuccessfulOperation = system_clock() - 10000

@local_action({ 'group': 'Power', 'schema': { 'type': 'string', 'enum': [ 'On', 'Off'] } })
def Power(arg):
    if arg in ['On', 'on', 'ON', 1, True]:
        desired = 'Opened'
    elif arg in ['Off', 'off', 'OFF', 0, False]:
        desired = 'Closed'
    else:
        return console.warn('state: unknown arg "%s"' % arg)
    
    console.info('Power: %s (meaning "%s")' % (arg, desired))
    local_event_DesiredStatus.emit(desired)


@local_action({'group': 'Power', 'order': next_seq()})
def PowerOn(arg):
    Power.call('On')

@local_action({'group': 'Power', 'order': next_seq()})
def PowerOff(arg):
    Power.call('Off')

@after_main
def combine_feedback():
    def handler(arg):
        desiredStatus = local_event_DesiredStatus.getArg()
        rawStatus =local_event_RawStatus.getArg()

        desiredAsPower = 'On' if desiredStatus == 'Opened' else ('Off' if desiredStatus == 'Closed' else 'Unknown') # Should never be Unknown but keeping for completeness
        rawAsPower = 'On' if rawStatus == 'Opened' else ('Off' if rawStatus == 'Closed' else 'Unknown')

        if desiredStatus == None:           power = rawAsPower
        elif desiredStatus == rawStatus:    power = rawAsPower
        else:                               power = 'Partially %s' % desiredAsPower

        local_event_Power.emit(power)

        local_event_Opened.emit(rawStatus == 'Opened')
        local_event_Closed.emit(rawStatus == 'Closed')
    
    local_event_DesiredStatus.addEmitHandler(handler)
    local_event_RawStatus.addEmitHandler(handler)

@local_action({'group': 'Operation'})
def SyncNow():
    result = call('getpower')

    log(1, 'result: %s' % result)

    raw = result[4]
    console.log('raw is: %s' % raw)
    raw = int(raw)
    if raw in ['On', 'on', 'ON', 1, True]:
        raw = 'Opened'
    elif raw in ['Off', 'off', 'OFF', 0, False]:
        raw = 'Closed'
    else:
        return console.warn('state: unknown arg "%s"' % raw)
    
    local_event_RawStatus.emit(raw)
    desired = local_event_DesiredStatus.getArg()

    lastAction = (Power.getTimestamp() or date_parse('1990'))
    if (date_now().getMillis() - lastAction.getMillis()) > SYNC_PERSISTENCE * 1000:
        if _timer_sync.getInterval() != LONG_POLL:
            log(1, 'has been more than %s mins since action or just restarted, long polling now' % (SYNC_PERSISTENCE / 60.0))
            _timer_sync.setInterval(LONG_POLL)
        return
    
    if desired == None:
        return log(1, 'desired state is blank, nothing to do')
    
    if desired == raw:
        return log(1, 'desired and raw are the same (%s) so nothing to do right now' % desired)

    # They're different and not blank so sync
    global _lastSuccessfulOperation

    if (system_clock() - _lastSuccessfulOperation) < 10000:
        log(1, 'want to change status to "%s", but has been less than 10 seconds since last successful operation; will stagger' % desired)
        return
    
    if desired == 'Opened':
        log(1, 'opened')
        result = call('setpower+p61=1')
        if result == False:
            return
        _lastSuccessfulOperation = system_clock()

    elif desired == 'Closed':
        log(1, 'closed')
        result = call('setpower+p61=0')
        if result == False:
            return
        _lastSuccessfulOperation = system_clock()

_timer_sync = Timer(lambda: SyncNow.call(), LONG_POLL, 5, stopped=True)




def call(command, query=None, forceLog=False):
    global _busy

    if _busy:
        return False
    
    _busy = True

    try:
        url = 'http://%s:%s@%s/set.cmd?cmd=%s' % (param_username, param_password, param_ipAddress, command)

        if forceLog: console.info('req: url%s' % url)
        else: log(1, 'req: url%s' % url)

        try:
            timestamp = system_clock()
            resp = get_url(url, connectTimeout=5, readTimeout=5, query=query)
        except:
            e = sys.exc_info()[1]   # Tuple order is excType, value, trace
            msg = 'get_url: failed (took %0.1f) with "%s"' % ((system_clock()-timestamp)/1000.0, e)

            if forceLog: console.warn(msg)
            else:       warn(1, msg)

            return False

        log(1, 'resp: %s' % resp)
        result = html_decode(resp)

        global _lastReceive
        _lastReceive = system_clock()

        return result
    
    finally:
        _busy = False



def html_decode(text):
    clean = re.compile('<.*?>')
    return re.sub(clean, '', text)

# -->

# <--- status and error reporting

_lastReceive = 0

local_event_LastContactDetect = LocalEvent({'group': 'Status', 'order': 99999+next_seq(), 'title': 'Last contact detect', 'schema': {'type': 'string'}})

local_event_Status = LocalEvent({'group': 'Status', 'order': 99999+next_seq(), 'schema': {'type': 'object', 'properties': {
        'level': {'type': 'integer', 'order': 1},
        'message': {'type': 'string', 'order': 2}}}})
  
def statusCheck():
    diff = (system_clock() - _lastReceive)/1000.0 # in secs
  
    if diff > status_check_interval:
        previous_contact_value = local_event_LastContactDetect.getArg()
    
        if previous_contact_value == None:
            message = 'Never seen'
        else:
            previous_contact = date_parse(previous_contact_value)
            message = "Missing %s" % formatPeriod(previous_contact)
        local_event_Status.emit({'level': 2, 'message': message})
    
    else:
        local_event_LastContactDetect.emit(str(date_now()))
        local_event_Status.emit({'level': 0, 'message': 'OK'})

def formatPeriod(date, as_instant=False):
    """Takes in a date object and returns the phrase to be displayed in the dashboard"""

    if date == None:
        return 'for unknown period'
    
    time_difference = (date_now().getMillis() - date.getMillis()) / 1000 / 60 # in mins

    if time_difference < 0:
        return 'never ever'
    elif time_difference == 0:
        return 'for <1 min' if not as_instant else '<1 min ago'
    elif time_difference < 60:
        return ('for <%s mins' if not as_instant else '<%s mins ago') % time_difference
    elif time_difference < 60*24:
        return ('since %s' if not as_instant else 'at %s') % date.toString('h:mm:ss a')
    else:
        return ('since %s' if not as_instant else 'at %s') % date.toString('E d-MMM h:mm:ss a')
    
status_check_interval = 75
status_timer = Timer(statusCheck, status_check_interval)

# --->

# <!-- logging

local_event_LogLevel = LocalEvent({'group': 'Debug', 'order': 10000+next_seq(), 'desc': 'Use this to ramp up the logging (with indentation)',  
                                   'schema': {'type': 'integer'}})
# local_event_LogLevel.emit(2)

def warn(level, msg):
  if (local_event_LogLevel.getArg() or 0) >= level:
    console.warn(('  ' * level) + msg)

def log(level, msg):
  if (local_event_LogLevel.getArg() or 0) >= level:
    console.log(('  ' * level) + msg)

# --!>

# From User Manual

# Password in http:
# http://login:password@ipaddrss:port/set.cmd?cmd=command

# Read Port
# http://192.168.1.3/set.cmd?cmd=getpower
# command = getpower

# Ex. For Single Port Control On
# http://192.168.1.3/set.cmd?cmd=setpower+p61=1
# Output: P61=1
# command = setpower+61=1

# Ex. For Single Port Control Off
# http://192.168.1.3/set.cmd?cmd=setpower+p61=0
# Output:P61=0
# command = setpower+61=0
