import urllib2

FIRMWARE_VERSIONS = ['ENTTEC DIN Ethergate Firmware V2.x']

param_version = Parameter({'title': 'Firmware version', 'schema': {'type': 'string', 'enum': FIRMWARE_VERSIONS}, 'order': next_seq()})

# An alternative to the default get_url function for V2.x firmware.
# It (strangely) uses HTTP/0.9 to communicate with the device.
def v2firmware_get_url(address):

    if param_version == FIRMWARE_VERSIONS[0]:

      # Ignore default recipe address
      address = 'http://%s:80/index.html?buffer1.cgi' % _ipAddress

      # Set the HTTP version to HTTP/0.9
      req = urllib2.Request("%s" % address)
      req.add_header("Accept", "HTTP/0.9")

      # Send the request
      response = urllib2.urlopen(req)

      # Get the response status code
      status_code = response.code
      log(2, ("Status code: %s" % status_code))

      # Get the response body
      response_body = response.read()

      # Close the connection
      response.close()

      # Return the body
      return response_body

    else:

      # Use the default recipe fucntion
      return original_get_url(address)

# Replace the default get_url function with the custom one
original_get_url = globals().get("get_url", None)
def get_url(address):
    return v2firmware_get_url(address) if param_version == FIRMWARE_VERSIONS[0] else original_get_url(address)