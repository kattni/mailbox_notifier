import alarm
import time
import struct
import board
import digitalio
import adafruit_rfm9x
from adafruit_lc709203f import LC709203F, PackSize

if alarm.wake_alarm:
    print("Awake", alarm.wake_alarm)
    alarm.sleep_memory[0] += 1
else:
    print("No wake up alarm")
    alarm.sleep_memory[0] = 0
    alarm.sleep_memory[2] = 0

# Set up battery monitor
battery_monitor = LC709203F(board.I2C())
battery_monitor.pack_size = PackSize.MAH1000

# Set up red LED
led = digitalio.DigitalInOut(board.LED)
led.switch_to_output()
led.value = True

# Set up the alarm pin
pin = digitalio.DigitalInOut(board.D12)
pin.pull = digitalio.Pull.UP

print("Count:", alarm.sleep_memory[0])

# Define radio parameters.
# Frequency of the radio in Mhz. Must match your
# module! Can be a value like 915.0, 433.0, etc.
RADIO_FREQ_MHZ = 915.0

# Define pins connected to the loRa chip.
CS = digitalio.DigitalInOut(board.D10)
RESET = digitalio.DigitalInOut(board.D11)

# Initialize SPI bus.
spi = board.SPI()

# Initialise RFM radio
rfm9x = adafruit_rfm9x.RFM9x(spi, CS, RESET, RADIO_FREQ_MHZ)
rfm9x.node = 1
rfm9x.destination = 0
rfm9x.tx_power = 23

# Send a message as long as the pin is low
alarm.sleep_memory[1] = 0

byte_packet = bytearray(10)
while not pin.value:
    packet = struct.pack('<BBBff', alarm.sleep_memory[0], alarm.sleep_memory[1],
                         alarm.sleep_memory[2], battery_monitor.cell_voltage,
                         battery_monitor.cell_percent)
    print("Packet sent.")
    if not rfm9x.send_with_ack(bytes(packet)):
        alarm.sleep_memory[2] += 1
        print("No Ack")
    time.sleep(3)
    alarm.sleep_memory[1] += 1

# Deinitialise the alarm pin
pin.deinit()

rfm9x.sleep()
print("RFM9x sleeping.")

# Create an alarm on Pin D12
pin_alarm = alarm.pin.PinAlarm(pin=board.D12, value=False, pull=True)

print("about to deep_sleep")

# exit and set the alarm
alarm.exit_and_deep_sleep_until_alarms(pin_alarm)

