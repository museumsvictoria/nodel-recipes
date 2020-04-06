'''
An agent with native Windows operations, tested with Windows 10 but might work on older or newer versions.

Includes:

* reboot, shutdown
* periodic screenshots
* basic volume control and of primary audio device
* audio signal metering
* CPU monitoring

'''

DEFAULT_FREESPACEMB = 0.5

param_FreeSpaceThreshold = Parameter({ 'title': 'Freespace threshold (GB)', 'schema': { 'type': 'integer', 'hint': '(default %s)' % DEFAULT_FREESPACEMB }})

# <!-- CPU

local_event_CPU = LocalEvent({ 'order': next_seq(), 'schema': { 'type': 'number' }}) # using no group so shows prominentl


# <!--- power

@local_action({ 'group':'Power', 'order': next_seq() })
def PowerOff():
    console.info('PowerOff action')
    quick_process(['shutdown', '/s', '/f', '/t', '5' , '/c', 'Nodel_SHUTDOWN_in_5_seconds...']) # not happy with spaces in args

@local_action({ 'group':'Power', 'order': next_seq() })
def Suspend():
    console.info('Suspend action')
    quick_process('rundll32.exe powrprof.dll,SetSuspendState 0,1,0'.split(' '))

@local_action({ 'group':'Power', 'order': next_seq() })
def Restart():
    console.info('Restart action')
    quick_process(['shutdown', '/r', '/f', '/t', '5' , '/c', 'Nodel_RESTART_in_5_seconds...']) # not happy with spaces in args

# --->


# <!--- mute and volume

local_event_Mute = LocalEvent({ 'group': 'Volume', 'order': next_seq(), 'schema': { 'type': 'boolean' }})

@local_action({ 'group': 'Mute', 'order': next_seq(), 'schema': { 'type': 'boolean' } })
def Mute(arg):
    console.info('Mute %s action' % arg)

    # some of this for backwards compatibility
    if arg in [ True, 1, 'On', 'ON', 'on' ]:
        state = True
    elif arg in [ False, 0, 'Off', 'OFF', 'off']:
        state = False
    else:
        console.warn('Mute: arg missing')
        return
    
    _controller.send('set-mute %s' % (1 if state else 0))

@local_action({ 'group': 'Mute', 'order': next_seq() })
def MuteOn():
    Mute.call(True)

@local_action({ 'group': 'Mute', 'order': next_seq() })
def MuteOff():
    Mute.call(False)

local_event_Volume = LocalEvent({ 'group': 'Volume', 'schema': {'type': 'number' }})

@local_action({ 'group':'Volume', 'order': next_seq(), 'schema': { 'type': 'integer', 'hint': 'Scalar (0 | 100), dB (-100 | 0)' }})
def Volume(arg):
    console.info('Volume %s action' % arg)
    
    if arg == None:
      console.warn('Volume: no arg')
      return

    decibel = lookup_local_event('Decibel').getArg()

    if decibel == False or decibel == None:
      
      if (arg < 0 or arg > 100):
          console.warn('Volume: bad arg')
          return

      _controller.send('set-volume %s' % (arg / 100.0))
      
    else:
      
      if (arg < -100 or arg > 0):
          console.warn('Volume: bad arg')
          return

      _controller.send('set-volume %s' % int(arg))

local_event_Meter = LocalEvent({ 'group': 'Volume', 'schema': {'type': 'integer' }})
local_event_Decibel = LocalEvent({ 'group': 'Volume', 'schema': {'type': 'boolean', 'title': 'Are we using dBFS for volume?' }})

@after_main
def update_audio_controller_on_event_change():

  def handler(arg):
    if arg == True:
      _controller.send('meter-type decibel')
    else:
      _controller.send('meter-type scalar')

  event = lookup_local_event('Decibel').addEmitHandler(handler)

# mute and volume --!>


# <!- status

local_event_Status = LocalEvent({ 'group': 'Status', 'order': next_seq(), 'schema': { 'type': 'object', 'properties': {
                                      'level':   {'type': 'integer', 'order': 1 },
                                      'message': {'type': 'string', 'order': 2 }}}})


# <! -- monitor disk storage

from java.io import File

def check_status():
    # unfortunately this pulls in removable disk drives
    # roots = list(File.listRoots())
    
    roots = [ File('.') ] # so just using current drive instead
    
    warnings = list()
    
    roots.sort(lambda x, y: cmp(x.getAbsolutePath(), y.getAbsolutePath()))
    
    for root in roots:
        path = root.getAbsolutePath()
        
        total = root.getTotalSpace()
        free = root.getFreeSpace()
        usable = root.getUsableSpace()
        
        if free < (param_FreeSpaceThreshold or DEFAULT_FREESPACEMB)*1024*1024*1024L:
            warnings.append('%s has less than %0.1f GB left' % (path, long(free)/1024/1024/1024))
        
    if len(warnings) > 0:
        local_event_Status.emit({'level': 2, 'message': 'Disk space is low on some drives: %s' % (','.join(warnings))})
        
    else:
        local_event_Status.emit({'level': 0, 'message': 'OK'})

Timer(check_status, 150, 10) # check status every 2.5 mins (10s first time)

# -- >

# <! -- controller

def controller_feedback(data):
    log(1, 'feedback> %s' % data)
    
    if data.startswith('//'):
      # ignore comments
      return
    
    try:
        message = json_decode(data) #except java.lang.Exception as err:
        
    except:
        console.warn('feedback problem, expected JSON data, got [%s]' % data)
        return
    
    signalName = message.get('event')
    arg = message.get('arg')
    
    signal = lookup_local_event(signalName)
    
    if not signal:
      if signalName.startswith('Screenshot'):
        # create screenshot signal dynamically
        signal = Event(signalName, { 'order': next_seq(), 'group': 'Screenshots', 'schema': { 'type': 'string', 'format': 'image' }})
        
      else:
        # unknown event
        log(1, 'ignoring unknown signal %s' % signalName)
        return
      
    signal.emit(arg)

def controller_started():
  
  if lookup_local_event('Decibel').getArg() == True:
    _controller.send('meter-type decibel')
      
  _controller.send('get-mute')
  _controller.send('get-volume')

_controller = Process([ '%s\\ComputerController.exe' % _node.getRoot().getAbsolutePath() ], 
                     stdout=controller_feedback, 
                     started=controller_started)
_controller.stop()

# compile to code on first run

import os

# 32bit path is C:\Windows\Microsoft.NET\Framework\v4.0.30319\csc.exe
# 64bit      is C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe

COMPILER_PATH = r'%s\Microsoft.NET\Framework%s\v4.0.30319\csc.exe' % (os.environ['WINDIR'], 
                                                                      '64' if '64' in os.environ['PROCESSOR_ARCHITECTURE'] else '')

@after_main
def performCompilation():
  log(1, 'Using compiler path %s' % COMPILER_PATH)
  
  quick_process([COMPILER_PATH, 'ComputerController.cs'], finished=compileComplete)
  
def compileComplete(arg):
    if arg.code != 0:
        console.error('BAD COMPILATION RESULT (code was %s)' % arg.code)
        console.error(arg.stdout)
        return
    
    # otherwise run the program
    _controller.start()
  
# -- >


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
