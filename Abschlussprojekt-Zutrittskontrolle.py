# Erstelldatum: 11.03.2025
# letztes Änderungsdatum: 06.05.2025
# Programmierer: Marek Kötter

# ----------- Bibliotheken einbinden -----------------------------------------------------------#

from machine import UART, Pin, SPI, SoftI2C  # Hardware-Schnittstellen des ESP32
from pyfingerprint import PyFingerprint        # Bibliothek für den Fingerabdrucksensor
from aht10 import AHT10                        # Bibliothek für den Temperatur- und Feuchtigkeitssensor
from bh1750 import BH1750                      # Bibliothek für den Helligkeitssensor
from ili9341 import ILI9341, color565          # Bibliothek für das Display
from umqtt.simple import MQTTClient            # MQTT-Kommunikation
import network                                  # WLAN-Verbindung
import time                                     # Zeitfunktionen
import json                                     # Umwandlung in JSON-Format

# ----------------- Fingerabrucksensor einrichten und Relai definiert ------------------------------------#

wak = Pin(20, Pin.IN, Pin.PULL_UP)             # WAKE-Pin für Fingerkontakt (aktiv LOW)
uart = UART(2, baudrate=57600, tx=18, rx=17, timeout=2000)  # UART-Schnittstelle für Fingerabdrucksensor
f = PyFingerprint(uart)                        # Initialisierung Fingerabdrucksensor
if not f.verifyPassword():                     # Passwortüberprüfung des Sensors
    raise Exception('Sensor-Passwort falsch!')

relay = Pin(48, Pin.OUT)                       # Ausgang für Türöffner-Relais
relay.value(0)                                 # Relais ist standardmäßig AUS
relay_on = False                               # Status-Variable für externes Schalten über MQTT

# ----------- Sensoren über I2C ansprechen --------------------------------------------------------#

i2c = SoftI2C(scl=Pin(41), sda=Pin(42))        # I2C-Bus 1 für AHT10
i2c0 = SoftI2C(scl=Pin(47), sda=Pin(21))       # I2C-Bus 2 für BH1750
aht10 = AHT10(i2c)                             
bh1750 = BH1750(0x23, i2c0)                    

# ----------- Display einrichten ------------------------------------------------------------------------#

spi = SPI(2, baudrate=20000000, sck=Pin(13), mosi=Pin(12))  # SPI-Bus für Display
tft = ILI9341(spi, cs=Pin(9), dc=Pin(11), rst=Pin(10), w=320, h=240, rot=1)  # Display-Initialisierung
tft.fill(color565(0, 0, 50))                                # Hintergrundfarbe für das Display: Dunkelblau

# ----------- WLAN & MQTT konfigurieren ------------------------------------------------------------------#

SSID = "FRITZ!Box Koetter"    # Daten für WLAN und MQTT/Topic
PASSWORD = "Koetter0702"
BROKER = "192.168.178.93"
PORT = 1883
CLIENT_ID = "Projekt Zutrittskontrolle"
TOPIC = "Zutrittskontrolle"
TOPIC_TUERSCHLOSS = "Schloss"

wlan = network.WLAN(network.STA_IF)            # WLAN-Schnittstelle aktivieren und mit Netz verbinden
wlan.active(True)
wlan.connect(SSID, PASSWORD)                  
while not wlan.isconnected():
    print("Verbinde mit WLAN...")
    time.sleep(1)
print("WLAN verbunden:", wlan.ifconfig())     

# ----------- MQTT Callback für Fernsteuerung des Relais ------------------------------------------------#

def sub_tuerschloss(topic, msg):
    global relay_on
    try:                                          # Versucht den Block auszuführen
        daten = json.loads(msg)                    # Nachricht in JSON umwandeln
        schalter = daten.get('Schalter', '').upper()  # Holt sich den Wert
        if schalter == "ON":                       # Wenn "ON", Relais aktivieren
            relay_on = True
        else:
            relay_on = False                       # Wenn "OFF" Realis deaktivieren
        print("Empfang Türschloss:", schalter)
    except Exception as e:                          # Fehlerüberprüfung
        print("Fehler in sub_tuerschloss:", e)

# ----------- MQTT-Client starten und Topic abonnieren -----------------------------------------------------#

client = MQTTClient(CLIENT_ID, BROKER, PORT)      # Verbindung mit MQTT und Ausführung von festen Funktionen
client.set_callback(sub_tuerschloss)           
client.connect()
client.subscribe(TOPIC_TUERSCHLOSS)            # Topic Subscriben

# ----------- Hauptschleife ---------------------------------------------------------------------------------#

last_measurement = 0
intervall = 5  # Alle 5 Sekunden Messdaten erfassen

print("System bereit. Warte auf Finger...")

while True:
    client.check_msg()                          # Eingehende MQTT-Nachrichten prüfen

    if relay_on:                                # Wenn extern "ON", Relais einschalten
        relay.value(1)
    else:
        relay.value(0)

#-------------------- Fingerprüfung --------------------------------------------------------------#

    if wak.value() == 0:
        print("Fingerkontakt erkannt – starte Scan...")

        try:
            if f.readImage():                    # Bild vom Finger aufnehmen
                f.convertImage(0x01)             # Bild umwandeln
                positionNumber, accuracyScore = f.searchTemplate()  # Suche im Speicher

                if positionNumber >= 0:          # Treffer gefunden
                    tft.fill(color565(0, 100, 0))  # Grün anzeigen
                    print("Finger erkannt – ID:", positionNumber)
                    relay.value(1)     # Relai zieht an
                    tft.text("Zutritt erlaubt", 105, 105, color565(255, 255, 255))
                    tft.text("ID: {}".format(positionNumber), 140, 125, color565(255, 255, 255))

                    daten = {"Zutritt": "erlaubt", "ID": positionNumber}
                    json_string = json.dumps(daten)
                    client.publish(TOPIC, json_string)  # MQTT Daten senden
                    print("MQTT:", json_string)

                    time.sleep(5)  # Relais aktiv lassen für 5 sekunden
                    relay.value(0)
                    tft.fill(color565(0, 0, 50)) # Display zurücksetzen auf Hintergrundfarbe
                else:
                    print("Falscher Finger – Zugriff verweigert.")
                    tft.fill(color565(100, 0, 0))  # Rot anzeigen
                    tft.text("Zutritt verweigert", 95, 110, color565(255, 255, 255))

                    daten = {"Zutritt": "verweigert", "ID": -1}
                    json_string = json.dumps(daten)
                    client.publish(TOPIC, json_string)  # MQTT Daten senden
                    print("MQTT:", json_string)

                    time.sleep(2)
                    tft.fill(color565(0, 0, 50))   # Display zurücksetzen auf Hintergrund
            else:
                print("Kein Bild erhalten.")
        except Exception as e:       # Automatische Fehlererkennung
            print("Scan-Fehler:", e)  

        time.sleep(2)  # 2sekunden warten bis man den Finger erneut prüfen lassen kann

# ------------ Sensorwerte erfassen und senden --------------------------------------------------------------------------------------#

    if time.time() - last_measurement >= intervall:
        try:
            temp = round(aht10.temperature(), 0)    # Sensordaten werden abgefragt
            luft = round(aht10.humidity(), 0)
            licht = round(bh1750.measurement, 0)

            daten = {"Temperatur": temp, "Luftfeuchtigkeit": luft, "Helligkeit": licht}   # MQTT Daten werden vorbereitet und gesendet
            json_string = json.dumps(daten)
            client.publish(TOPIC, json_string)
            print("MQTT:", json_string)

            tft.fill(color565(0, 0, 50))    # Hier werden die Daten Live im Display angezeigt
            tft.text("Temp: {} C".format(temp), 105, 90, color565(255, 255, 0))
            tft.text("Feuchte: {} %".format(luft), 105, 110, color565(0, 255, 255))
            tft.text("Licht: {} Lux".format(licht), 105, 130, color565(255, 255, 255))

            last_measurement = time.time() # Zeitpunkt der letzten Messung speichern
        except Exception as e:    # Automatische Fehlererkennung
            print("Sensor-/MQTT-Fehler:", e)

    time.sleep(0.1)  
