import RPi.GPIO as GPIO
import time

# список пинов с кнопками
buttons = [5, 6, 13, 19, 26]

def button_callback(channel):
    print(f"Нажата кнопка на GPIO{channel}")

# --- настройка GPIO ---
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

for pin in buttons:
    GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)  # кнопки на GND
    GPIO.add_event_detect(pin, GPIO.FALLING, callback=button_callback, bouncetime=200)

print("Ожидание нажатий кнопок... Нажми Ctrl+C для выхода.")

try:
    while True:
        time.sleep(0.1)
except KeyboardInterrupt:
    print("\nВыход")
finally:
    GPIO.cleanup()
