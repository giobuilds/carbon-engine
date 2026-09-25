"""Interactive check of the Vulkan backend's window on Linux (phase 3): opens the main window, clears it with a colour
that changes every frame, and prints the window's callbacks.

Keys: F fullscreen, W windowed, X fixed window, V toggles vsync, C copies text to the clipboard and reads it back,
Esc quits. Closing the window goes through onClose, which allows it.
Every second it prints frames per second (vsync on: the display's refresh rate).
Run with linux-tools/trinity_window_demo.sh; DEMO_SECONDS limits the run time (0 = until closed).
"""
import sys
import blue_debug as blue
sys.modules["blue"] = blue
import importlib, os, time

trinity = importlib.import_module(f"_trinity_{os.environ.get('TRINITY_PLATFORM', 'vulkan')}_debug")
VK_ESCAPE, VK_F, VK_W, VK_X, VK_V, VK_C = 0x1B, ord("F"), ord("W"), ord("X"), ord("V"), ord("C")
FULL_SCREEN, WINDOWED, FIXED_WINDOW = 0, 1, 2

device = trinity.TriDevice()
window = trinity.Tr2MainWindow()
window.SetWindowTitle("Carbon Vulkan window demo")

state = window.GetDefaultState(WINDOWED)
state.width, state.height = 1280, 720
window.SanitizeState(state)
window.SetWindowState(state)
print("window:", window.GetWindowState(), flush=True)

jobs = trinity.Tr2RenderJobs()
device.SetRenderJobs(jobs)
job = trinity.TriRenderJob()
job.name = "demo"
clear = trinity.TriStepClear()
job.steps.append(clear)
jobs.recurring.append(job)


def log(*args):
    print(*args, flush=True)


def set_mode(mode):
    st = window.GetDefaultState(mode)
    if mode == WINDOWED:
        st.width, st.height = 1280, 720
    st.presentInterval = window.GetWindowState().presentInterval
    window.SanitizeState(st)
    window.SetWindowState(st)
    log("mode ->", window.GetWindowState())


def on_key_down(vk, flags):
    log(f"onKeyDown vk=0x{vk:02X} ({window.GetKeyName(vk)!r}) repeat={bool(flags & 0x40000000)}")
    if flags & 0x40000000:
        return
    if vk == VK_F:
        set_mode(FULL_SCREEN)
    elif vk == VK_W:
        set_mode(WINDOWED)
    elif vk == VK_X:
        set_mode(FIXED_WINDOW)
    elif vk == VK_V:
        st = window.GetWindowState()
        st.presentInterval = 0 if st.presentInterval == 1 else 1
        window.SetWindowState(st)
        log("vsync ->", "on" if window.GetWindowState().presentInterval == 1 else "off")
    elif vk == VK_C:
        text = f"carbon clipboard ✓ {time.strftime('%H:%M:%S')}"
        try:
            blue.clipboard.SetClipboardData(text)
            log("clipboard set, read back:", repr(blue.clipboard.GetClipboardUnicode()))
        except OSError as e:
            log("clipboard failed:", e)
    elif vk == VK_ESCAPE:
        log("escape: closing")
        blue.os.Terminate(0)


window.onKeyDown = on_key_down
window.onKeyUp = lambda vk, flags: log(f"onKeyUp vk=0x{vk:02X}")
window.onChar = lambda code, flags, dead: log(f"onChar {chr(code)!r}")
window.onMouseDown = lambda button, x, y: log(f"onMouseDown button={button} at ({x}, {y})")
window.onMouseUp = lambda button, x, y: log(f"onMouseUp button={button} at ({x}, {y})")
window.onMouseWheel = lambda delta: log(f"onMouseWheel {delta}")
window.onFocusChange = lambda focused: log(f"onFocusChange {focused}")
window.onWindowStateChange = lambda st: log(f"onWindowStateChange {st}")
moves = [0]
def on_mouse_move(x, y):
    moves[0] += 1
    if moves[0] % 30 == 1:
        log(f"onMouseMove ({x}, {y}) [every 30th]")
window.onMouseMove = on_mouse_move
def on_close():
    log("onClose: allowing")
    return True
window.onClose = on_close

if os.environ.get("DEMO_CLIPBOARD"):
    try:
        blue.clipboard.SetClipboardData("carbon clipboard ✓")
        log("clipboard round trip:", repr(blue.clipboard.GetClipboardUnicode()))
    except OSError as e:
        log("clipboard failed:", e)

limit = float(os.environ.get("DEMO_SECONDS", "0"))
start = last = time.monotonic()
frames = 0
while True:
    now = time.monotonic()
    t = now - start
    clear.color = (0.5 + 0.5 * __import__("math").sin(t), 0.3, 0.5 + 0.5 * __import__("math").cos(t * 0.7), 1.0)
    blue.os.Pump()
    frames += 1
    if now - last >= 1.0:
        log(f"{frames / (now - last):.1f} frames/s, back buffer {window.width}x{window.height}, focus {window.HasFocus()}")
        frames, last = 0, now
    if limit and t > limit:
        log("time limit reached")
        break
