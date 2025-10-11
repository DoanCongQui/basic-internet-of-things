#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time
import random
import threading
import requests
from collections import deque
import socket
import paho.mqtt.client as mqtt

# ===== CONFIG =====
WRITE_API_KEY = "8TCXXRHS2MI50OIM"
CHANNEL_ID    = "3092104"
THINGSPEAK_URL = "https://api.thingspeak.com/update"

MQTT_BROKER     = "mqtt3.thingspeak.com"
MQTT_PORT       = 1883
MQTT_CLIENT_ID  = "BTUwPBwEBgQnJiYhGyIxLgY"
MQTT_USERNAME   = "BTUwPBwEBgQnJiYhGyIxLgY"
MQTT_PASSWORD   = "QpwjZY63Lu1NUci696wS8THR"

SUB_TOPICS = [
    f"channels/{CHANNEL_ID}/subscribe/fields/field5",
    f"channels/{CHANNEL_ID}/subscribe/fields/field6",
    f"channels/{CHANNEL_ID}/subscribe/fields/field7",
    f"channels/{CHANNEL_ID}/subscribe/fields/field8",
]

SEND_INTERVAL   = 20
RUN_DURATION    = 45 * 60
SAMPLE_INTERVAL = 1
CONTROL_PERIOD  = 1

window = deque(maxlen=20)
mode_auto = 0
manual_states = {"led": 0, "buzzer": 0, "relay": 0}
control_event = threading.Event()
state_lock = threading.Lock()

# ====== Kiểm tra mạng ======
def has_internet(host="8.8.8.8", port=53, timeout=3):
    """Kiểm tra kết nối mạng bằng DNS socket"""
    try:
        socket.setdefaulttimeout(timeout)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
        return True
    except OSError:
        return False

def wait_for_network():
    print("🌐 Kiểm tra kết nối mạng...")
    while not has_internet():
        print("⏳ Chưa có mạng, đang chờ...")
        time.sleep(5)
    print("✅ Đã có kết nối mạng!")

# ====== Mô phỏng thiết bị ======
class Device:
    def __init__(self, name): self.name, self._value = name, 0
    @property
    def value(self): return self._value
    @value.setter
    def value(self, v):
        v = 1 if v else 0
        if v != self._value:
            self._value = v
            print(f"[ACT] {self.name} -> {'ON' if v else 'OFF'}")
    def on(self): self.value = 1
    def off(self): self.value = 0

led, buzzer, relay = Device("LED"), Device("Buzzer"), Device("Relay")

# ====== Đọc cảm biến (giả lập) ======
def read_sensors():
    temp = random.uniform(25, 80)
    hum  = random.uniform(30, 80)
    volt = random.uniform(0.5, 3.3)
    dist = random.uniform(5, 150)
    return temp, hum, volt, dist

def get_average(seq):
    if not seq: return 0,0,0,0
    n=len(seq)
    s1=sum(x[0] for x in seq); s2=sum(x[1] for x in seq)
    s3=sum(x[2] for x in seq); s4=sum(x[3] for x in seq)
    return s1/n,s2/n,s3/n,s4/n

# ====== Gửi ThingSpeak ======
def send_to_thingspeak(temp, hum, volt, dist):
    while True:
        if not has_internet():
            print("⚠️ Mất mạng! Đang chờ có lại...")
            time.sleep(5)
            continue
        try:
            r = requests.post(
                THINGSPEAK_URL,
                params={
                    "api_key": WRITE_API_KEY,
                    "field1": round(temp, 2),
                    "field2": round(hum, 2),
                    "field3": round(volt, 2),
                    "field4": round(dist, 2),
                },
                timeout=5
            )
            if r.status_code == 200:
                print(f"✅ Sent avg: T={temp:.1f} H={hum:.1f} V={volt:.2f} D={dist:.1f}")
                break
            else:
                print("❌ HTTP error:", r.status_code, r.text[:100])
        except Exception as e:
            print("HTTP error:", e)
        time.sleep(5)

# ====== Điều khiển ======
def apply_manual_states():
    led.value, buzzer.value, relay.value = manual_states["led"], manual_states["buzzer"], manual_states["relay"]

def apply_auto_rules(temp, hum):
    h = time.localtime().tm_hour
    led.on() if 18 <= h < 22 else led.off()
    if temp > 40: buzzer.on()
    elif temp < 30: buzzer.off()
    if hum > 70: relay.on()
    elif hum < 40: relay.off()

def control_tick(t, h):
    with state_lock:
        if mode_auto: apply_auto_rules(t, h)
        else: apply_manual_states()

# ====== MQTT Callbacks ======
def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        print("✅ MQTT connected")
        for t in SUB_TOPICS:
            client.subscribe(t)
            print("→ Subscribed:", t)
    else:
        print("❌ MQTT connect error:", rc)

def on_message(client, userdata, msg):
    global mode_auto
    payload = msg.payload.decode("utf-8").strip()
    topic = msg.topic
    try:
        val = 1 if int(float(payload)) == 1 else 0
    except:
        print("⚠️ Invalid payload:", payload)
        return
    with state_lock:
        if topic.endswith("/field5"): manual_states["led"] = val
        elif topic.endswith("/field6"): manual_states["buzzer"] = val
        elif topic.endswith("/field7"): manual_states["relay"] = val
        elif topic.endswith("/field8"): mode_auto = val
    control_event.set()

# ====== MQTT Client ổn định ======
def build_mqtt_client():
    while True:
        wait_for_network()
        try:
            client = mqtt.Client(client_id=MQTT_CLIENT_ID, protocol=mqtt.MQTTv311)
            client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
            client.on_connect = on_connect
            client.on_message = on_message
            client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
            client.loop_start()
            return client
        except Exception as e:
            print(f"⚠️ Lỗi MQTT kết nối ({e}). Thử lại sau 5s...")
            time.sleep(5)

# ====== Threads ======
def sensor_thread():
    while True:
        temp, hum, volt, dist = read_sensors()
        window.append((temp, hum, volt, dist))
        print(f"[SENS] T={temp:5.1f}C H={hum:5.1f}% V={volt:4.2f}V D={dist:5.1f}cm  ({time.strftime('%H:%M:%S')})")
        time.sleep(SAMPLE_INTERVAL)

def control_thread():
    while True:
        control_event.wait(timeout=CONTROL_PERIOD)
        control_event.clear()
        if window:
            t, h, _, _ = window[-1]
            control_tick(t, h)

def upload_thread():
    start = time.time()
    while time.time() - start < RUN_DURATION:
        avg_temp, avg_hum, avg_volt, avg_dist = get_average(list(window))
        send_to_thingspeak(avg_temp, avg_hum, avg_volt, avg_dist)
        time.sleep(SEND_INTERVAL)
    print("⏱️ Hoàn thành 45 phút gửi dữ liệu.")

# ===== MAIN =====
if __name__ == "__main__":
    wait_for_network()
    print("🚀 Start: HTTP upload (fields 1–4) + MQTT control (fields 5–8)")
    mqtt_client = build_mqtt_client()

    threading.Thread(target=sensor_thread, daemon=True).start()
    threading.Thread(target=control_thread, daemon=True).start()

    upload_thread()

    mqtt_client.loop_stop()
    mqtt_client.disconnect()

