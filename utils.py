# utils.py
import os
import sys
import pygame
import RPi.GPIO as GPIO

def clean_exit(manager=None, status_updater=None, poweroff=False, reboot=False, restart_app=False):
    """
    Корректное завершение приложения с остановкой потоков и очисткой ресурсов.

    Параметры:
        manager: объект ScreenManager (опционально)
        status_updater: объект SystemStatusUpdater (опционально)
        poweroff: если True — выключить систему
        reboot: если True — перезагрузить систему
        restart_app: если True — мягко перезапустить демон через systemd
    """
    print("[INFO] Stopping all threads and cleaning up...")

    # остановка апдейтера
    if status_updater:
        status_updater.stop()

    # остановка логов в менеджере экранов
    if manager:
        try:
            for screen in getattr(manager, "screens", []):
                if hasattr(screen, "log_manager"):
                    screen.log_manager.stop()
        except Exception:
            pass

    # очистка ресурсов
    GPIO.cleanup()
    pygame.quit()

    # системные действия
    if poweroff:
        print("[INFO] Powering off system...")
        os.system("sudo poweroff -i")
    elif reboot:
        print("[INFO] Rebooting system...")
        os.system("sudo reboot -i")
    elif restart_app:
        print("[INFO] Restarting smart_programmer.service...")
        os.system("sudo systemctl restart smart_programmer.service")

    # завершение процесса
    sys.exit(0)
