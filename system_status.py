import time
import subprocess
import board
import busio
import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn
import RPi.GPIO as GPIO


# ==================== BATTERY MONITOR ==================== #
class BatteryMonitor:
    def __init__(self, channel=ADS.P0, multiplier=2.0, charge_pin=21):
        """
        channel: вход ADS1115 (ADS.P0..P3)
        multiplier: множитель для пересчёта (делитель напряжения)
        charge_pin: GPIO, показывающий наличие зарядки (1 — зарядка подключена)
        """
        i2c = busio.I2C(board.SCL, board.SDA)
        self.ads = ADS.ADS1115(i2c)
        self.chan = AnalogIn(self.ads, channel)
        self.multiplier = multiplier
        self.charge_pin = charge_pin

        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.charge_pin, GPIO.IN)

    def get_voltage(self) -> float:
        """Возвращает текущее напряжение батареи (в Вольтах)"""
        return round(self.chan.voltage * self.multiplier, 3)

    def is_charging(self) -> bool:
        """Возвращает True, если подключена зарядка"""
        try:
            return GPIO.input(self.charge_pin) == GPIO.HIGH
        except Exception:
            return False

    def get_status_text(self) -> str:
        """Возвращает строку с состоянием батареи"""
        voltage = self.get_voltage()
        charging = self.is_charging()
        if charging:
            return f"🔌 {voltage:.2f} V (зарядка)"
        else:
            return f"🔋 {voltage:.2f} V"


# ==================== WIFI MONITOR ==================== #
class WifiMonitor:
    def __init__(self, interface="wlan0", cache_time=10.0):
        self.interface = interface
        self.cache_time = cache_time
        self._last_update = 0
        self._cached_rssi = None
        self._cached_quality = None
        self._cached_ssid = None

    def get_quality_percent(self):
        """Возвращает качество сигнала (0–100 %)"""
        self._update_data()
        return self._cached_quality

    def get_signal_level(self):
        """Возвращает уровень сигнала (RSSI, dBm)"""
        self._update_data()
        return self._cached_rssi

    def get_ssid(self):
        """Возвращает SSID текущей сети"""
        self._update_data()
        return self._cached_ssid

    def _update_data(self):
        now = time.time()
        if now - self._last_update < self.cache_time:
            return

        try:
            # Читаем RSSI и качество сигнала из /proc/net/wireless
            with open("/proc/net/wireless", "r") as f:
                for line in f:
                    if self.interface in line:
                        parts = line.split()
                        quality = float(parts[2].replace(".", ""))
                        rssi = int(float(parts[3]))
                        self._cached_quality = int(quality / 70 * 100)
                        self._cached_rssi = rssi
                        break

            # Получаем SSID
            result = subprocess.run(
                ["iwgetid", "-r", self.interface],
                capture_output=True,
                text=True
            )
            self._cached_ssid = result.stdout.strip() or "—"

        except Exception:
            self._cached_quality = None
            self._cached_rssi = None
            self._cached_ssid = None

        self._last_update = now

    def get_status_text(self):
        self._update_data()
        if self._cached_quality is None:
            return "📶 WiFi: нет соединения"
        return f"📶 WiFi: {self._cached_ssid} ({self._cached_rssi} dBm)"


# ==================== DEMO ==================== #
if __name__ == "__main__":
    batt = BatteryMonitor()
    wifi = WifiMonitor()

    try:
        while True:
            print(batt.get_status_text())
            print(wifi.get_status_text())
            print("-" * 30)
            time.sleep(2)
    except KeyboardInterrupt:
        print("\nВыход.")
