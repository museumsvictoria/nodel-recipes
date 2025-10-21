# Minimal Nodel recipe: poll BME280 shell script once per minute and parse JSON-like output.

CMD = ['/home/nodel/read_bme280.py']

local_event_LastReading = LocalEvent({
    'title': 'Last Reading',
    'group': 'Monitoring',
    'schema': {
        'type': 'object',
        'properties': {
            'temperature_c': {'type': 'number', 'title': 'Temperature'},
            'humidity_pct': {'type': 'number', 'title': 'Humidity'},
            'pressure_hpa': {'type': 'number', 'title': 'Pressure'},
            'altitude_m': {'type': 'number', 'title': 'Altitude'}
        }
    },
    'desc': 'Latest parsed payload from read_bme280.sh'
})

local_event_Status = LocalEvent({
    'title': 'Status',
    'group': 'Status',
    'order': 9990,
    "schema": {
        'title': 'Status',
        'type': 'object',
        'properties': {
            'level': {'title': 'Level', 'order': 1, 'type': 'integer'},
            'message': {'title': 'Message', 'order': 2, 'type': 'string'}
        }
    }
})

def poll():
    quick_process(CMD, finished=_handle_process_finished)

def _handle_process_finished(result):
    if result.code != 0:
        stderr_text = (result.stderr or '').strip()
        console.warn('read_bme280.sh exited with code %s: %s' % (result.code, stderr_text))
        local_event_Status.emit({'level': 2, 'message': 'Error: exit code %s' % result.code})
        return

    payload = (result.stdout or '').strip()

    if not payload:
        console.warn('read_bme280.sh returned no output')
        local_event_Status.emit({'level': 2, 'message': 'Error: empty output'})
        return

    data = _parse_payload(payload)
    if data is None:
        console.warn('Failed to parse payload: %s' % payload)
        local_event_Status.emit({'level': 2, 'message': 'Error: invalid payload'})
        return

    local_event_LastReading.emit(data)
    local_event_Status.emit({'level': 0, 'message': 'OK'})

def _parse_payload(payload):
    """Parse a simple JSON-like string into a Python dict (floats only)."""
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

poll_timer = Timer(poll, 10.0, True)

@after_main
def init():
    poll_timer.start()  # runs every 10 seconds
