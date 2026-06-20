import time
from grove.grove_button import GroveButton
from grove.grove_led import GPIO, GroveLed

# ==========================
#     LED & BUTTON PIN
# ==========================

LED_1_P     =   5
BUTTON_1_P  =   4

LED_2_P     =   6
BUTTON_2_P  =   7

LED_3_P     =   8
BUTTON_3_P  =   9

led_1_i = GroveLed(LED_1_P)
btn_1_i = GroveButton(BUTTON_1_P)
led_2_i = GroveLed(LED_2_P)
btn_2_i = GroveButton(BUTTON_2_P)
led_3_i = GroveLed(LED_3_P)
btn_3_i = GroveButton(BUTTON_3_P)


# Function to turn on/off LED with specified time
def on_off_led(led, time_on, time_off):
    led.on()
    time.sleep(time_on)
    led.off()
    time.sleep(time_off)

def main():

    module_1_on = 1
    module_2_on = 5
    module_1_off = 6
    module_2_off = 2

    old_btn1 = False
    old_btn2 = False

    try:
        while True:
            # ==========================
            #      LED Module 1  
            # ==========================
            on_off_led(led_1_i, module_1_on, module_1_off)

            # ==========================
            #      LED Module 2  
            # ==========================
            on_off_led(led_2_i, module_2_on, module_2_off)

            # ==========================
            #      LED Module 3  
            # ==========================
            if btn_3_i.is_pressed():
                print("Button 3 pressed")
                on_off_led(led_3_i, module_1_on, module_1_off)
                
            else:
                on_off_led(led_3_i, module_2_on, module_2_off)

            # ==========================
            #      Button Module 1 
            # ==========================
            new_btn1 = btn_1_i.is_pressed()

            if new_btn1 and not old_btn1:
                module_1_on = min(module_1_on + 0.5, 10)
                module_1_off = max(module_1_off - 0.5, 0.5)

                print("Button 1")
                print("t_on =", module_1_on)
                print("t_off =", module_1_off)

            old_btn1 = new_btn1

            # ==========================
            #      Button Module 2
            # ==========================
            new_btn2 = btn_2_i.is_pressed()

            if new_btn2 and not old_btn2:
                module_2_on = max(module_2_on - 0.5, 0.5)
                module_2_off = min(module_2_off + 0.5, 10)

                print("Button 2")
                print("t_on =", module_2_on)
                print("t_off =", module_2_off)

            old_btn2 = new_btn2
        
            time.sleep(0.05)

            
    except KeyboardInterrupt:
        led_1_i.off()
        led_2_i.off()
        led_3_i.off()
        print("Stop program")

# ------------------ Run ------------------
if __name__ == "__main__":
    main()