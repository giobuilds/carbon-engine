import sys
import blue_debug as blue  # flavored module name, as blue's own tests import it
sys.modules["blue"] = blue
import _trinity_stub_debug as trinity
names = [n for n in dir(trinity) if not n.startswith('_')]
print("trinity module:", trinity.__file__)
print("exposed names:", len(names))
created = []
for cls in ("EveSpaceScene", "EveTransform", "Tr2Mesh", "Tr2Effect", "EveShip2", "Tr2MainWindow", "TriCurveSet"):
    if hasattr(trinity, cls):
        obj = getattr(trinity, cls)()
        created.append(f"{cls}={type(obj).__name__}")
print("created:", ", ".join(created))
t = trinity.EveTransform()
t.name = "linux"
t.translation = (1.0, 2.0, 3.0)
print("EveTransform:", t.name, tuple(t.translation))

device = trinity.TriDevice()  # becomes the global device, as the game sets it up before the window
print("device:", type(device).__name__)
w = trinity.Tr2MainWindow()
w.SetWindowTitle("carbon on linux")
print("title:", w.GetWindowTitle(), "| focus:", w.HasFocus())
st = w.GetDefaultState(1)  # WINDOWED
w.SanitizeState(st)
print("default windowed state:", st)
print("size options (adapter 0, windowed):", w.GetWindowSizeOptions(0, 1)[:5])
try:
    print("SetWindowState ->", w.SetWindowState(st))
    print("state after:", w.GetWindowState(), "| backbuffer:", w.width, "x", w.height)
except Exception as e:
    print("SetWindowState raised:", type(e).__name__, e)
