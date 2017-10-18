'''Serveredge Switched PDU Node'''

### Libraries required by this Node
import urllib2
import base64
import xml.etree.ElementTree as et
from time import sleep



### Parameters used by this Node
DEFAULT_PORT = 80
DEFAULT_USER = 'snmp'
DEFAULT_PASS = '1234'
SLOW_GET_INTERVAL = 60 * 30 # every 30 minute

lastReceive = [0] # the last time *anything* was sent to the unit

param_ipAddress = Parameter({ "title": "IP address", "schema": {"type": "string", "required": True }})
param_username = Parameter({ "title": "Username", "schema": {"type": "string", "hint": DEFAULT_USER }})
param_password = Parameter({ "title": "Password", "schema": {"type": "string", "hint": DEFAULT_PASS }})



### Functions used by this node
def request(cmd):
  try:
    request = urllib2.Request('http://' + param_ipAddress + ':' + str(DEFAULT_PORT) + '/' + cmd) # check for errors here
    base64string = base64.b64encode('%s:%s' % (param_username or DEFAULT_USER, param_password or DEFAULT_PASS))
    request.add_header("Authorization", "Basic %s" % base64string)   
    response = urllib2.urlopen(request) # and here
    # update last received
    lastReceive[0] = system_clock()
    return response
  except Exception:
    local_event_Error.emit()
    return False

def get_power():
  response = request('status.xml')
  if not response:
    return
  tree = et.parse(response).getroot()
  result = tree[0].text
  status = result[34] + result[36]

  outlets = lookup_local_event('OutletState') # is there a 2 port status
  # emit status logic based on 1 or 2 outlet models
  # 2 port model
  if outlets:
    # both ports are are on
    if status[0] == '1' and status[1] == '1':
      local_event_Power.emit('On')
      outlets.emit({'outlet1': 'On', 'outlet2': 'On'})
    # both ports are off
    elif status[0] == '0' and status[1] == '0':
      local_event_Power.emit('Off')
      outlets.emit({'outlet1': 'Off', 'outlet2': 'Off'})
    # either of the ports are reporting errors
    elif status[0] == '-1' or status[1] == '-1':
      local_event_Error.emit()
    else:
      local_event_Power.emit('Partially On')
      # just outlet 1 on
      if status[0] == '1' and not status[1] == '1':
        outlets.emit({'outlet1': 'On', 'outlet2': 'Off'})
      # just outlet 2 on
      elif status[0] == '0' and not status[1] == '0':
        outlets.emit({'outlet1': 'Off', 'outlet2': 'On'})
      # an error on either outlet
      else:
        local_event_Error.emit()
  else:
  # 1 port model
     # emit status based on status of port 1
    if status[0] == '1':
      local_event_Power.emit('On')
    elif status[0] == '0':
      local_event_Power.emit('Off')
    else:
      local_event_Error.emit()
    
  # EXAMPLE RESPONSES
  # ,,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,1,1,0,0,0,0,0,0,1,1,0,0,0,0,0,0,1,1,0,0,0,0,0,0,5,5,5,5,5,5,5,5,0.0,0, // ON - PORT 1 & 2
  # ,,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0,0,0,0,0,0,0,0,1,1,0,0,0,0,0,0,1,1,0,0,0,0,0,0,5,5,5,5,5,5,5,5,0.0,0, // OFF - ALL PORTS

def set_power(status, outlet):
  if status == 'Off':
    command = ('offs.cgi?led=%s0000000000000000000000' % outlet)
  else:
    command = ('ons.cgi?led=%s0000000000000000000000' % outlet)
  response = request(command)
  if not response:
    return
  # wait a moment for ports to update
  sleep(2)
  get_power()

lastReceive = [0]

def status_check():
  get_power()

  diff = (system_clock() - lastReceive[0])/1000.0 # (in secs)
  now = date_now()
  
  if diff > status_check_interval+15:
    previousContactValue = local_event_LastContactDetect.getArg()
    
    if previousContactValue == None:
      message = 'Always been missing.'
      
    else:
      previousContact = date_parse(previousContactValue)
      roughDiff = (now.getMillis() - previousContact.getMillis())/1000/60
      if roughDiff < 60: # less than an hour, show just minutes
        message = 'Missing for approx. %s mins' % roughDiff
      elif roughDiff < (60*24): # less than a day, concise time is useful
        message = 'Missing since %s' % previousContact.toString('h:mm:ss a')
      else: # more than a day, concise date and time
        message = 'Missing since %s' % previousContact.toString('h:mm:ss a, E d-MMM')

      local_event_Status.emit({'level': 2, 'message': message})
      
  else:
    local_event_LastContactDetect.emit(str(now))
    local_event_Status.emit({'level': 0, 'message': 'OK'})
    
status_check_interval = SLOW_GET_INTERVAL+15
status_timer = Timer(status_check, status_check_interval, 60)
status_timer.start()



# Local actions this Node provides
def local_action_PowerOn(arg):
  '''{"title":"PowerOn","desc":"PowerOn","group":"Power"}'''
  console.log('Action PowerOn requested.')
  set_power('On','11')

def local_action_PowerOff(arg):
  '''{"title":"PowerOff","desc":"PowerOff","group":"Power"}'''
  console.log('Action PowerOff requested.')
  set_power('Off','11')

def local_action_GetPower(arg):
  '''{"title":"GetPower","desc":"GetPower","group":"Information","order":1}'''
  print 'Action GetPower requested.'
  get_power()



### Local events this Node provides
local_event_Power = LocalEvent({'schema': {'type':'string','enum':['On','Off','Partially On']}, 'group': 'Power', 'order': next_seq()})
local_event_Error = LocalEvent({'group': 'Status',' order': next_seq()})
local_event_LastContactDetect = LocalEvent({'order': next_seq(), 'group': 'Information', 'title': 'Last contact', 'schema': {'type': 'string'}})
local_event_Status = LocalEvent({'order': 100, 'schema': {'type': 'object', 'title': 'Status', 'properties': {
        'level': {'type': 'integer', 'title': 'Level'},
        'message': {'type': 'string', 'title': 'Message'}
      }}})



def main(arg = None):
  print 'Rustling up your node.'

  if len((param_ipAddress or '').strip()) == 0:
    console.warn('No IP address configured; nothing to do')
    return

# <!--- dual uutlets

param_dualoutlet = Parameter({ "title": "Dual Port Controls", "schema": {"type": "boolean" }, "order": 100 })

@after_main
def expandActions():

  # add dual outlet support
  if param_dualoutlet:
    Action('Outlet1On', lambda arg: set_power('On','10'), {'title': 'Outlet1On', 'group': 'Outlet'})
    Action('Outlet2On', lambda arg: set_power('On','01'), {'title': 'Outlet2On', 'group': 'Outlet'})
    Action('Outlet1Off', lambda arg: set_power('Off','10'), {'title': 'Outlet1Off', 'group': 'Outlet'})
    Action('Outlet2Off', lambda arg: set_power('Off','01'), {'title': 'Outlet2Off', 'group': 'Outlet'})

    Event('OutletState', {'title': 'Outlets', 'group': 'Power', 'schema': {'type': 'object', 'title': 'Outlets', 'properties': {
        'outlet1': {'type':'string','enum':['On','Off'], 'title': 'Outlet 1'},
        'outlet2': {'type':'string','enum':['On','Off'], 'title': 'Outlet 2'}
      }}})

# dual outlets ---!>
