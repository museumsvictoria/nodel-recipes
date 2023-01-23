# -*- coding: utf-8 -*-

'''
Ubiquiti switch control using **Unifi-Controller API**

`rev 5 2023.01.16`

This is roughly written and provides read-only information for IP address information by port and by MAC. It also attempts to show when devices appear and disappear on and off the network. 

Part of it has been written using this incomplete reference - [unifi-controller/api](https://ubntwiki.com/products/software/unifi-controller/api).

See script for possible **TODOs**.
'''

'''
rev 5 (2023.01.16) changelog:
- Specify an alternative authenticated user in the parameters.
'''

import time

DEFAULT_USERNAME = 'api'

param_IPAddress = Parameter({ 'schema': { 'type': 'string' }, 'order': next_seq() })

param_Username = Parameter({ 'schema': { 'type': 'string', 'hint': DEFAULT_USERNAME }, 'order': next_seq()})

param_Password = Parameter({ 'schema': { 'type': 'string', 'format': 'password' }, 'order': next_seq()})

param_IgnoreList = Parameter({'schema': { 'type': 'array', 'items': { 'type': 'object', 'properties': {
  'mac': { 'type': 'string', 'order': next_seq(), 'required': True },
  'note': { 'type': 'string', 'order': next_seq()}}}}})

param_InterestingHosts = Parameter({'schema': { 'type': 'array', 'items': { 'type': 'object', 'properties': {
  'label': { 'type': 'string', 'order': next_seq(), 'required': True },
  'mac': { 'title': 'MAC (ideally)', 'type': 'string', 'order': next_seq()},
  'hostname': { 'title': '(otherwise) hostname', 'type': 'string', 'order': next_seq()},
  'ip': { 'title': '(otherwise) IP', 'type': 'string', 'order': next_seq() },
  'note': { 'title': 'Any notes', 'type': 'string', 'order': next_seq()}}}}})

param_InterestingSwitches = Parameter({'schema': { 'type': 'array', 'items': { 'type': 'object', 'properties': {
  'label': { 'title': 'Label', 'type': 'string', 'order': next_seq()},
  'mac': { 'title': 'MAC', 'type': 'string', 'order': next_seq(), 'required': True},
  }}}})

_ignoreSet_bySimpleMAC = set()

# An Enum-style class for time constants
class Time:
    SECOND = 1
    MINUTE = SECOND * 60
    HOUR = MINUTE * 60
    DAY = HOUR * 24

def main():
  if is_blank(param_IPAddress):
    return console.warn('No IP address specified')
  
  if is_blank(param_Password):
    return console.warn('No API password specified')
  
  # prepare the ignore set
  for item in param_IgnoreList or EMPTY:
    _ignoreSet_bySimpleMAC.add(SimpleName(item['mac']))
  
  console.info('Will connect to %s...' % param_IPAddress)
  
  # reset access cookie
  local_event_AccessCookie.emit(None)

  # record switches managed by this unifi controller
  lookup_local_action('statDeviceBasic').call()
  
  # regularly record all clients on site
  timer_pollStat.start()

  # regularly poll all switches for details
  timer_pollSwitches.start()
  
_lastSetOfDetails = set() # holds the previous details, e.g. [ '22:cc:aa... MYHOSTNAME ... ', 'ee:aa... ']

_loadedOnce = False # only want to notify when things change (init. in 'statSta' method)

_loadedSwitchesOnce = False # only want to create the switch events once

_items_byID = { } # e.g. { '6131a8cc4b4aae0405d399a5': { 'id': '6131a8cc4b4aae0405d399a5', 'mac': '3e:2f:b5:28:27:c2',
                  #                                      'network': 'Security', 'sw_port': 3, 'wired_rate_mbps': ...
                  #                                      'firstSeen': '2021-01-02...', 'timestamp': '2021....'
                  #                                      'rates': (14941, 9086,1239591,2015989), # tx_packets, rx_packets, tx_bytes, rx_bytes ... }          

# List all switches on site by requesting an outline of all devices via 'stat/device-basic' API and parsing by device type.
@local_action({ 'title': 'stat/device-basic (List all site devices with simple keys)', 'group': 'Operations', 'order': next_seq()})
def statDeviceBasic():
  result = callAPI('s/default/stat/device-basic')  # expecting: {"meta":{"rc":"ok"},"data":[{"mac":"70:a7:41:ed:ba:25","state":1,"adopted":true,"disabled":false,"type":"udm","model":"UDMPRO","name":"Warders"}, ...
  
  global _active_switch_profiles_byMAC
  
  _active_switch_profiles_byMAC = { }
  
  for item in result['data']:
    if item.get('type') == 'usw': # only interested in switches
      _active_switch_profiles_byMAC[item.get('mac')] = item

# List of all devices on site. Can be filtered by POSTing {"macs": ["mac1", ... ]}.
@local_action({ 'title': 'stat/device (List all devices)', 'group': 'Operations', 'order': next_seq()})
def statDevice():
  log(3, 'Calling /stat/device API...')

  # if no switches specified in parameters, then get all devices
  if is_empty(param_InterestingSwitches):
    result = callAPI('s/default/stat/device')

  # otherwise, get only the specified switches
  else:
    # sanitise MAC addresses and filter out any that are not managed by this controller
    sanitised_macs = [ sanitise_mac(item['mac']) for item in param_InterestingSwitches ]
    valid_macs = [ mac for mac in sanitised_macs if mac in _active_switch_profiles_byMAC ]

    if sanitised_macs != valid_macs:
      console.warn('Some of the specified switch MAC addresses are not managed by this controller. Will ignore them.')

    result = callAPI('s/default/stat/device', arg = {"macs": valid_macs}, contentType='application/json') # arg = {"macs": ["70:a7:41:e5:d3:89"]}

  global _active_switch_state_byMAC

  _active_switch_state_byMAC = result

# Iterate over all switches and populate the switch events.
def populateSwitchEvents(arg = None):
  log(3, 'Populating switch events based of results of /stat/device API in _active_switch_state_byMAC...')
  
  # if no switches are active, then return
  global _active_switch_state_byMAC
  
  if _active_switch_state_byMAC == None:
    return
  
  # iterate over all switches
  for item in _active_switch_state_byMAC['data']:
    # example { ip=10.97.10.50, mac=70:a7:41:e5:d3:89, model=US624P, port_table=[{port_poe=true, ...}, ...], ... }
    mac = item.get('mac')
    port_table = item.get('port_table')

    # describe switch event schema
    switch_id = item.get('_id')
    switch_label = (getSwitchLabelByMAC(mac) or 'Switch')
    group_name = '%s %s - POE' % (switch_label, mac)

    # get state of ports in port table
    for port in port_table:
      port_id = port.get('port_idx')

      if port.get('port_poe') == True: # only interested in POE ports
        
        event_poeStateByPort = lookup_local_event('Switch%sPort%sPOEState' % (mac, port_id))
        event_poeInfoByPort = lookup_local_event('Switch%sPort%sPOEInfo' % (mac, port_id))

        if (event_poeInfoByPort or event_poeStateByPort) == None:
          log(5, '+local event & action for port %s poe on switch %s...' % (port_id, mac))
          
          # create local event for POE state
          event_poeStateByPort = create_poe_state_local_event(mac, port_id, group_name)

          # create local action for POE state
          create_poe_state_local_action(mac, port_id, group_name, switch_id)

          # create local event for POE info
          event_poeInfoByPort = create_poe_info_local_event(mac, port_id, group_name)


        # emit poe info
        poe_info = {'poe_enable': port.get('poe_enable'), 'poe_mode': port.get('poe_mode'), 'poe_power': port.get('poe_power')}
        event_poeInfoByPort.emitIfDifferent(poe_info)

        # emit poe state
        poe_state = 'On' if port.get('poe_mode') == 'auto' else 'Off'
        event_poeStateByPort.emitIfDifferent(poe_state)


poe_queue  = dict() # holds the queue of API PUT calls to make for POE control

def overwrite_poe(switch_id, data):
  callAPI('s/default/rest/device/%s' % (switch_id), arg = {"port_overrides":data}, contentType='application/json', method='PUT')
  log(5, "%s - %s" % (switch_id, data))

def process_poe_queue():
  for mac, switch_data in poe_queue.items():
    switch_id = switch_data['id']
    port_overwrites = switch_data['port_overwrites']
    num_port_overwrites = len(port_overwrites)
    overwrite_poe(switch_id, port_overwrites)

    poe_queue_timer.stop()

    log(2, "%s" % ('Writing %s POE port state%s to [%s].' % (num_port_overwrites, 's' if num_port_overwrites > 1 else '', mac)))
  
  timer_pollSwitches.reset()
  call(pollSwitches, delay=Time.SECOND)

poe_queue_timer = Timer(process_poe_queue, intervalInSeconds=Time.SECOND, firstDelayInSeconds=Time.SECOND, stopped=True)

# time_to_live is the time period after which an item will be removed from the dictionary (in seconds)
def remove_expired_items(time_to_live = 60):
    current_time = time.time()
    expired_items = []
    for mac, switch_data in poe_queue.items():
        if current_time - switch_data["timestamp"] > time_to_live:
            expired_items.append(mac)
    for mac in expired_items:
        poe_queue.pop(mac, None)

expiration_timer = Timer(remove_expired_items, intervalInSeconds=Time.MINUTE * 5, firstDelayInSeconds=Time.SECOND, stopped=False)

def create_poe_state_local_event(mac, port_id, group_name):
  event_name = "Switch%sPort%sPOEState" % (mac, port_id)
  return create_local_event(event_name, metadata = {'title': 'Port %s POE State' % port_id, 'group': group_name, 'order': next_seq() + port_id, 'schema': {'type': 'string', 'enum': ['On', 'Off']}})

def create_poe_state_local_action(mac, port_id, group_name, switch_id):
  action_name = "Switch%sPort%sPOEState" % (mac, port_id)
  def action_handler(arg):
    
    # queue up the API call to make later, so we don't flood the controller with API calls
    # also, the controller seems to reset the port state to the previous state if we make too many API calls too quickly
    updated_port_state = {"port_idx":port_id,"poe_mode": 'auto' if arg == 'On' else 'off'}
    timestamp = time.time()

    if mac not in poe_queue:
      poe_queue[mac] = {"id": switch_id, "port_overwrites": [], "timestamp": timestamp}
    else:
      for idx, port in enumerate(poe_queue[mac]["port_overwrites"]):
        if port['port_idx'] == port_id:
          poe_queue[mac]["port_overwrites"][idx] = updated_port_state
          poe_queue_timer.start()
          return
    poe_queue[mac]["port_overwrites"].append(updated_port_state)
    poe_queue_timer.start()

  create_local_action(action_name, handler = action_handler, metadata = {'title': 'Port %s POE State' % port_id, 'group': group_name, 'order': next_seq() + port_id, 'schema': {'type': 'string', 'enum': ['On', 'Off']}})

def create_poe_info_local_event(mac, port_id, group_name):
  event_name = "Switch%sPort%sPOEInfo" % (mac, port_id)
  event_schema = {'title': 'Info', 'type': 'object', 'properties': {
    'poe_enable': {'title': 'Active', 'type': 'boolean'},
    'poe_mode': {'title': 'Mode', 'type': 'string', 'enum': ['off', 'auto', 'passv24', 'passthrough']},
    'poe_power': {'title': 'Current (W)', 'type': 'number'}
  }}
  return create_local_event(event_name, {'title': 'Port %s POE Info' % port_id, 'group': group_name, 'order': next_seq() + port_id, 'schema': event_schema})

def getSwitchLabelByMAC(mac):
  for item in param_InterestingSwitches:
    if sanitise_mac(item.get('mac')) == mac:
      return item.get('label')

def pollSwitches():
  call(func=lambda: lookup_local_action('statDevice').call(), complete=populateSwitchEvents)

timer_pollSwitches = Timer(pollSwitches, intervalInSeconds=Time.MINUTE, firstDelayInSeconds=Time.SECOND * 10, stopped=True) # every 60 secs, first after 5,


# List all 'active' clients on the site and their associated information.
@local_action({ 'title': 'stat/sta (List active clients)', 'group': 'Operations', 'order': next_seq()})
def statSta():
  result = callAPI('s/default/stat/sta')
  
  global _loadedOnce
  
  data = result['data']
    
  now = date_now()
    
  for item in data:
    id = item.get('_id')        
    hostname = item.get('hostname')
    mac = item.get('mac')
    ip = item.get('ip')
    firstSeen = item.get('first_seen')
    if firstSeen != None:
      firstSeen = date_instant(firstSeen*1000L)
    lastSeen = item.get('last_seen')
    if lastSeen != None:
      lastSeen = date_instant(lastSeen*1000L)
    is_wired = item.get('is_wired') or False
    wired_rate_mbps = item.get('wired_rate_mbps')
    product_line = item.get('product_line')
    product_model = item.get('product_model')
    network = item.get('network')
    oui = item.get('oui')
    sw_mac = item.get('sw_mac') 
    sw_port = item.get('sw_port')
    
    wired_rx_bytes = item.get('wired-rx_bytes')
    if wired_rx_bytes:
      rates = (wired_rx_bytes or 0, item.get('wired-rx_packets') or 0, item.get('wired-tx_bytes') or 0, item.get('wired-tx_packets') or 0)
    else:
      rates = (item.get('rx_bytes') or 0, item.get('rx_packets') or 0, item.get('tx_bytes') or 0, item.get('tx_packets') or 0)
    
    # if is_blank(ip):
    #   # sometimes no IP is available, so consider this a transient condition and skip this item
    #   continue
      
    ratesDetails = ''
    prevOnline = True
    firstTime = False
      
    cache = _items_byID.get(id)
    if cache == None:
      firstTime = True
      cache = { 'firstFound': now } # NOTE: a native date object here, only used internally
      
    else:
      # check if online status flipped
      prevOnline = cache['online']
      
      # do some comparisons
      prevRates = cache['rates']
      
      timeDiff = (now.getMillis() - cache['timestamp'].getMillis()) / 1000.0 # secs
      
      dataDiff0, dataDiff1, dataDiff2, dataDiff3 = rates[0] - prevRates[0], rates[1] - prevRates[1], rates[2] - prevRates[2], rates[3] - prevRates[3]
      
      # e.g.: <5.5 Kbps rx (20 pps), <10 Kbps (30 pps) tx
      ratesDetails = '<%0.0f Kbps RX (%0.1f pps), <%0.0f Kbps RX (%0.1f pps)' % ((dataDiff0) * 8 / 1000 / timeDiff,
                                                                                 (dataDiff1) / timeDiff,
                                                                                 (dataDiff2) * 8 / 1000 / timeDiff,
                                                                                 (dataDiff3) / timeDiff)
      
    cache['id'] = id
    cache['hostname'] = hostname
    cache['mac'] = mac
    cache['ip'] = ip
    cache['firstSeen'] = firstSeen
    cache['lastSeen'] = lastSeen
    cache['wired_rate_mbps'] = wired_rate_mbps 
    cache['product_line'] = product_line
    cache['product_model'] = product_model
    cache['network'] = network
    cache['oui'] = oui
    cache['rates'] = rates
    cache['timestamp'] = now
    cache['online'] = True
    cache['is_wired'] = is_wired
    cache['sw_mac'] = sw_mac
    cache['sw_port'] = sw_port    
    
    groupTags = []
    if not is_blank(network): groupTags.append('"%s"' % network)
    if not is_blank(product_line): groupTags.append(product_line)

    titleTags = []
    if not is_blank(hostname): titleTags.append('"%s"' % hostname)
    if not is_blank(product_model): titleTags.append(product_model)
    if not is_blank(oui): titleTags.append(oui)
      
    fingerPrintTags = [] # use in 'detail' line
    if not is_blank(product_line): fingerPrintTags.append(product_line)
    if not is_blank(product_model): fingerPrintTags.append(product_model)
    if not is_blank(oui): fingerPrintTags.append(oui)
    if not is_wired: fingerPrintTags.append('Wi-Fi')
                
    # e.g. *WinDev2101Eval** • `10.0.0.213` • _00:15:5d:b2:5b:1e_ • "LAN" network • first registration Tue 17-Aug 1:16 PM • Microsof
    detail = u'*%s* • `%s` • _%s_ • "%s" network • %s • first registration %s' % (hostname or 'NO_HOSTNAME', ip or 'NO_IP', mac, network, u' • '.join(fingerPrintTags), formatPeriod(firstSeen))
    
    # previously
    # detail = u'%18s %16s %30s  %40s  %s -- %s' % (mac, ip or 'NO IP', hostname or '', 'first seen %s' % formatPeriod(firstSeen), u' • '.join(groupTags + titleTags), id)

    cache['detail'] = detail
    
    key = 'IP %s' % mac
    eIP = lookup_local_event(key)
    if eIP == None:
      # brand new so set up all related signals
      eIP = create_local_event(key, { 'title': '%s IP (%s)' % (mac, u' • '.join(titleTags)), 
                                             'group': 'Network %s' % u' • '.join(groupTags), 'order': next_seq(), 'schema': { 'type': 'string' } })
      
      eLastPresent = create_local_event('%s Last Present' % mac, { 'title': '... Last Present', 'group': 'Network %s' % u' • '.join(groupTags), 'order': next_seq(), 'schema': { 'type': 'string' } })
      eLastMissing = create_local_event('%s Last Missing' % mac, { 'title': '... Last Missing', 'group': 'Network %s' % u' • '.join(groupTags), 'order': next_seq(), 'schema': { 'type': 'string' } })
      eLastRates = create_local_event('%s Last Rates' % mac, { 'title': '... Last Rates', 'group': 'Network %s' % u' • '.join(groupTags), 'order': next_seq(), 'schema': { 'type': 'string' } })
                          
    eLastPresent = lookup_local_event('%s Last Present' % mac)
    eLastMissing = lookup_local_event('%s Last Missing' % mac)
    eLastRates = lookup_local_event('%s Last Rates' % mac)
    
    if not prevOnline:
      lastPresent = date_parse(eLastPresent.getArg())
      if SimpleName(mac) not in _ignoreSet_bySimpleMAC:
        announce(u'APPEARED! • last offline for %s • %s' % (formatMillis(now.getMillis() - lastPresent.getMillis()), detail))
    
    eIP.emit(ip)
    eLastPresent.emit(str(now))
    eLastRates.emit(ratesDetails)

    ipByPortKey = 'Switch %s Port %s IP' % (sw_mac, sw_port)
    eIPbyPort = lookup_local_event(ipByPortKey)
    if eIPbyPort == None:
      sw_label = (getSwitchLabelByMAC(sw_mac) or 'Switch')
      eIPbyPort = create_local_event(ipByPortKey, { 'title': 'Port %s IP' % sw_port, 'group': '%s %s - Client(s)' % (sw_label, sw_mac), 'order': sw_port, 'schema': { 'type': 'string' } })
    
    eIPbyPort.emit(ip)
    
    if firstTime:
      # update this _after_ creation of the signal lookups to prevent race condition elsewhere
      _items_byID[id] = cache    
  
timer_pollStat = Timer(lambda: statSta.call(), 45, 5, stopped=True) # every 45 secs, first after 5, 

def offlineScan():
  now = date_now()
  
  for id in _items_byID:
    item = _items_byID[id]
    mac = item['mac']
    lastPresent = lookup_local_event('%s Last Present' % mac).getArg()
    
    if is_blank(lastPresent):
      continue
      
    lastPresent = date_parse(lastPresent)
    
    if (now.getMillis() - lastPresent.getMillis()) > 5 * 60000: # been away for more than 5 mins
      lastMissingSignal = lookup_local_event('%s Last Missing' % mac)
      lastMissingSignalArg = lastMissingSignal.getArg()

      lastMissingSignal.emit(str(now))
      
      if lastMissingSignalArg == None: # use first found
        prevLastMissing = item['firstFound']
      else:
        prevLastMissing = date_parse(lastMissingSignalArg)
        
      if item['online']:
        # flipped to missing
        if lastMissingSignalArg != None:
          
          if SimpleName(mac) not in _ignoreSet_bySimpleMAC:
            announce(u'DISAPPEARED! • last online for %s • %s' % (formatMillis(now.getMillis() - prevLastMissing.getMillis()), item['detail']))
        
        item['online'] = False
      
timer_offlineScan = Timer(offlineScan, 120) # every 2 mins       
  
API_AUTH_PREFIX = '/api/auth/login'
API_PREFIX = '/proxy/network/api/'

@local_action({'title': 'Dump IP addresses by network', 'order': 1 })
def dumpIPsByNetwork():
  lines = [ 'IP ADDRESS DUMP' ]
  
  byNetwork = {}
  for item in _items_byID.values():
    if not item['online']:
      continue
      
    network = item['network']
    ips = byNetwork.get(network)
    
    if ips == None:
      ips = list()
      byNetwork[network] = ips
      
    ips.append(item['ip'] or 'missing')
    
  for network in byNetwork:
    ips = byNetwork[network]
    ips.sort(key=lambda ip: (ip or '').split('.'))
    lines.append('    "%s" network (%s online):' % (network, len(ips)))
    lines.append('     - %s' % ' '.join(ips))
  
  console.info('\n'.join(lines))
  
  
@local_action({'title': 'Dump host details', 'order': 2 })
def dumpHostDetails():
  lines = [ 'HOST DETAILS' ]
  
  items = _items_byID.values()
  
  items.sort(key=lambda item: (item['network'], item['is_wired'], item['online'], item['mac']))
  
  currentGroup = ''
  
  for item in items:
    network = item['network']
    is_wired = item['is_wired']
    
    if is_wired: group = '"%s" network:' % network
    else:        group = '"%s" Wi-Fi network:' % network
    
    if group != currentGroup:
      lines.append(group)
      currentGroup = group
      
    lines.append(u'%s • %s' % ('ONLINE' if item['online'] else 'OFFLINE', item['detail']))
  
  console.info('\n'.join(lines))
    
from org.nodel import SimpleName                         # mainly for MAC address comparisons                     
from org.nodel.net.NodelHTTPClient import urlEncodeQuery 
nodetoolkit.getHttpClient().setIgnoreSSL(True)           # ignores any cert issues
nodetoolkit.getHttpClient().setIgnoreRedirects(True)     # do not follow redirects (direct ops only)

local_event_AccessCookie = LocalEvent({ 'group': 'Auth', 'schema': { 'type': 'string' }, 'order': next_seq() })
local_event_CSRFToken = LocalEvent({ 'group': 'Auth', 'schema': { 'type': 'string' }, 'order': next_seq() })

def getCookieToken():
  url = 'https://%s%s' % (param_IPAddress, API_AUTH_PREFIX)
  post = json_encode({ 'username': (param_Username or DEFAULT_USERNAME), 'password': param_Password })
  
  log(3, 'authenticating with url:\"%s\" post:\"%s\"' % (url, post))
  
  resp = get_url(url, post=post, contentType='application/json', fullResponse=True)
  
  if resp.statusCode != 200:
    return console.warn('Failed to login, resp code was %s' % resp.statusCode)
  
  dumpResponse('getCookieToken', resp)
  
  # e.g. TOKEN=eyJhbG...LONG...asdf; path=/; samesite=strict; secure; httponly
  cookie = resp.get('Set-cookie')[0].split(';')[0] # grab only 'TOKEN=...' part
  local_event_AccessCookie.emit(cookie)
  
  # e.g. b5247804-7ea5-4980-b26f-55a1f45ad247 (anti-forgery token for website protection; needed for repeat requests).
  csrf_token = resp.get('X-csrf-token')[0]
  local_event_CSRFToken.emit(csrf_token)

_lastReceive = 0
  
def callAPI(apiMethod, arg=None, contentType=None, leaveAsRaw=False, method=None):
  log(2, 'callAPI:%s arg:"%s", contentType:%s' % (apiMethod, arg, contentType))
    
  if is_blank(param_IPAddress):
    console.warn('callAPI: No IP address configured or discovered; aborting')
    return
  
  # authenticate if necessary
  
  if is_blank(local_event_AccessCookie.getArg()):
    getCookieToken()
        
  url = 'https://%s%s%s' % (param_IPAddress, API_PREFIX, apiMethod)
  # e.g. https://10.0.0.1/proxy/network/api/s/default/stat/sta
  #         API_PREFIX is /proxy/network/api/ part
  
  if 'json' in (contentType or EMPTY):
    post = json_encode(arg)
  else:
    post = urlEncodeQuery(arg) if contentType == None and arg != None else None
    
  contentType = 'application/json' if contentType == None else contentType
    
  for i in ['tryOnce', 'tryAgain']:
    try:
      log(3, 'calling with url:"%s" contentType:%s' % (url, contentType))
      if post != None: log(3, '      post:"%s"' % (post))
      
      rawResult = get_url(url, method=method, post=post, contentType=contentType, headers={'Cookie': local_event_AccessCookie.getArg(), 'x-csrf-token': local_event_CSRFToken.getArg()})
      
      if leaveAsRaw:
        log(2, 'got raw result: %s%s' % (rawResult[:30], '...' if len(rawResult) > 30 else ''))
        return rawResult

      jResult = json_decode(rawResult)

      log(2, 'got result: %s' % rawResult)
      
      global _lastReceive
      lastReceive = system_clock()
      
      return jResult
      
    except:
      if i == 'tryOnce':
        console.warn('got exception, will assume auth issue (rebooted recently?) and retry just once more')
        getCookieToken()
      else:
        raise
  
  console.warn('failure: callAPI:%s arg:%s' % (apiMethod, arg))
  
                    
def announce(message):
  console.info(message)
  
  # allow for other messaging mechanisms

  
# TODO: Control POE port state:
# e.g. turning port 44 POE off
# curl 'https://10.0.0.1/proxy/network/api/s/default/rest/device/613815fd4b4aae0405d50313' \
#   -X 'PUT' \
#   -H 'authority: 10.0.0.1' \
#   -H 'accept: application/json, text/plain, */*' \
#   -H 'accept-language: en-AU,en;q=0.9' \
#   -H 'cache-control: no-cache' \
#   -H 'content-type: application/json' \
#   -H 'cookie: TOKEN=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9....yNn0._bxvqGV9yOWPoU8HJZVu632-S4cWdMaj0taAxpVWVzI' \
#   -H 'origin: https://10.0.0.1' \
#   -H 'pragma: no-cache' \
#   -H 'referer: https://10.0.0.1/network/default/devices/24:5a:4c:12:7e:0d/ports/configurations' \
#   -H 'sec-ch-ua: "Not?A_Brand";v="8", "Chromium";v="108", "Google Chrome";v="108"' \
#   -H 'sec-ch-ua-mobile: ?0' \
#   -H 'sec-ch-ua-platform: "Windows"' \
#   -H 'sec-fetch-dest: empty' \
#   -H 'sec-fetch-mode: cors' \
#   -H 'sec-fetch-site: same-origin' \
#   -H 'user-agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36' \
#   -H 'x-csrf-token: 4ae3ba8b-a2c5-4473-b0d1-15dfad062b9a' \
#   --data-raw '{"port_overrides":[{"port_idx":44,"poe_mode":"off","portconf_id":"60c5ae683e27d303a66a602c","port_security_mac_address":[],"stp_port_mode":true,"autoneg":true,"port_security_enabled":false},{"speed":100,"port_idx":29,"poe_mode":"auto","portconf_id":"60c5ae683e27d303a66a602c","full_duplex":true,"port_security_mac_address":[],"stp_port_mode":true,"autoneg":false,"port_security_enabled":false},{"port_idx":37,"poe_mode":"auto","portconf_id":"60c5ae683e27d303a66a602c","port_security_mac_address":[],"stp_port_mode":true,"autoneg":true}]}' \
#   --compressed \
#   --insecure
#
# # turning back on
#   curl 'https://10.0.0.1/proxy/network/api/s/default/stat/device/24:5a:4c:12:7e:0d' \
#   -H 'authority: 10.0.0.1' \
#   -H 'accept: application/json, text/plain, */*' \
#   -H 'accept-language: en-AU,en;q=0.9' \
#   -H 'cache-control: no-cache' \
#   -H 'cookie: TOKEN=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9....yNn0._bxvqGV9yOWPoU8HJZVu632-S4cWdMaj0taAxpVWVzI' \
#   -H 'pragma: no-cache' \
#   -H 'referer: https://10.0.0.1/network/default/devices/24:5a:4c:12:7e:0d/ports/configurations' \
#   -H 'sec-ch-ua: "Not?A_Brand";v="8", "Chromium";v="108", "Google Chrome";v="108"' \
#   -H 'sec-ch-ua-mobile: ?0' \
#   -H 'sec-ch-ua-platform: "Windows"' \
#   -H 'sec-fetch-dest: empty' \
#   -H 'sec-fetch-mode: cors' \
#   -H 'sec-fetch-site: same-origin' \
#   -H 'user-agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36' \
#   -H 'x-csrf-token: 4ae3ba8b-a2c5-4473-b0d1-15dfad062b9a' \
#   --compressed \
#   --insecure
#
# # turning back on
# curl 'https://10.0.0.1/proxy/network/api/s/default/rest/device/613815fd4b4aae0405d50313' \
#   -X 'PUT' \
#   -H 'authority: 10.0.0.1' \
#   -H 'accept: application/json, text/plain, */*' \
#   -H 'accept-language: en-AU,en;q=0.9' \
#   -H 'cache-control: no-cache' \
#   -H 'content-type: application/json' \
#   -H 'cookie: TOKEN=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9....yNn0._bxvqGV9yOWPoU8HJZVu632-S4cWdMaj0taAxpVWVzI' \
#   -H 'origin: https://10.0.0.1' \
#   -H 'pragma: no-cache' \
#   -H 'referer: https://10.0.0.1/network/default/devices/24:5a:4c:12:7e:0d/ports/configurations' \
#   -H 'sec-ch-ua: "Not?A_Brand";v="8", "Chromium";v="108", "Google Chrome";v="108"' \
#   -H 'sec-ch-ua-mobile: ?0' \
#   -H 'sec-ch-ua-platform: "Windows"' \
#   -H 'sec-fetch-dest: empty' \
#   -H 'sec-fetch-mode: cors' \
#   -H 'sec-fetch-site: same-origin' \
#   -H 'user-agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36' \
#   -H 'x-csrf-token: 4ae3ba8b-a2c5-4473-b0d1-15dfad062b9a' \
#   --data-raw '{"port_overrides":[{"port_idx":44,"poe_mode":"auto","portconf_id":"60c5ae683e27d303a66a602c","port_security_mac_address":[],"stp_port_mode":true,"autoneg":true,"port_security_enabled":false},{"speed":100,"port_idx":29,"poe_mode":"auto","portconf_id":"60c5ae683e27d303a66a602c","full_duplex":true,"port_security_mac_address":[],"stp_port_mode":true,"autoneg":false,"port_security_enabled":false},{"port_idx":37,"poe_mode":"auto","portconf_id":"60c5ae683e27d303a66a602c","port_security_mac_address":[],"stp_port_mode":true,"autoneg":true}]}' \
#   --compressed \
#   --insecure

# <!-- utilities
  
def dumpResponse(ctx, resp):
  if local_event_LogLevel.getArg() < 3:
    return
  
  console.info('%s %s %s' % (ctx, resp.statusCode, resp.reasonPhrase))
  for key in resp:
    for value in resp[key]:
      console.info('%s "%s: %s"' % (ctx, key, value))
      
def formatPeriod(dateObj):
  if dateObj == None:      return 'for unknown period'
  
  now = date_now()
  diff = (now.getMillis() - dateObj.getMillis()) / 1000 / 60 # in mins
  
  if diff == 0:             return '<1 min ago'
  elif diff < 60:           return '<%s mins ago' % diff
  elif diff < 60*24:        return '%s' % dateObj.toString('h:mm a')
  elif diff < 300*60*24:    return '%s' % dateObj.toString('E d-MMM h:mm a')
  else:                     return '%s' % dateObj.toString('E d-MMM-YY h:mm a')
  
def formatMillis(millis):
  mins = millis / 60000
  if mins == 0:        return '<1 min'
  if mins < 60:        return '<%s mins' % mins
  if mins < 60*24:     return '%sh %sm' % (mins/60, mins%60)
  else:                return '%sd %sh' % ((mins/60)/24, (mins/60)%24)

def sanitise_mac(mac_address):
    # remove all non-hex characters
    cleaned_mac = ''.join([c for c in mac_address if c in '0123456789abcdefABCDEF'])
    # add colons every 2 characters
    formatted_mac = ':'.join([cleaned_mac[i:i+2] for i in range(0, 12, 2)])
    return formatted_mac.lower()

# --!>

# <!-- logging

local_event_LogLevel = LocalEvent({'group': 'Debug', 'schema': { 'type': 'integer' }, 'order': 10000 + next_seq(),
                                   'desc': 'Use this to ramp up the logging (with indentation)' })

def warn(level, msg):
  if (local_event_LogLevel.getArg() or 0) >= level:
    console.warn(('  ' * level) + msg)

def log(level, msg):
  if (local_event_LogLevel.getArg() or 0) >= level:
    console.log(('  ' * level) + msg)

# --!>
