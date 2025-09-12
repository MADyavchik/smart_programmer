from gpiozero import Button
from signal import pause

buttons = {
    5: Button(5, pull_up=True),
    6: Button(6, pull_up=True),
    13: Button(13, pull_up=True),
    19: Button(19, pull_up=True),
    26: Button(26, pull_up=True),
}

for pin, btn in buttons.items():
    btn.when_pressed = lambda p=pin: print(f"Нажата кнопка на GPIO{p}")

print("Жми кнопки... (Ctrl+C чтобы выйти)")
pause()
