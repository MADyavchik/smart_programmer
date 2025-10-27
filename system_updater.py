# system_updater.py
import threading
import time

class SystemStatusUpdater:
    def __init__(self, batt, wifi, interval=1.0):
        self.batt = batt
        self.wifi = wifi
        self.interval = interval
        self.battery_percent = 0
        self.battery_charging = False
        self.wifi_quality = 0
        self.wifi_ssid = None
        self.wifi_rssi = None
        self._stop_event = threading.Event()
        self.thread = threading.Thread(target=self._loop, daemon=True)

    def start(self):
        self.thread.start()

    def stop(self):
        self._stop_event.set()
        self.thread.join()

    def _loop(self):
        while not self._stop_event.is_set():
            # Обновляем батарею
            self.battery_percent = int((max(2.8, min(4.0, self.batt.get_voltage())) - 2.8) / (4.0 - 2.8) * 100)
            self.battery_charging = self.batt.is_charging()
            # Обновляем WiFi
            self.wifi_quality = self.wifi.get_quality_percent() or 0
            self.wifi_rssi = self.wifi.get_signal_level() or 0
            self.wifi_ssid = self.wifi.get_ssid()
            time.sleep(self.interval)
