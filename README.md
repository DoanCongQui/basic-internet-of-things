# THỰC HÀNH INTERNET OF THINGS (IOT)

## Install OS & library 

- Đầu tiên download OS (Operating system) cho Raspberry Pi 4 với Images phiên bản [2024-03-15-raspios-bookworm-arm64.img.xz](https://downloads.raspberrypi.com/raspios_arm64/images/raspios_arm64-2024-03-15/) là ổn định cho 1 số thư viện cần thiết.

```
sudo apt update && sudo apt upgrade
sudo raspi-config
```
Chọn vào `Interface Options` tiếp đến bật `I2C` & `SSH` nếu muốn remote thông qua màn hình thì bật luôn cả `VNC`

-  Tiếp theo download library [grove hat](https://github.com/Seeed-Studio/grove.py) cho các hệ thống.
```
sudo apt install python3-venv
cd ~/
python3 -m venv env
source env/bin/activate
python3 -m pip install --upgrade pip setuptools wheel
pip3 install .
```