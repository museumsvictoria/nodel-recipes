'''
**ENTTEC ODE Mk2**, DMX lighting with Artnet - [info](https://www.enttec.com/product/controls/dmx-ethernet-lighting-control/ethernet-to-dmx-interface/).

`rev 13 2023.03.06`

* loads channels buffer on first use; unused channels will be left unchanged.
* smoothing is done over 1200 ms @ 20 Hz unless overridden

This nodes allows for single and multi-channel color+ channel modes.

Channel **D** denotes a dimmer channel in use, otherwise refer to [wiki](https://github.com/museumsvictoria/nodel/wiki/lighting-front-end-element) documentation
for other channels including how the `<lighting>` frontend element can work inconjunction with this recipe.

Useful links:

* [ArtNet DMX Packet definition](https://art-net.org.uk/structure/streaming-packets/artdmx-packet-definition/)
* Example multichannel fixtures - [ShowPro Hercules](https://www.showtech.com.au/webdata/LEDSET005/downloads/Hercules%20-%20User%20Manual.pdf) and [BT320 LED Flat Par 18x 6W 4-in-1](https://www.tronios.com/fileuploader/download/download/?d=0&file=custom%2Fupload%2F151.316+BT320+LED+Flat+Par+18x6W+RGBW+4-1+V1.0.pdf)
'''

'''
CHANGELOG:

- added support for stream rate adjustments
- included custom script which support V2 firmware for the Ethergate series (which has a different endpoint and HTTP scheme)

TODO:

- discovery using MAC via broadcast UDP

'''

param_ipAddress = Parameter({ 'schema': { 'type': 'string' }})
_ipAddress = None

param_singleChannels = Parameter({ 'title': 'Single Channels', 'schema': { 'type': 'array', 'items': { 'type': 'object', 'properties': {
  'name': { 'type': 'string', 'hint': 'e.g. Light 1', 'order': next_seq() },
  'label': { 'title': 'label / group', 'type': 'string', 'hint': 'e.g. Front', 'order': next_seq() },
  'num': { 'title': 'channel num.', 'type': 'integer', 'hint': '(1 means first)' },
}}}})

param_rgbChannels = Parameter({ 'title': 'RGB+ Channels', 'schema': { 'type': 'array', 'items': { 'type': 'object', 'properties': {
  'name': { 'type': 'string', 'hint': 'e.g. Light 1', 'order': next_seq() },
  'label': { 'title': 'label / group', 'type': 'string', 'hint': 'e.g. Front', 'order': next_seq() },
  'num': { 'title': 'first channel num.', 'type': 'integer', 'hint': '(1 means first)' },
  'channels': { 'type': 'string', 'hint': '(e.g. "rgbwaiD")', 'desc': 'Refer to light manaul for applicable multi-channel modes, e.g. "w" - white, "a" - amber", "i" - infrared, "D" - dimmer, etc' }
}}}})

DEFAULT_STREAM_RATE = 20 # (Hz) e.g. 20/sec (0.05)

param_streamRate = Parameter({'title': 'Stream rate (Hz)', 'schema': {'type': 'integer', 'hint': '%s' % DEFAULT_STREAM_RATE, 'default': DEFAULT_STREAM_RATE, 'min': 1, 'max': 44}})

_rawChannels = None # must be either None or a full array of channel values

_singleChannelTargets_byChannel = { } # [ 11: ( targetValue, startTime, endTime ) ]

UDP_PORT = 6454 # is 0x1936

def main():
  if is_blank(param_ipAddress):
    return console.warn('No IP address specified')
  
  global _ipAddress
  _ipAddress = param_ipAddress
  
  # single channel faders
  for info in param_singleChannels or EMPTY:
    initSingleChannel(info)
  
  # rgb-mode channels
  for info in param_rgbChannels or EMPTY:
    init_rgbChannels(info)
      
  console.info('Raw channel values will be synced before faders will be operational...')
  timer_syncOnce.start()

  # update stream rate
  if param_streamRate:
    timer_streamer.setInterval(1.0 / param_streamRate)
  
# -->

LIGHTING_HINT = '(e.g. "hsbw(180, 0, 10, 100)", "#rrggbb", ...)' # for use in the schema

FADESMOOTH_RES = 1200 # millis
    
def initSingleChannel(info):
  name = info['name']
  label = info['label'] or 'Default group'
  
  num = info['num']
  
  ctx = 'singleChannelFader#%s' % name
  
  e = Event(name, { 'title': name, 'group': '"%s"' % label, 'order': next_seq(), 'schema': { 'type': 'number', 'format': 'range', 'min': 0, 'max': 100 }})
  
  def do_fade(target, period):
    if _rawChannels == None: return # not ready
    if target == None: return console.warn( '%s: no arg supplied' % ctx)
    if target < 0.0: return console.warn('%s: arg less than 0.0 percent' % ctx)
    if target > 100.0: return console.warn('%s: arg greater than 100.0 percent' % ctx)
    
    rawValue = int(target * 255 / 100)
    
    now = system_clock() # millis
    _singleChannelTargets_byChannel[num] = ( _rawChannels[num-1], rawValue, now, now+period )    
    
    console.info('%s: setting to %s percent over %s ms' % (ctx, target, period))
    
    e.emit(target)
    
    # streamer will then take care of sending
  
  # with default period
  Action(name, lambda arg: do_fade(arg, FADESMOOTH_RES), 
         { 'title': name, 'group': '"%s"' % label, 'order': next_seq(), 
           'schema': { 'type': 'number', 'hint': '(0.0%% - 100.0%%)', 'format': 'range', 'min': 0, 'max': 100 }})

  # with period parameter
  Action('%s Timed' % name, lambda arg: do_fade(arg['target'], arg['period']), 
         { 'title': '(timed)', 'group': '"%s"' % label, 'order': next_seq(), 
           'schema': { 'type': 'object', 'properties': {
             'target': { 'type': 'number', 'hint': '(0.0%% - 100.0%%)', 'format': 'range', 'min': 0, 'max': 100, 'order': 1 },
             'period': { 'type': 'integer', 'hint': '(in ms)', 'order': 2 }}}})
    
def init_rgbChannels(info):
  name = info['name']
  label = info['label'] or 'Default group'
  
  num = info['num']
  channels = info['channels'] # e.g. 'rgbwaiD' "w" - white, "a" - amber", "i" - infrared, "D" - dimmer, etc

  ctx = 'rgbChannels#%s' % name
    
  channels_byLetter = { }
  for i, c in enumerate(channels):
    channels_byLetter[c] = num + i
    
  hasDimmer = 'D' in channels_byLetter # has a dimmer channel
  
  e = Event(name, { 'title': name, 'group': '"%s"' % label, 'order': next_seq(), 'schema': { 'type': 'string' }})
  
  eDimmer = Event('%s Dimmer' % name, { 'title': '(dimmer)', 'group': '"%s"' % label, 'order': next_seq(), 'schema': { 'type': 'number' }})

  def do_fade(target, dimmer, period):
    if _rawChannels == None: return # not ready yet
    
    # e.g. target="hsbw(180, 0, 10, 100)" OR "#rrggbb", ...
    #      dimmer=100.0, period=2000
    
    if is_blank(target):
      return console.warn('%s: no target supplied' % ctx)

    if dimmer == None:
      dimmer = 100.0

    channelValues = into_channels_with_rgb(target)
    
    # will now have _at least_ { 'r': ..., 'g': ..., 'b': .... } in percentages 0.0 - 100.0,
    # needs to be in 0 - 255
    raw_byLetter = { }
    logParts = []

    for c in channelValues: # only deal with channels that are referenced in target
      if c in channels_byLetter: # ...and defined
        raw = round(channelValues[c] / 100.0 * 255 * dimmer / 100.0)
        raw_byLetter[c] = int(raw)
        # e.g. when static: r = round(channelValues['r'] / 100.0 * 255 * dimmer / 100.0)
        logParts.append('%s:%s' % (c, raw)) # e.g. "r:255"
    
    now = system_clock() # millis
    endTime = now + period
    
    for c in channels:
      if c not in raw_byLetter:
        continue

      xChan = channels_byLetter[c]
      startValue = _rawChannels[xChan-1]
      targetValue = raw_byLetter[c]
      
      _singleChannelTargets_byChannel[xChan] = ( startValue, targetValue, now, endTime )
    
    log(1, '%s: set to %s dimmer:%s over %s ms' % (ctx, ' '.join(logParts), dimmer, period))
    
    e.emit(target) # ...and streamer will then take care of sending...
  
  Action(name, lambda arg: do_fade(arg, None, FADESMOOTH_RES), { 'title': name, 'group': '"%s"' % label, 'order': next_seq(), 'schema': { 'type': 'string', 'hint': LIGHTING_HINT }})

  Action('%s Timed' % name, lambda arg: do_fade(arg['target'], eDimmer.getArg(), arg['period']), 
         { 'title': '(timed)', 'group': '"%s"' % label, 'order': next_seq(), 'schema': { 'type': 'object', 'properties': {
             'target': { 'type': 'string', 'hint': LIGHTING_HINT, 'order': 1 },
             'period': { 'type': 'integer', 'hint': '(in ms)', 'order': 2 }}}})
  
  def handle_dimmer(level, period):
    if _rawChannels == None: return # not ready
    if level == None: return console.warn( '%s: no arg supplied' % ctx)
    if level < 0.0: return console.warn('%s: arg less than 0.0 percent' % ctx)
    if level > 100.0: return console.warn('%s: arg greater than 100.0 percent' % ctx)

    eDimmer.emit(level)
      
    if not hasDimmer:
      # fade using pseudo dimmer
      target = e.getArg() # use existing colour (channel) target
      do_fade(target, level, period)
      
    else:
      # use actual dimmer channel
      rawValue = int(level * 255 / 100)
      now = system_clock() # millis
      dChan = channels_byLetter['D']
      _singleChannelTargets_byChannel[dChan] = ( _rawChannels[dChan-1], rawValue, now, now+period )

  Action('%s Dimmer' % name, lambda arg: handle_dimmer(arg, FADESMOOTH_RES), 
         { 'title': '(dimmer)', 'group': '"%s"' % label, 'order': next_seq(), 'schema': { 'type': 'number', 'hint': '(0.0%% - 100.0%%)', 'format': 'range', 'min': 0, 'max': 100, 'order': 1 }})

  Action('%s Dimmer Timed' % name, lambda arg: handle_dimmer(arg['level'], arg['period']), { 'title': '(dimmer timed)', 'group': '"%s"' % label, 'order': next_seq(), 'schema': { 'type': 'object', 'properties': {
           'level': { 'type': 'number', 'hint': '(0.0%% - 100.0%%)', 'format': 'range', 'min': 0, 'max': 100, 'order': 1 },
           'period': { 'type': 'integer', 'hint': '(in ms)', 'order': 2 }}}})

  
def stream():
  if _rawChannels == None:
    # have not synced buffer
    return
 
  # _singleChannelTargets_byChannel[num] = ( rawValue, now, now+FADESMOOTH_RES )    
  # _rawChannels[num-1] = rawValue
  
  now = system_clock() # millis  
  
  # deal with targets
  doneWith = list()
  
  for chan in _singleChannelTargets_byChannel:
    current = _rawChannels[chan-1] # e.g. going from 200 to 255
    startValue, target, startTime, endTime = _singleChannelTargets_byChannel[chan]
    
    # range
    diffValue = target - startValue
    
    # percentage time into operation
    #                         progress / total time
    totalTime = (endTime - startTime)
    if totalTime == 0: percTime = 1.0
    else:              percTime = (now - startTime) * 1.0 / totalTime
    
    if percTime >= 1.0:
      newValue = target
    else:
      newValue = int(startValue + diffValue * percTime)
    
    if current != target:
      log(2, 'autoramping: diffValue:%s newValue:%s perc:%s' % (diffValue, newValue, percTime))
    
    _rawChannels[chan-1] = newValue
  
  sendDmx(0, 0, _rawChannels)

timer_streamer = Timer(stream, intervalInSeconds=(1.0 / DEFAULT_STREAM_RATE), firstDelayInSeconds=5)

# <!-- protocol & operation

# initialised the channels from the device
@local_action({})
def syncChannels():
  url = 'http://%s:80/buffer1.cgi' % _ipAddress  
  result = get_url(url)
  
  # e.g. result: row1=0,0,0,0,0,0,0,0
  #              row2=0,0,0,0,0,0,0,0
  #              ...
  #              row63=0,0,0,0,0,0,0,0
  #              row64=0,0,0,0,0,0,0,0
  
  channels = list()
  lines = result.splitlines()
  for line in lines:
    parts = line.split('=')
    if not parts[0].startswith('row'):
      continue
      
    values = parts[1].split(',')
    for v in values:
      channels.append(int(v))
  
  global _rawChannels
  
  if _rawChannels == None:
    # this is first time so ensure data consistency
    rawChannels = [ v for v in channels ]
    _rawChannels = rawChannels
    
  else:
    for i, v in enumerate(channels):
      _rawChannels[i] = v
    
  console.info('syncChannels: channel buffer has been synced; got %s values (%s rows)' % (len(channels), len(lines)))
  
def syncOnce():
  if _rawChannels != None:
    # already synced
    timer_syncOnce.stop()
    return
  
  syncChannels.call()
  
timer_syncOnce = Timer(syncOnce, 30, 5, stopped=True) # every 30 secs, first after 5
   
_seq = 0

P_ArtDMX = '0050' # hex

def sendDmx(subnet, universe, channels):
  global _seq
  
  p = list()
  p.append('Art-Net'.encode('hex') + '00')
  p.append(P_ArtDMX)
  p.append(toU16bits(14).encode('hex'))
  p.append(toU8bits(_seq).encode('hex'))
  p.append('00') # "physical" not sure what this is
  p.append(toU16bits(universe).encode('hex'))
  
  count = len(channels)
  p.append(toU16bits(count).encode('hex'))
  
  for b in channels:
    p.append(toU8bits(b).encode('hex'))
  
  _seq = (_seq + 1) % 256
  udp.sendTo('%s:%s' % (_ipAddress, UDP_PORT), ''.join(p).decode('hex'))

def udp_received(src, data):
  hexData = data.encode('hex')
  log(3, 'udp_recv from:%s data:[%s]' % (src, hexData))

def udp_sent(data):
  log(3, 'udp_sent data:[%s]' % data.encode('hex'))
                 
udp = UDP(received=udp_received,
          sent=udp_sent,
          ready=lambda: console.info('udp_ready'))                 

# protocol --!>

import colorsys

def into_channels_with_rgb(s):
  """Takes:
      * #RxGxBx
      * rbg...(R, G, B, ...), 
      * hsb...(H, S, B, ...), hsv...(H, S, V, ...)
      * hsl...(H, S, L, ...)

     Returns:
      * { 'r': A, 'g': G, 'b': B, ...}

     e.g. "hsba(360, 100, 100, 100)" => { 'r': 100, 'g': 0, 'b': 0, 'a': 100 }
  """
  if s == None:
    raise Exception('No color string provided')

  if s.startswith('#'):
    return { 'r': int(target[1:3], 16) / 255.0, # as perc
             'g': int(target[3:5], 16) / 255.0, 
             'b': int(target[5:7], 16) / 255.0 }

  lBracket, rBracket = s.find('('), s.rfind(')')

  if lBracket < 0 or rBracket < 0:
      raise Exception('No brackets present in color string')

  leftChars = s[:lBracket]           # e.g. "rgba"
  rightPart = s[lBracket+1:rBracket] # e.g. "360, 100, 100, 100"
  rightNums = [ float(p) for p in rightPart.split(',') ]

  result = dict(zip(leftChars, rightNums)) # { 'r': 100, 'g': 0, 'b': 0, 'a': 100 } i.e. it includes rgb and other channels

  if leftChars.startswith('rgb'):
    # no colour conversion necessary, return all channels
    return result

  if leftChars[0] == 'h':
    # HUE is present, needs to be converted into 0 - 1.0  
    hPerc = (rightNums[0] % 360) / 360
    
  if leftChars.startswith('hsb') or leftChars.startswith('hsv'):
    rgb = colorsys.hsv_to_rgb(hPerc, rightNums[1] / 100.0, rightNums[2] / 100.0)

  elif leftChars.startswith('hsl'): # note 2nd and 3rd indices swapped to match function, order convention can be different
    rgb = colorsys.rgb_to_hls(hPerc, rightNums[2] / 100.0, rightNums[1] / 100.0)

  elif leftChars.startswith('hls'): # same as above, 
    rgb = colorsys.rgb_to_hls(hPerc, rightNums[1] / 100.0, rightNums[2] / 100.0)

  else:
    raise Exception('Color string format not rgb, hsb/hsv or hsl/hls')
    
  if rgb == None:
    raise Exception('Color parameters could not be converted properly')

  # add the r, g, b channels
  result['r'] = rgb[0] * 100.0
  result['g'] = rgb[1] * 100.0
  result['b'] = rgb[2] * 100.0
  return result
    
# <!-- big endien binary convenience functions
    
def read8(data, i):    
    return ord(data[i])

def read16(data, i):
    return ord(data[i+1]) + (ord(data[i]) << 8)

def read32(data, i):
    return (ord(data[i]) << 24) + (ord(data[i+1]) << 16) + (ord(data[i+2]) << 8) + ord(data[i+3])
  
def toU8bits(b):
    return chr(b & 0xff)
    
def toU16bits(i):
    return '%s%s' % (chr((i >> 8) & 0xff), chr(i & 0xff))
  
def toU32bits(i):
    return '%s%s%s%s' % (chr((i >> 24) & 0xff), chr((i >> 16) & 0xff), chr((i >> 8) & 0xff), chr(i & 0xff))
                       
def formatHexToBytes(hex):
  return ':'.join(hex[i:i+2] for i in range(0,len(hex),2))

# --!>

# example
#

# for this example:
# name: ODE Mk2
# arp Internet Address      Physical Address      Type
#     136.154.24.246        00-50-c2-08-00-8d     dynamic

# Packet examples
# Poll send PORT 3333
#   0000   45 53 50 50 01                                    ESPP.

# Poll receive:
#   0000   45 53 50 52[00 50 c2 08 00 8d]00 11 0b 03 4f 44   ESPR.P........OD
#   0010   45 20 4d 6b 32 00 00 00 00 00 ff 03 2f 9a 02 00   E Mk2......./...
#   0020   00 88 9a 18 f6                                    .....

# some other packet that arrived:
#   0000   01 00 5e 7f ff fa 00 50 c2 08 00 8d 08 00 45 00   ..^....P......E.
#   0010   01 64 fd b2 00 00 20 11 0a 4c 88 9a 18 f6 ef ff   .d.... ..L......
#   0020   ff fa 04 02 07 6e 01 50 a3 dc 4e 4f 54 49 46 59   .....n.P..NOTIFY
#   0030   20 41 4c 49 56 45 20 53 44 44 50 2f 31 2e 30 0d    ALIVE SDDP/1.0.
#   0040   0a 46 72 6f 6d 3a 20 22 31 33 36 2e 31 35 34 2e   .From: "136.154.
#   0050   32 34 2e 32 34 36 3a 31 39 30 32 22 0d 0a 48 6f   24.246:1902"..Ho
#   0060   73 74 3a 20 22 4f 44 45 2d 30 30 35 30 43 32 30   st: "ODE-0050C20
#   0070   38 30 30 38 44 22 0d 0a 4d 61 78 2d 41 67 65 3a   8008D"..Max-Age:
#   0080   20 31 38 30 30 0d 0a 54 79 70 65 3a 20 22 65 6e    1800..Type: "en
#   0090   74 74 65 63 3a 4f 44 45 22 0d 0a 50 72 69 6d 61   ttec:ODE"..Prima
#   00a0   72 79 2d 50 72 6f 78 79 3a 20 22 45 78 74 72 61   ry-Proxy: "Extra
#   00b0   56 65 67 5f 41 72 74 4e 65 74 5f 49 50 5f 43 6c   Veg_ArtNet_IP_Cl
#   00c0   6f 75 64 22 0d 0a 50 72 6f 78 69 65 73 3a 20 22   oud"..Proxies: "
#   00d0   45 78 74 72 61 56 65 67 5f 41 72 74 4e 65 74 5f   ExtraVeg_ArtNet_
#   00e0   49 50 5f 43 6c 6f 75 64 22 0d 0a 4d 61 6e 75 66   IP_Cloud"..Manuf
#   00f0   61 63 74 75 72 65 72 3a 20 22 45 6e 74 74 65 63   acturer: "Enttec
#   0100   22 0d 0a 4d 6f 64 65 6c 3a 20 22 45 6e 74 74 65   "..Model: "Entte
#   0110   63 20 4f 44 45 22 0d 0a 44 72 69 76 65 72 3a 20   c ODE"..Driver: 
#   0120   22 45 78 74 72 61 56 65 67 5f 41 72 74 4e 65 74   "ExtraVeg_ArtNet
#   0130   5f 49 50 5f 43 6c 6f 75 64 2e 63 34 7a 22 0d 0a   _IP_Cloud.c4z"..
#   0140   43 6f 6e 66 69 67 2d 55 52 4c 3a 20 22 68 74 74   Config-URL: "htt
#   0150   70 3a 2f 2f 31 33 36 2e 31 35 34 2e 32 35 2e 32   p://136.154.25.2
#   0160   30 2f 73 65 74 74 69 6e 67 73 2e 68 74 6d 6c 22   0/settings.html"
#   0170   0d 0a                                             ..



                       
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