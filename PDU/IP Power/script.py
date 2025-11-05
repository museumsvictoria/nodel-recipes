'''
**IP Power 9255 Pro** single port relay PDU using CGI HTTP commands

`REV 1`

**MANUAL**

* [IP Power 9255 Pro User Manual](https://s6aae352bbf6a48e4.jimcontent.com/download/version/1698733519/module/12331169760/name/9255Pro-manual.pdf)

**REVISION HISTORY**

* rev. 1: Power control (with persistent syncing) and status

'''

param_disabled = Parameter({'schema': {'type': 'boolean'}, 'desc': 'Disables this node' })

param_ipAddress = Parameter({'schema': {'type': 'string', 'hint': '(overrides binding method)'}})

param_username = Parameter({'schema': {'type': 'string', 'hint': 'username'}})

param_password = Parameter({'schema': {'type': 'string', 'hint': 'password'}})

local_event_RawStatus = LocalEvent({'group': 'Operation', 'order': next_seq(), 'schema': {'type': 'string'}}) 

local_event_DesiredStatus = LocalEvent({'group': 'Operation', 'order': next_seq(), 'schema': {'type': 'string', 'enum': ['On', 'Off']}})

local_event_Power = LocalEvent({'group': 'Power', 'order': next_seq(), 'schema': {'type': 'string', 'enum': ['On', 'Partially On', 'Off', 'Partially Off']}})

LONG_POLL           = 30    # when polling
QUICK_POLL          = 5     # when actively syncing
SYNC_PERSISTENCE    = 90    # how long to persist for when syncing desired states

import sys                  # for stacktrace summary
import re                   # for stripping html tags

def main():
    if param_disabled:
        return console.warn('Disabled! Nothing to do')

    if is_blank(param_ipAddress):
        _timer_sync.stop()
        return console.warn('IP address not specified!')
    
    console.info('Polling will start in %ss' % _timer_sync.getDelay())
    _timer_sync.start()


### Power

@local_action({ 'group': 'Power', 'schema': { 'type': 'string', 'enum': [ 'On', 'Off'] } })
def Power(arg):
    if arg in ['On', 'on', 'ON', 1, True]:
        desired = 'On'
        call('setpower+p61=1')
    elif arg in ['Off', 'off', 'OFF', 0, False]:
        desired = 'Off'
        call('setpower+p61=0')
    else:
        return console.warn('state: unknown arg "%s"' % arg)
    
    console.info('Power: %s (meaning "%s")' % (arg, desired))
    local_event_DesiredStatus.emit(desired)

    log(1, 'nudging sync timer now')
    _timer_sync.setDelayAndInterval(0.001, QUICK_POLL) # Sync now, and every 5 seconds
    #SyncNow.call()

@local_action({'group': 'Power', 'order': next_seq()})
def PowerOn(arg):
    Power.call('On')

@local_action({'group': 'Power', 'order': next_seq()})
def PowerOff(arg):
    Power.call('Off')

# When desired or raw statuses change, update the power status accordingly (using "Partially" if theres a mismatch)
@after_main
def combine_feedback():
    def handler(arg):
        desiredStatus = local_event_DesiredStatus.getArg()
        rawStatus = local_event_RawStatus.getArg()

        if desiredStatus == None:           power = rawStatus
        elif desiredStatus == rawStatus:    power = rawStatus
        else:                               power = 'Partially %s' % desiredStatus

        local_event_Power.emit(power)
    
    local_event_DesiredStatus.addEmitHandler(handler)
    local_event_RawStatus.addEmitHandler(handler)

_lastSuccessfulOperation = system_clock() - 10000

@local_action({'group': 'Operation'})
def SyncNow():
    print('Syncing now...')

    # Update raw status
    call('getpower')

    desiredStatus = local_event_DesiredStatus.getArg()
    rawStatus = local_event_RawStatus.getArg()

    # Check if it's been more than 1.5mins since last action request so polling can slow down if necessary
    lastAction = (Power.getTimestamp() or date_parse('1990'))
    if (date_now().getMillis() - lastAction.getMillis()) > SYNC_PERSISTENCE * 1000:
        if _timer_sync.getInterval() != LONG_POLL:
            log(1, 'has been more than %s mins since action or just restarted, long polling now' % (SYNC_PERSISTENCE / 60.0))
            _timer_sync.setInterval(LONG_POLL)
            return

    # Compare desired and raw states, act accordingly
    if desiredStatus == None:
        return log(1, 'desired state is blank, nothing to do')
    
    if desiredStatus == rawStatus:
        return log(1, 'desired and raw are the same (%s) so nothing to do right now' % desiredStatus)

    # Desired and raw different and not blank so sync
    global _lastSuccessfulOperation
    if (system_clock() - _lastSuccessfulOperation) < 10000:
        log(1, 'want to change status to "%s", but has been less than 10 seconds since last successful operation; will stagger' % desiredStatus)
        return
    
    if desiredStatus == 'On':
        log(1, 'calling on')
        if call('setpower+p61=1') == False:
            return
        _lastSuccessfulOperation = system_clock()

    elif desiredStatus == 'Off':
        log(1, 'calling off')
        if call('setpower+p61=0') == False:
            return
        _lastSuccessfulOperation = system_clock()

_timer_sync = Timer(lambda: SyncNow.call(), LONG_POLL, 5, stopped=True)


### HTTP Communications

_busy = False

def call(command, query=None, forceLog=False):
    # Avoid simultaneous calls by tracking one at a time
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
        result = decodeResult(resp)

        global _lastReceive
        _lastReceive = system_clock()

        return result
    
    finally:
        _busy = False

def decodeResult(result):
    # Result format: '<html>p61=1</html>'
    # State format: 'On'

    # Remove html tags
    clean = re.compile('<.*?>')
    cleaned_result = re.sub(clean, '', result)

    # Isolate power
    port, power = cleaned_result.split("=")
    power = int(power)
    if power in ['On', 'on', 'ON', 1, True]:
        state = 'On'
    elif power in ['Off', 'off', 'OFF', 0, False]:
        state = 'Off'
    else:
        return console.warn('state: unknown arg "%s"' % power)
    
    local_event_RawStatus.emit(state)

    return state


### Status and Error Reporting

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
            message = 'Missing %s' % formatPeriod(previous_contact)
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


### Logging

local_event_LogLevel = LocalEvent({'group': 'Debug', 'order': 10000+next_seq(), 'desc': 'Use this to ramp up the logging (with indentation)', 'schema': {'type': 'integer'}})

def warn(level, msg):
    if (local_event_LogLevel.getArg() or 0) >= level:
        console.warn(('  ' * level) + msg)

def log(level, msg):
    if (local_event_LogLevel.getArg() or 0) >= level:
        console.log(('  ' * level) + msg)


# From User Manual 9255Pro-manual.pdf

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