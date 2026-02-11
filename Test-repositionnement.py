import cv2
import numpy as np
import pytesseract
import tkinter as tk
from tkinter import ttk
import threading
import time
import re
import os
import subprocess
from pathlib import Path
from pynput import keyboard, mouse
from pynput.keyboard import Key, Controller as KeyboardController
from pynput.mouse import Button
import pydirectinput
from mss import mss
from PIL import Image, ImageTk
import pygetwindow as gw

# Configuration pydirectinput
pydirectinput.PAUSE = 0.01  # Reduced for more responsiveness

# Configuration Tesseract
def setup_tesseract():
    """Configure Tesseract with forced path"""
    # Known path - IMPORTANT: use forward slashes for Windows
    tesseract_exe = 'C:/Program Files/Tesseract-OCR/tesseract.exe'

    # Verify existence
    tesseract_check = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
    if os.path.exists(tesseract_check):
        # Configure pytesseract with forward slash path
        pytesseract.pytesseract.pytesseract_cmd = tesseract_exe
        print(f"Tesseract configured: {tesseract_exe}")

        # Also add to PATH
        if 'C:\\Program Files\\Tesseract-OCR' not in os.environ['PATH']:
            os.environ['PATH'] = r'C:\Program Files\Tesseract-OCR' + os.pathsep + os.environ['PATH']

        return tesseract_exe

    # Alternatives
    alt_paths = [
        (r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe', 'C:/Program Files (x86)/Tesseract-OCR/tesseract.exe'),
        (r'D:\Tesseract-OCR\tesseract.exe', 'D:/Tesseract-OCR/tesseract.exe')
    ]

    for check_path, forward_path in alt_paths:
        if os.path.exists(check_path):
            pytesseract.pytesseract.pytesseract_cmd = forward_path
            print(f"Tesseract configured: {forward_path}")
            return forward_path

    print("Tesseract not found!")
    return None

tesseract_path = setup_tesseract()

class RobloxAutomationSystem:
    def __init__(self, root):
        self.root = root
        self.root.title("Roblox Automation System")
        self.root.geometry("800x600")
        self.root.config(bg="#1e1e1e")

        # State
        self.ocr_zone = None
        self.current_coords = {"x": 0.0, "y": 0.0, "z": 0.0}
        self.target_coords = {"x": None, "y": None, "z": None}
        self.cursor_position = None
        self.running = False
        self.click_interval = 3  # seconds
        self.tolerance = 15

        # Controllers
        self.keyboard_ctrl = KeyboardController()
        self.mouse_ctrl = mouse.Controller()

        # UI
        self.setup_ui()

        # Check Tesseract (AFTER setup_ui)
        self.verify_tesseract()

        self.setup_keyboard_listeners()
        self.start_ocr_thread()

    def verify_tesseract(self):
        """Verify that Tesseract is installed and accessible"""
        try:
            # Simple test with subprocess
            result = subprocess.run([pytesseract.pytesseract.pytesseract_cmd, '--version'],
                                  capture_output=True, text=True, timeout=5)
            version = result.stdout.split('\n')[0] if result.stdout else "Unknown version"
            print(f"Tesseract found and functional: {version}")
            self.update_status(f"Tesseract ready")
        except FileNotFoundError as fnf:
            print(f"ERROR: Tesseract not found at {pytesseract.pytesseract.pytesseract_cmd}")
            print(f"  Error: {fnf}")
            self.update_status(f"Tesseract not found")
        except Exception as e:
            print(f"Tesseract verification error: {e}")
            self.update_status(f"Tesseract warning")

    def setup_ui(self):
        """Create the user interface"""
        # Keep the GUI always on top
        self.root.attributes('-topmost', True)

        main_frame = tk.Frame(self.root, bg="#1e1e1e")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Title
        title = tk.Label(main_frame, text="Roblox Automation System",
                        font=("Arial", 16, "bold"), fg="#00ff00", bg="#1e1e1e")
        title.pack(pady=10)

        # Coordinates display
        coords_frame = tk.LabelFrame(main_frame, text="Real-time Coordinates",
                                    font=("Arial", 11, "bold"), fg="#00ff00", bg="#2d2d2d",
                                    foreground="#00ff00")
        coords_frame.pack(fill=tk.X, pady=10)

        self.coord_text = tk.Label(coords_frame, text="X: 0.0  |  Y: 0.0  |  Z: 0.0",
                                  font=("Courier", 14, "bold"), fg="#00ff00", bg="#2d2d2d")
        self.coord_text.pack(pady=15)

        # Target coordinates
        targets_frame = tk.LabelFrame(main_frame, text="Target Position",
                                     font=("Arial", 11, "bold"), fg="#ff6600", bg="#2d2d2d",
                                     foreground="#ff6600")
        targets_frame.pack(fill=tk.X, pady=10)

        self.target_text = tk.Label(targets_frame, text="X: --  |  Y: --  |  Z: --",
                                   font=("Courier", 14, "bold"), fg="#ff6600", bg="#2d2d2d")
        self.target_text.pack(pady=15)

        # Control buttons
        control_frame = tk.LabelFrame(main_frame, text="Controls",
                                     font=("Arial", 11, "bold"), fg="#00aaff", bg="#2d2d2d",
                                     foreground="#00aaff")
        control_frame.pack(fill=tk.X, pady=10)

        btn_frame = tk.Frame(control_frame, bg="#2d2d2d")
        btn_frame.pack(pady=10, padx=10, fill=tk.X)

        btn1 = tk.Button(btn_frame, text="Set Coordinate (F2+Click)", command=self.set_coordinate,
                        bg="#004499", fg="#00aaff", font=("Arial", 10, "bold"))
        btn1.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)

        btn2 = tk.Button(btn_frame, text="Memory Cursor (F5)", command=self.set_cursor_position,
                        bg="#440099", fg="#ff00ff", font=("Arial", 10, "bold"))
        btn2.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)

        btn3 = tk.Button(btn_frame, text="Start Clicks (F6)", command=self.toggle_clicks,
                        bg="#009944", fg="#00ff99", font=("Arial", 10, "bold"))
        btn3.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)

        # Status
        self.status_label = tk.Label(main_frame, text="System ready",
                                    font=("Arial", 10), fg="#00ff00", bg="#1e1e1e")
        self.status_label.pack(pady=10)

        # Help text
        help_text = tk.Label(main_frame, text=
            "F2: Select OCR zone | F1: Auto cycle (6s click + rest) | F5: Memorize cursor | F6: Repeat clicks | ESC: Stop",
            font=("Arial", 9), fg="#999999", bg="#1e1e1e", wraplength=700, justify=tk.CENTER)
        help_text.pack(pady=5)

    def setup_keyboard_listeners(self):
        """Set up keyboard listeners"""
        listener = keyboard.Listener(on_press=self.on_key_press)
        listener.start()

    def on_key_press(self, key):
        """Handle key presses"""
        try:
            if key == Key.f2:
                self.select_ocr_zone()
            elif key == Key.f1:
                self.cycle_main_action()
            elif key == Key.f5:
                self.set_cursor_position()
            elif key == Key.f6:
                self.toggle_clicks()
            elif key == Key.esc:
                self.running = False
                self.update_status("Stop requested")
        except:
            pass

    def select_ocr_zone(self):
        """Allow visual selection of the OCR zone with preview"""
        self.update_status("Select the OCR zone (click and drag, ENTER to confirm)...")

        screenshot = self.capture_screen().copy()
        drawing = screenshot.copy()
        zone_info = {'start': None, 'end': None}

        def mouse_callback(event, x, y, flags, param):
            nonlocal drawing
            drawing = screenshot.copy()

            if event == cv2.EVENT_LBUTTONDOWN:
                zone_info['start'] = (x, y)

            elif event == cv2.EVENT_MOUSEMOVE and zone_info['start']:
                zone_info['end'] = (x, y)

                if zone_info['start'] and zone_info['end']:
                    x1, y1 = zone_info['start']
                    x2, y2 = zone_info['end']

                    x1, x2 = min(x1, x2), max(x1, x2)
                    y1, y2 = min(y1, y2), max(y1, y2)

                    cv2.rectangle(drawing, (x1, y1), (x2, y2), (0, 255, 0), 2)
                    w = abs(x2 - x1)
                    h = abs(y2 - y1)
                    cv2.putText(drawing, f"Zone: {w}x{h}", (x1, y1 - 10),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

            elif event == cv2.EVENT_LBUTTONUP and zone_info['start']:
                zone_info['end'] = (x, y)

            cv2.imshow('Select OCR Zone', drawing)

        cv2.namedWindow('Select OCR Zone', cv2.WINDOW_AUTOSIZE)
        cv2.setMouseCallback('Select OCR Zone', mouse_callback, zone_info)
        cv2.imshow('Select OCR Zone', drawing)

        # Wait for Enter
        while True:
            key = cv2.waitKey(30)
            if key == 13:  # Enter
                break
            elif key == 27:  # ESC
                zone_info['start'] = None
                zone_info['end'] = None
                break

        cv2.destroyAllWindows()

        if zone_info['start'] and zone_info['end']:
            x1, y1 = zone_info['start']
            x2, y2 = zone_info['end']

            x1, x2 = min(x1, x2), max(x1, x2)
            y1, y2 = min(y1, y2), max(y1, y2)

            self.ocr_zone = (x1, y1, x2, y2)
            self.update_status(f"OCR zone defined: X={x1}, Y={y1}, W={x2-x1}, H={y2-y1}")
        else:
            self.update_status("Selection cancelled")

    def capture_screen(self):
        """Capture the screen"""
        with mss() as sct:
            monitor = sct.monitors[1]
            screenshot = sct.grab(monitor)
            frame = np.array(screenshot)
            return cv2.cvtColor(frame, cv2.COLOR_RGBA2BGR)

    def read_coordinates_ocr(self):
        """Read coordinates via OCR"""
        try:
            screenshot = self.capture_screen()

            if self.ocr_zone:
                x1, y1, x2, y2 = self.ocr_zone
                roi = screenshot[y1:y2, x1:x2]
            else:
                # If no zone defined, use the central part
                h, w = screenshot.shape[:2]
                roi = screenshot[int(h*0.4):int(h*0.6), int(w*0.3):int(w*0.7)]

            # Check if ROI is valid
            if roi.size == 0:
                return False

            # Upsampling
            roi = cv2.resize(roi, (0, 0), fx=2, fy=2)

            # HSV conversion
            hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)

            # White/light mask (high values in V)
            msk = cv2.inRange(hsv, np.array([0, 0, 123]), np.array([179, 255, 255]))

            # Contrast enhancement
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
            msk = cv2.morphologyEx(msk, cv2.MORPH_CLOSE, kernel)

            # Save image temporarily
            temp_path = os.path.join(os.path.expanduser("~"), "temp_ocr.png")
            cv2.imwrite(temp_path, msk)

            # OCR optimized for numbers
            txt = ""
            try:
                # Try with pytesseract first
                txt = pytesseract.image_to_string(msk, config='--psm 6 -c tessedit_char_whitelist=0123456789.,-')
            except Exception as ptse:
                # Fallback: use subprocess directly
                try:
                    result = subprocess.run(
                        [pytesseract.pytesseract.pytesseract_cmd, temp_path, 'stdout', '-c', 'tessedit_char_whitelist=0123456789.,-'],
                        capture_output=True, text=True, timeout=10
                    )
                    txt = result.stdout
                except Exception as supe:
                    print(f"OCR completely failed: pytesseract={ptse}, subprocess={supe}")
                    return False

            # Extract coordinates
            numbers = re.findall(r'-?\d+\.?\d*', txt)

            if len(numbers) >= 3:
                try:
                    self.current_coords = {
                        "x": float(numbers[0]),
                        "y": float(numbers[1]),
                        "z": float(numbers[2])
                    }
                    return True
                except ValueError:
                    return False
            return False
        except Exception as e:
            print(f"General OCR error: {e}")
            return False

    def update_coord_display(self):
        """Update coordinate display"""
        coord_str = f"X: {self.current_coords['x']:.1f}  |  Y: {self.current_coords['y']:.1f}  |  Z: {self.current_coords['z']:.1f}"
        self.coord_text.config(text=coord_str)

        if self.target_coords["x"] is not None:
            target_str = f"X: {self.target_coords['x']:.1f}  |  Y: {self.target_coords['y']:.1f}  |  Z: {self.target_coords['z']:.1f}"
            self.target_text.config(text=target_str)

    def set_coordinate(self):
        """Set target coordinate"""
        self.target_coords = self.current_coords.copy()
        self.update_status(f"Target coordinate memorized: X={self.target_coords['x']:.1f}, Y={self.target_coords['y']:.1f}, Z={self.target_coords['z']:.1f}")

    def set_cursor_position(self):
        """Memorize cursor position"""
        self.cursor_position = self.mouse_ctrl.position
        self.update_status(f"Cursor position memorized: {self.cursor_position}")

    def reposition_to_target(self):
        """Reposition via calibration then positioning"""
        if self.target_coords["x"] is None:
            self.update_status("No target defined")
            return False

        # Force focus on Roblox window
        try:
            roblox_windows = gw.getWindowsWithTitle('Roblox')
            if roblox_windows:
                roblox_windows[0].activate()
                time.sleep(0.3)
                print("Focus on Roblox activated")
        except Exception as e:
            print(f"Activation error: {e}")

        self.update_status("Phase 1: Calibration...")
        print("\n=== START REPOSITIONING ===")
        print("Phase 1: CALIBRATION")

        # PHASE 1: CALIBRATION - Determine the best direction for X and Z

        # Read current position
        if not self.read_coordinates_ocr():
            self.update_status("Cannot read OCR")
            return False

        pos_initial_x = self.current_coords["x"]
        pos_initial_z = self.current_coords["z"]
        target_x = self.target_coords["x"]
        target_z = self.target_coords["z"]

        dist_initial_x = abs(target_x - pos_initial_x)
        dist_initial_z = abs(target_z - pos_initial_z)

        print(f"Initial position: X={pos_initial_x:.1f}, Z={pos_initial_z:.1f}")
        print(f"Initial distance: dX={dist_initial_x:.1f}, dZ={dist_initial_z:.1f}")

        # Test direction A (left) - MULTIPLE TIMES for clear signal
        print("\n→ TEST: Press A (left) x3 (0.7s each)...")
        for i in range(3):
            pydirectinput.keyDown("a")
            time.sleep(0.7)
            pydirectinput.keyUp("a")
            time.sleep(0.3)

        if self.read_coordinates_ocr():
            dist_after_a = abs(target_x - self.current_coords["x"])
            print(f"  Distance X after: {dist_after_a:.1f}")
        else:
            dist_after_a = dist_initial_x

        # Return to initial position (loop until close)
        print("→ RETURN to initial position (press D to correct A)...")
        return_attempts = 0
        last_diff_x = abs(pos_initial_x - self.current_coords["x"])
        current_key_return_x = "d"
        while abs(pos_initial_x - self.current_coords["x"]) > 15 and return_attempts < 10:
            pydirectinput.keyDown(current_key_return_x)
            time.sleep(0.7)
            pydirectinput.keyUp(current_key_return_x)
            time.sleep(0.3)
            self.read_coordinates_ocr()
            diff_x = abs(pos_initial_x - self.current_coords["x"])

            # If distance increases, reverse direction!
            if diff_x > last_diff_x:
                current_key_return_x = "a" if current_key_return_x == "d" else "d"
                print(f"  Attempt {return_attempts+1}: X={self.current_coords['x']:.1f} (diff={diff_x:.1f}) ❌ Moving away! Reverse → {current_key_return_x}")
            else:
                print(f"  Attempt {return_attempts+1}: X={self.current_coords['x']:.1f} (diff={diff_x:.1f})")

            last_diff_x = diff_x
            return_attempts += 1

        # Test direction D (right) - MULTIPLE TIMES for clear signal
        print("→ TEST: Press D (right) x3 (0.7s each)...")
        for i in range(3):
            pydirectinput.keyDown("d")
            time.sleep(0.7)
            pydirectinput.keyUp("d")
            time.sleep(0.3)

        if self.read_coordinates_ocr():
            dist_after_d = abs(target_x - self.current_coords["x"])
            print(f"  Distance X after: {dist_after_d:.1f}")
        else:
            dist_after_d = dist_initial_x

        # Choose best direction for X
        if dist_after_a < dist_after_d:
            best_key_x = "a"
            reverse_key_x = "d"
            print(f"✓ Best direction X: A (distance: {dist_after_a:.1f})")
        else:
            best_key_x = "d"
            reverse_key_x = "a"
            print(f"✓ Best direction X: D (distance: {dist_after_d:.1f})")

        # Return to initial position to test Z (loop until close)
        print(f"→ RETURN to initial position (press {reverse_key_x} to correct D)...")
        return_attempts = 0
        last_diff_x = abs(pos_initial_x - self.current_coords["x"])
        current_key_return_x = reverse_key_x
        while abs(pos_initial_x - self.current_coords["x"]) > 15 and return_attempts < 10:
            pydirectinput.keyDown(current_key_return_x)
            time.sleep(0.7)
            pydirectinput.keyUp(current_key_return_x)
            time.sleep(0.3)
            self.read_coordinates_ocr()
            diff_x = abs(pos_initial_x - self.current_coords["x"])

            # If distance increases, reverse direction!
            if diff_x > last_diff_x:
                current_key_return_x = reverse_key_x if current_key_return_x == best_key_x else best_key_x
                print(f"  Attempt {return_attempts+1}: X={self.current_coords['x']:.1f} (diff={diff_x:.1f}) ❌ Moving away! Reverse → {current_key_return_x}")
            else:
                print(f"  Attempt {return_attempts+1}: X={self.current_coords['x']:.1f} (diff={diff_x:.1f})")

            last_diff_x = diff_x
            return_attempts += 1

        print(f"Position before Z test: X={self.current_coords['x']:.1f}, Z={self.current_coords['z']:.1f}")

        # Test direction W (forward) - MULTIPLE TIMES for clear signal
        print("\n→ TEST: Press W (forward) x3 (0.8s each)...")
        for i in range(3):
            pydirectinput.keyDown("w")
            time.sleep(0.8)
            pydirectinput.keyUp("w")
            time.sleep(0.3)

        if self.read_coordinates_ocr():
            dist_after_w = abs(target_z - self.current_coords["z"])
            print(f"  Distance Z after: {dist_after_w:.1f}")
        else:
            dist_after_w = dist_initial_z

        # Return to initial position (loop until close)
        print("→ RETURN to initial position (press S to correct W)...")
        return_attempts = 0
        last_diff_z = abs(pos_initial_z - self.current_coords["z"])
        current_key_return_z = "s"
        while abs(pos_initial_z - self.current_coords["z"]) > 15 and return_attempts < 10:
            pydirectinput.keyDown(current_key_return_z)
            time.sleep(0.8)
            pydirectinput.keyUp(current_key_return_z)
            time.sleep(0.3)
            self.read_coordinates_ocr()
            diff_z = abs(pos_initial_z - self.current_coords["z"])

            # If distance increases, reverse direction!
            if diff_z > last_diff_z:
                current_key_return_z = "w" if current_key_return_z == "s" else "s"
                print(f"  Attempt {return_attempts+1}: Z={self.current_coords['z']:.1f} (diff={diff_z:.1f}) ❌ Moving away! Reverse → {current_key_return_z}")
            else:
                print(f"  Attempt {return_attempts+1}: Z={self.current_coords['z']:.1f} (diff={diff_z:.1f})")

            last_diff_z = diff_z
            return_attempts += 1

        # Test direction S (backward) - MULTIPLE TIMES for clear signal
        print("→ TEST: Press S (backward) x3 (0.8s each)...")
        for i in range(3):
            pydirectinput.keyDown("s")
            time.sleep(0.8)
            pydirectinput.keyUp("s")
            time.sleep(0.3)

        if self.read_coordinates_ocr():
            dist_after_s = abs(target_z - self.current_coords["z"])
            print(f"  Distance Z after: {dist_after_s:.1f}")
        else:
            dist_after_s = dist_initial_z

        # Choose best direction for Z
        if dist_after_w < dist_after_s:
            best_key_z = "w"
            reverse_key_z = "s"
            print(f"✓ Best direction Z: W (distance: {dist_after_w:.1f})")
        else:
            best_key_z = "s"
            reverse_key_z = "w"
            print(f"✓ Best direction Z: S (distance: {dist_after_s:.1f})")

        # Return to initial position to start positioning (loop)
        print(f"→ FINAL RETURN to initial position (press {reverse_key_z} to correct S)...")
        return_attempts = 0
        last_diff_z = abs(pos_initial_z - self.current_coords["z"])
        current_key_return_z = reverse_key_z
        while abs(pos_initial_z - self.current_coords["z"]) > 15 and return_attempts < 10:
            pydirectinput.keyDown(current_key_return_z)
            time.sleep(0.8)
            pydirectinput.keyUp(current_key_return_z)
            time.sleep(0.3)
            self.read_coordinates_ocr()
            diff_z = abs(pos_initial_z - self.current_coords["z"])

            # If distance increases, reverse direction!
            if diff_z > last_diff_z:
                current_key_return_z = reverse_key_z if current_key_return_z == best_key_z else best_key_z
                print(f"  Attempt {return_attempts+1}: Z={self.current_coords['z']:.1f} (diff={diff_z:.1f}) ❌ Moving away! Reverse → {current_key_return_z}")
            else:
                print(f"  Attempt {return_attempts+1}: Z={self.current_coords['z']:.1f} (diff={diff_z:.1f})")

            last_diff_z = diff_z
            return_attempts += 1

        print(f"INITIAL position for Phase 2: X={self.current_coords['x']:.1f}, Z={self.current_coords['z']:.1f}")

        print("\n=== Phase 2: POSITIONING ===")
        self.update_status("Phase 2: Positioning...")

        # PHASE 2: POSITIONING - Press in the right directions until arrival
        # With overshoot management and diagonals
        max_attempts = 150
        attempts = 0

        while attempts < max_attempts:
            if not self.read_coordinates_ocr():
                time.sleep(0.1)
                attempts += 1
                continue

            self.update_coord_display()

            current_x = self.current_coords["x"]
            current_z = self.current_coords["z"]

            dist_x = abs(target_x - current_x)
            dist_z = abs(target_z - current_z)

            # Check if overshot (sign changes)
            overshoot_x = (target_x - current_x) * (target_x - pos_initial_x) < 0
            overshoot_z = (target_z - current_z) * (target_z - pos_initial_z) < 0

            print(f"[{attempts}] X={current_x:.1f} (dist={dist_x:.1f}, overshoot={overshoot_x}), Z={current_z:.1f} (dist={dist_z:.1f}, overshoot={overshoot_z})")

            # Check if arrived
            if dist_x <= self.tolerance and dist_z <= self.tolerance:
                self.update_status("Target position reached")
                print("=== POSITION REACHED ===\n")
                return True

            # Determine keys to press
            key_x = reverse_key_x if overshoot_x else best_key_x
            key_z = reverse_key_z if overshoot_z else best_key_z

            # If both axes need correction → DIAGONAL
            if dist_x > self.tolerance and dist_z > self.tolerance:
                print(f"  → DIAGONAL press: {key_z}+{key_x} (0.7s)")
                pydirectinput.keyDown(key_z)
                pydirectinput.keyDown(key_x)
                time.sleep(0.7)
                pydirectinput.keyUp(key_z)
                pydirectinput.keyUp(key_x)
                time.sleep(0.3)

            # Correct X ONLY (ONCE per iteration)
            elif dist_x > self.tolerance:
                print(f"  → X ONLY press: {key_x} (0.7s) | Z={self.current_coords['z']:.1f}")
                pydirectinput.keyDown(key_x)
                time.sleep(0.7)
                pydirectinput.keyUp(key_x)
                time.sleep(0.3)

            # Correct Z ONLY (ONCE per iteration)
            elif dist_z > self.tolerance:
                print(f"  → Z ONLY press: {key_z} (0.8s) | X={self.current_coords['x']:.1f}")
                pydirectinput.keyDown(key_z)
                time.sleep(0.8)
                pydirectinput.keyUp(key_z)
                time.sleep(0.3)

            attempts += 1

        self.update_status("Repositioning completed (timeout)")
        print("=== REPOSITIONING TIMEOUT ===\n")
        return False

    def cycle_main_action(self):
        """Main cycle: 6s click + repositioning until arrival"""
        if self.cursor_position is None:
            self.update_status("Memorize cursor with F5 first")
            return

        if self.target_coords["x"] is None:
            self.update_status("Set target with Set Coordinate")
            return

        self.running = True

        while self.running:
            # Phase 1: Click for 6 seconds
            self.update_status("Phase 1: Held clicks (6s)...")
            end_time = time.time() + 6
            while time.time() < end_time and self.running:
                self.mouse_ctrl.position = self.cursor_position
                self.mouse_ctrl.press(Button.left)
                time.sleep(0.05)
                self.mouse_ctrl.release(Button.left)
                time.sleep(0.05)

            if not self.running:
                break

            # Phase 2: Repositioning until arrival (no time limit)
            self.update_status("Phase 2: Repositioning until arrival...")
            self.reposition_to_target()

            if not self.running:
                break

            self.update_status("Next cycle...")
            time.sleep(0.5)  # Short pause between cycles

    def toggle_clicks(self):
        """Enable/disable repeated clicks"""
        self.running = not self.running

        if self.running:
            if self.cursor_position is None:
                self.update_status("Memorize cursor with F5 first")
                self.running = False
                return
            self.update_status(f"Repeated clicks every {self.click_interval}s")
            threading.Thread(target=self.click_loop, daemon=True).start()
        else:
            self.update_status("Clicks stopped")

    def click_loop(self):
        """Repeated clicks loop"""
        while self.running:
            self.mouse_ctrl.position = self.cursor_position
            self.mouse_ctrl.press(Button.left)
            time.sleep(0.1)
            self.mouse_ctrl.release(Button.left)
            time.sleep(self.click_interval - 0.1)

    def start_ocr_thread(self):
        """Start continuous OCR reading thread"""
        def ocr_loop():
            while True:
                self.read_coordinates_ocr()
                self.update_coord_display()
                time.sleep(0.5)

        threading.Thread(target=ocr_loop, daemon=True).start()

    def update_status(self, message):
        """Update status message"""
        self.status_label.config(text=message)

if __name__ == "__main__":
    root = tk.Tk()
    app = RobloxAutomationSystem(root)
    root.mainloop()
