import RPi.GPIO as GPIO
import time

GPIO.setmode(GPIO.BCM)

led_pins = [17, 27, 22, 5, 6, 13, 19, 26]

for pin in led_pins:
    GPIO.setup(pin, GPIO.OUT)
    GPIO.output(pin, GPIO.HIGH)

try:
    while True:
        for pin in led_pins:
            GPIO.output(pin, GPIO.LOW)   # On LED
            time.sleep(1)                # Delay 1 giay
            GPIO.output(pin, GPIO.HIGH)  # Off LED
except KeyboardInterrupt:
    print("Stop")

finally:
    GPIO.cleanup() 