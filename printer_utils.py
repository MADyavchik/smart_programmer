# printer_utils.py
import asyncio
from PIL import Image, ImageDraw, ImageFont
from NiimPrintX.nimmy.printer import PrinterClient
from bleak import BleakScanner
import traceback

# Параметры принтера
WIDTH = 176  # 22 мм * 8 точек/мм
HEIGHT = 112  # 14 мм * 8 точек/мм
QUANTITY = 1
DENSITY = 3

def create_text_image(text):
    image = Image.new("1", (WIDTH, HEIGHT), "white")
    draw = ImageDraw.Draw(image)
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", 16)
    except:
        font = ImageFont.load_default()

    # Разбивка на строки
    max_chars_per_line = 16
    lines = [text[i:i+max_chars_per_line] for i in range(0, len(text), max_chars_per_line)]
    line_height = 16
    total_text_height = line_height * len(lines)
    y = (HEIGHT - total_text_height) // 2

    for line in lines:
        bbox = draw.textbbox((0,0), line, font=font)
        text_width = bbox[2] - bbox[0]
        x = (WIDTH - text_width) // 2
        draw.text((x, y), line, font=font, fill=0)
        y += line_height

    return image.rotate(270, expand=True)

async def get_device_by_mac(mac_address):
    devices = await BleakScanner.discover()
    for device in devices:
        if device.address == mac_address:
            return device
    return None

async def connect_printer(device):
    printer = PrinterClient(device)
    await printer.connect()
    return printer

async def print_label_async(mac_address, printer_mac):
    device = await get_device_by_mac(printer_mac)
    if not device:
        raise Exception(f"Printer {printer_mac} not found")
    printer = await connect_printer(device)
    try:
        image = create_text_image(mac_address)
        await printer.print_image(image, quantity=QUANTITY, density=DENSITY)
    finally:
        await printer.disconnect()

def print_label(mac_address, printer_mac):
    """Синхронная обертка для вызова из обычного кода"""
    asyncio.run(print_label_async(mac_address, printer_mac))
