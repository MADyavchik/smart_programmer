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
    def __init__(self, interface="wlan0", cache_time=2.0):
        """
        interface: имя WiFi-интерфейса
        cache_time: минимальный интервал обновления данных (сек)
        """
        self.interface = interface
        self.cache_time = cache_time
        self._last_update = 0
        self._cached_rssi = None
        self._cached_quality = None

    def _update_data(self):
        """Читает данные WiFi через iwconfig, если кэш устарел"""
        now = time.time()
        if now - self._last_update < self.cache_time:
            return  # используем кэш

        try:
            result = subprocess.run(
                ["iwconfig", self.interface],
                capture_output=True,
                text=True
            )
            rssi, quality = None, None
            for line in result.stdout.splitlines():
                if "Link Quality" in line:
                    parts = line.split()
                    for part in parts:
                        if "Quality=" in part or "Link" in part:
                            qstr = part.split("=")[-1]
                            if "/" in qstr:
                                num, denom = qstr.split("/")
                                quality = int(int(num) / int(denom) * 100)
                        elif "level=" in part:
                            try:
                                rssi = int(part.split("=")[1].replace("dBm", ""))
                            except:
                                pass
            self._cached_rssi = rssi
            self._cached_quality = quality
            self._last_update = now
        except Exception:
            self._cached_rssi = None
            self._cached_quality = None

    def get_signal_level(self) -> int | None:
        """Возвращает уровень сигнала WiFi (RSSI, dBm)"""
        self._update_data()
        return self._cached_rssi

    def get_quality_percent(self) -> int | None:
        """Возвращает качество сигнала (0–100 %)"""
        self._update_data()
        return self._cached_quality

    def get_status_text(self) -> str:
        """Возвращает строку для отображения статуса WiFi"""
        self._update_data()
        if self._cached_quality is None:
            return "📶 WiFi: нет соединения"
        return f"📶 WiFi: {self._cached_quality}% ({self._cached_rssi} dBm)"


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
