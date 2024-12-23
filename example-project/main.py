import os
from numpy import float64
import pyModeS as pms
from dotenv import load_dotenv
from rtlsdr import RtlSdrTcpClient

load_dotenv()

LATITUDE = int(os.getenv("SERVER_LATITUDE", 0))
LONGITUDE = int(os.getenv("SERVER_LONGITUDE", 0))

directions = {"N": 0, "NNE": 22.5, "NE": 45, "ENE": 67.5, "E": 90, "ESE": 112.5, "SE": 135, "SSE": 157.5, "S": 180, "SSW": 202.5, "SW": 225, "WSW": 247.5, "W": 270, "WNW": 292.5, "NW": 315, "NNW": 337.5}

def get_direction(degrees):
    for direction, degree in directions.items():
        if degree - 11.25 < degrees < degree + 11.25:
            return direction

sdr = RtlSdrTcpClient(hostname=os.getenv("SERVER_HOST", "0.0.0.0"), port=int(os.getenv("SERVER_PORT", 8000)))

sdr.sample_rate = 2.4e6 # Hz
sdr.center_freq = 109e7 # 1090MHz, ADS-B frequency
sdr.gain = 'auto'

samples = sdr.read_samples(256)
sdr.close()

weather = []

for msg in samples:
    msg = str(msg)
    if pms.df(msg) != 17:
        continue
    pms.bds.infer(msg, mrar=True)
    alt = pms.adsb.altitude(msg) if type(pms.adsb.altitude(msg)) == float else 30000.0
    temp = pms.commb.temp44(msg)[0] + (1.98 * (alt / 1000))
    weather.append((pms.adsb.surface_position_with_ref(msg, LATITUDE, LONGITUDE), alt, pms.commb.hum44(msg), pms.commb.p44(msg), get_direction(pms.commb.wind44(msg)[1]), temp))

weather.sort(key=lambda x: x[0])

# TODO: display weather on an interactive map on a locally served webpage
