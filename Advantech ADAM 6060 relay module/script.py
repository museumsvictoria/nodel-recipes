# Copyright (c) 2014 Museum Victoria
# This software is released under the MIT license (see license.txt for details)

'''Lightweight modbus one-way control for ADAM 6060.'''

TCP_PORT = 502

DEFAULT_BOUNCE = 1.2 # the default bounce time (1200 ms)

param_ipAddress = Parameter({ "title":"IP address", "value": "192.168.100.1", "order":0, "schema": { "type":"string" }
                              "desc": "The IP address of the unit."})

param_bounceTime = Parameter({"title": "Bounce time", "order": 1, "schema": { "type": "string" },
                              "desc": "The bounce time in seconds (default %s)" % DEFAULT_BOUNCE})

param_relay1Label = Parameter({"title": "Relay 1 label", "order": 1, "schema": { "type": "string" } } )
param_relay2Label = Parameter({"title": "Relay 2 label", "order": 2, "schema": { "type": "string" } } )
param_relay3Label = Parameter({"title": "Relay 3 label", "order": 3, "schema": { "type": "string" } } )
param_relay4Label = Parameter({"title": "Relay 4 label", "order": 4, "schema": { "type": "string" } } )
param_relay5Label = Parameter({"title": "Relay 5 label", "order": 5, "schema": { "type": "string" } } )
param_relay6Label = Parameter({"title": "Relay 6 label", "order": 6, "schema": { "type": "string" } } )

def connected():
  console.info('TCP connected')

def received(data):
  # print 'received: [%s]' % data.encode('hex')
  pass

def sent(data):
  # print 'sent: [%s]' % data.encode('hex')
  pass
  
def disconnected():
  console.info('TCP disconnected')
  
def timeout():
  console.warn('TCP timeout!')

tcp = TCP(connected=connected, 
          received=received, 
          sent=sent, 
          disconnected=disconnected, 
          timeout=timeout, 
          sendDelimiters=None, 
          receiveDelimiters=None)

def main(arg = None):
  global param_bounceTime
  if param_bounceTime == None or param_bounceTime == 0:
    param_bounceTime = DEFAULT_BOUNCE

  tcp.setDest('%s:%s' % (param_ipAddress, TCP_PORT))
  
  bindRelay(1, param_relay1Label, 
               '\x00\x01\x00\x00\x00\x06\x01\x05\x00\x10\xff\x00', 
               '\x00\x02\x00\x00\x00\x06\x01\x05\x00\x10\x00\x00')
  bindRelay(2, param_relay2Label, 
               '\x00\x03\x00\x00\x00\x06\x01\x05\x00\x11\xff\x00',
               '\x00\x04\x00\x00\x00\x06\x01\x05\x00\x11\x00\x00')
  bindRelay(3, param_relay3Label, 
               '\x00\x05\x00\x00\x00\x06\x01\x05\x00\x12\xff\x00', 
               '\x00\x06\x00\x00\x00\x06\x01\x05\x00\x12\x00\x00')
  bindRelay(4, param_relay4Label, 
               '\x00\x07\x00\x00\x00\x06\x01\x05\x00\x13\xff\x00', 
               '\x00\x08\x00\x00\x00\x06\x01\x05\x00\x13\x00\x00')
  bindRelay(5, param_relay5Label, 
               '\x00\x09\x00\x00\x00\x06\x01\x05\x00\x14\xff\x00', 
               '\x00\x0a\x00\x00\x00\x06\x01\x05\x00\x14\x00\x00')
  bindRelay(6, param_relay6Label, 
               '\x00\x0b\x00\x00\x00\x06\x01\x05\x00\x15\xff\x00', 
               '\x00\x0c\x00\x00\x00\x06\x01\x05\x00\x15\x00\x00')
  
def bindRelay(num, label, onCmd, offCmd):
  defaultGroup = 'Relay %s' % num
  
  if label == None or label == '':
    group = defaultGroup
  else:
    group = label
  
  name = '"%s" state' % group
  stateEvent = Event(name, { 'group': group, 'title': name, 'order': next_seq(), 'schema': { 'type': 'boolean' } } )
  
  name = '"%s" on' % group
  onEvent = Event(name, { 'group': group, 'title': name, 'order': next_seq() } )

  name = '"%s" off' % group
  offEvent = Event(name, { 'group': group, 'title': name, 'order': next_seq() } )
  
  name = '"%s" bounce' % group
  bounceEvent = Event(name, { 'group': group, 'title': name, 'order': next_seq() } )
  
  def on(arg=None):
    tcp.send(onCmd)
    stateEvent.emit(True)
    onEvent.emit()
    
  def off(arg=None):
    tcp.send(offCmd)
    stateEvent.emit(False)
    offEvent.emit()
    
  def bounce(arg=None):
    period = DEFAULT_BOUNCE
    
    if arg != None:
      period = int(arg)
      
    # open, then close a little while later
    on()
    call(lambda: off(), delay=period)
    
  def setState(value):
    if value == None:
      console.warn('No state supplied for %s' % name)
      return
    
    lowerValue = str(value).lower()
    
    if value == True or value == 1 or lowerValue == 'true' or lowerValue == '1' or lowerValue == 'on' or lowerValue == 'closed' or lowerValue == 'close':
      on()

    elif value == False or value == 1 or lowerValue == 'false' or lowerValue == '0' or lowerValue == 'off' or lowerValue == 'opened' or lowerValue == 'open':
      off()
      
    else:
      console.warn('Unknown state supplied for %s; use true/false, 1/0, on/off, close/open' % name)
  
  defaultName = '"%s" on' % defaultGroup
  action = Action(defaultName, on, { 'title': defaultName, 'order': next_seq(), 'group': group } )
  
  defaultName = '"%s" off' % defaultGroup
  action = Action(defaultName, off, { 'title': defaultName, 'order': next_seq(), 'group': group } )
  
  defaultName = '"%s" state' % defaultGroup
  action = Action(defaultName, setState, { 'title': defaultName, 'order': next_seq(), 'group': group, 'schema': { 'type' : 'boolean' } } )
  
  defaultName = '"%s" bounce' % defaultGroup
  action = Action(defaultName, bounce, { 'title': defaultName, 'order': next_seq(), 'group': group } )

  if label != None or label != '':
    name = '"%s" on' % group
    action = Action(name, on, { 'title': name, 'order': next_seq(), 'group': group } )

    name = '"%s" off' % group
    action = Action(name, off, { 'title': name, 'order': next_seq(), 'group': group } )

    name = '"%s" state' % group
    action = Action(name, setState, { 'title': name, 'order': next_seq(), 'group': group, 'schema': { 'type' : 'boolean' } } )
    
    name = '"%s" bounce' % group
    action = Action(name, bounce, { 'title': name, 'order': next_seq(), 'group': group } )
    
  