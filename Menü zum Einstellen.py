from machine import UART, Pin
from pyfingerprint import PyFingerprint
import time

# ------------------ Fingerabdrucksensor initialisieren ------------------ #
def init_sensor():
    Pin(20, Pin.OUT).value(1)  # WAKE-Pin aktivieren (Sensor aufwecken)
    uart = UART(2, baudrate=57600, tx=18, rx=17, timeout=2000)  # UART-Verbindung über TX/RX
    sensor = PyFingerprint(uart)  # Sensorobjekt erzeugen
    if not sensor.verifyPassword():  # Passwort prüfen
        raise Exception('Sensor-Passwort falsch!')
    return sensor

# ------------------ Finger registrieren (einlernen) ------------------ #
def finger_einlesen(sensor):
    print('Finger auflegen...')
    while not sensor.readImage():  # Warten bis Fingerbild aufgenommen wird
        time.sleep(0.5)
    sensor.convertImage(0x01)  # Erstes Bild konvertieren

    print('Nimm den Finger runter...')
    time.sleep(2)  # Pause damit Finger entfernt werden kann

    print('Nochmal auflegen...')
    while not sensor.readImage():  # Zweites Bild aufnehmen
        time.sleep(0.5)
    sensor.convertImage(0x02)  # Zweites Bild konvertieren

    if sensor.createTemplate():  # Template aus beiden Bildern erstellen
        pos = sensor.storeTemplate()  # Im Speicher ablegen
        print('Gespeichert auf Position:', pos)
    else:
        print('Speichern fehlgeschlagen.')

# ------------------ Finger erkennen (vergleichen) ------------------ #
def finger_erkennen(sensor):
    print('Finger auflegen...')
    while not sensor.readImage():  # Fingerbild aufnehmen
        time.sleep(0.5)
    sensor.convertImage(0x01)  # Bild konvertieren für Vergleich

    pos, score = sensor.searchTemplate()  # Suche im Speicher
    if pos >= 0:
        print(f'Erkannt! Pos: {pos}, Score: {score}')  # Treffer
    else:
        print('Nicht erkannt.')  # Kein Treffer

# ------------------ Menüstruktur zur Bedienung ------------------ #
def menu():
    try:
        sensor = init_sensor()  # Sensor starten
        print('Sensor bereit.')
    except Exception as e:
        print('Initialisierungsfehler:', e)
        return  # Bei Fehler abbrechen

    while True:
        print('\n--- Menü ---')
        print('1: Registrieren')           # Finger einlernen
        print('2: Erkennen')               # Finger prüfen
        print('3: Kommunikationstest')     # Nur Sensorverbindung checken
        print('0: Beenden')                # Beenden

        wahl = input('Auswahl: ')          # Eingabe abfragen
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
            print('Ungültige Eingabe.')    # Bei falscher Eingabe Hinweis

menu()  # Starte Menü
