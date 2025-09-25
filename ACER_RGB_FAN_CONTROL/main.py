import curses
import enum
import time
import usb.core
import usb.util
from ecwrite import ECWrite

# ==============================
# ASCII Banner
# ==============================
BANNER = '''

██████╗ ██████╗ ███████╗██████╗  █████╗ ████████╗ ██████╗ ██████╗ 
██╔══██╗██╔══██╗██╔════╝██╔══██╗██╔══██╗╚══██╔══╝██╔═══██╗██╔══██╗
██████╔╝██████╔╝█████╗  ██║  ██║███████║   ██║   ██║   ██║██████╔╝
██╔═══╝ ██╔══██╗██╔══╝  ██║  ██║██╔══██║   ██║   ██║   ██║██╔══██╗
██║     ██║  ██║███████╗██████╔╝██║  ██║   ██║   ╚██████╔╝██║  ██║
╚═╝     ╚═╝  ╚═╝╚══════╝╚═════╝ ╚═╝  ╚═╝   ╚═╝    ╚═════╝ ╚═╝  ╚═╝
'''


# ==============================
# Fan Control Constants
# ==============================
class ECS(enum.Enum):
    CPU_FAN_MODE_CONTROL = 0x22
    CPU_AUTO_MODE   = 0x54
    CPU_TURBO_MODE  = 0x58
    CPU_MANUAL_MODE = 0x5C

    GPU_FAN_MODE_CONTROL = 0x21
    GPU_AUTO_MODE   = 0x50
    GPU_TURBO_MODE  = 0x60
    GPU_MANUAL_MODE = 0x70

    CPU_MANUAL_SPEED_CONTROL = 0x37
    GPU_MANUAL_SPEED_CONTROL = 0x3A

class PFS(enum.Enum):
    Auto = 1
    Turbo = 2
    Manual = 3

# ==============================
# RGB Constants
# ==============================
VENDOR_ID = 0x04f2
PRODUCT_ID = 0x0117
INTERFACE = 3

HEADER = [0x08, 0x00]
TERMINATOR = 0xbe
EFFECTS = ["Static","Pulsating","Rainbow Wave","Fast Rainbow Wave",
           "Snake","On Click Raindrop 1","On Click Raindrop 2",
           "Color Shifts 1","Color Shifts 2","Color Shifts 3",
           "Color Shifts 4","Random Electro Lights"]
COLORS = ["Red","Green","Yellow","Dark Blue","Bright Blue","Bright Pink","White"]

def format_payload(effect, brightness, color, anim_speed=0x00, tweak_byte=0x00):
    effect_id = list(EFFECTS).index(effect)+1
    color_id = list(COLORS).index(color)+1
    return bytes(HEADER + [effect_id, anim_speed, brightness, color_id, tweak_byte, TERMINATOR])

def send_payload(dev, payload):
    dev.ctrl_transfer(0x21, 0x09, 0x0300, INTERFACE, payload)

# ==============================
# Dashboard
# ==============================

def draw_bar(value, max_value, length=30):
    """Return a string progress bar like ███░░░ (with %)"""
    if max_value <= 0:
        return "░" * length + " (0%)"
    filled = int((value / max_value) * length)
    bar = "█" * filled + "░" * (length - filled)
    percent = int((value / max_value) * 100)
    return f"{bar} ({percent}%)"


def draw_section_title(stdscr, y, title, color_pair=2):
    """Draw a section header with separators"""
    stdscr.attron(curses.color_pair(color_pair) | curses.A_BOLD)
    stdscr.addstr(y, 2, f"─[ {title} ]" + "─" * 50)
    stdscr.attroff(curses.color_pair(color_pair) | curses.A_BOLD)


def dashboard(stdscr):
    curses.curs_set(0)
    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(1, curses.COLOR_CYAN, -1)
    curses.init_pair(2, curses.COLOR_GREEN, -1)
    curses.init_pair(3, curses.COLOR_YELLOW, -1)
    curses.init_pair(4, curses.COLOR_RED, -1)
    curses.init_pair(5, curses.COLOR_MAGENTA, -1)

    # Initialize EC
    ec = ECWrite()

    # Fan states
    cpu_mode = PFS.Auto
    gpu_mode = PFS.Auto
    cpu_manual_level = 5
    gpu_manual_level = 5

    # RGB states
    effect_idx = 0
    color_idx = 0
    brightness = 30

    # Mode switch
    current_tab = "fan"

    while True:
        stdscr.erase()
        height, width = stdscr.getmaxyx()

        # Draw header
        stdscr.attron(curses.color_pair(1) | curses.A_BOLD)
        stdscr.addstr(15, 0, BANNER.center(width-4))
        stdscr.attroff(curses.color_pair(1) | curses.A_BOLD)

        stdscr.addstr(1, 2, "[TAB] Switch Menu | [Q] Quit")

        if current_tab == "fan":
            ec.ec_refresh()
            cpu_temp = ec.ec_read(0xB0)
            gpu_temp = ec.ec_read(0xB7)
            sys_temp = ec.ec_read(0xB3)
            cpu_rpm = (ec.ec_read(0x14) << 8) | ec.ec_read(0x13)
            gpu_rpm = (ec.ec_read(0x16) << 8) | ec.ec_read(0x15)

            draw_section_title(stdscr, 3, "Temperatures")
            stdscr.addstr(4, 4, f"CPU Temp : {cpu_temp}°C   {draw_bar(cpu_temp, 100)}")
            stdscr.addstr(5, 4, f"GPU Temp : {gpu_temp}°C   {draw_bar(gpu_temp, 100)}")
            stdscr.addstr(6, 4, f"SYS Temp : {sys_temp}°C   {draw_bar(sys_temp, 100)}")

            draw_section_title(stdscr, 8, "Fan Speeds")
            stdscr.addstr(9, 4, f"CPU Fan : {cpu_rpm} RPM   {draw_bar(cpu_rpm, 7142)}")
            stdscr.addstr(10, 4, f"GPU Fan : {gpu_rpm} RPM   {draw_bar(gpu_rpm, 7142)}")

            draw_section_title(stdscr, 12, "Status")
            stdscr.addstr(13, 4, f"CPU Mode: {cpu_mode.name} | GPU Mode: {gpu_mode.name}")
            stdscr.addstr(14, 4, f"Manual Levels → CPU: {cpu_manual_level*10}% | GPU: {gpu_manual_level*10}%")


            stdscr.addstr(height-2, 2,
                          "Controls: 1/2/3 CPU | 4/5/6 GPU | Arrows Adjust | Q Quit")

        elif current_tab == "rgb":
            stdscr.addstr(3, 2, "[ RGB Settings ]", curses.color_pair(3))
            stdscr.addstr(5, 4, f"Effect    : {EFFECTS[effect_idx]}")
            stdscr.addstr(6, 4, f"Color     : {COLORS[color_idx]}")
            stdscr.addstr(7, 4, f"Brightness: {brightness}")

            stdscr.addstr(height-2, 2,
                          "Controls: ←/→ Effect | ↑/↓ Color | +/- Brightness | Enter Apply")

        stdscr.refresh()

        # --- Key handling (timeout ensures refresh) ---
        stdscr.timeout(100)   # wait max 100ms for a key, then continue loop
        ch = stdscr.getch()   # -1 if no key pressed
        key = None
        if ch != -1:
            if ch in (ord('q'), ord('Q')):
                key = 'q'
            elif ch == 9:                # TAB
                key = '\t'
            elif ch in (10, 13):         # Enter
                key = '\n'
            elif ch == curses.KEY_UP:
                key = 'KEY_UP'
            elif ch == curses.KEY_DOWN:
                key = 'KEY_DOWN'
            elif ch == curses.KEY_LEFT:
                key = 'KEY_LEFT'
            elif ch == curses.KEY_RIGHT:
                key = 'KEY_RIGHT'
            elif ch in (ord('1'), ord('2'), ord('3'),
                        ord('4'), ord('5'), ord('6'),
                        ord('+'), ord('='), ord('-')):
                key = chr(ch)

        if key == 'q':
            break
        elif key == '\t':
            current_tab = "rgb" if current_tab == "fan" else "fan"





        if current_tab == "fan":
            if key == "1":
                ec.ec_write(ECS.CPU_FAN_MODE_CONTROL.value, ECS.CPU_AUTO_MODE.value)
                cpu_mode = PFS.Auto
            elif key == "2":
                ec.ec_write(ECS.CPU_FAN_MODE_CONTROL.value, ECS.CPU_TURBO_MODE.value)
                cpu_mode = PFS.Turbo
            elif key == "3":
                ec.ec_write(ECS.CPU_FAN_MODE_CONTROL.value, ECS.CPU_MANUAL_MODE.value)
                cpu_mode = PFS.Manual
            elif key == "4":
                ec.ec_write(ECS.GPU_FAN_MODE_CONTROL.value, ECS.GPU_AUTO_MODE.value)
                gpu_mode = PFS.Auto
            elif key == "5":
                ec.ec_write(ECS.GPU_FAN_MODE_CONTROL.value, ECS.GPU_TURBO_MODE.value)
                gpu_mode = PFS.Turbo
            elif key == "6":
                ec.ec_write(ECS.GPU_FAN_MODE_CONTROL.value, ECS.GPU_MANUAL_MODE.value)
                gpu_mode = PFS.Manual
            elif key == "KEY_UP" and cpu_mode == PFS.Manual:
                cpu_manual_level = min(10, cpu_manual_level+1)
                ec.ec_write(ECS.CPU_MANUAL_SPEED_CONTROL.value, cpu_manual_level*10)
            elif key == "KEY_DOWN" and cpu_mode == PFS.Manual:
                cpu_manual_level = max(0, cpu_manual_level-1)
                ec.ec_write(ECS.CPU_MANUAL_SPEED_CONTROL.value, cpu_manual_level*10)
            elif key == "KEY_RIGHT" and gpu_mode == PFS.Manual:
                gpu_manual_level = min(10, gpu_manual_level+1)
                ec.ec_write(ECS.GPU_MANUAL_SPEED_CONTROL.value, gpu_manual_level*10)
            elif key == "KEY_LEFT" and gpu_mode == PFS.Manual:
                gpu_manual_level = max(0, gpu_manual_level-1)
                ec.ec_write(ECS.GPU_MANUAL_SPEED_CONTROL.value, gpu_manual_level*10)

        elif current_tab == "rgb":
            if key == "KEY_LEFT":
                effect_idx = (effect_idx - 1) % len(EFFECTS)
            elif key == "KEY_RIGHT":
                effect_idx = (effect_idx + 1) % len(EFFECTS)
            elif key == "KEY_UP":
                color_idx = (color_idx - 1) % len(COLORS)
            elif key == "KEY_DOWN":
                color_idx = (color_idx + 1) % len(COLORS)
            elif key in ["+", "="]:
                brightness = min(255, brightness+5)
            elif key == "-":
                brightness = max(0, brightness-5)
            elif key == "\n":
                dev = usb.core.find(idVendor=VENDOR_ID, idProduct=PRODUCT_ID)
                if dev:
                    if dev.is_kernel_driver_active(INTERFACE):
                        dev.detach_kernel_driver(INTERFACE)
                    usb.util.claim_interface(dev, INTERFACE)
                    payload = format_payload(EFFECTS[effect_idx], brightness, COLORS[color_idx])
                    send_payload(dev, payload)
                    usb.util.release_interface(dev, INTERFACE)

    ec.shutdownEC()

if __name__ == "__main__":
    curses.wrapper(dashboard)

    
    
    
    
    
    
    
    
    
    
    
    
    
    

