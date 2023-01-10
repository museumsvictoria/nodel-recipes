# -*- coding: utf-8 -*-

'''
Ubiquity switch control using **Unifi-Controller API**

This is roughly written and provides read-only information for IP address information by port and by MAC. It also attempts to show when devices appear and disappear on and off the network. 

Part of it has been written using this incomplete reference - [unifi-controller/api](https://ubntwiki.com/products/software/unifi-controller/api).

It logs in using the "api" user.

See script for possible **TODOs**.

_(rev 4: added IP by port)_
'''

param_IPAddress = Parameter({ 'schema': { 'type': 'string' } })

param_Password = Parameter({ 'schema': { 'type': 'string', 'format': 'password' }})

param_IgnoreList = Parameter({'schema': { 'type': 'array', 'items': { 'type': 'object', 'properties': {
  'mac': { 'type': 'string', 'order': 1, 'required': True },
  'note': { 'type': 'string', 'order': 2 }}}}})

param_InterestingHosts = Parameter({'schema': { 'type': 'array', 'items': { 'type': 'object', 'properties': {
  'label': { 'type': 'string', 'order': 1, 'required': True },
  'mac': { 'title': 'MAC (ideally)', 'type': 'string', 'order': 2 },
  'hostname': { 'title': '(otherwise) hostname', 'type': 'string', 'order': 3 },
  'ip': { 'title': '(otherwise) IP', 'type': 'string', 'order': 4 },
  'note': { 'title': 'Any notes', 'type': 'string', 'order': 5 }}}}})

_ignoreSet_bySimpleMAC = set()

def main():
  if is_blank(param_IPAddress):
    return console.warn('No IP address specified')
  
  if is_blank(param_Password):
    return console.warn('No API password specified')
  
  # prepare the ignore set
  for item in param_IgnoreList or EMPTY:
    _ignoreSet_bySimpleMAC.add(SimpleName(item['mac']))
  
  console.info('Will connect to %s...' % param_IPAddress)
  
  local_event_AccessCookie.emit(None)
  
  timer_pollStat.start()
  
_lastSetOfDetails = set() # holds the previous details, e.g. [ '22:cc:aa... MYHOSTNAME ... ', 'ee:aa... ']

_loadedOnce = False # only want to notify when things change (init. in 'statSta' method)

_items_byID = { } # e.g. { '6131a8cc4b4aae0405d399a5': { 'id': '6131a8cc4b4aae0405d399a5', 'mac': '3e:2f:b5:28:27:c2',
                  #                                      'network': 'Security', 'sw_port': 3, 'wired_rate_mbps': ...
                  #                                      'firstSeen': '2021-01-02...', 'timestamp': '2021....'
                  #                                      'rates': (14941, 9086,1239591,2015989), # tx_packets, rx_packets, tx_bytes, rx_bytes ... }

@local_action({ 'title': 'stat/sta (List active clients)', 'group': 'Operations' })
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
      eIPbyPort = create_local_event(ipByPortKey, { 'title': 'Port %s IP' % sw_port, 'group': 'Switch %s' % sw_mac, 'order': sw_port, 'schema': { 'type': 'string' } })
    
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

local_event_AccessCookie = LocalEvent({ 'group': 'Auth', 'schema': { 'type': 'string' } })

def getCookieToken():
  url = 'https://%s%s' % (param_IPAddress, API_AUTH_PREFIX)
  post = json_encode({ 'username': 'api', 'password': param_Password })
  
  log(3, 'authenticating with url:\"%s\" post:\"%s\"' % (url, post))
  
  resp = get_url(url, post=post, contentType='application/json', fullResponse=True)
  
  if resp.statusCode != 200:
    return console.warn('Failed to login, resp code was %s' % resp.statusCode)
  
  dumpResponse('getCookieToken', resp)
  
  # e.g. TOKEN=eyJhbG...LONG...asdf; path=/; samesite=strict; secure; httponly
  cookie = resp.get('Set-cookie')[0].split(';')[0] # grab only 'TOKEN=...' part
  local_event_AccessCookie.emit(cookie)

_lastReceive = 0
  
def callAPI(apiMethod, arg=None, contentType=None, leaveAsRaw=False):
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
      
      rawResult = get_url(url, post=post, contentType=contentType)
                         #  headers = { 'Cookie': local_event_AccessCookie.getArg() })
      
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
