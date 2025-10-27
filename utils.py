# utils.py
import os
import sys
import pygame
import RPi.GPIO as GPIO

def clean_exit(manager=None, status_updater=None, poweroff=False, reboot=False):
    print("[INFO] Stopping all threads and cleaning up...")

    if status_updater:
        status_updater.stop()

    try:
        if manager:
            for screen in getattr(manager, "screens", []):
                if hasattr(screen, "log_manager"):
                    screen.log_manager.stop()
    except Exception:
        pass

    GPIO.cleanup()
    pygame.quit()

    if poweroff:
        os.system("sudo poweroff -i")
    elif reboot:
        os.system("sudo reboot -i")

    sys.exit(0)
