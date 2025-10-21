#!/home/nodel/myenv/bin/python

import json
import board
import busio
from adafruit_bme280 import basic as adafruit_bme280

# Initialize I2C with the Pi's default pins
i2c = busio.I2C(board.SCL, board.SDA)

# Initialize the BME280 using the default address of 0x76 (some modules use 0x77)
bme280 = adafruit_bme280.Adafruit_BME280_I2C(i2c, address=0x76)

# Optional: set local sea level pressure (in hPa) for altitude calculations
bme280.sea_level_pressure = 1013.25

# Read sensor data once
temperature_c = round(bme280.temperature, 1)  # Celsius, 1 decimal
humidity_pct = round(bme280.humidity, 1)      # %, 1 decimal
pressure_hpa = round(bme280.pressure, 1)      # hPa, 1 decimal
altitude_m = round(bme280.altitude, 2)        # Meters, 2 decimals

# Format as JSON
data = {
    "temperature_c": temperature_c,
    "humidity_pct": humidity_pct,
    "pressure_hpa": pressure_hpa,
    "altitude_m": altitude_m
}

# Print JSON and exit
print(json.dumps(data))
