##Dieser Code wurde nicht von mir erstellt#
from machine import UART, Pin
from pyfingerprint import PyFingerprint
import time

# Initialisierung
def init_sensor():
    Pin(20, Pin.OUT).value(1)  # WAKE-Pin aktivieren
    uart = UART(2, baudrate=57600, tx=18, rx=17, timeout=2000)
    sensor = PyFingerprint(uart)
    if not sensor.verifyPassword():
        raise Exception('Sensor-Passwort falsch!')
    return sensor

# Finger registrieren
def finger_einlesen(sensor):
    print('Finger auflegen...')
    while not sensor.readImage():
        time.sleep(0.5)
    sensor.convertImage(0x01)

    print('Nimm den Finger runter...')
    time.sleep(2)

    print('Nochmal auflegen...')
    while not sensor.readImage():
        time.sleep(0.5)
    sensor.convertImage(0x02)

    if sensor.createTemplate():
        pos = sensor.storeTemplate()
        print('Gespeichert auf Position:', pos)
    else:
        print('Speichern fehlgeschlagen.')

# Finger erkennen
def finger_erkennen(sensor):
    print('Finger auflegen...')
    while not sensor.readImage():
        time.sleep(0.5)
    sensor.convertImage(0x01)

    pos, score = sensor.searchTemplate()
    if pos >= 0:
        print(f'Erkannt! Pos: {pos}, Score: {score}')
    else:
        print('Nicht erkannt.')

# Menü
def menu():
    try:
        sensor = init_sensor()
        print('Sensor bereit.')
    except Exception as e:
        print('Initialisierungsfehler:', e)
        return

    while True:
        print('\n--- Menü ---')
        print('1: Registrieren')
        print('2: Erkennen')
        print('3: Kommunikationstest')
        print('0: Beenden')

        wahl = input('Auswahl: ')
        if wahl == '1':
            finger_einlesen(sensor)
        elif wahl == '2':
            finger_erkennen(sensor)
        elif wahl == '3':
            print('Sensor verbunden & Passwort korrekt!')
        elif wahl == '0':
            print('Tschüss, Boss.')
            break
        else:
            print('Ungültige Eingabe.')

menu()
