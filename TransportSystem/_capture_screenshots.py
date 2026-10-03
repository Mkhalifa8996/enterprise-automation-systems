"""Capture a screenshot of every screen in the TransportApp window.

Drives the real application (not a mock-up): seeds the demo dataset into a
throwaway database, walks each navigation tab, and grabs the window with
PIL.ImageGrab. Output goes to docs/screenshots/.

Run from the TransportSystem folder:

    python _capture_screenshots.py
"""
import os
import sys
import time

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

OUT_DIR = os.path.join(HERE, "docs", "screenshots")

# Tk and ImageGrab must agree on pixels. Without this, Windows reports the
# display to Tk at a scaled resolution while ImageGrab grabs real device
# pixels, so every capture is offset and shows whatever is behind the window.
try:
    import ctypes
    ctypes.windll.shcore.SetProcessDpiAwareness(2)   # PER_MONITOR_AWARE
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

# Use a throwaway database so the real one is never touched, and so the
# screenshots show representative content instead of empty tables.
DEMO_DB = os.path.join(HERE, "_screenshot_demo.db")
os.environ["TRANSPORT_DB_PATH"] = DEMO_DB

from transport import data as td  # noqa: E402
from transport.data import demo_data  # noqa: E402


def main():
    from PIL import ImageGrab

    print("seeding demo data...")
    demo_data.seed(verbose=False)
    print(f"  drivers={len(td.load_drivers())} trips={len(td.load_trips())} "
          f"invoices={len(td.load_invoices())}")

    from transport import TransportApp
    from transport.app_config import NAV_ITEMS

    app = TransportApp()

    width = 1360
    height = 780
    app.update_idletasks()
    sw = app.winfo_screenwidth()
    sh = app.winfo_screenheight()
    # never ask for more than the display can show, or the window is clamped
    # and the captured area no longer matches the real size
    width = min(width, sw - 40)
    height = min(height, sh - 80)
    x = max(0, (sw - width) // 2)
    y = max(0, (sh - height) // 2)
    app.geometry(f"{width}x{height}+{x}+{y}")
    app.update_idletasks()
    app.update()
    time.sleep(1.5)

    try:
        app.lift()
        app.focus_force()
        app.attributes("-topmost", True)
        app.update()
        time.sleep(0.5)
    except Exception:
        pass

    os.makedirs(OUT_DIR, exist_ok=True)

    shots = []
    for key, _icon, label in NAV_ITEMS:
        try:
            app.show_page(key)
            app.update_idletasks()
            app.update()
            time.sleep(1.2)
            app.update()

            x = app.winfo_rootx()
            y = app.winfo_rooty()
            w = app.winfo_width()
            h = app.winfo_height()
            img = ImageGrab.grab(bbox=(x, y, x + w, y + h))
            path = os.path.join(OUT_DIR, f"{key}.png")
            img.save(path, optimize=True)
            shots.append((key, label, img.size, path))
            print(f"  captured {key:<12} {img.size[0]}x{img.size[1]}")
        except Exception as exc:
            print(f"  FAILED {key}: {type(exc).__name__}: {exc}")

    try:
        app.destroy()
    except Exception:
        pass

    print(f"\nwrote {len(shots)} screenshots to {OUT_DIR}")
    return shots


if __name__ == "__main__":
    main()