import os
from pyaudio import PyAudio, paInt16
from openai import OpenAI
from geopy import distance as gd
import pyModeS as pms
from dotenv import load_dotenv
from rtlsdr import RtlSdrTcpClient

print("Calculating weather near you...", end="\r")

load_dotenv()

LATITUDE = int(os.getenv("SERVER_LATITUDE", 0))
LONGITUDE = int(os.getenv("SERVER_LONGITUDE", 0))

directions = {
    "N": 0,
    "NNE": 22.5,
    "NE": 45,
    "ENE": 67.5,
    "E": 90,
    "ESE": 112.5,
    "SE": 135,
    "SSE": 157.5,
    "S": 180,
    "SSW": 202.5,
    "SW": 225,
    "WSW": 247.5,
    "W": 270,
    "WNW": 292.5,
    "NW": 315,
    "NNW": 337.5,
}

client = OpenAI()

def get_direction(degrees):
    for direction, degree in directions.items():
        if degree - 11.25 < degrees < degree + 11.25:
            return direction


sdr = RtlSdrTcpClient(
    hostname=os.getenv("SERVER_HOST", "0.0.0.0"),
    port=int(os.getenv("SERVER_PORT", 8000)),
)

sdr.sample_rate = 2.4e6  # Hz
sdr.center_freq = 109e7  # 1090MHz, ADS-B frequency
sdr.gain = "auto"

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
    weather.append(
        (
            pms.adsb.surface_position_with_ref(msg, LATITUDE, LONGITUDE),
            alt,
            pms.commb.hum44(msg),
            pms.commb.p44(msg),
            get_direction(pms.commb.wind44(msg)[1]),
            pms.commb.wind44(msg)[0],
            temp,
        )
    )

weather.sort(
    key=lambda x: gd.distance((LATITUDE, LONGITUDE), x[0]).km, reverse=True
)

close_weather = weather[:5]
distances = [gd.distance((LATITUDE, LONGITUDE), x[0]).km for x in close_weather]

positions, alts, hums, ps, dirs, speeds, temps = zip(*close_weather)

av_alt = sum(alts) / len(alts)
av_hum = sum(hums) / len(hums)
av_p = sum(ps) / len(ps)
close_dir = dirs[0]
close_speeds= speeds[0]
av_temp = sum(temps) / len(temps)

tts_text = f"This is the weather report for your area based on data from nearby aircraft. The average humidity is {av_hum} percent. The average pressure is {av_p} hectopascals. The average wind direction at the closest source is {close_dir}, and the average wind speed at the closest source is {close_speeds} knots. The average temperature (corrected for altitude differences) is {av_temp} degrees Celsius. Please make sure to read the accuracy report to verify these results. Lower numbers often mean more accurate data."

print("Weather report (read by AI)        ")
print("-----------------------------")
print(f"Average humidity: {av_hum}%")
print(f"Average pressure: {av_p}hPa")
print(f"Wind direction (at closest source): {close_dir}")
print(f"Wind speed (at closest source): {close_speeds}kt")
print(f"Average temperature (altitude corrected): {av_temp}°C")
print("-----------------------------\n")
print("Accuracy report")
print("-----------------------------")
print(f"Average altitude: {av_alt}ft")
print(f"Average source distance: {sum(distances) / len(distances)}km")
print(f"Closest source distance: {distances[0]}km")
print("-----------------------------")

player_stream = PyAudio().open(format=paInt16, channels=1, rate=24000, output=True)
with client.audio.speech.with_streaming_response.create(
    model="tts-1",
    voice="alloy",
    input=tts_text,
) as response:
    for chunk in response.iter_bytes(chunk_size=1024):
        player_stream.write(chunk)
