#!/bin/bash
# --------------------------------------------
# File: startup.sh
# Mục đích: Chạy Node-RED và chương trình Python song song khi khởi động
# --------------------------------------------

# Đường dẫn đến script Python
PY_SCRIPT="/home/pi/IOT/Week5/test/T6.py"

# Log files (lưu lại thông tin chạy)
LOG_DIR="/home/pi/IOT/logs"
mkdir -p "$LOG_DIR"

# Chạy Node-RED (ghi log)
echo "Starting Node-RED..."
nohup sudo node-red-pi > "$LOG_DIR/node_red.log" 2>&1 &

# Chạy Python script (ghi log)
echo "Starting Python script..."
nohup python3 "$PY_SCRIPT" > "$LOG_DIR/python_T6.log" 2>&1 &

echo "All processes started successfully."
exit 0

