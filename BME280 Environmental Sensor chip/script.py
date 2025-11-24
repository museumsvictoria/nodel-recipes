'''
Minimal Nodel recipe to poll **BME280 Environment Sensor** using CPython and **adafruit_bme280** dependency.

The file `read_bme280.py` accompanies this recipe.

Make sure you follow the instructions at [Adafruit_CircuitPython_BME280](https://github.com/adafruit/Adafruit_CircuitPython_BME280) where it shows how a Python virtual environment is created.

`rev 1`

 * _r1.251021 MC:  added_

'''

CMD = ['read_bme280.py']

local_event_LastReading = LocalEvent({ 'group': 'Monitoring', 'desc': 'Latest parsed payload from read_bme280.py', 'schema': { 'type': 'object', 'properties': {
            'temperature_c': { 'type': 'number', 'title': 'Temperature' },
            'humidity_pct': { 'type': 'number', 'title': 'Humidity' },
            'pressure_hpa': { 'type': 'number', 'title': 'Pressure' },
            'altitude_m': { 'type': 'number', 'title': 'Altitude' }}}})

local_event_Status = LocalEvent({ 'group': 'Status', 'order': 9990, "schema": { 'type': 'object', 'properties': {
            'level': { 'title': 'Level', 'order': 1, 'type': 'integer' },
            'message': { 'title': 'Message', 'order': 2, 'type': 'string' }}}})

def poll():
    quick_process(CMD, finished=_handle_process_finished)

def _handle_process_finished(result):
    if result.code != 0:
        stderr_text = (result.stderr or '').strip()
        console.warn('read_bme280.py exited with code %s: %s' % (result.code, stderr_text))
        local_event_Status.emit({'level': 2, 'message': 'Exit code did not indicate success - %s' % result.code})
        return

    payload = (result.stdout or '').strip()

    if not payload:
        console.warn('read_bme280.py returned no output')
        local_event_Status.emit({'level': 2, 'message': 'Empty output'})
        return

    data = _parse_payload(payload)
    if data is None:
        console.warn('Failed to parse payload: %s' % payload)
        local_event_Status.emit({'level': 2, 'message': 'Invalid payload'})
        return

    local_event_LastReading.emit(data)
    local_event_Status.emit({'level': 0, 'message': 'OK'})

def _parse_payload(payload):
    text = payload.strip()
    if not (text.startswith('{') and text.endswith('}')):
        return None

    text = text[1:-1]  # strip braces
    parts = text.split(',')
    data = {}

    for part in parts:
        if ':' not in part:
            return None
        key_part, value_part = part.split(':', 1)
        key = key_part.strip()
        value = value_part.strip()

        if len(key) >= 2 and key[0] == '"' and key[-1] == '"':
            key = key[1:-1]
        else:
            return None

        # remove potential trailing commas or spaces
        if value.endswith(','):
            value = value[:-1].strip()

        try:
            data[key] = float(value)
        except:
            # try removing quotes (e.g. if script ever returns quoted numbers)
            if len(value) >= 2 and value[0] == '"' and value[-1] == '"':
                try:
                    data[key] = float(value[1:-1])
                except:
                    return None
            else:
                return None

    return data

poll_timer = Timer(poll, 30.0, True) # every 1/2 minute

@after_main
def init():
    poll_timer.start()
