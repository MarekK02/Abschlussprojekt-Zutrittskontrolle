###################################################
# Erstelldatum: 28.01.2025#########################
# letztes Änderungsdatum: 05.05.2025###############
# Programmierer: Marek Kötter#####################
###################################################

from machine import UART, Pin, SPI, SoftI2C
from pyfingerprint import PyFingerprint
from aht10 import AHT10
from bh1750 import BH1750
from ili9341 import ILI9341, color565
from umqtt.simple import MQTTClient
import network
import time
import json

################## Initialisierung ##################

wak = Pin(20, Pin.IN, Pin.PULL_UP)
uart = UART(2, baudrate=57600, tx=18, rx=17, timeout=2000)
f = PyFingerprint(uart)
if not f.verifyPassword():
    raise Exception('Sensor-Passwort falsch!')

relay = Pin(48, Pin.OUT)
relay.value(0)
relay_on = False  # Zustand für MQTT-Steuerung

i2c = SoftI2C(scl=Pin(41), sda=Pin(42))   # AHT10
i2c0 = SoftI2C(scl=Pin(47), sda=Pin(21))  # BH1750
aht10 = AHT10(i2c)
bh1750 = BH1750(0x23, i2c0)

spi = SPI(2, baudrate=20000000, sck=Pin(13), mosi=Pin(12))
tft = ILI9341(spi, cs=Pin(9), dc=Pin(11), rst=Pin(10), w=320, h=240, rot=1)
tft.fill(color565(0, 0, 50))  # Dunkelblau

SSID = "FRITZ!Box Koetter"
PASSWORD = "Koetter0702"
BROKER = "192.168.178.93"
PORT = 1883
CLIENT_ID = "Projekt Zutrittskontrolle"
TOPIC = "Zutrittskontrolle"
TOPIC_TUERSCHLOSS = "Schloss"

wlan = network.WLAN(network.STA_IF)
wlan.active(True)
wlan.connect(SSID, PASSWORD)
while not wlan.isconnected():
    print("Verbinde mit WLAN...")
    time.sleep(1)
print("WLAN verbunden:", wlan.ifconfig())

# MQTT Callback-Funktion zur Relaissteuerung via externem Dashboard
def sub_tuerschloss(topic, msg):
    global relay_on
    try:
        daten = json.loads(msg)
        schalter = daten.get('Schalter', '').upper()
        if schalter == "ON":
            relay_on = True
        else:
            relay_on = False
        print("Empfang Türschloss:", schalter)
    except Exception as e:
        print("Fehler in sub_tuerschloss:", e)

# MQTT Client konfigurieren und abonnieren
client = MQTTClient(CLIENT_ID, BROKER, PORT)
client.set_callback(sub_tuerschloss)
client.connect()
client.subscribe(TOPIC_TUERSCHLOSS)

################## Hauptloop ##################

last_measurement = 0
intervall = 5  # Sekunden

print("System bereit. Warte auf Finger...")

while True:
    client.check_msg()  # auf eingehende MQTT-Befehle prüfen

    # Relais je nach externem Schaltbefehl setzen
    if relay_on:
        relay.value(1)
    else:
        relay.value(0)

    # --- Fingerprüfung ---
    if wak.value() == 0:
        print("Fingerkontakt erkannt – starte Scan...")

        try:
            if f.readImage():
                f.convertImage(0x01)
                positionNumber, accuracyScore = f.searchTemplate()

                if positionNumber >= 0:
                    tft.fill(color565(0, 100, 0))  # Grün
                    print("Finger erkannt – ID:", positionNumber)
                    relay.value(1)
                    tft.text("Zutritt erlaubt", 105, 105, color565(255, 255, 255))
                    tft.text("ID: {}".format(positionNumber), 140, 125, color565(255, 255, 255))

                    daten = {"Zutritt": "erlaubt", "ID": positionNumber}
                    json_string = json.dumps(daten)
                    client.publish(TOPIC, json_string)
                    print("MQTT:", json_string)

                    time.sleep(5)
                    relay.value(0)
                    tft.fill(color565(0, 0, 50))

                else:
                    print("Falscher Finger – Zugriff verweigert.")
                    tft.fill(color565(100, 0, 0))  # Rot
                    tft.text("Zutritt verweigert", 95, 110, color565(255, 255, 255))

                    daten = {"Zutritt": "verweigert", "ID": -1}
                    json_string = json.dumps(daten)
                    client.publish(TOPIC, json_string)
                    print("MQTT:", json_string)

                    time.sleep(2)
                    tft.fill(color565(0, 0, 50))
            else:
                print("Kein Bild erhalten.")
        except Exception as e:
            print("Scan-Fehler:", e)

        time.sleep(2)

    # --- Sensor-Messung alle 5 Sekunden ---
    if time.time() - last_measurement >= intervall:
        try:
            temp = round(aht10.temperature(), 0)
            luft = round(aht10.humidity(), 0)
            licht = round(bh1750.measurement, 0)

            daten = {"Temperatur": temp, "Luftfeuchtigkeit": luft, "Helligkeit": licht}
            json_string = json.dumps(daten)
            client.publish(TOPIC, json_string)
            print("MQTT:", json_string)

            tft.fill(color565(0, 0, 50))
            tft.text("Temp: {} C".format(temp), 105, 90, color565(255, 255, 0))
            tft.text("Feuchte: {} %".format(luft), 105, 110, color565(0, 255, 255))
            tft.text("Licht: {} Lux".format(licht), 105, 130, color565(255, 255, 255))

            last_measurement = time.time()
        except Exception as e:
            print("Sensor-/MQTT-Fehler:", e)

    time.sleep(0.1)
