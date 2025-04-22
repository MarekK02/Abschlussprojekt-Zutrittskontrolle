###################################################
# Erstelldatum: 28.01.2025#########################
# letztes Änderungsdatum: 22.04.2025###############
# Programmierer: Marek Kötter##################
###################################################

###############Bibliotheken#########################
from machine import Pin, SPI, SoftI2C, I2C
from aht10 import AHT10
from bh1750 import BH1750
import network
import time
from umqtt.simple import MQTTClient
import json
from ili9341 import ILI9341, color565

##################Initialiesierung##################

# Einrichtung der I2C-Busse:
i2c = SoftI2C(scl=Pin(41), sda=Pin(42))  # I2C-Bus für den AHT10-Sensor
i2c0 = SoftI2C(scl=Pin(47), sda=Pin(21))  # I2C-Bus für den BH1750-Sensor

spi = SPI(2, baudrate=20000000, sck=Pin(13), mosi=Pin(12))
tft = ILI9341(spi, cs=Pin(9), dc=Pin(11), rst=Pin(10), w=320, h=240, rot=1)

# Display-Hintergrund initialisieren
tft.fill(color565(0, 0, 50))  # Dunkelblau

# Initialisierung der Sensoren
aht10 = AHT10(i2c)						 # AHT10: Temperatur- und Feuchtigkeitssensor
bh1750 = BH1750(0x23, i2c0)				 # BH1750: Lichtsensor

# MQTT-Konfiguration
BROKER = "192.168.1.179"  				 # IP-Adresse des Brokers (Laptop,PC)
PORT = 1883								 # Port definieren
CLIENT_ID = "KTR"						 # Client-Id vom MQTT
TOPIC = "Marek/Projekt"				 # Topic des MQTT Broker


# WLAN-Verbindung herstellen
SSID = "BZTG-IoT"						 # Wlan "Name"
PASSWORD = "WerderBremen24"				 # Passwort des Wlan


wlan = network.WLAN(network.STA_IF)		 # Wlan-Client erzeugen
wlan.active(False)						 # Wlan Reset
wlan.active(True)						 # Wlan einschalten
wlan.connect(SSID, PASSWORD)

while not wlan.isconnected():
    print("Verbinde mit WLAN...")
    time.sleep(1)

print("WLAN verbunden:", wlan.ifconfig())


#################################Ende#############################################

#############################Hauptprogramm########################################

while True:

    # Messwerte erfassen
    temp = round(aht10.temperature(),0)   # Temperatur in °C
    luft = round(aht10.humidity(), 0)     # Luftfeuchtigkeit in %
    licht = round(bh1750.measurement,0)    # Helligkeit in Lux

    # Ausgabe der Messwerte in der Konsole
    print("Temperatur (°C):", temp)
    print("Luftfeuchtigkeit (%):", luft)
    print("Helligkeit (Lux):", licht)
    
    #daten = {"Temperatur": temp,"Luftfeuchtigkeit": luft,"Helligkeit": licht}
    daten = {"Temperatur": temp,"Luftfeuchtigkeit": luft,"Helligkeit": licht,}   
    # Erstellen einer JSON-Datei
    jsons_string = json.dumps(daten)

    # MQTT-Client einrichten
    client = MQTTClient(CLIENT_ID, BROKER, PORT)
        
    # MQTT-Client Verbindung herstellen  
    client.connect()
    print("Mit MQTT-Broker verbunden.")
         
    # Nachricht an MQTT senden
    client.publish(TOPIC, jsons_string)
    print(f"Nachricht gesendet: {jsons_string}")
    
    #Löschen der alten Daten aus dem Display
    tft.fill(color565(0, 0, 50))

    # Text zeichnen
    tft.text("Temp: {} C".format(temp), 50, 40, color565(255, 255, 0))  # Gelb
    tft.text("Feuchte: {} %".format(luft), 50, 60, color565(0, 255, 255))  # Cyan
    tft.text("Licht: {} Lux".format(licht), 50, 80, color565(255, 255, 255))  # Weiß
            
    time.sleep(5)
        

