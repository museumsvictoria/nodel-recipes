'''
This recipe should be run on a Windows host (server and client OS) to monitor when excessive memory or handle 
use is taking place. Normally under those conditions the system would be running much slower than it otherwise 
would be and may require intervention if runaway handle or memory use is taking place.

Sensible default options will be used however there's not necessarily a once-size fits all so you may choose to alter the default thresholds to match your system.

It works by running some special Powershell queries and periodically checking the results against the configured 
thresholds. The "Status Check" action only runs about once every 12 mins and will update the **Status** signal which can be easily dropped onto a Dashboards.

_rev. 2: prepared for public recipe_
'''

DEFAULT_MAX_HANDLES = 10000
param_MaxHandles = Parameter({ 'title': 'Max. OS handles threshold', 'schema': { 'type': 'integer', 'hint': '(default %s)' % DEFAULT_MAX_HANDLES },
                               'desc': 'The maximum OS handle count before raising a status fault.' })

DEFAULT_MAX_MEMORY = 1.8
param_MaxMemory = Parameter({ 'title': 'Max. memory threshold (GB)', 'schema': { 'type': 'number', 'hint': '(default %s)' % DEFAULT_MAX_MEMORY },
                              'desc': 'The maximum memory usage of a single process before raising a status fault.' })


# multi-line string concatenation is done using brackets here

PS_TOTAL_MEMORY = (
    'powershell -Command Get-CimInstance -ClassName Win32_ComputerSystem'
    ' | Select TotalPhysicalMemory | ConvertTo-Json').split(' ') # unit : bytes

PS_FREE_MEMORY = (
    'powershell -Command Get-CimInstance -ClassName Win32_OperatingSystem'
    ' | Select FreePhysicalMemory | ConvertTo-Json').split(' ') # unit : kilobytes

PS_PROCESS_BY_PRIVATE_BYTES = (
    'powershell -Command Get-CimInstance -ClassName Win32_PerfFormattedData_PerfProc_Process'
    ' | Sort-Object -Property PrivateBytes -Descending'
    ' | Select-Object -First 5'
    ' | Select ' "'Name','PrivateBytes', 'IDProcess', 'HandleCount' | ConvertTo-Json").split(' ') # unit : bytes

PS_PROCESS_BY_HANDLECOUNT = (
    'powershell -Command Get-CimInstance -ClassName Win32_PerfFormattedData_PerfProc_Process'
    ' | Sort-Object -Property HandleCount -Descending'
    ' | Select-Object -First 5'
    ' | Select ' "'Name','PrivateBytes', 'IDProcess', 'HandleCount' | ConvertTo-Json").split(' ') # unit : bytes

# For more detail, use:
# PS_PROCESS_BY_WORKING_SET_SIZE = (
#     'powershell -Command Get-CimInstance -ClassName Win32_Process'
#     ' | Sort-Object -Property WorkingSetSize -Descending',
#     ' | Select-Object -First 10',
#     ' | Select ' "'Name','Path','ExecutablePath','CommandLine','WorkingSetSize' | ConvertTo-Json").split(' ')  # unit : bytes

local_event_PhysicalMemory = LocalEvent({ 'schema': { 'type': 'number', 'desc': '(GB)' }})

local_event_AvailableMemory = LocalEvent({ 'schema': { 'type': 'number', 'desc': '(GB)' }})

SCHEMA_PROCINFO = { 'type': 'object', 'properties': {
                      'id': { 'type': 'string', 'order': 1 },
                      'name': { 'type': 'string', 'order': 2 },
                      'memory': { 'type': 'string', 'order': 3 },
                      'handles': { 'type': 'number', 'order': 4 }}}

local_event_MostExcessiveMemory = LocalEvent({ 'group': 'Memory', 'schema': SCHEMA_PROCINFO })

local_event_NextExcessiveMemory = LocalEvent({ 'group': 'Memory', 'schema': SCHEMA_PROCINFO })

local_event_MostExcessiveHandles = LocalEvent({ 'group': 'Handles', 'schema': SCHEMA_PROCINFO })

local_event_NextExcessiveHandles = LocalEvent({ 'group': 'Handles', 'schema': SCHEMA_PROCINFO })

local_event_Status = LocalEvent({ 'group': 'Status', 'schema': { 'type': 'object', 'properties': {
                                    'level': { 'type': 'integer', 'order': 1 },
                                    'message': { 'type': 'string', 'order': 2 }}}})

@local_action({})
def StatusCheck():
  mostMemory = local_event_MostExcessiveMemory.getArg()
  memory = mostMemory['memory']
  
  if memory > (param_MaxMemory or DEFAULT_MAX_MEMORY): # anything over ~2 GB is probably an issue
    message = '"%s#%s" is using %s GB physical memory (%s open handles)' % (mostMemory['name'], mostMemory['id'], mostMemory['memory'], mostMemory['handles'])
    local_event_Status.emit({ 'level': 1, 'message': message })
    return

  
  mostHandles = local_event_MostExcessiveHandles.getArg()
  handles = mostHandles['handles']
  
  if handles > (param_MaxHandles or DEFAULT_MAX_HANDLES): # anything over 10000 is probably an issue UPDATE: has occurred once
    message = '"%s#%s" has %s open handles (%s GB physical memory in use)' % (mostHandles['name'], mostHandles['id'], mostHandles['handles'], mostHandles['memory'])
    local_event_Status.emit({ 'level': 1, 'message': message })
    return
  
  # otherwise no resource usage issues
  local_event_Status.emit({ 'level': 0, 'message':  'OK' })

# randomly stagged all the timers
Timer(lambda: PhysicalMemory.call(), 10.0 * 60, 5)
Timer(lambda: AvailableMemory.call(), 9.0 * 60, 10)
Timer(lambda: TopProcesses.call(), 10.5 * 60, 12)
Timer(lambda: TopHandles.call(), 10.5 * 60, 12)
Timer(lambda: StatusCheck.call(), 12.5*60) # every 12 mins
    
@local_action({})
def PhysicalMemory():
    def finished(arg):
        res_code = arg.code

        if res_code != 0:
            console.error('[PhysicalMemory] process exited with code: %d' % (res_code))
            return

        log(1, 'PhysicalMemory: result: [%s]' % arg.stdout)
        
        parsed = json_decode(arg.stdout) # bytes
        
        gb = int(parsed['TotalPhysicalMemory'] / 1024.0 / 1024.0 / 1024.0 * 10.0) / 10.0
        local_event_PhysicalMemory.emit(gb)

    quick_process(PS_TOTAL_MEMORY, finished=finished)

@local_action({})
def AvailableMemory():
    def finished(arg):
        res_code = arg.code

        if res_code != 0:
            return console.error('[AvailableMemory] process exited with code: %d' % (res_code))
          
        log(1, 'AvailableMemory: result: [%s]' % arg.stdout)

        parsed = json_decode(arg.stdout)  # kilobytes
        
        gb = int(parsed['FreePhysicalMemory'] / 1024.0 / 1024.0 * 10.0) / 10.0
        local_event_AvailableMemory.emit(gb)

    quick_process(PS_FREE_MEMORY, working=None, finished=finished)

@local_action({})
def TopProcesses():
    def finished(arg):
        res_code = arg.code

        if res_code != 0:
            return console.error('[TopProcesses] process exited with code: %d' % (res_code))
          
        log(1, 'TopProcesses: result: [%s]' % arg.stdout)

        parsed = jsonDecodeByArray(arg.stdout)  # []
        
        item = parsed[1] # first one is actually _Total, but will ignore that
        
        name = item['Name']
        gb = int(item['PrivateBytes'] / 1024.0 / 1024.0 / 1024.0 * 10.0) / 10.0
        handles = item['HandleCount']
        processID = item['IDProcess']
        local_event_MostExcessiveMemory.emit({ 'id': '#%s' % processID,
                                                'handles': handles,
                                                'memory': gb,
                                                'name': name })
        
        item = parsed[2]
        
        name = item['Name']
        gb = int(item['PrivateBytes'] / 1024.0 / 1024.0 / 1024.0 * 10.0) / 10.0
        handles = item['HandleCount']
        processID = item['IDProcess']
        local_event_NextExcessiveMemory.emit({ 'id': '#%s' % processID,
                                                'handles': handles,
                                                'memory': gb,
                                                'name': name })

    quick_process(PS_PROCESS_BY_PRIVATE_BYTES, finished=finished)

@local_action({})
def TopHandles():
    def finished(arg):
        res_code = arg.code

        if res_code != 0:
            return console.error('[TopHandles] process exited with code: %d' % (res_code))
          
        log(1, 'TopHandles: result: [%s]' % arg.stdout)

        parsed = jsonDecodeByArray(arg.stdout)  # []
        
        item = parsed[1] # first one is actually _Total, but will ignore that
        
        name = item['Name']
        gb = int(item['PrivateBytes'] / 1024.0 / 1024.0 / 1024.0 * 10.0) / 10.0
        handles = item['HandleCount']
        processID = item['IDProcess']
        local_event_MostExcessiveHandles.emit({ 'id': '#%s' % processID,
                                                'handles': handles,
                                                'memory': gb,
                                                'name': name })
        
        item = parsed[2]
        
        name = item['Name']
        gb = int(item['PrivateBytes'] / 1024.0 / 1024.0 / 1024.0 * 10.0) / 10.0
        handles = item['HandleCount']
        processID = item['IDProcess']
        local_event_NextExcessiveHandles.emit({ 'id': '#%s' % processID,
                                                'handles': handles,
                                                'memory': gb,
                                                'name': name })

    quick_process(PS_PROCESS_BY_HANDLECOUNT, finished=finished)    
    
from org.nodel.reflection import Serialisation
from org.nodel.json import JSONArray

def jsonDecodeByArray(arrayString):
    return Serialisation.coerce(None, JSONArray(arrayString))

def sizeToString(size):
    if long(size) < 1000:
        return '%d bytes' % (long(size))
    elif long(size) < 1000000:
        return '%0.3f KB' % (long(size) / 1000.0)
    elif long(size) < 1000000000:
        return '%0.3f MB' % (long(size) / (1000.0 * 1000.0))
    else:
        return '%0.3f GB' % (long(size) / (1000.0 * 1000.0 * 1000.0))
      
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