#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time
import random
import threading
import requests
from collections import deque

# ========== MQTT ==========
import paho.mqtt.client as mqtt

# ===== CONFIG =====
WRITE_API_KEY = "8TCXXRHS2MI50OIM"
READ_API_KEY  = "28HN8TRMTLPQZNR2"
CHANNEL_ID    = "3092104"

THINGSPEAK_URL = "https://api.thingspeak.com/update"

# =============== MQTT (ThingSpeak) ==============
MQTT_BROKER     = "mqtt3.thingspeak.com"
MQTT_PORT       = 1883
MQTT_CLIENT_ID  = "BTUwPBwEBgQnJiYhGyIxLgY"
MQTT_USERNAME   = "BTUwPBwEBgQnJiYhGyIxLgY"
MQTT_PASSWORD   = "QpwjZY63Lu1NUci696wS8THR"

SUB_TOPICS = [
    f"channels/{CHANNEL_ID}/subscribe/fields/field5",  # LED (0/1)
    f"channels/{CHANNEL_ID}/subscribe/fields/field6",  # Buzzer (0/1)
    f"channels/{CHANNEL_ID}/subscribe/fields/field7",  # Relay (0/1)
    f"channels/{CHANNEL_ID}/subscribe/fields/field8",  # Mode  (1=Auto, 0=Manual)
]

SEND_INTERVAL    = 20     # giây
RUN_DURATION     = 45 * 60
SAMPLE_INTERVAL  = 1
CONTROL_PERIOD   = 1      # tick điều khiển (đảm bảo ≤ 2s khi có cập nhật)

# ===== Trạng thái hệ thống =====
window = deque(maxlen=20)  # lưu 20 mẫu gần nhất (20s)
mode_auto = 0  # 0=Manual, 1=Auto
manual_states = {"led": 0, "buzzer": 0, "relay": 0}

control_event = threading.Event()
state_lock = threading.Lock()

# ===== Thiết bị dạng mô phỏng (in ra terminal) =====
class Device:
    def __init__(self, name):
        self.name = name
        self._value = 0  # 0=OFF, 1=ON
    @property
    def value(self):
        return self._value
    @value.setter
    def value(self, v):
        v = 1 if v else 0
        if v != self._value:
            self._value = v
            print(f"[ACT] {self.name} -> {'ON' if v else 'OFF'}")
    def on(self):
        self.value = 1
    def off(self):
        self.value = 0

led    = Device("LED")
buzzer = Device("Buzzer")
relay  = Device("Relay")

# ====== Đọc cảm biến (giả lập) ======
def read_sensors():
    """
    Trả về: temp (°C), hum (%), volt (V), dist (cm)
    """
    temp = random.uniform(25, 80)
    hum  = random.uniform(30, 80)
    volt = random.uniform(0.5, 3.3)   # giả lập biến trở ADC
    dist = random.uniform(5, 150)
    return temp, hum, volt, dist

# ====== Trung bình ======
def get_average(seq):
    if not seq:
        return 0, 0, 0, 0
    n = len(seq)
    s1 = sum(x[0] for x in seq)
    s2 = sum(x[1] for x in seq)
    s3 = sum(x[2] for x in seq)
    s4 = sum(x[3] for x in seq)
    return s1/n, s2/n, s3/n, s4/n

# ====== Gửi ThingSpeak (HTTP) ======
def send_to_thingspeak(temp, hum, volt, dist):
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
        else:
            print("❌ HTTP status:", r.status_code, r.text[:120])
    except Exception as e:
        print("HTTP error:", e)

# ====== Điều khiển thiết bị ======
def apply_manual_states():
    led.value    = manual_states["led"]
    buzzer.value = manual_states["buzzer"]
    relay.value  = manual_states["relay"]

def apply_auto_rules(temp, hum):
    # LED theo giờ 18h-22h
    h = time.localtime().tm_hour
    if 18 <= h < 22:
        led.on()
    else:
        led.off()

    # Buzzer theo nhiệt độ: >40 ON, <30 OFF, giữa 30..40 giữ nguyên
    if temp > 40:
        buzzer.on()
    elif temp < 30:
        buzzer.off()

    # Relay theo độ ẩm: >70 ON, <40 OFF, giữa 40..70 giữ nguyên
    if hum > 70:
        relay.on()
    elif hum < 40:
        relay.off()

def control_tick(latest_temp, latest_hum):
    with state_lock:
        if mode_auto == 1:
            apply_auto_rules(latest_temp, latest_hum)
        else:
            apply_manual_states()

# ====== MQTT callbacks ======
def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        print("✅ MQTT connected")
        for t in SUB_TOPICS:
            client.subscribe(t)
            print("→ Subscribed:", t)
    else:
        print("❌ MQTT connect error, rc:", rc)

def on_message(client, userdata, msg):
    global mode_auto
    payload = msg.payload.decode("utf-8").strip()
    topic = msg.topic
    # ThingSpeak gửi chuỗi; chuẩn hóa về 0/1
    try:
        val = int(float(payload))
        val = 1 if val == 1 else 0
    except:
        print("⚠️ Invalid payload:", payload)
        return

    updated = False
    with state_lock:
        if topic.endswith("/field5"):
            manual_states["led"] = val
            updated = True
            print(f"[MQTT] field5 LED -> {val}")
        elif topic.endswith("/field6"):
            manual_states["buzzer"] = val
            updated = True
            print(f"[MQTT] field6 Buzzer -> {val}")
        elif topic.endswith("/field7"):
            manual_states["relay"] = val
            updated = True
            print(f"[MQTT] field7 Relay -> {val}")
        elif topic.endswith("/field8"):
            mode_auto = 1 if val == 1 else 0
            updated = True
            print(f"[MQTT] field8 Mode -> {'Auto' if mode_auto==1 else 'Manual'}")

    if updated:
        # Đánh thức vòng điều khiển để phản hồi ≤ 2s
        control_event.set()

def build_mqtt_client():
    # Tương thích nhiều phiên bản paho-mqtt
    try:
        client = mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION2,
            client_id=MQTT_CLIENT_ID,
            clean_start=True
        )
    except Exception:
        client = mqtt.Client(client_id=MQTT_CLIENT_ID, clean_session=True)

    client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
    client.loop_start()
    return client

# ====== Threads ======
def sensor_thread():
    while True:
        temp, hum, volt, dist = read_sensors()
        window.append((temp, hum, volt, dist))
        print(f"[SENS] T={temp:5.1f}C H={hum:5.1f}% V={volt:4.2f}V D={dist:5.1f}cm  ({time.strftime('%H:%M:%S')})")
        time.sleep(SAMPLE_INTERVAL)

def control_thread():
    """
    Tick mỗi CONTROL_PERIOD giây.
    Ngoài ra nếu có control_event (do MQTT), xử lý ngay.
    """
    while True:
        # Nếu có cập nhật MQTT, xử lý ngay lập tức (wake-up ≤ CONTROL_PERIOD)
        control_event.wait(timeout=CONTROL_PERIOD)
        control_event.clear()

        if window:
            t, h, _, _ = window[-1]
            control_tick(t, h)

def upload_thread():
    """
    Gửi trung bình mỗi 20s trong 45 phút
    """
    start = time.time()
    while time.time() - start < RUN_DURATION:
        avg_temp, avg_hum, avg_volt, avg_dist = get_average(list(window))
        send_to_thingspeak(avg_temp, avg_hum, avg_volt, avg_dist)
        time.sleep(SEND_INTERVAL)
    print("⏱️ Hoàn thành 45 phút gửi dữ liệu.")

# ====== Main ======
if __name__ == "__main__":
    print("🚀 Start: HTTP upload (fields 1-4) + MQTT control (fields 5-8)")
    print("   Mode: 1=Auto, 0=Manual | Manual controls: LED/Buzzer/Relay via fields 5/6/7")

    mqtt_client = build_mqtt_client()

    threading.Thread(target=sensor_thread,  daemon=True).start()
    threading.Thread(target=control_thread, daemon=True).start()

    upload_thread()

    mqtt_client.loop_stop()
    mqtt_client.disconnect()

