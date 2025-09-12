import RPi.GPIO as GPIO
import time

buttons = [5, 6, 13, 19, 26]

GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)

for pin in buttons:
    GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

print("Жми кнопки... (Ctrl+C чтобы выйти)")

try:
    while True:
        for pin in buttons:
            if GPIO.input(pin) == GPIO.LOW:
                print(f"Нажата кнопка на GPIO{pin}")
        time.sleep(0.1)
except KeyboardInterrupt:
    GPIO.cleanup()
    print("Выход")
