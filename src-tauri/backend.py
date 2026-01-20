from flask import Flask, request, jsonify
from flask_cors import CORS
import keyboard
import threading
import json
import os
import time
import mss
import numpy as np
import ctypes
import pyautogui
from pynput import mouse
import win32gui
import win32con
import tkinter as tk
from tkinter import ttk

pyautogui.PAUSE = 0

try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except:
        pass

app = Flask(__name__)
CORS(app)

class AreaSelector:
    def __init__(self, parent, initialBox, callback):
        self.Callback = callback
        self.Parent = parent
        self.Closed = False
        
        self.Window = tk.Tk()
        self.Window.attributes('-alpha', 0.6)
        self.Window.attributes('-topmost', True)
        self.Window.overrideredirect(True)
        self.X1, self.Y1 = initialBox["x1"], initialBox["y1"]
        self.X2, self.Y2 = initialBox["x2"], initialBox["y2"]
        width = self.X2 - self.X1
        height = self.Y2 - self.Y1
        self.Window.geometry(f"{width}x{height}+{self.X1}+{self.Y1}")
        self.Window.configure(bg='blue')
        self.Canvas = tk.Canvas(self.Window, bg='blue', highlightthickness=3, highlightbackground='black')
        self.Canvas.pack(fill='both', expand=True)
        self.Dragging = False
        self.Resizing = False
        self.ResizeEdge = None
        self.StartX = 0
        self.StartY = 0
        self.ResizeThreshold = 10
        self.Canvas.bind('<Button-1>', self.OnMouseDown)
        self.Canvas.bind('<B1-Motion>', self.OnMouseDrag)
        self.Canvas.bind('<ButtonRelease-1>', self.OnMouseUp)
        self.Canvas.bind('<Motion>', self.OnMouseMove)
        
        self.Window.bind('<Return>', lambda e: self.Close())
        self.Window.bind('<Escape>', lambda e: self.Close())
        
        self.Window.protocol("WM_DELETE_WINDOW", self.Close)
        
        self.Window.mainloop()

    def OnMouseMove(self, event):
        x, y = event.x, event.y
        width = self.Window.winfo_width()
        height = self.Window.winfo_height()
        atLeft = x < self.ResizeThreshold
        atRight = x > width - self.ResizeThreshold
        atTop = y < self.ResizeThreshold
        atBottom = y > height - self.ResizeThreshold

        if atLeft and atTop:
            self.Canvas.config(cursor='top_left_corner')
        elif atRight and atTop:
            self.Canvas.config(cursor='top_right_corner')
        elif atLeft and atBottom:
            self.Canvas.config(cursor='bottom_left_corner')
        elif atRight and atBottom:
            self.Canvas.config(cursor='bottom_right_corner')
        elif atLeft or atRight:
            self.Canvas.config(cursor='sb_h_double_arrow')
        elif atTop or atBottom:
            self.Canvas.config(cursor='sb_v_double_arrow')
        else:
            self.Canvas.config(cursor='fleur')

    def OnMouseDown(self, event):
        self.StartX = event.x
        self.StartY = event.y
        x, y = event.x, event.y
        width = self.Window.winfo_width()
        height = self.Window.winfo_height()
        atLeft = x < self.ResizeThreshold
        atRight = x > width - self.ResizeThreshold
        atTop = y < self.ResizeThreshold
        atBottom = y > height - self.ResizeThreshold

        if atLeft or atRight or atTop or atBottom:
            self.Resizing = True
            self.ResizeEdge = {'left': atLeft, 'right': atRight, 'top': atTop, 'bottom': atBottom}
        else:
            self.Dragging = True

    def OnMouseDrag(self, event):
        if self.Dragging:
            dx = event.x - self.StartX
            dy = event.y - self.StartY
            newX = self.Window.winfo_x() + dx
            newY = self.Window.winfo_y() + dy
            self.Window.geometry(f"+{newX}+{newY}")
        elif self.Resizing:
            currentX = self.Window.winfo_x()
            currentY = self.Window.winfo_y()
            currentWidth = self.Window.winfo_width()
            currentHeight = self.Window.winfo_height()
            newX = currentX
            newY = currentY
            newWidth = currentWidth
            newHeight = currentHeight

            if self.ResizeEdge['left']:
                dx = event.x - self.StartX
                newX = currentX + dx
                newWidth = currentWidth - dx
            elif self.ResizeEdge['right']:
                newWidth = event.x

            if self.ResizeEdge['top']:
                dy = event.y - self.StartY
                newY = currentY + dy
                newHeight = currentHeight - dy
            elif self.ResizeEdge['bottom']:
                newHeight = event.y

            if newWidth < 50:
                newWidth = 50
                newX = currentX
            if newHeight < 50:
                newHeight = 50
                newY = currentY

            self.Window.geometry(f"{newWidth}x{newHeight}+{newX}+{newY}")

    def OnMouseUp(self, event):
        self.Dragging = False
        self.Resizing = False
        self.ResizeEdge = None

    def Close(self):
        if self.Closed:
            return
        self.Closed = True
        
        try:
            x1 = self.Window.winfo_x()
            y1 = self.Window.winfo_y()
            x2 = x1 + self.Window.winfo_width()
            y2 = y1 + self.Window.winfo_height()
            coords = {"x1": x1, "y1": y1, "x2": x2, "y2": y2}
            
            self.Window.quit()
            self.Window.destroy()
            
            if self.Callback:
                self.Callback(coords)
        except Exception as e:
            print(f"Error closing area selector: {e}")

class FishingMacroBackend:
    def __init__(self):
        user32 = ctypes.windll.user32
        screenWidth = user32.GetSystemMetrics(0)
        screenHeight = user32.GetSystemMetrics(1)

        self.configFile = "Auto Fish Settings.json"
        self.hotkeys = {"start_stop": "f1", "change_area": "f2", "exit": "f3"}

        self.alwaysOnTop = True
        self.showDebugOverlay = False

        self.areaBox = {
            "x1": int(screenWidth * 0.52461),
            "y1": int(screenHeight * 0.29167),
            "x2": int(screenWidth * 0.68477),
            "y2": int(screenHeight * 0.79097)
        }

        self.waterPoint = None

        self.kp = 1.4
        self.kd = 0.6
        self.pdClamp = 1.0
        self.castHoldDuration = 0.1
        self.recastTimeout = 25.0
        self.fishEndDelay = 0.5
        self.rodHotkey = "4"
        self.anythingElseHotkey = "1"
        self.autoBuyCommonBait = True
        self.autoStoreDevilFruit = False
        self.autoSelectTopBait = False

        self.areaSelectorActive = False
        self.areaSelector = None

        self.leftPoint = None
        self.middlePoint = None
        self.rightPoint = None
        self.storeFruitPoint = None
        self.baitPoint = None

        self.loopsPerPurchase = 100
        self.devilFruitHotkey = "6"

        self.robloxFocusDelay = 0.2
        self.robloxPostFocusDelay = 0.2
        self.preCastEDelay = 1.25
        self.preCastClickDelay = 0.5
        self.preCastTypeDelay = 0.25
        self.preCastAntiDetectDelay = 0.05
        self.storeFruitHotkeyDelay = 1.0
        self.storeFruitClickDelay = 2.0
        self.storeFruitShiftDelay = 0.5
        self.storeFruitBackspaceDelay = 1.5
        self.autoSelectBaitDelay = 0.5
        self.blackScreenThreshold = 0.5
        self.antiMacroSpamDelay = 0.25
        self.rodSelectDelay = 0.2
        self.cursorAntiDetectDelay = 0.05
        self.scanLoopDelay = 0.1
        self.pdApproachingDamping = 2.0
        self.pdChasingDamping = 0.5
        self.gapToleranceMultiplier = 2.0
        self.stateResendInterval = 0.5

        self.isRunning = False
        self.isRebinding = None
        self.isHoldingClick = False
        self.lastError = None
        self.lastDarkGrayY = None
        self.lastScanTime = time.time()
        self.lastStateChangeTime = time.time()
        self.lastInputResendTime = time.time()
        self.hasFocusedRoblox = False
        self.baitPurchaseLoopCounter = 0

        self.fishCaught = 0
        self.totalElapsedTime = 0
        self.currentSessionStartTime = None
        self.lastFishTime = None

        self.mouseListener = None
        self.currentPointSetting = None

        self.loadSettings()
        self.setupHotkeys()
    
    def loadSettings(self):
        if os.path.exists(self.configFile):
            try:
                with open(self.configFile, 'r') as f:
                    data = json.load(f)

                    self.hotkeys.update(data.get("hotkeys", {}))
                    self.areaBox.update(data.get("area_box", {}))

                    self.alwaysOnTop = data.get("always_on_top", True)
                    self.showDebugOverlay = data.get("show_debug_overlay", False)

                    self.waterPoint = data.get("water_point", None)

                    self.kp = data.get("kp", 1.4)
                    self.kd = data.get("kd", 0.6)
                    self.pdClamp = data.get("pd_clamp", 1.0)

                    self.castHoldDuration = data.get("cast_hold_duration", 0.1)
                    self.recastTimeout = data.get("recast_timeout", 25.0)
                    self.fishEndDelay = data.get("fish_end_delay", 0.5)

                    self.rodHotkey = data.get("rod_hotkey", "4")
                    self.anythingElseHotkey = data.get("anything_else_hotkey", "1")
                    self.devilFruitHotkey = data.get("devil_fruit_hotkey", "6")

                    self.autoBuyCommonBait = data.get("auto_buy_common_bait", True)
                    self.autoStoreDevilFruit = data.get("auto_store_devil_fruit", False)
                    self.autoSelectTopBait = data.get("auto_select_top_bait", False)

                    self.leftPoint = data.get("left_point", None)
                    self.middlePoint = data.get("middle_point", None)
                    self.rightPoint = data.get("right_point", None)
                    self.storeFruitPoint = data.get("store_fruit_point", None)
                    self.baitPoint = data.get("bait_point", None)

                    self.loopsPerPurchase = data.get("loops_per_purchase", 100)

                    self.robloxFocusDelay = data.get("roblox_focus_delay", 0.2)
                    self.robloxPostFocusDelay = data.get("roblox_post_focus_delay", 0.2)
                    self.preCastEDelay = data.get("pre_cast_e_delay", 1.25)
                    self.preCastClickDelay = data.get("pre_cast_click_delay", 0.5)
                    self.preCastTypeDelay = data.get("pre_cast_type_delay", 0.25)
                    self.preCastAntiDetectDelay = data.get("pre_cast_anti_detect_delay", 0.05)

                    self.storeFruitHotkeyDelay = data.get("store_fruit_hotkey_delay", 1.0)
                    self.storeFruitClickDelay = data.get("store_fruit_click_delay", 2.0)
                    self.storeFruitShiftDelay = data.get("store_fruit_shift_delay", 0.5)
                    self.storeFruitBackspaceDelay = data.get("store_fruit_backspace_delay", 1.5)

                    self.autoSelectBaitDelay = data.get("auto_select_bait_delay", 0.5)
                    self.blackScreenThreshold = data.get("black_screen_threshold", 0.5)
                    self.antiMacroSpamDelay = data.get("anti_macro_spam_delay", 0.25)
                    self.rodSelectDelay = data.get("rod_select_delay", 0.2)
                    self.cursorAntiDetectDelay = data.get("cursor_anti_detect_delay", 0.05)
                    self.scanLoopDelay = data.get("scan_loop_delay", 0.1)

                    self.pdApproachingDamping = data.get("pd_approaching_damping", 2.0)
                    self.pdChasingDamping = data.get("pd_chasing_damping", 0.5)
                    self.gapToleranceMultiplier = data.get("gap_tolerance_multiplier", 2.0)
                    self.stateResendInterval = data.get("state_resend_interval", 0.5)
            except Exception as e:
                import traceback
                traceback.print_exc()

    
    def saveSettings(self):
        try:
            with open(self.configFile, 'w') as f:
                json.dump({
                    "hotkeys": self.hotkeys,
                    "area_box": self.areaBox,
                    "always_on_top": self.alwaysOnTop,
                    "show_debug_overlay": self.showDebugOverlay,
                    "water_point": self.waterPoint,
                    "kp": self.kp,
                    "kd": self.kd,
                    "pd_clamp": self.pdClamp,
                    "cast_hold_duration": self.castHoldDuration,
                    "recast_timeout": self.recastTimeout,
                    "fish_end_delay": self.fishEndDelay,
                    "rod_hotkey": self.rodHotkey,
                    "anything_else_hotkey": self.anythingElseHotkey,
                    "auto_buy_common_bait": self.autoBuyCommonBait,
                    "auto_store_devil_fruit": self.autoStoreDevilFruit,
                    "auto_select_top_bait": self.autoSelectTopBait,
                    "left_point": self.leftPoint,
                    "middle_point": self.middlePoint,
                    "right_point": self.rightPoint,
                    "loops_per_purchase": self.loopsPerPurchase,
                    "store_fruit_point": self.storeFruitPoint,
                    "devil_fruit_hotkey": self.devilFruitHotkey,
                    "bait_point": self.baitPoint,
                    "pd_approaching_damping": self.pdApproachingDamping,
                    "pd_chasing_damping": self.pdChasingDamping,
                    "gap_tolerance_multiplier": self.gapToleranceMultiplier,
                    "state_resend_interval": self.stateResendInterval
                }, f, indent=4)
        except Exception as e:
            print(f"Error saving settings: {e}")
    
    def setupHotkeys(self):
        try:
            keyboard.add_hotkey(self.hotkeys["start_stop"], self.toggleMacro)
            keyboard.add_hotkey(self.hotkeys["change_area"], self.changeArea)
            keyboard.add_hotkey(self.hotkeys["exit"], self.forceExit)
        except Exception as e:
            print(f"Error setting up hotkeys: {e}")
    
    def toggleMacro(self):
        self.isRunning = not self.isRunning
        
        if self.isRunning:
            self.currentSessionStartTime = time.time()
            self.hasFocusedRoblox = False
            threading.Thread(target=self.mainLoop, daemon=True).start()
        else:
            if self.currentSessionStartTime:
                self.totalElapsedTime += time.time() - self.currentSessionStartTime
                self.currentSessionStartTime = None
            if self.isHoldingClick:
                pyautogui.mouseUp()
                self.isHoldingClick = False
    
    def changeArea(self):
        if self.areaSelectorActive:
            if self.areaSelector:
                try:
                    self.areaSelector.Window.after(10, self.areaSelector.Close)
                except:
                    pass
            return
        
        self.areaSelectorActive = True
        
        def runSelector():
            try:
                self.areaSelector = AreaSelector(None, self.areaBox, self.onAreaSelected)
            finally:
                self.areaSelectorActive = False
                self.areaSelector = None
        
        threading.Thread(target=runSelector, daemon=True).start()

    def onAreaSelected(self, coords):
        self.areaBox = coords
        self.saveSettings()
        self.areaSelector = None
        self.areaSelectorActive = False
    
    def forceExit(self):
        os._exit(0)
    
    def setPoint(self, pointName):
        if self.mouseListener:
            self.mouseListener.stop()
        
        self.currentPointSetting = pointName
        
        def onClick(x, y, button, pressed):
            if pressed and self.currentPointSetting == pointName:
                setattr(self, pointName, {"x": x, "y": y})
                self.saveSettings()
                self.currentPointSetting = None
                return False
        
        self.mouseListener = mouse.Listener(on_click=onClick)
        self.mouseListener.start()
    
    def mainLoop(self):
        while self.isRunning:
            try:
                self.lastError = None
                self.lastDarkGrayY = None
                self.lastScanTime = time.time()
                
                if self.isHoldingClick:
                    pyautogui.mouseUp()
                    self.isHoldingClick = False
                
                if not self.isRunning:
                    break
                
                if not self.preCast():
                    continue
                
                if not self.isRunning:
                    break
                
                if not self.waiting():
                    continue
                
                while self.isRunning:
                    if not self.fishing():
                        break
                
                if self.isRunning:
                    self.fishCaught += 1
                    self.lastFishTime = time.time()
                    
                    delayRemaining = self.fishEndDelay
                    while delayRemaining > 0 and self.isRunning:
                        chunk = min(0.1, delayRemaining)
                        time.sleep(chunk)
                        delayRemaining -= chunk
            
            except Exception as e:
                print(f"Error in Main: {e}")
                break
    
    def preCast(self):
        if not self.hasFocusedRoblox:
            def findRobloxWindow(hwnd, windows):
                if win32gui.IsWindowVisible(hwnd):
                    title = win32gui.GetWindowText(hwnd)
                    if "Roblox" in title:
                        windows.append(hwnd)
            
            windows = []
            win32gui.EnumWindows(findRobloxWindow, windows)
            
            if windows:
                win32gui.SetForegroundWindow(windows[0])
                time.sleep(self.robloxFocusDelay)
                self.hasFocusedRoblox = True
                time.sleep(self.robloxPostFocusDelay)

        if not self.isRunning:
            return False
        
        if self.autoBuyCommonBait and self.leftPoint and self.middlePoint and self.rightPoint:
            if self.baitPurchaseLoopCounter == 0 or self.baitPurchaseLoopCounter >= self.loopsPerPurchase:                
                keyboard.press_and_release('e')
                time.sleep(self.preCastEDelay)
                if not self.isRunning: return False
                
                ctypes.windll.user32.SetCursorPos(self.leftPoint['x'], self.leftPoint['y'])
                time.sleep(self.preCastAntiDetectDelay)
                ctypes.windll.user32.mouse_event(0x0001, 0, 1, 0, 0)
                time.sleep(self.preCastAntiDetectDelay)
                pyautogui.click()
                time.sleep(self.preCastClickDelay)
                if not self.isRunning: return False
                
                ctypes.windll.user32.SetCursorPos(self.middlePoint['x'], self.middlePoint['y'])
                time.sleep(self.preCastAntiDetectDelay)
                ctypes.windll.user32.mouse_event(0x0001, 0, 1, 0, 0)
                time.sleep(self.preCastAntiDetectDelay)
                pyautogui.click()
                time.sleep(self.preCastClickDelay)
                if not self.isRunning: return False
                
                keyboard.write(str(self.loopsPerPurchase))
                time.sleep(self.preCastTypeDelay)
                if not self.isRunning: return False
                
                ctypes.windll.user32.SetCursorPos(self.leftPoint['x'], self.leftPoint['y'])
                time.sleep(self.preCastAntiDetectDelay)
                ctypes.windll.user32.mouse_event(0x0001, 0, 1, 0, 0)
                time.sleep(self.preCastAntiDetectDelay)
                pyautogui.click()
                time.sleep(self.preCastClickDelay)
                if not self.isRunning: return False
                
                ctypes.windll.user32.SetCursorPos(self.rightPoint['x'], self.rightPoint['y'])
                time.sleep(self.preCastAntiDetectDelay)
                ctypes.windll.user32.mouse_event(0x0001, 0, 1, 0, 0)
                time.sleep(self.preCastAntiDetectDelay)
                pyautogui.click()
                time.sleep(self.preCastClickDelay)
                if not self.isRunning: return False
                
                ctypes.windll.user32.SetCursorPos(self.middlePoint['x'], self.middlePoint['y'])
                time.sleep(self.preCastAntiDetectDelay)
                ctypes.windll.user32.mouse_event(0x0001, 0, 1, 0, 0)
                time.sleep(self.preCastAntiDetectDelay)
                pyautogui.click()
                time.sleep(self.preCastClickDelay)
                
                self.baitPurchaseLoopCounter = 1
            else:
                self.baitPurchaseLoopCounter += 1
        
        if not self.isRunning:
            return False
        
        if self.autoStoreDevilFruit and self.storeFruitPoint:
            keyboard.press_and_release(self.devilFruitHotkey)
            time.sleep(self.storeFruitHotkeyDelay)
            if not self.isRunning: return False
            
            ctypes.windll.user32.SetCursorPos(self.storeFruitPoint['x'], self.storeFruitPoint['y'])
            time.sleep(self.preCastAntiDetectDelay)
            ctypes.windll.user32.mouse_event(0x0001, 0, 1, 0, 0)
            time.sleep(self.preCastAntiDetectDelay)
            pyautogui.click()
            time.sleep(self.storeFruitClickDelay)
            if not self.isRunning: return False
            
            keyboard.press_and_release('shift')
            time.sleep(self.storeFruitShiftDelay)
            if not self.isRunning: return False
            
            keyboard.press_and_release('backspace')
            time.sleep(self.storeFruitBackspaceDelay)
            if not self.isRunning: return False
            
            keyboard.press_and_release('shift')

        return True
    
    def waiting(self):
        if not self.waterPoint:
            return False
        
        keyboard.press_and_release(self.anythingElseHotkey)
        time.sleep(self.rodSelectDelay)
        
        if not self.isRunning:
            return False
        
        keyboard.press_and_release(self.rodHotkey)
        time.sleep(self.rodSelectDelay)
        
        if not self.isRunning:
            return False
        
        if self.autoSelectTopBait and self.baitPoint:
            ctypes.windll.user32.SetCursorPos(self.baitPoint['x'], self.baitPoint['y'])
            time.sleep(self.preCastAntiDetectDelay)
            ctypes.windll.user32.mouse_event(0x0001, 0, 1, 0, 0)
            time.sleep(self.preCastAntiDetectDelay)
            pyautogui.click()
            time.sleep(self.autoSelectBaitDelay)
        
        if not self.isRunning:
            return False
        
        ctypes.windll.user32.SetCursorPos(self.waterPoint['x'], self.waterPoint['y'])
        time.sleep(self.cursorAntiDetectDelay)
        ctypes.windll.user32.mouse_event(0x0001, 0, 1, 0, 0)
        
        if not self.isRunning:
            return False
        
        pyautogui.mouseDown()
        time.sleep(self.castHoldDuration)
        
        if not self.isRunning:
            pyautogui.mouseUp()
            return False
        
        pyautogui.mouseUp()
        
        startTime = time.time()
        targetBlue = np.array([85, 170, 255])
        targetWhite = np.array([255, 255, 255])
        targetDarkGray = np.array([25, 25, 25])
        
        while self.isRunning:
            elapsedTime = time.time() - startTime
            
            if elapsedTime >= self.recastTimeout:
                return False
            
            with mss.mss() as sct:
                monitor = {
                    "top": self.areaBox["y1"],
                    "left": self.areaBox["x1"],
                    "width": self.areaBox["x2"] - self.areaBox["x1"],
                    "height": self.areaBox["y2"] - self.areaBox["y1"]
                }
                screenshot = sct.grab(monitor)
                img = np.array(screenshot)
            
            if self.checkBlackScreen(img):
                if not self.handleAntiMacroScreen():
                    return False
                continue
            
            blueMask = ((img[:, :, 2] == targetBlue[0]) & 
                       (img[:, :, 1] == targetBlue[1]) & 
                       (img[:, :, 0] == targetBlue[2]))
            whiteMask = ((img[:, :, 2] == targetWhite[0]) & 
                        (img[:, :, 1] == targetWhite[1]) & 
                        (img[:, :, 0] == targetWhite[2]))
            darkGrayMask = ((img[:, :, 2] == targetDarkGray[0]) & 
                           (img[:, :, 1] == targetDarkGray[1]) & 
                           (img[:, :, 0] == targetDarkGray[2]))
            
            blueFound = np.any(blueMask)
            whiteFound = np.any(whiteMask)
            darkGrayFound = np.any(darkGrayMask)
            
            if blueFound and whiteFound and darkGrayFound:
                return True
            
            time.sleep(self.scanLoopDelay)
        
        return False
    
    def checkBlackScreen(self, img=None):
        if img is None:
            with mss.mss() as sct:
                monitor = {
                    "top": self.areaBox["y1"],
                    "left": self.areaBox["x1"],
                    "width": self.areaBox["x2"] - self.areaBox["x1"],
                    "height": self.areaBox["y2"] - self.areaBox["y1"]
                }
                screenshot = sct.grab(monitor)
                img = np.array(screenshot)
        
        blackMask = ((img[:, :, 2] == 0) & (img[:, :, 1] == 0) & (img[:, :, 0] == 0))
        blackPixelCount = np.sum(blackMask)
        totalPixels = img.shape[0] * img.shape[1]
        blackPercentage = blackPixelCount / totalPixels
        
        return blackPercentage >= self.blackScreenThreshold
    
    def handleAntiMacroScreen(self):
        attempts = 0
        maxAttempts = 20
        
        while self.isRunning and attempts < maxAttempts:
            if not self.checkBlackScreen():
                return True
            
            keyboard.press_and_release(self.anythingElseHotkey)
            time.sleep(self.antiMacroSpamDelay)
            attempts += 1
        
        return False
    
    def fishing(self):
        with mss.mss() as sct:
            monitor = {
                "top": self.areaBox["y1"],
                "left": self.areaBox["x1"],
                "width": self.areaBox["x2"] - self.areaBox["x1"],
                "height": self.areaBox["y2"] - self.areaBox["y1"]
            }
            screenshot = sct.grab(monitor)
            img = np.array(screenshot)
        
        if self.checkBlackScreen(img):
            if self.isHoldingClick:
                pyautogui.mouseUp()
                self.isHoldingClick = False
            self.handleAntiMacroScreen()
            return False
        
        targetColor = np.array([85, 170, 255])
        colorMask = ((img[:, :, 2] == targetColor[0]) & 
                    (img[:, :, 1] == targetColor[1]) & 
                    (img[:, :, 0] == targetColor[2]))
        
        if not np.any(colorMask):
            if self.isHoldingClick:
                pyautogui.mouseUp()
                self.isHoldingClick = False
            return False
        
        yCoords, xCoords = np.where(colorMask)
        middleX = int(np.mean(xCoords))
        
        croppedSlice = img[:, middleX:middleX+1, :]
        
        targetGray = np.array([25, 25, 25])
        grayMask = ((croppedSlice[:, 0, 2] == targetGray[0]) & 
                   (croppedSlice[:, 0, 1] == targetGray[1]) & 
                   (croppedSlice[:, 0, 0] == targetGray[2]))
        
        if not np.any(grayMask):
            return True
        
        grayYCoords = np.where(grayMask)[0]
        topGrayY = grayYCoords[0]
        bottomGrayY = grayYCoords[-1]
        finalSlice = croppedSlice[topGrayY:bottomGrayY+1, :, :]
        
        targetWhite = np.array([255, 255, 255])
        whiteMask = ((finalSlice[:, 0, 2] == targetWhite[0]) & 
                    (finalSlice[:, 0, 1] == targetWhite[1]) & 
                    (finalSlice[:, 0, 0] == targetWhite[2]))
        
        if not np.any(whiteMask):
            return True
        
        whiteYCoords = np.where(whiteMask)[0]
        topWhiteYRelative = whiteYCoords[0]
        bottomWhiteYRelative = whiteYCoords[-1]
        whiteHeight = bottomWhiteYRelative - topWhiteYRelative + 1
        middleWhiteYRelative = (topWhiteYRelative + bottomWhiteYRelative) // 2
        middleWhiteYScreen = self.areaBox["y1"] + topGrayY + middleWhiteYRelative
        
        targetDarkGray = np.array([25, 25, 25])
        darkGrayMask = ((finalSlice[:, 0, 2] == targetDarkGray[0]) & 
                       (finalSlice[:, 0, 1] == targetDarkGray[1]) & 
                       (finalSlice[:, 0, 0] == targetDarkGray[2]))
        
        if not np.any(darkGrayMask):
            return True
        
        darkGrayYCoords = np.where(darkGrayMask)[0]
        gapTolerance = whiteHeight * self.gapToleranceMultiplier
        
        groups = []
        currentGroup = [darkGrayYCoords[0]]
        
        for i in range(1, len(darkGrayYCoords)):
            if darkGrayYCoords[i] - darkGrayYCoords[i-1] <= gapTolerance:
                currentGroup.append(darkGrayYCoords[i])
            else:
                groups.append(currentGroup)
                currentGroup = [darkGrayYCoords[i]]
        
        groups.append(currentGroup)
        
        biggestGroup = max(groups, key=len)
        biggestGroupMiddle = (biggestGroup[0] + biggestGroup[-1]) // 2
        biggestGroupMiddleYScreen = self.areaBox["y1"] + topGrayY + biggestGroupMiddle
        
        kp = self.kp
        kd = self.kd
        pdClamp = self.pdClamp
        
        error = middleWhiteYScreen - biggestGroupMiddleYScreen
        pTerm = kp * error
        dTerm = 0.0
        
        currentTime = time.time()
        timeDelta = currentTime - self.lastScanTime
        
        if self.lastError is not None and self.lastDarkGrayY is not None and timeDelta > 0.001:
            darkGrayVelocity = (biggestGroupMiddleYScreen - self.lastDarkGrayY) / timeDelta
            errorMagnitudeDecreasing = abs(error) < abs(self.lastError)
            barMovingTowardTarget = (darkGrayVelocity > 0 and error > 0) or (darkGrayVelocity < 0 and error < 0)
            
            if errorMagnitudeDecreasing and barMovingTowardTarget:
                dampingMultiplier = self.pdApproachingDamping
                dTerm = -kd * dampingMultiplier * darkGrayVelocity
            else:
                dampingMultiplier = self.pdChasingDamping
                dTerm = -kd * dampingMultiplier * darkGrayVelocity
        
        controlSignal = pTerm + dTerm
        controlSignal = max(-pdClamp, min(pdClamp, controlSignal))
        shouldHold = controlSignal <= 0
        
        if shouldHold and not self.isHoldingClick:
            pyautogui.mouseDown()
            self.isHoldingClick = True
            self.lastStateChangeTime = currentTime
            self.lastInputResendTime = currentTime
        elif not shouldHold and self.isHoldingClick:
            pyautogui.mouseUp()
            self.isHoldingClick = False
            self.lastStateChangeTime = currentTime
            self.lastInputResendTime = currentTime
        else:
            timeSinceLastResend = currentTime - self.lastInputResendTime
            
            if timeSinceLastResend >= self.stateResendInterval:
                if self.isHoldingClick:
                    pyautogui.mouseDown()
                else:
                    pyautogui.mouseUp()
                self.lastInputResendTime = currentTime
        
        self.lastError = error
        self.lastDarkGrayY = biggestGroupMiddleYScreen
        self.lastScanTime = currentTime
        
        return True
    
    def getState(self):
        fishPerHour = 0.0
        timeElapsed = "0:00:00"
        totalTime = self.totalElapsedTime
        
        if self.currentSessionStartTime:
            currentSessionTime = time.time() - self.currentSessionStartTime
            totalTime = self.totalElapsedTime + currentSessionTime
        
        if totalTime > 0:
            hours = int(totalTime // 3600)
            minutes = int((totalTime % 3600) // 60)
            seconds = int(totalTime % 60)
            timeElapsed = f"{hours}:{minutes:02d}:{seconds:02d}"
            fishPerHour = (self.fishCaught / totalTime) * 3600
        
        return {
            "isRunning": self.isRunning,
            "fishCaught": self.fishCaught,
            "timeElapsed": timeElapsed,
            "fishPerHour": round(fishPerHour, 1),
            "waterPoint": self.waterPoint,
            "leftPoint": self.leftPoint,
            "middlePoint": self.middlePoint,
            "rightPoint": self.rightPoint,
            "storeFruitPoint": self.storeFruitPoint,
            "baitPoint": self.baitPoint,
            "hotkeys": self.hotkeys,
            "rodHotkey": self.rodHotkey,
            "anythingElseHotkey": self.anythingElseHotkey,
            "devilFruitHotkey": self.devilFruitHotkey,
            "alwaysOnTop": self.alwaysOnTop,
            "showDebugOverlay": self.showDebugOverlay,
            "autoBuyCommonBait": self.autoBuyCommonBait,
            "autoStoreDevilFruit": self.autoStoreDevilFruit,
            "autoSelectTopBait": self.autoSelectTopBait,
            "kp": self.kp,
            "kd": self.kd,
            "pdClamp": self.pdClamp,
            "castHoldDuration": self.castHoldDuration,
            "recastTimeout": self.recastTimeout,
            "fishEndDelay": self.fishEndDelay,
            "loopsPerPurchase": self.loopsPerPurchase,
            "pdApproachingDamping": self.pdApproachingDamping,
            "pdChasingDamping": self.pdChasingDamping,
            "gapToleranceMultiplier": self.gapToleranceMultiplier,
            "stateResendInterval": self.stateResendInterval,
            "robloxFocusDelay": self.robloxFocusDelay,
            "robloxPostFocusDelay": self.robloxPostFocusDelay,
            "preCastEDelay": self.preCastEDelay,
            "preCastClickDelay": self.preCastClickDelay,
            "preCastTypeDelay": self.preCastTypeDelay,
            "preCastAntiDetectDelay": self.preCastAntiDetectDelay,
            "storeFruitHotkeyDelay": self.storeFruitHotkeyDelay,
            "storeFruitClickDelay": self.storeFruitClickDelay,
            "storeFruitShiftDelay": self.storeFruitShiftDelay,
            "storeFruitBackspaceDelay": self.storeFruitBackspaceDelay,
            "autoSelectBaitDelay": self.autoSelectBaitDelay,
            "blackScreenThreshold": self.blackScreenThreshold,
            "antiMacroSpamDelay": self.antiMacroSpamDelay,
            "rodSelectDelay": self.rodSelectDelay,
            "cursorAntiDetectDelay": self.cursorAntiDetectDelay,
            "scanLoopDelay": self.scanLoopDelay
        }

backend = FishingMacroBackend()

@app.route('/state', methods=['GET'])
def get_state():
    return jsonify(backend.getState())

@app.route('/set_window_property', methods=['POST'])
def set_window_property():
    try:
        data = request.json
        property_name = data.get('property')
        
        if property_name == 'always_on_top':
            return jsonify({"alwaysOnTop": backend.alwaysOnTop})
        
        return jsonify({"status": "ok"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    
@app.route('/command', methods=['POST'])
def handle_command():
    try:
        data = request.json
        action = data.get('action')
        payload = data.get('payload')
                
        if action == 'rebind_hotkey':
            backend.isRebinding = payload
            keyboard.unhook_all_hotkeys()
            
            def on_key_event(event):
                if backend.isRebinding == payload:
                    new_hotkey = event.name.lower()
                    backend.hotkeys[payload] = new_hotkey
                    backend.saveSettings()
                    backend.isRebinding = None
                    backend.setupHotkeys()
            
            keyboard.on_release(on_key_event, suppress=False)
            return jsonify({"status": "waiting_for_key"})
        
        elif action == 'set_water_point':
            backend.setPoint('waterPoint')
            return jsonify({"status": "waiting_for_click"})
        
        elif action == 'set_left_point':
            backend.setPoint('leftPoint')
            return jsonify({"status": "waiting_for_click"})
        
        elif action == 'set_middle_point':
            backend.setPoint('middlePoint')
            return jsonify({"status": "waiting_for_click"})
        
        elif action == 'set_right_point':
            backend.setPoint('rightPoint')
            return jsonify({"status": "waiting_for_click"})
        
        elif action == 'set_store_fruit_point':
            backend.setPoint('storeFruitPoint')
            return jsonify({"status": "waiting_for_click"})
        
        elif action == 'set_bait_point':
            backend.setPoint('baitPoint')
            return jsonify({"status": "waiting_for_click"})
        
        elif action == 'set_rod_hotkey':
            backend.rodHotkey = payload
            backend.saveSettings()
            return jsonify({"status": "success"})
        
        elif action == 'set_anything_else_hotkey':
            backend.anythingElseHotkey = payload
            backend.saveSettings()
            return jsonify({"status": "success"})
        
        elif action == 'set_devil_fruit_hotkey':
            backend.devilFruitHotkey = payload
            backend.saveSettings()
            return jsonify({"status": "success"})
        
        elif action == 'toggle_always_on_top':
            backend.alwaysOnTop = payload.lower() == 'true'
            backend.saveSettings()
            return jsonify({"status": "success", "value": backend.alwaysOnTop})

        elif action == 'toggle_debug_overlay':
            backend.showDebugOverlay = payload.lower() == 'true'
            backend.saveSettings()
            return jsonify({"status": "success", "value": backend.showDebugOverlay})
        
        elif action == 'toggle_auto_buy':
            backend.autoBuyCommonBait = payload.lower() == 'true'
            backend.saveSettings()
            return jsonify({"status": "success", "value": backend.autoBuyCommonBait})
        
        elif action == 'toggle_auto_store':
            backend.autoStoreDevilFruit = payload.lower() == 'true'
            backend.saveSettings()
            return jsonify({"status": "success", "value": backend.autoStoreDevilFruit})

        elif action == 'toggle_auto_select_bait':
            backend.autoSelectTopBait = payload.lower() == 'true'
            backend.saveSettings()
            return jsonify({"status": "success", "value": backend.autoSelectTopBait})
        
        elif action == 'set_kp':
            backend.kp = float(payload)
            backend.saveSettings()
            return jsonify({"status": "success"})
        
        elif action == 'set_kd':
            backend.kd = float(payload)
            backend.saveSettings()
            return jsonify({"status": "success"})
        
        elif action == 'set_pd_clamp':
            backend.pdClamp = float(payload)
            backend.saveSettings()
            return jsonify({"status": "success"})
        
        elif action == 'set_pd_approaching':
            backend.pdApproachingDamping = float(payload)
            backend.saveSettings()
            return jsonify({"status": "success"})
        
        elif action == 'set_pd_chasing':
            backend.pdChasingDamping = float(payload)
            backend.saveSettings()
            return jsonify({"status": "success"})
        
        elif action == 'set_gap_tolerance':
            backend.gapToleranceMultiplier = float(payload)
            backend.saveSettings()
            return jsonify({"status": "success"})
        
        elif action == 'set_cast_hold':
            backend.castHoldDuration = float(payload)
            backend.saveSettings()
            return jsonify({"status": "success"})
        
        elif action == 'set_recast_timeout':
            backend.recastTimeout = float(payload)
            backend.saveSettings()
            return jsonify({"status": "success"})
        
        elif action == 'set_fish_end_delay':
            backend.fishEndDelay = float(payload)
            backend.saveSettings()
            return jsonify({"status": "success"})
        
        elif action == 'set_state_resend':
            backend.stateResendInterval = float(payload)
            backend.saveSettings()
            return jsonify({"status": "success"})
        
        elif action == 'set_loops_per_purchase':
            backend.loopsPerPurchase = int(payload)
            backend.saveSettings()
            return jsonify({"status": "success"})
        
        elif action == 'set_focus_delay':
            backend.robloxFocusDelay = float(payload)
            backend.saveSettings()
            return jsonify({"status": "success"})
        
        elif action == 'set_post_focus_delay':
            backend.robloxPostFocusDelay = float(payload)
            backend.saveSettings()
            return jsonify({"status": "success"})
        
        elif action == 'set_precast_e_delay':
            backend.preCastEDelay = float(payload)
            backend.saveSettings()
            return jsonify({"status": "success"})
        
        elif action == 'set_precast_click_delay':
            backend.preCastClickDelay = float(payload)
            backend.saveSettings()
            return jsonify({"status": "success"})
        
        elif action == 'set_precast_type_delay':
            backend.preCastTypeDelay = float(payload)
            backend.saveSettings()
            return jsonify({"status": "success"})
        
        elif action == 'set_anti_detect_delay':
            backend.preCastAntiDetectDelay = float(payload)
            backend.saveSettings()
            return jsonify({"status": "success"})
        
        elif action == 'set_fruit_hotkey_delay':
            backend.storeFruitHotkeyDelay = float(payload)
            backend.saveSettings()
            return jsonify({"status": "success"})
        
        elif action == 'set_fruit_click_delay':
            backend.storeFruitClickDelay = float(payload)
            backend.saveSettings()
            return jsonify({"status": "success"})
        
        elif action == 'set_fruit_shift_delay':
            backend.storeFruitShiftDelay = float(payload)
            backend.saveSettings()
            return jsonify({"status": "success"})
        
        elif action == 'set_fruit_backspace_delay':
            backend.storeFruitBackspaceDelay = float(payload)
            backend.saveSettings()
            return jsonify({"status": "success"})
        
        elif action == 'set_rod_delay':
            backend.rodSelectDelay = float(payload)
            backend.saveSettings()
            return jsonify({"status": "success"})
        
        elif action == 'set_bait_delay':
            backend.autoSelectBaitDelay = float(payload)
            backend.saveSettings()
            return jsonify({"status": "success"})
        
        elif action == 'set_cursor_delay':
            backend.cursorAntiDetectDelay = float(payload)
            backend.saveSettings()
            return jsonify({"status": "success"})
        
        elif action == 'set_scan_delay':
            backend.scanLoopDelay = float(payload)
            backend.saveSettings()
            return jsonify({"status": "success"})
        
        elif action == 'set_black_threshold':
            backend.blackScreenThreshold = float(payload)
            backend.saveSettings()
            return jsonify({"status": "success"})
        
        elif action == 'set_spam_delay':
            backend.antiMacroSpamDelay = float(payload)
            backend.saveSettings()
            return jsonify({"status": "success"})
        
        else:
            return jsonify({"status": "error", "message": f"Unknown action: {action}"}), 400
    
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "ok", "message": "Backend running"})

def run_flask():
    app.run(host='0.0.0.0', port=8765, debug=False, use_reloader=False)

if __name__ == "__main__":
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
        
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        os._exit(0)