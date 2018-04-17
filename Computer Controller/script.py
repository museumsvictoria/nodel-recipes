'''Computer Node'''

### Libraries required by this Node
import java.lang.System
import subprocess



### Parameters used by this Node
system = java.lang.System.getProperty('os.name')
arch = java.lang.System.getProperty('sun.arch.data.model').lower()

windows = [ "Windows 7", "Windows 8", "Windows 10" ]



### Functions used by this Node
def shutdown():
  if system in windows:
    # shutdown WIN
    returncode = subprocess.call("shutdown -s -f -t 0", shell=True)
  elif(system=="Mac OS X"):
    # shutdown OSX
    # nodel process must have sudo rights to shutdown command
    returncode = subprocess.call("sudo shutdown -h -u now", shell=True)
  else:
    print 'unknown system: ' + system

def suspend():
  if system in windows:
    # suspend WIN
    returncode = subprocess.call("rundll32.exe powrprof.dll,SetSuspendState 0,1,0", shell=True)
  elif(system=="Mac OS X"):
    # suspend OSX
    # nodel process must have sudo rights to shutdown command
    returncode = subprocess.call("sudo shutdown -s now", shell=True)
  else:
    print 'unknown system: ' + system

def restart():
  if system in windows:
    # restart WIN
    returncode = subprocess.call("shutdown -r -f -t 0", shell=True)
  elif(system=="Mac OS X"):
    # restart OSX
    returncode = subprocess.call("sudo shutdown -r now", shell=True)
  else:
    print 'unknown system: ' + system

def mute():
  if system in windows:
    returncode = subprocess.call("nircmd"+arch+".exe mutesysvolume 1", shell=True)
  elif(system=="Mac OS X"):
    returncode = subprocess.call("osascript -e 'set volume output muted true'", shell=True)
  else:
    print 'unknown system: ' + system

def unmute():
  if system in windows:
    returncode = subprocess.call("nircmd"+arch+".exe mutesysvolume 0", shell=True)
    print returncode
  elif(system=="Mac OS X"):
    returncode = subprocess.call("osascript -e 'set volume output muted false'", shell=True)
  else:
    print 'unknown system: ' + system

def set_volume(vol):
  if system in windows:
    winvol = (65535/100)*vol
    returncode = subprocess.call("nircmd"+arch+".exe setsysvolume "+str(winvol), shell=True)
  elif(system=="Mac OS X"):
    returncode = subprocess.call("osascript -e 'set volume output volume "+str(vol)+"'", shell=True)
    # raspberry pi volume: "amixer cset numid=1 -- 20%"
    # returncode = subprocess.call("amixer cset numid=1 -- "+str(vol)+"%", shell=True)
  else:
    print 'unknown system: ' + system



### Local actions this Node provides
def local_action_PowerOff(arg = None):
  """{"title":"PowerOff","desc":"Turns this computer off.","group":"Power"}"""
  print 'Action PowerOff requested'
  shutdown()

def local_action_Suspend(arg = None):
  """{"title":"Suspend","desc":"Suspends this computer.","group":"Power"}"""
  print 'Action Suspend requested'
  suspend()

def local_action_Restart(arg = None):
  """{"title":"Restart","desc":"Restarts this computer.","group":"Power"}"""
  print 'Action Restart requested'
  restart()

def local_action_MuteOn(arg = None):
  """{"title":"MuteOn","desc":"Mute this computer.","group":"Volume"}"""
  print 'Action MuteOn requested'
  mute()

def local_action_MuteOff(arg = None):
  """{"title":"MuteOff","desc":"Un-mute this computer.","group":"Volume"}"""
  print 'Action MuteOff requested'
  unmute()

def local_action_SetVolume(arg = None):
  """{"title":"SetVolume","desc":"Set volume.","schema":{"title":"Drag slider to adjust level.","type":"integer","format":"range","min": 0, "max": 100,"required":"true"},"group":"Volume"}"""
  print 'Action SetVolume requested - '+str(arg)
  set_volume(arg)

DEFAULT_FREESPACEMB = 0.5
param_FreeSpaceThreshold = Parameter({'title': 'Freespace threshold (GB)', 'schema': {'type': 'integer', 'hint': DEFAULT_FREESPACEMB}})

local_event_Status = LocalEvent({'group': 'Status', 'order': next_seq(), 'schema': {'type': 'object', 'properties': {
        'level': {'type': 'integer', 'order': 1},
        'message': {'type': 'string', 'order': 2}}}})

from java.io import File

def check_status():
  # unfortunately this pulls in removable disk drives
  # roots = list(File.listRoots())
  
  roots = [File('.')] # so just using current drive instead
  
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
      
### Main
def main(arg = None):
  # Start your script here.
  print 'Nodel script started.'
