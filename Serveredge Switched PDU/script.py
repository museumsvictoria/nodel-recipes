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

param_ipAddress = Parameter({ "title": "IP address", "schema": {"type": "string", "required": True}})
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
  status = tree[0].text
  # emit status based on status of port 1 - should cover all models
  if status[34] == '1':
    local_event_Power.emit('On')
  elif status[34] == '0':
    local_event_Power.emit('Off')
  else:
    local_event_Error.emit()

  # EXAMPLE RESPONSES
  # ,,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,1,1,0,0,0,0,0,0,1,1,0,0,0,0,0,0,1,1,0,0,0,0,0,0,5,5,5,5,5,5,5,5,0.0,0, // ON - PORT 1 & 2
  # ,,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0,0,0,0,0,0,0,0,1,1,0,0,0,0,0,0,1,1,0,0,0,0,0,0,5,5,5,5,5,5,5,5,0.0,0, // OFF - ALL PORTS

def set_power(status):
  response = request('offs.cgi?led=110000000000000000000000') if (status == 'Off') else request('ons.cgi?led=110000000000000000000000')
  if not response:
    return
  # wait a moment for ports to update
  sleep(1)
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
  '''{"title":"PowerOn","desc":"PowerOn","group":"Outlet"}'''
  console.log('Action PowerOn requested.')
  set_power('On')

def local_action_PowerOff(arg):
  '''{"title":"PowerOff","desc":"PowerOff","group":"Outlet"}'''
  console.log('Action PowerOff requested.')
  set_power('Off')

def local_action_GetPower(arg):
  '''{"title":"GetPower","desc":"GetPower","group":"Information","order":1}'''
  print 'Action GetPower requested.'
  get_power()



### Local events this Node provides
local_event_Power = LocalEvent({'schema': {'type':'string','enum':['On','Off']}, 'group': 'Outlet', 'order': next_seq()})
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
