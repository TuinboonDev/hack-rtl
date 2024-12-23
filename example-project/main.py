import os
import pyModeS
from dotenv import load_dotenv
from rtlsdr import RtlSdrTcpClient

load_dotenv()

LATITUDE = int(os.getenv("SERVER_LATITUDE", 0))
LONGITUDE = int(os.getenv("SERVER_LONGITUDE", 0))

sdr = RtlSdrTcpClient(hostname=os.getenv("SERVER_HOST", "0.0.0.0"), port=int(os.getenv("SERVER_PORT", 8000)))

sdr.sample_rate = 2.4e6 # Hz
sdr.center_freq = 109e7 # 1090MHz, ADS-B frequency
sdr.gain = 'auto'

samples = sdr.read_samples(256)
sdr.close()

weather = []

for msg in samples:
    msg = str(msg)
    pyModeS.bds.infer(msg, mrar=True)
    weather.append((pyModeS.adsb.surface_position_with_ref(msg, LATITUDE, LONGITUDE), pyModeS.adsb.altitude(msg), pyModeS.commb.hum44(msg)))
