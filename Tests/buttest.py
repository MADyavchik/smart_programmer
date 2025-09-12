import RPi.GPIO as GPIO
import time

buttons = [5, 6, 13, 19, 26]

def button_callback(channel):
    print(f"Нажата кнопка на GPIO{channel}")

GPIO.setwarnings(False)
GPIO.cleanup()          # сброс всех старых настроек!
GPIO.setmode(GPIO.BCM)

for pin in buttons:
    GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.add_event_detect(pin, GPIO.FALLING, callback=button_callback, bouncetime=200)

print("Ожидание кнопок... Нажми Ctrl+C для выхода.")
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    GPIO.cleanup()
    print("Выход")
