import board
import busio
import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn
import RPi.GPIO as GPIO

# Настройка ADC
i2c = busio.I2C(board.SCL, board.SDA)
ads = ADS.ADS1115(i2c)
chan = AnalogIn(ads, ADS.P0)

# GPIO для статуса зарядки
CHARGER_PIN = 21
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
GPIO.setup(CHARGER_PIN, GPIO.IN)

def get_battery_status():
    """
    Возвращает кортеж (voltage, charging)
    voltage: напряжение батареи (float, V)
    charging: bool, True если зарядка подключена
    """
    voltage = chan.voltage * 2  # если делитель на 2
    charging = GPIO.input(CHARGER_PIN) == GPIO.HIGH
    return voltage, charging
