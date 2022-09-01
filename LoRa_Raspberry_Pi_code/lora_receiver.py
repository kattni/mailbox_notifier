#!/bin/env python3

# Mailbox notifications
# Authors: Jerry Needell, Rose Hooper, Kattni Rembor
#
"""
Mailbox notifications on-screen.
"""
import atexit
import dataclasses
import logging
import os
import re
import subprocess
import time
from functools import partial
from typing import Optional

# For local development
try:
    import RPi.GPIO
except (RuntimeError, ModuleNotFoundError):
    import fake_rpigpio.utils

    fake_rpigpio.utils.install()

import struct
from datetime import datetime
from queue import Queue
from threading import Thread

import adafruit_rfm9x
import adafruit_ssd1306
import board
import busio
import digitalio

# pylint: disable=missing-function-docstring,missing-class-docstring
if os.environ.get("INVOCATION_ID"):
    LOG_FORMAT = "%(levelname)s %(module)s %(filename)s:%(funcName)s:%(lineno)d %(threadName)s %(message)s"
else:
    LOG_FORMAT = "%(asctime)s %(levelname)s %(module)s %(filename)s:%(funcName)s:%(lineno)d %(threadName)s %(message)s"

logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)

# Define radio parameters.
# Frequency of the radio in Mhz. Must match your
# module! Can be a value like 915.0, 433.0, etc.
RADIO_FREQ_MHZ = 915

# WIFI Bars
WIFI_RSSI = [
    -89,
    -78,
    -67,
    -56
    # - 89, -78, -67, -20
]

NEW_MAIL_MESSAGE = "U GOT MAIL"
MORE_MAIL = "MAILBOX x{}"

# Set up blue LED.
blue_led = digitalio.DigitalInOut(board.TX)
blue_led.switch_to_output()

# setup I2C
i2c = busio.I2C(board.SCL, board.SDA)

# 128x32 OLED Display
reset_pin = digitalio.DigitalInOut(board.D4)
display = adafruit_ssd1306.SSD1306_I2C(128, 32, i2c, reset=reset_pin)

# Clear the display.
display.fill(0)
for pixel_y in range(0, display.height, 4):
    display.hline(0, pixel_y, display.width, color=1)
for pixel_x in range(0, display.width, 4):
    display.vline(pixel_x, 0, display.height, color=1)
display.show()
width = display.width
height = display.height

# Define pins connected to the chip.
# set GPIO pins as necessary - this example is for Raspberry Pi
CS = digitalio.DigitalInOut(board.CE1)
RESET = digitalio.DigitalInOut(board.D25)

# Set up buttons.

BUTTONS = [digitalio.DigitalInOut(pin) for pin in (board.D5, board.D6, board.D12)]
for _button in BUTTONS:
    _button.switch_to_input(pull=digitalio.Pull.UP)

# Button check interval
BUTTON_CHECK_INTERVAL = 0.05
DEBOUNCE_INTERVAL = 0.2

# Initialise SPI bus.
spi = busio.SPI(board.SCK, MOSI=board.MOSI, MISO=board.MISO)
# Initialise RFM radio
rfm9x = adafruit_rfm9x.RFM9x(spi, CS, RESET, RADIO_FREQ_MHZ)
# set address to Node 0 - ignore packets to other addresses
rfm9x.node = 0
# enable CRC checking
rfm9x.enable_crc = True
# set delay before transmitting ACK (seconds)
rfm9x.ack_delay = 0.1

packet_queue = Queue()


@dataclasses.dataclass
class Packet:
    count: int
    subcount: int
    error_count: int
    battery_charge_level: float


class State:
    mailbox_was_opened: bool = False
    mailbox_opened_at: datetime = None
    last_battery_percent: float = None
    last_packet_data: Optional[Packet]
    last_packet_raw: bytearray
    trigger_count: int = 0
    count_since_last_reset: int = 0
    last_reset: Optional[datetime] = None
    wifi_rssi = -100


def get_wifi_strength():
    # output = subprocess.run(["/usr/sbin/iwconfig", "wlan0"], capture_output=True)
    with open("/proc/net/wireless", "r") as fh:
        lines = fh.readlines()

    wlan_if = [line for line in lines if "wlan0" in line]
    signal_level = -100
    if wlan_if:
        sig = re.match(r"^\s*wlan\d+:\s+\d+\s+\S+\s+(-\d+).", wlan_if[-1])
        if sig:
            signal_level = int(sig.group(1))
    State.wifi_rssi = signal_level
    return State.wifi_rssi


def draw_wifi_signal(show=False):
    # Lower right corner
    x_left = 86
    y_bottom = 30
    x_spacing = 3
    y_multiplier = 2
    x_width_on = 2
    num_bars = len(WIFI_RSSI)

    # Clear the area
    display.rect(
        x=x_left,
        y=y_bottom - (num_bars * y_multiplier),
        width=x_spacing * num_bars,
        height=y_multiplier * num_bars,
        color=0,
        fill=True,
    )
    for num, bar in enumerate(WIFI_RSSI):
        is_on = State.wifi_rssi > bar
        y_height = max(1, y_multiplier * num)
        x_pos = x_left + (num * x_spacing)
        if is_on:
            display.rect(
                x=x_pos,
                y=y_bottom - y_height,
                width=x_width_on,
                height=y_height,
                color=1,
            )
    if show:
        display.show()


def pixel_blinker(interval=1) -> None:
    logging.info("Pixel Blinker every %d sec", interval)
    while True:
        time.sleep(interval)
        display.pixel(x=127, y=31, color=1)
        display.show()
        time.sleep(interval)
        display.pixel(x=127, y=31, color=0)
        display.show()
        draw_wifi_signal()


def led_blinker(interval=0.5):
    while True:
        blue_led.value = 0
        logging.info("LED blinking")

        while State.mailbox_was_opened:
            blue_led.value = not blue_led.value
            time.sleep(interval)

        logging.info("LED NOT blinking")
        blue_led.value = 0
        while not State.mailbox_was_opened:
            time.sleep(0.1)


def fetch_wifi_signal_loop():
    while True:
        get_wifi_strength()
        time.sleep(1)


class PacketReceiver(Thread):
    # Look for a new packet: only accept if addresses to my_node

    @staticmethod
    def read_packet():
        logging.debug("Waiting for packet")
        packet = rfm9x.receive(with_ack=True, with_header=True)

        if not packet:
            logging.debug("No packet")
            return

        logging.info("Got a packet!")
        # Print out the raw bytes of the packet:
        logging.info("RSSI: %s", rfm9x.last_rssi)
        packet_header = packet[0:4]
        packet_payload = packet[4:]
        logging.info("Received (raw header): %s", [hex(x) for x in packet_header])
        logging.info("Received (raw payload): %s", [hex(x) for x in packet_payload])
        State.last_packet_raw = packet

        try:
            # count, subcount, error_count, battery_charge_level = struct.unpack('<BBBff', packet_payload)
            unpacked = struct.unpack("<BBBff", packet_payload)[:4]
            packet = Packet(*unpacked)
            logging.info("%s", packet)
            packet_queue.put(packet)
        except struct.error as exc:
            logging.error("Invalid packet: %s", exc)

    def run(self):
        logging.info("Starting to wait for packets")

        while True:
            self.read_packet()

def send_alert():
    logging.info("Sending alert (Adafruit IO)")
    # res = aio_client.send_data(FEED_ID, "Triggered")


def read_buttons_gpio():
    buttons_pressed = [False, False, False]
    for button_no, button in enumerate(BUTTONS):
        buttons_pressed[button_no] = not button.value
    return buttons_pressed


def show_notice(text, text2="", text3=""):
    display.fill(0)
    display.text(text, x=0, y=0, size=2, color=1)
    display.text(text2, x=0, y=16, size=1, color=1)
    display.text(text3, x=0, y=24, size=1, color=1)
    display.show()


def update_display(big_text, size=2):
    blank_display()
    display.text(big_text, x=0, y=0, color=1, size=size)
    if State.mailbox_was_opened:
        when = State.mailbox_opened_at.strftime("%a at %H:%M")
        display.text(when, x=0, y=16, color=1, size=1)
        display.text(f"{State.last_battery_percent:3.0f}%", x=90, y=24, color=1, size=1)
    draw_wifi_signal()
    display.show()


def blank_display():
    display.fill(0)
    draw_wifi_signal()
    display.show()


def packet_handler():
    packet = packet_queue.get()
    update_flags(packet)


def trigger_mailbox():
    update_display(NEW_MAIL_MESSAGE)
    send_alert()
    State.count_since_last_reset += 1
    State.trigger_count += 1


def clear_mailbox():
    State.count_since_last_reset = 0
    State.mailbox_was_opened = False


def wait_for_ack():
    # Wait for a button OR "tomorrow"
    logging.info("Waiting for button")
    while True:
        buttons = read_buttons_gpio()
        if any(buttons):
            clear_mailbox()
            show_notice("Cleared")
            time.sleep(1)
            blank_display()
            return

        if not packet_queue.empty():
            State.count_since_last_reset += 1
            packet_available = packet_queue.get()
            update_flags(packet_available)
            State.last_reset = datetime.now()
            update_display(MORE_MAIL.format(State.count_since_last_reset))

        time.sleep(0.1)


def mailbox_sequence():
    while True:
        buttons = read_buttons_gpio()
        packet_available = not packet_queue.empty()

        if packet_available:
            packet_handler()
            trigger_mailbox()
            wait_for_ack()
            return

        if any(buttons):
            button_handler(buttons)
            return

        time.sleep(0.01)


# def ask_question(text, b1, b2, b3, timeout, interruptible, cancel_check):
#     display.fill(0)
#     # display.text()


def button_handler(buttons):
    # Debounce
    time.sleep(0.1)
    initial_buttons = read_buttons_gpio()

    while any(buttons):
        button_numbers = [str(n) if b else " " for n, b in enumerate(buttons)]
        show_notice(f"BTN {''.join(button_numbers)}")
        time.sleep(0.05)
        buttons = read_buttons_gpio()

    buttons = initial_buttons
    if buttons[0] and buttons[2]:
        update_display("Triggered")
        time.sleep(1)
        blank_display()
        packet_queue.put(Packet(1, 1, 1, 0))


def update_flags(packet):
    State.mailbox_opened_at = datetime.now()
    State.mailbox_was_opened = True
    State.last_battery_percent = packet.battery_charge_level
    State.last_packet_data = packet


def heartbeat(interval=900):
    while True:
        time.sleep(interval)


def main():

    threads = [
        Thread(target=led_blinker, daemon=True),
        Thread(target=pixel_blinker, daemon=True, kwargs=dict(interval=0.333)),
        Thread(target=fetch_wifi_signal_loop, daemon=True),
        PacketReceiver(daemon=True),
        Thread(target=heartbeat, daemon=True, kwargs=dict(interval=300)),
    ]
    [t.start() for t in threads]

    while True:
        # noinspection PyBroadException
        blank_display()
        try:
            mailbox_sequence()
        except Exception as exc:  # pylint: disable=broad-except
            logging.exception("Exception caught", exc_info=exc)


if __name__ == "__main__":
    atexit.register(partial(update_display, "not running", size=1))

    logging.info("Started")
    main()
