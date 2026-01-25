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

FlaskApplication = Flask(__name__)
CORS(FlaskApplication)

class RegionSelectionWindow:
    def __init__(self, ParentWindow, InitialBoundingBox, CompletionCallback):
        self.CompletionCallback = CompletionCallback
        self.ParentWindow = ParentWindow
        self.IsWindowClosed = False

        self.RootWindow = tk.Tk()
        self.RootWindow.attributes('-alpha', 0.6)
        self.RootWindow.attributes('-topmost', True)
        self.RootWindow.overrideredirect(True)
        self.LeftBoundary, self.TopBoundary = InitialBoundingBox["x1"], InitialBoundingBox["y1"]
        self.RightBoundary, self.BottomBoundary = InitialBoundingBox["x2"], InitialBoundingBox["y2"]
        WindowWidth = self.RightBoundary - self.LeftBoundary
        WindowHeight = self.BottomBoundary - self.TopBoundary
        self.RootWindow.geometry(f"{WindowWidth}x{WindowHeight}+{self.LeftBoundary}+{self.TopBoundary}")
        self.RootWindow.configure(bg='blue')
        self.DrawingCanvas = tk.Canvas(self.RootWindow, bg='blue', highlightthickness=3, highlightbackground='black')
        self.DrawingCanvas.pack(fill='both', expand=True)
        self.IsDraggingWindow = False
        self.IsResizingWindow = False
        self.ActiveResizeEdge = None
        self.MouseDownPositionX = 0
        self.MouseDownPositionY = 0
        self.EdgeDetectionThreshold = 10
        self.DrawingCanvas.bind('<Button-1>', self.HandleMousePress)
        self.DrawingCanvas.bind('<B1-Motion>', self.HandleMouseDragMotion)
        self.DrawingCanvas.bind('<ButtonRelease-1>', self.HandleMouseRelease)
        self.DrawingCanvas.bind('<Motion>', self.HandleMouseHover)
        
        self.RootWindow.bind('<Return>', lambda EventData: self.CloseWindow())
        self.RootWindow.bind('<Escape>', lambda EventData: self.CloseWindow())
        
        self.RootWindow.protocol("WM_DELETE_WINDOW", self.CloseWindow)
        
        self.RootWindow.mainloop()

    def HandleMouseHover(self, EventData):
        CurrentMouseX, CurrentMouseY = EventData.x, EventData.y
        CurrentWindowWidth = self.RootWindow.winfo_width()
        CurrentWindowHeight = self.RootWindow.winfo_height()
        IsNearLeftEdge = CurrentMouseX < self.EdgeDetectionThreshold
        IsNearRightEdge = CurrentMouseX > CurrentWindowWidth - self.EdgeDetectionThreshold
        IsNearTopEdge = CurrentMouseY < self.EdgeDetectionThreshold
        IsNearBottomEdge = CurrentMouseY > CurrentWindowHeight - self.EdgeDetectionThreshold

        if IsNearLeftEdge and IsNearTopEdge:
            self.DrawingCanvas.config(cursor='top_left_corner')
        elif IsNearRightEdge and IsNearTopEdge:
            self.DrawingCanvas.config(cursor='top_right_corner')
        elif IsNearLeftEdge and IsNearBottomEdge:
            self.DrawingCanvas.config(cursor='bottom_left_corner')
        elif IsNearRightEdge and IsNearBottomEdge:
            self.DrawingCanvas.config(cursor='bottom_right_corner')
        elif IsNearLeftEdge or IsNearRightEdge:
            self.DrawingCanvas.config(cursor='sb_h_double_arrow')
        elif IsNearTopEdge or IsNearBottomEdge:
            self.DrawingCanvas.config(cursor='sb_v_double_arrow')
        else:
            self.DrawingCanvas.config(cursor='fleur')

    def HandleMousePress(self, EventData):
        self.MouseDownPositionX = EventData.x
        self.MouseDownPositionY = EventData.y
        CurrentMouseX, CurrentMouseY = EventData.x, EventData.y
        CurrentWindowWidth = self.RootWindow.winfo_width()
        CurrentWindowHeight = self.RootWindow.winfo_height()
        IsNearLeftEdge = CurrentMouseX < self.EdgeDetectionThreshold
        IsNearRightEdge = CurrentMouseX > CurrentWindowWidth - self.EdgeDetectionThreshold
        IsNearTopEdge = CurrentMouseY < self.EdgeDetectionThreshold
        IsNearBottomEdge = CurrentMouseY > CurrentWindowHeight - self.EdgeDetectionThreshold

        if IsNearLeftEdge or IsNearRightEdge or IsNearTopEdge or IsNearBottomEdge:
            self.IsResizingWindow = True
            self.ActiveResizeEdge = {'left': IsNearLeftEdge, 'right': IsNearRightEdge, 'top': IsNearTopEdge, 'bottom': IsNearBottomEdge}
        else:
            self.IsDraggingWindow = True

    def HandleMouseDragMotion(self, EventData):
        if self.IsDraggingWindow:
            HorizontalDelta = EventData.x - self.MouseDownPositionX
            VerticalDelta = EventData.y - self.MouseDownPositionY
            UpdatedWindowX = self.RootWindow.winfo_x() + HorizontalDelta
            UpdatedWindowY = self.RootWindow.winfo_y() + VerticalDelta
            self.RootWindow.geometry(f"+{UpdatedWindowX}+{UpdatedWindowY}")
        elif self.IsResizingWindow:
            CurrentWindowX = self.RootWindow.winfo_x()
            CurrentWindowY = self.RootWindow.winfo_y()
            CurrentWindowWidth = self.RootWindow.winfo_width()
            CurrentWindowHeight = self.RootWindow.winfo_height()
            UpdatedWindowX = CurrentWindowX
            UpdatedWindowY = CurrentWindowY
            UpdatedWindowWidth = CurrentWindowWidth
            UpdatedWindowHeight = CurrentWindowHeight

            if self.ActiveResizeEdge['left']:
                HorizontalDelta = EventData.x - self.MouseDownPositionX
                UpdatedWindowX = CurrentWindowX + HorizontalDelta
                UpdatedWindowWidth = CurrentWindowWidth - HorizontalDelta
            elif self.ActiveResizeEdge['right']:
                UpdatedWindowWidth = EventData.x

            if self.ActiveResizeEdge['top']:
                VerticalDelta = EventData.y - self.MouseDownPositionY
                UpdatedWindowY = CurrentWindowY + VerticalDelta
                UpdatedWindowHeight = CurrentWindowHeight - VerticalDelta
            elif self.ActiveResizeEdge['bottom']:
                UpdatedWindowHeight = EventData.y

            if UpdatedWindowWidth < 50:
                UpdatedWindowWidth = 50
                UpdatedWindowX = CurrentWindowX
            if UpdatedWindowHeight < 50:
                UpdatedWindowHeight = 50
                UpdatedWindowY = CurrentWindowY

            self.RootWindow.geometry(f"{UpdatedWindowWidth}x{UpdatedWindowHeight}+{UpdatedWindowX}+{UpdatedWindowY}")

    def HandleMouseRelease(self, EventData):
        self.IsDraggingWindow = False
        self.IsResizingWindow = False
        self.ActiveResizeEdge = None

    def CloseWindow(self):
        if self.IsWindowClosed:
            return
        self.IsWindowClosed = True
        
        try:
            FinalLeftBoundary = self.RootWindow.winfo_x()
            FinalTopBoundary = self.RootWindow.winfo_y()
            FinalRightBoundary = FinalLeftBoundary + self.RootWindow.winfo_width()
            FinalBottomBoundary = FinalTopBoundary + self.RootWindow.winfo_height()
            FinalCoordinates = {"x1": FinalLeftBoundary, "y1": FinalTopBoundary, "x2": FinalRightBoundary, "y2": FinalBottomBoundary}
            
            self.RootWindow.quit()
            self.RootWindow.destroy()
            
            if self.CompletionCallback:
                self.CompletionCallback(FinalCoordinates)
        except Exception as ErrorDetails:
            print(f"Error closing area selector: {ErrorDetails}")

class AutomatedFishingSystem:
    def __init__(self):
        SystemDisplayMetrics = ctypes.windll.user32
        MonitorWidth = SystemDisplayMetrics.GetSystemMetrics(0)
        MonitorHeight = SystemDisplayMetrics.GetSystemMetrics(1)

        self.ConfigurationFilePath = "Auto Fish Settings.json"
        self.GlobalHotkeyBindings = {"start_stop": "f1", "change_area": "f2", "exit": "f3"}

        self.WindowAlwaysOnTopEnabled = True
        self.DebugOverlayVisible = False

        self.ScanningRegionBounds = {
            "x1": int(MonitorWidth * 0.52461),
            "y1": int(MonitorHeight * 0.29167),
            "x2": int(MonitorWidth * 0.68477),
            "y2": int(MonitorHeight * 0.79097)
        }

        self.WaterCastingTargetLocation = None

        self.ProportionalGainCoefficient = 1.4
        self.DerivativeGainCoefficient = 0.6
        self.ControlSignalMaximumClamp = 1.0
        self.MouseHoldDurationForCast = 0.1
        self.MaximumWaitTimeBeforeRecast = 25.0
        self.DelayAfterFishCaptured = 0.5
        self.FishingRodInventorySlot = "4"
        self.AlternateInventorySlot = "1"
        self.AutomaticBaitPurchaseEnabled = True
        self.AutomaticFruitStorageEnabled = False
        self.AutomaticTopBaitSelectionEnabled = False

        self.StoreToBackpackEnabled = False
        self.DevilFruitLocationPoint = None
        self.DevilFruitStorageFrequencyCounter = 50
        self.DevilFruitStorageIterationCounter = 0

        self.RegionSelectorCurrentlyActive = False
        self.ActiveRegionSelectorInstance = None

        self.ShopLeftButtonLocation = None
        self.ShopCenterButtonLocation = None
        self.ShopRightButtonLocation = None
        self.FruitStorageButtonLocation = None
        self.BaitSelectionButtonLocation = None

        self.BaitPurchaseFrequencyCounter = 100
        self.DevilFruitInventorySlot = "6"

        self.RobloxWindowFocusInitialDelay = 0.2
        self.RobloxWindowFocusFollowupDelay = 0.2
        self.PreCastDialogOpenDelay = 1.25
        self.PreCastMouseClickDelay = 0.5
        self.PreCastKeyboardInputDelay = 0.25
        self.PreCastAntiDetectionDelay = 0.05
        self.FruitStorageHotkeyActivationDelay = 1.0
        self.FruitStorageClickConfirmationDelay = 2.0
        self.FruitStorageShiftKeyPressDelay = 0.5
        self.FruitStorageBackspaceDeletionDelay = 1.5
        self.BaitSelectionConfirmationDelay = 0.5
        self.BlackScreenDetectionRatioThreshold = 0.5
        self.AntiMacroDialogSpamDelay = 0.25
        self.InventorySlotSwitchingDelay = 0.2
        self.MouseMovementAntiDetectionDelay = 0.05
        self.ImageProcessingLoopDelay = 0.1
        self.PDControllerApproachingStateDamping = 2.0
        self.PDControllerChasingStateDamping = 0.5
        self.BarGroupingGapToleranceMultiplier = 2.0
        self.InputStateResendFrequency = 0.5

        self.MacroCurrentlyExecuting = False
        self.CurrentlyRebindingHotkey = None
        self.MouseButtonCurrentlyPressed = False
        self.PreviousControlLoopErrorValue = None
        self.PreviousTargetBarVerticalPosition = None
        self.LastImageScanTimestamp = time.time()
        self.LastControlStateChangeTimestamp = time.time()
        self.LastInputResendTimestamp = time.time()
        self.RobloxWindowAlreadyFocused = False
        self.BaitPurchaseIterationCounter = 0

        self.TotalFishSuccessfullyCaught = 0
        self.CumulativeRunningTimeSeconds = 0
        self.CurrentSessionBeginTimestamp = None
        self.MostRecentFishCaptureTimestamp = None

        self.MouseEventListenerInstance = None
        self.CurrentlySettingPointName = None

        self.AutomaticBaitCraftingEnabled = False
        self.CraftLeftButtonLocation = None
        self.CraftMiddleButtonLocation = None
        self.BaitRecipeButtonLocation = None
        self.AddRecipeButtonLocation = None
        self.TopRecipeButtonLocation = None
        self.CraftButtonLocation = None
        self.CloseMenuButtonLocation = None
        self.CraftsPerCycleCount = 80
        self.BaitCraftFrequencyCounter = 40
        self.MoveDurationSeconds = 4.25
        self.BaitCraftIterationCounter = 0

        self.LoadConfigurationFromDisk()
        self.RegisterAllHotkeyBindings()
    
    def LoadConfigurationFromDisk(self):
        if os.path.exists(self.ConfigurationFilePath):
            try:
                with open(self.ConfigurationFilePath, 'r') as ConfigurationFileHandle:
                    ParsedConfigurationData = json.load(ConfigurationFileHandle)

                    self.GlobalHotkeyBindings.update(ParsedConfigurationData.get("hotkeys", {}))
                    self.ScanningRegionBounds.update(ParsedConfigurationData.get("area_box", {}))

                    self.WindowAlwaysOnTopEnabled = ParsedConfigurationData.get("always_on_top", True)
                    self.DebugOverlayVisible = ParsedConfigurationData.get("show_debug_overlay", False)

                    self.WaterCastingTargetLocation = ParsedConfigurationData.get("water_point", None)

                    self.ProportionalGainCoefficient = ParsedConfigurationData.get("kp", 1.4)
                    self.DerivativeGainCoefficient = ParsedConfigurationData.get("kd", 0.6)
                    self.ControlSignalMaximumClamp = ParsedConfigurationData.get("pd_clamp", 1.0)

                    self.MouseHoldDurationForCast = ParsedConfigurationData.get("cast_hold_duration", 0.1)
                    self.MaximumWaitTimeBeforeRecast = ParsedConfigurationData.get("recast_timeout", 25.0)
                    self.DelayAfterFishCaptured = ParsedConfigurationData.get("fish_end_delay", 0.5)

                    self.FishingRodInventorySlot = ParsedConfigurationData.get("rod_hotkey", "4")
                    self.AlternateInventorySlot = ParsedConfigurationData.get("anything_else_hotkey", "1")
                    self.DevilFruitInventorySlot = ParsedConfigurationData.get("devil_fruit_hotkey", "6")

                    self.AutomaticBaitPurchaseEnabled = ParsedConfigurationData.get("auto_buy_common_bait", True)
                    self.AutomaticFruitStorageEnabled = ParsedConfigurationData.get("auto_store_devil_fruit", False)
                    self.AutomaticTopBaitSelectionEnabled = ParsedConfigurationData.get("auto_select_top_bait", False)

                    self.ShopLeftButtonLocation = ParsedConfigurationData.get("left_point", None)
                    self.ShopCenterButtonLocation = ParsedConfigurationData.get("middle_point", None)
                    self.ShopRightButtonLocation = ParsedConfigurationData.get("right_point", None)
                    self.FruitStorageButtonLocation = ParsedConfigurationData.get("store_fruit_point", None)
                    self.BaitSelectionButtonLocation = ParsedConfigurationData.get("bait_point", None)

                    self.BaitPurchaseFrequencyCounter = ParsedConfigurationData.get("loops_per_purchase", 100)

                    self.StoreToBackpackEnabled = ParsedConfigurationData.get("store_to_backpack", False)
                    self.DevilFruitLocationPoint = ParsedConfigurationData.get("devil_fruit_location_point", None)
                    self.DevilFruitStorageFrequencyCounter = ParsedConfigurationData.get("loops_per_store", 50)

                    self.RobloxWindowFocusInitialDelay = ParsedConfigurationData.get("roblox_focus_delay", 0.2)
                    self.RobloxWindowFocusFollowupDelay = ParsedConfigurationData.get("roblox_post_focus_delay", 0.2)
                    self.PreCastDialogOpenDelay = ParsedConfigurationData.get("set_precast_e_delay", 1.25)
                    self.PreCastMouseClickDelay = ParsedConfigurationData.get("pre_cast_click_delay", 0.5)
                    self.PreCastKeyboardInputDelay = ParsedConfigurationData.get("pre_cast_type_delay", 0.25)
                    self.PreCastAntiDetectionDelay = ParsedConfigurationData.get("pre_cast_anti_detect_delay", 0.05)

                    self.FruitStorageHotkeyActivationDelay = ParsedConfigurationData.get("store_fruit_hotkey_delay", 1.0)
                    self.FruitStorageClickConfirmationDelay = ParsedConfigurationData.get("store_fruit_click_delay", 2.0)
                    self.FruitStorageShiftKeyPressDelay = ParsedConfigurationData.get("store_fruit_shift_delay", 0.5)
                    self.FruitStorageBackspaceDeletionDelay = ParsedConfigurationData.get("store_fruit_backspace_delay", 1.5)

                    self.BaitSelectionConfirmationDelay = ParsedConfigurationData.get("auto_select_bait_delay", 0.5)
                    self.BlackScreenDetectionRatioThreshold = ParsedConfigurationData.get("black_screen_threshold", 0.5)
                    self.AntiMacroDialogSpamDelay = ParsedConfigurationData.get("anti_macro_spam_delay", 0.25)
                    self.InventorySlotSwitchingDelay = ParsedConfigurationData.get("rod_select_delay", 0.2)
                    self.MouseMovementAntiDetectionDelay = ParsedConfigurationData.get("cursor_anti_detect_delay", 0.05)
                    self.ImageProcessingLoopDelay = ParsedConfigurationData.get("scan_loop_delay", 0.1)

                    self.PDControllerApproachingStateDamping = ParsedConfigurationData.get("pd_approaching_damping", 2.0)
                    self.PDControllerChasingStateDamping = ParsedConfigurationData.get("pd_chasing_damping", 0.5)
                    self.BarGroupingGapToleranceMultiplier = ParsedConfigurationData.get("gap_tolerance_multiplier", 2.0)
                    self.InputStateResendFrequency = ParsedConfigurationData.get("state_resend_interval", 0.5)

                    self.AutomaticBaitCraftingEnabled = ParsedConfigurationData.get("auto_craft_bait", False)
                    self.CraftLeftButtonLocation = ParsedConfigurationData.get("craft_left_point", None)
                    self.CraftMiddleButtonLocation = ParsedConfigurationData.get("craft_middle_point", None)
                    self.BaitRecipeButtonLocation = ParsedConfigurationData.get("bait_recipe_point", None)
                    self.AddRecipeButtonLocation = ParsedConfigurationData.get("add_recipe_point", None)
                    self.TopRecipeButtonLocation = ParsedConfigurationData.get("top_recipe_point", None)
                    self.CraftButtonLocation = ParsedConfigurationData.get("craft_button_point", None)
                    self.CloseMenuButtonLocation = ParsedConfigurationData.get("close_menu_point", None)
                    self.CraftsPerCycleCount = ParsedConfigurationData.get("crafts_per_cycle", 80)
                    self.BaitCraftFrequencyCounter = ParsedConfigurationData.get("loops_per_craft", 40)
                    self.MoveDurationSeconds = ParsedConfigurationData.get("move_duration", 4.25)
            except Exception as LoadError:
                import traceback
                traceback.print_exc()

    
    def SaveConfigurationToDisk(self):
        try:
            with open(self.ConfigurationFilePath, 'w') as ConfigurationFileHandle:
                json.dump({
                    "hotkeys": self.GlobalHotkeyBindings,
                    "area_box": self.ScanningRegionBounds,
                    "always_on_top": self.WindowAlwaysOnTopEnabled,
                    "show_debug_overlay": self.DebugOverlayVisible,
                    "water_point": self.WaterCastingTargetLocation,
                    "kp": self.ProportionalGainCoefficient,
                    "kd": self.DerivativeGainCoefficient,
                    "pd_clamp": self.ControlSignalMaximumClamp,
                    "cast_hold_duration": self.MouseHoldDurationForCast,
                    "recast_timeout": self.MaximumWaitTimeBeforeRecast,
                    "fish_end_delay": self.DelayAfterFishCaptured,
                    "rod_hotkey": self.FishingRodInventorySlot,
                    "anything_else_hotkey": self.AlternateInventorySlot,
                    "auto_buy_common_bait": self.AutomaticBaitPurchaseEnabled,
                    "auto_store_devil_fruit": self.AutomaticFruitStorageEnabled,
                    "auto_select_top_bait": self.AutomaticTopBaitSelectionEnabled,
                    "left_point": self.ShopLeftButtonLocation,
                    "middle_point": self.ShopCenterButtonLocation,
                    "right_point": self.ShopRightButtonLocation,
                    "loops_per_purchase": self.BaitPurchaseFrequencyCounter,
                    "store_fruit_point": self.FruitStorageButtonLocation,
                    "devil_fruit_hotkey": self.DevilFruitInventorySlot,
                    "bait_point": self.BaitSelectionButtonLocation,
                    "pd_approaching_damping": self.PDControllerApproachingStateDamping,
                    "pd_chasing_damping": self.PDControllerChasingStateDamping,
                    "gap_tolerance_multiplier": self.BarGroupingGapToleranceMultiplier,
                    "state_resend_interval": self.InputStateResendFrequency,
                    "auto_craft_bait": self.AutomaticBaitCraftingEnabled,
                    "craft_left_point": self.CraftLeftButtonLocation,
                    "craft_middle_point": self.CraftMiddleButtonLocation,
                    "bait_recipe_point": self.BaitRecipeButtonLocation,
                    "add_recipe_point": self.AddRecipeButtonLocation,
                    "top_recipe_point": self.TopRecipeButtonLocation,
                    "craft_button_point": self.CraftButtonLocation,
                    "close_menu_point": self.CloseMenuButtonLocation,
                    "crafts_per_cycle": self.CraftsPerCycleCount,
                    "loops_per_craft": self.BaitCraftFrequencyCounter,
                    "move_duration": self.MoveDurationSeconds,
                    "store_to_backpack": self.StoreToBackpackEnabled,
                    "devil_fruit_location_point": self.DevilFruitLocationPoint,
                    "loops_per_store": self.DevilFruitStorageFrequencyCounter,
                }, ConfigurationFileHandle, indent=4)
        except Exception as SaveError:
            print(f"Error saving settings: {SaveError}")
    
    def RegisterAllHotkeyBindings(self):
        try:
            keyboard.add_hotkey(self.GlobalHotkeyBindings["start_stop"], self.ToggleMacroExecution)
            keyboard.add_hotkey(self.GlobalHotkeyBindings["change_area"], self.ModifyScanningRegion)
            keyboard.add_hotkey(self.GlobalHotkeyBindings["exit"], self.TerminateApplicationImmediately)
        except Exception as HotkeyError:
            print(f"Error setting up hotkeys: {HotkeyError}")
    
    def ToggleMacroExecution(self):
        self.MacroCurrentlyExecuting = not self.MacroCurrentlyExecuting
        
        if self.MacroCurrentlyExecuting:
            self.CurrentSessionBeginTimestamp = time.time()
            self.RobloxWindowAlreadyFocused = False
            threading.Thread(target=self.ExecutePrimaryMacroLoop, daemon=True).start()
        else:
            if self.CurrentSessionBeginTimestamp:
                self.CumulativeRunningTimeSeconds += time.time() - self.CurrentSessionBeginTimestamp
                self.CurrentSessionBeginTimestamp = None
            if self.MouseButtonCurrentlyPressed:
                pyautogui.mouseUp()
                self.MouseButtonCurrentlyPressed = False
    
    def ModifyScanningRegion(self):
        if self.RegionSelectorCurrentlyActive:
            if self.ActiveRegionSelectorInstance:
                try:
                    self.ActiveRegionSelectorInstance.RootWindow.after(10, self.ActiveRegionSelectorInstance.CloseWindow)
                except:
                    pass
            return
        
        self.RegionSelectorCurrentlyActive = True
        
        def ExecuteRegionSelector():
            try:
                self.ActiveRegionSelectorInstance = RegionSelectionWindow(None, self.ScanningRegionBounds, self.HandleRegionSelectionComplete)
            finally:
                self.RegionSelectorCurrentlyActive = False
                self.ActiveRegionSelectorInstance = None
        
        threading.Thread(target=ExecuteRegionSelector, daemon=True).start()

    def HandleRegionSelectionComplete(self, UpdatedCoordinates):
        self.ScanningRegionBounds = UpdatedCoordinates
        self.SaveConfigurationToDisk()
        self.ActiveRegionSelectorInstance = None
        self.RegionSelectorCurrentlyActive = False
    
    def TerminateApplicationImmediately(self):
        os._exit(0)
    
    def InitiatePointSelectionMode(self, AttributeNameToSet):
        if self.MouseEventListenerInstance:
            self.MouseEventListenerInstance.stop()
        
        self.CurrentlySettingPointName = AttributeNameToSet
        
        def ProcessMouseClickEvent(ClickPositionX, ClickPositionY, ButtonPressed, IsPressed):
            if IsPressed and self.CurrentlySettingPointName == AttributeNameToSet:
                setattr(self, AttributeNameToSet, {"x": ClickPositionX, "y": ClickPositionY})
                self.SaveConfigurationToDisk()
                self.CurrentlySettingPointName = None
                return False
        
        self.MouseEventListenerInstance = mouse.Listener(on_click=ProcessMouseClickEvent)
        self.MouseEventListenerInstance.start()
    
    def ExecutePrimaryMacroLoop(self):
        while self.MacroCurrentlyExecuting:
            try:
                self.PreviousControlLoopErrorValue = None
                self.PreviousTargetBarVerticalPosition = None
                self.LastImageScanTimestamp = time.time()
                
                if self.MouseButtonCurrentlyPressed:
                    pyautogui.mouseUp()
                    self.MouseButtonCurrentlyPressed = False
                
                if not self.MacroCurrentlyExecuting:
                    break
                
                if not self.ExecutePreCastSequence():
                    continue
                
                if not self.MacroCurrentlyExecuting:
                    break
                
                if not self.WaitForFishingBobberReady():
                    continue
                
                while self.MacroCurrentlyExecuting:
                    if not self.PerformActiveFishingControl():
                        break
                
                if self.MacroCurrentlyExecuting:
                    self.TotalFishSuccessfullyCaught += 1
                    self.MostRecentFishCaptureTimestamp = time.time()
                    
                    RemainingDelayTime = self.DelayAfterFishCaptured
                    while RemainingDelayTime > 0 and self.MacroCurrentlyExecuting:
                        DelayIncrement = min(0.1, RemainingDelayTime)
                        time.sleep(DelayIncrement)
                        RemainingDelayTime -= DelayIncrement
            
            except Exception as MainLoopError:
                print(f"Error in Main: {MainLoopError}")
                break
    
    def ExecutePreCastSequence(self):
        if not self.RobloxWindowAlreadyFocused:
            def LocateRobloxWindowHandle(WindowHandle, WindowCollection):
                if win32gui.IsWindowVisible(WindowHandle):
                    WindowTitleText = win32gui.GetWindowText(WindowHandle)
                    if "Roblox" in WindowTitleText:
                        WindowCollection.append(WindowHandle)
            
            DiscoveredWindows = []
            win32gui.EnumWindows(LocateRobloxWindowHandle, DiscoveredWindows)
            
            if DiscoveredWindows:
                win32gui.SetForegroundWindow(DiscoveredWindows[0])
                time.sleep(self.RobloxWindowFocusInitialDelay)
                self.RobloxWindowAlreadyFocused = True
                time.sleep(self.RobloxWindowFocusFollowupDelay)

        if not self.MacroCurrentlyExecuting:
            return False
        
        if self.AutomaticBaitCraftingEnabled and all([
            self.CraftLeftButtonLocation,
            self.CraftMiddleButtonLocation,
            self.BaitRecipeButtonLocation,
            self.AddRecipeButtonLocation,
            self.TopRecipeButtonLocation,
            self.CraftButtonLocation,
            self.CloseMenuButtonLocation
        ]):
            if self.BaitCraftIterationCounter == 0 or self.BaitCraftIterationCounter >= self.BaitCraftFrequencyCounter:
                keyboard.press_and_release('shift')
                time.sleep(0.1)
                if not self.MacroCurrentlyExecuting: return False
                
                keyboard.press('d')
                time.sleep(self.MoveDurationSeconds)
                keyboard.release('d')
                time.sleep(1.0)
                if not self.MacroCurrentlyExecuting: return False
                
                keyboard.press_and_release('shift')
                time.sleep(0.1)
                if not self.MacroCurrentlyExecuting: return False
                
                keyboard.press_and_release('t')
                time.sleep(self.PreCastMouseClickDelay + 0.85)
                if not self.MacroCurrentlyExecuting: return False
                
                ctypes.windll.user32.SetCursorPos(self.CraftLeftButtonLocation['x'], self.CraftLeftButtonLocation['y'])
                time.sleep(self.PreCastAntiDetectionDelay)
                ctypes.windll.user32.mouse_event(0x0001, 0, 1, 0, 0)
                time.sleep(self.PreCastAntiDetectionDelay)
                pyautogui.click()
                time.sleep(self.PreCastMouseClickDelay)
                if not self.MacroCurrentlyExecuting: return False
                
                ctypes.windll.user32.SetCursorPos(self.CraftMiddleButtonLocation['x'], self.CraftMiddleButtonLocation['y'])
                time.sleep(self.PreCastAntiDetectionDelay)
                ctypes.windll.user32.mouse_event(0x0001, 0, 1, 0, 0)
                time.sleep(self.PreCastAntiDetectionDelay)
                pyautogui.click()
                time.sleep(self.PreCastMouseClickDelay)
                if not self.MacroCurrentlyExecuting: return False
                
                ctypes.windll.user32.SetCursorPos(self.BaitRecipeButtonLocation['x'], self.BaitRecipeButtonLocation['y'])
                time.sleep(self.PreCastAntiDetectionDelay)
                ctypes.windll.user32.mouse_event(0x0001, 0, 1, 0, 0)
                time.sleep(self.PreCastAntiDetectionDelay)
                pyautogui.click()
                time.sleep(self.PreCastMouseClickDelay)
                if not self.MacroCurrentlyExecuting: return False
                
                for fish_iteration in range(self.BaitCraftFrequencyCounter):
                    if not self.MacroCurrentlyExecuting: return False
                    
                    ctypes.windll.user32.SetCursorPos(self.AddRecipeButtonLocation['x'], self.AddRecipeButtonLocation['y'])
                    time.sleep(self.PreCastAntiDetectionDelay)
                    ctypes.windll.user32.mouse_event(0x0001, 0, 1, 0, 0)
                    time.sleep(self.PreCastAntiDetectionDelay)
                    pyautogui.click()
                    time.sleep(self.PreCastMouseClickDelay)
                    if not self.MacroCurrentlyExecuting: return False
                    
                    ctypes.windll.user32.SetCursorPos(self.TopRecipeButtonLocation['x'], self.TopRecipeButtonLocation['y'])
                    time.sleep(self.PreCastAntiDetectionDelay)
                    ctypes.windll.user32.mouse_event(0x0001, 0, 1, 0, 0)
                    time.sleep(self.PreCastAntiDetectionDelay)
                    pyautogui.click()
                    time.sleep(self.PreCastMouseClickDelay)
                    if not self.MacroCurrentlyExecuting: return False
                    
                    for craft_iteration in range(self.CraftsPerCycleCount):
                        if not self.MacroCurrentlyExecuting: return False
                        
                        ctypes.windll.user32.SetCursorPos(self.CraftButtonLocation['x'], self.CraftButtonLocation['y'])
                        time.sleep(self.PreCastAntiDetectionDelay)
                        ctypes.windll.user32.mouse_event(0x0001, 0, 1, 0, 0)
                        time.sleep(self.PreCastAntiDetectionDelay)
                        pyautogui.click()
                        time.sleep(self.PreCastMouseClickDelay)
                
                ctypes.windll.user32.SetCursorPos(self.CloseMenuButtonLocation['x'], self.CloseMenuButtonLocation['y'])
                time.sleep(self.PreCastAntiDetectionDelay)
                ctypes.windll.user32.mouse_event(0x0001, 0, 1, 0, 0)
                time.sleep(self.PreCastAntiDetectionDelay)
                pyautogui.click()
                time.sleep(self.PreCastMouseClickDelay)
                if not self.MacroCurrentlyExecuting: return False
                
                keyboard.press_and_release('shift')
                time.sleep(0.1)
                if not self.MacroCurrentlyExecuting: return False
                
                keyboard.press('a')
                time.sleep(self.MoveDurationSeconds)
                keyboard.release('a')
                time.sleep(1.0)
                if not self.MacroCurrentlyExecuting: return False
                
                keyboard.press_and_release('shift')
                time.sleep(0.1)
                if not self.MacroCurrentlyExecuting: return False
                
                self.BaitCraftIterationCounter = 1
            else:
                self.BaitCraftIterationCounter += 1
        
        if self.AutomaticBaitPurchaseEnabled and self.ShopLeftButtonLocation and self.ShopCenterButtonLocation and self.ShopRightButtonLocation:
            if self.BaitPurchaseIterationCounter == 0 or self.BaitPurchaseIterationCounter >= self.BaitPurchaseFrequencyCounter:                
                keyboard.press_and_release('e')
                time.sleep(self.PreCastDialogOpenDelay)
                if not self.MacroCurrentlyExecuting: return False
                
                ctypes.windll.user32.SetCursorPos(self.ShopLeftButtonLocation['x'], self.ShopLeftButtonLocation['y'])
                time.sleep(self.PreCastAntiDetectionDelay)
                ctypes.windll.user32.mouse_event(0x0001, 0, 1, 0, 0)
                time.sleep(self.PreCastAntiDetectionDelay)
                pyautogui.click()
                time.sleep(self.PreCastMouseClickDelay)
                if not self.MacroCurrentlyExecuting: return False
                
                ctypes.windll.user32.SetCursorPos(self.ShopCenterButtonLocation['x'], self.ShopCenterButtonLocation['y'])
                time.sleep(self.PreCastAntiDetectionDelay)
                ctypes.windll.user32.mouse_event(0x0001, 0, 1, 0, 0)
                time.sleep(self.PreCastAntiDetectionDelay)
                pyautogui.click()
                time.sleep(self.PreCastMouseClickDelay)
                if not self.MacroCurrentlyExecuting: return False
                
                keyboard.write(str(self.BaitPurchaseFrequencyCounter))
                time.sleep(self.PreCastKeyboardInputDelay)
                if not self.MacroCurrentlyExecuting: return False
                
                ctypes.windll.user32.SetCursorPos(self.ShopLeftButtonLocation['x'], self.ShopLeftButtonLocation['y'])
                time.sleep(self.PreCastAntiDetectionDelay)
                ctypes.windll.user32.mouse_event(0x0001, 0, 1, 0, 0)
                time.sleep(self.PreCastAntiDetectionDelay)
                pyautogui.click()
                time.sleep(self.PreCastMouseClickDelay)
                if not self.MacroCurrentlyExecuting: return False
                
                ctypes.windll.user32.SetCursorPos(self.ShopRightButtonLocation['x'], self.ShopRightButtonLocation['y'])
                time.sleep(self.PreCastAntiDetectionDelay)
                ctypes.windll.user32.mouse_event(0x0001, 0, 1, 0, 0)
                time.sleep(self.PreCastAntiDetectionDelay)
                pyautogui.click()
                time.sleep(self.PreCastMouseClickDelay)
                if not self.MacroCurrentlyExecuting: return False
                
                ctypes.windll.user32.SetCursorPos(self.ShopCenterButtonLocation['x'], self.ShopCenterButtonLocation['y'])
                time.sleep(self.PreCastAntiDetectionDelay)
                ctypes.windll.user32.mouse_event(0x0001, 0, 1, 0, 0)
                time.sleep(self.PreCastAntiDetectionDelay)
                pyautogui.click()
                time.sleep(self.PreCastMouseClickDelay)
                
                self.BaitPurchaseIterationCounter = 1
            else:
                self.BaitPurchaseIterationCounter += 1
        
        if not self.MacroCurrentlyExecuting:
            return False
        
        if self.AutomaticFruitStorageEnabled:
            if self.DevilFruitStorageIterationCounter == 0 or self.DevilFruitStorageIterationCounter >= self.DevilFruitStorageFrequencyCounter:
                if self.StoreToBackpackEnabled and self.DevilFruitLocationPoint:
                    keyboard.press_and_release('`')
                    time.sleep(self.FruitStorageHotkeyActivationDelay)
                    if not self.MacroCurrentlyExecuting: return False
                    
                    ctypes.windll.user32.SetCursorPos(self.DevilFruitLocationPoint['x'], self.DevilFruitLocationPoint['y'])
                    time.sleep(self.PreCastAntiDetectionDelay)
                    ctypes.windll.user32.mouse_event(0x0001, 0, 1, 0, 0)
                    time.sleep(self.PreCastAntiDetectionDelay)
                    pyautogui.click()
                    time.sleep(self.FruitStorageClickConfirmationDelay)
                    if not self.MacroCurrentlyExecuting: return False
                    
                    if self.FruitStorageButtonLocation:
                        ctypes.windll.user32.SetCursorPos(self.FruitStorageButtonLocation['x'], self.FruitStorageButtonLocation['y'])
                        time.sleep(self.PreCastAntiDetectionDelay)
                        ctypes.windll.user32.mouse_event(0x0001, 0, 1, 0, 0)
                        time.sleep(self.PreCastAntiDetectionDelay)
                        pyautogui.click()
                        time.sleep(self.FruitStorageClickConfirmationDelay)
                        if not self.MacroCurrentlyExecuting: return False
                        
                        pyautogui.moveTo(self.DevilFruitLocationPoint['x'], self.DevilFruitLocationPoint['y'], duration=0.2)
                        time.sleep(0.2)
                        if not self.MacroCurrentlyExecuting: return False
                        
                        pyautogui.mouseDown(button='left')
                        time.sleep(0.1)
                        
                        pyautogui.moveTo(self.DevilFruitLocationPoint['x'], self.DevilFruitLocationPoint['y'] - 150, duration=0.3)
                        time.sleep(0.1)
                        
                        pyautogui.mouseUp(button='left')
                        
                        time.sleep(self.PreCastAntiDetectionDelay)
                        if not self.MacroCurrentlyExecuting: return False
                        
                        keyboard.press_and_release('`')
                        time.sleep(self.FruitStorageHotkeyActivationDelay)
                elif self.FruitStorageButtonLocation:
                    keyboard.press_and_release(self.DevilFruitInventorySlot)
                    time.sleep(self.FruitStorageHotkeyActivationDelay)
                    if not self.MacroCurrentlyExecuting: return False
                    
                    ctypes.windll.user32.SetCursorPos(self.FruitStorageButtonLocation['x'], self.FruitStorageButtonLocation['y'])
                    time.sleep(self.PreCastAntiDetectionDelay)
                    ctypes.windll.user32.mouse_event(0x0001, 0, 1, 0, 0)
                    time.sleep(self.PreCastAntiDetectionDelay)
                    pyautogui.click()
                    time.sleep(self.FruitStorageClickConfirmationDelay)
                    if not self.MacroCurrentlyExecuting: return False
                    
                    keyboard.press_and_release('shift')
                    time.sleep(self.FruitStorageShiftKeyPressDelay)
                    if not self.MacroCurrentlyExecuting: return False
                    
                    keyboard.press_and_release('backspace')
                    time.sleep(self.FruitStorageBackspaceDeletionDelay)
                    if not self.MacroCurrentlyExecuting: return False
                    
                    keyboard.press_and_release('shift')
                
                self.DevilFruitStorageIterationCounter = 1
            else:
                self.DevilFruitStorageIterationCounter += 1

        return True
    
    def WaitForFishingBobberReady(self):
        if not self.WaterCastingTargetLocation:
            return False
        
        keyboard.press_and_release(self.AlternateInventorySlot)
        time.sleep(self.InventorySlotSwitchingDelay)
        
        if not self.MacroCurrentlyExecuting:
            return False
        
        keyboard.press_and_release(self.FishingRodInventorySlot)
        time.sleep(self.InventorySlotSwitchingDelay)
        
        if not self.MacroCurrentlyExecuting:
            return False
        
        if self.AutomaticTopBaitSelectionEnabled and self.BaitSelectionButtonLocation:
            ctypes.windll.user32.SetCursorPos(self.BaitSelectionButtonLocation['x'], self.BaitSelectionButtonLocation['y'])
            time.sleep(self.PreCastAntiDetectionDelay)
            ctypes.windll.user32.mouse_event(0x0001, 0, 1, 0, 0)
            time.sleep(self.PreCastAntiDetectionDelay)
            pyautogui.click()
            time.sleep(self.BaitSelectionConfirmationDelay)
        
        if not self.MacroCurrentlyExecuting:
            return False
        
        ctypes.windll.user32.SetCursorPos(self.WaterCastingTargetLocation['x'], self.WaterCastingTargetLocation['y'])
        time.sleep(self.MouseMovementAntiDetectionDelay)
        ctypes.windll.user32.mouse_event(0x0001, 0, 1, 0, 0)
        
        if not self.MacroCurrentlyExecuting:
            return False
        
        pyautogui.mouseDown()
        time.sleep(self.MouseHoldDurationForCast)
        
        if not self.MacroCurrentlyExecuting:
            pyautogui.mouseUp()
            return False
        
        pyautogui.mouseUp()
        
        CastingStartTime = time.time()
        BobberBlueColor = np.array([85, 170, 255])
        BobberWhiteColor = np.array([255, 255, 255])
        BobberDarkGrayColor = np.array([25, 25, 25])
        
        while self.MacroCurrentlyExecuting:
            ElapsedWaitTime = time.time() - CastingStartTime
            
            if ElapsedWaitTime >= self.MaximumWaitTimeBeforeRecast:
                return False
            
            with mss.mss() as ScreenCapture:
                CaptureRegion = {
                    "top": self.ScanningRegionBounds["y1"],
                    "left": self.ScanningRegionBounds["x1"],
                    "width": self.ScanningRegionBounds["x2"] - self.ScanningRegionBounds["x1"],
                    "height": self.ScanningRegionBounds["y2"] - self.ScanningRegionBounds["y1"]
                }
                CapturedScreen = ScreenCapture.grab(CaptureRegion)
                ScreenImageArray = np.array(CapturedScreen)
            
            if self.DetectBlackScreenCondition(ScreenImageArray):
                if not self.HandleAntiMacroDetection():
                    return False
                continue
            
            BluePixelMask = ((ScreenImageArray[:, :, 2] == BobberBlueColor[0]) & 
                       (ScreenImageArray[:, :, 1] == BobberBlueColor[1]) & 
                       (ScreenImageArray[:, :, 0] == BobberBlueColor[2]))
            WhitePixelMask = ((ScreenImageArray[:, :, 2] == BobberWhiteColor[0]) & 
                        (ScreenImageArray[:, :, 1] == BobberWhiteColor[1]) & 
                        (ScreenImageArray[:, :, 0] == BobberWhiteColor[2]))
            DarkGrayPixelMask = ((ScreenImageArray[:, :, 2] == BobberDarkGrayColor[0]) & 
                           (ScreenImageArray[:, :, 1] == BobberDarkGrayColor[1]) & 
                           (ScreenImageArray[:, :, 0] == BobberDarkGrayColor[2]))
            
            BlueColorDetected = np.any(BluePixelMask)
            WhiteColorDetected = np.any(WhitePixelMask)
            DarkGrayColorDetected = np.any(DarkGrayPixelMask)
            
            if BlueColorDetected and WhiteColorDetected and DarkGrayColorDetected:
                return True
            
            time.sleep(self.ImageProcessingLoopDelay)
        
        return False
    
    def DetectBlackScreenCondition(self, ImageArrayToCheck=None):
        if ImageArrayToCheck is None:
            with mss.mss() as ScreenCapture:
                CaptureRegion = {
                    "top": self.ScanningRegionBounds["y1"],
                    "left": self.ScanningRegionBounds["x1"],
                    "width": self.ScanningRegionBounds["x2"] - self.ScanningRegionBounds["x1"],
                    "height": self.ScanningRegionBounds["y2"] - self.ScanningRegionBounds["y1"]
                }
                CapturedScreen = ScreenCapture.grab(CaptureRegion)
                ImageArrayToCheck = np.array(CapturedScreen)
        
        BlackPixelMask = ((ImageArrayToCheck[:, :, 2] == 0) & (ImageArrayToCheck[:, :, 1] == 0) & (ImageArrayToCheck[:, :, 0] == 0))
        TotalBlackPixelCount = np.sum(BlackPixelMask)
        TotalPixelCount = ImageArrayToCheck.shape[0] * ImageArrayToCheck.shape[1]
        BlackPixelRatio = TotalBlackPixelCount / TotalPixelCount
        
        return BlackPixelRatio >= self.BlackScreenDetectionRatioThreshold
    
    def HandleAntiMacroDetection(self):
        RetryAttemptCount = 0
        MaximumRetryAttempts = 20
        
        while self.MacroCurrentlyExecuting and RetryAttemptCount < MaximumRetryAttempts:
            if not self.DetectBlackScreenCondition():
                return True
            
            keyboard.press_and_release(self.AlternateInventorySlot)
            time.sleep(self.AntiMacroDialogSpamDelay)
            RetryAttemptCount += 1
        
        return False
    
    def PerformActiveFishingControl(self):
        with mss.mss() as ScreenCapture:
            CaptureRegion = {
                "top": self.ScanningRegionBounds["y1"],
                "left": self.ScanningRegionBounds["x1"],
                "width": self.ScanningRegionBounds["x2"] - self.ScanningRegionBounds["x1"],
                "height": self.ScanningRegionBounds["y2"] - self.ScanningRegionBounds["y1"]
            }
            CapturedScreen = ScreenCapture.grab(CaptureRegion)
            ScreenImageArray = np.array(CapturedScreen)
        
        if self.DetectBlackScreenCondition(ScreenImageArray):
            if self.MouseButtonCurrentlyPressed:
                pyautogui.mouseUp()
                self.MouseButtonCurrentlyPressed = False
            self.HandleAntiMacroDetection()
            return False
        
        BobberBlueColor = np.array([85, 170, 255])
        BluePixelMask = ((ScreenImageArray[:, :, 2] == BobberBlueColor[0]) & 
                    (ScreenImageArray[:, :, 1] == BobberBlueColor[1]) & 
                    (ScreenImageArray[:, :, 0] == BobberBlueColor[2]))
        
        if not np.any(BluePixelMask):
            if self.MouseButtonCurrentlyPressed:
                pyautogui.mouseUp()
                self.MouseButtonCurrentlyPressed = False
            return False
        
        BluePixelYCoordinates, BluePixelXCoordinates = np.where(BluePixelMask)
        HorizontalCenterPosition = int(np.mean(BluePixelXCoordinates))
        
        VerticalSliceArray = ScreenImageArray[:, HorizontalCenterPosition:HorizontalCenterPosition+1, :]
        
        BoundaryGrayColor = np.array([25, 25, 25])
        GrayPixelMask = ((VerticalSliceArray[:, 0, 2] == BoundaryGrayColor[0]) & 
                (VerticalSliceArray[:, 0, 1] == BoundaryGrayColor[1]) & 
                (VerticalSliceArray[:, 0, 0] == BoundaryGrayColor[2]))
        
        if not np.any(GrayPixelMask):
            return True
        
        GrayPixelYCoordinates = np.where(GrayPixelMask)[0]
        TopBoundaryPosition = GrayPixelYCoordinates[0]
        BottomBoundaryPosition = GrayPixelYCoordinates[-1]
        BoundedSliceArray = VerticalSliceArray[TopBoundaryPosition:BottomBoundaryPosition+1, :, :]
        
        IndicatorWhiteColor = np.array([255, 255, 255])
        WhitePixelMask = ((BoundedSliceArray[:, 0, 2] == IndicatorWhiteColor[0]) & 
                    (BoundedSliceArray[:, 0, 1] == IndicatorWhiteColor[1]) & 
                    (BoundedSliceArray[:, 0, 0] == IndicatorWhiteColor[2]))
        
        if not np.any(WhitePixelMask):
            if not self.MouseButtonCurrentlyPressed:
                pyautogui.mouseDown()
                print("No White Indicator Detected - Mouse Button")
                
            return True
        
        WhitePixelYCoordinates = np.where(WhitePixelMask)[0]
        WhiteBarTopPosition = WhitePixelYCoordinates[0]
        WhiteBarBottomPosition = WhitePixelYCoordinates[-1]
        WhiteBarHeight = WhiteBarBottomPosition - WhiteBarTopPosition + 1
        WhiteBarCenterPosition = (WhiteBarTopPosition + WhiteBarBottomPosition) // 2
        WhiteBarCenterScreenY = self.ScanningRegionBounds["y1"] + TopBoundaryPosition + WhiteBarCenterPosition
        
        TargetDarkGrayColor = np.array([25, 25, 25])
        DarkGrayPixelMask = ((BoundedSliceArray[:, 0, 2] == TargetDarkGrayColor[0]) & 
                    (BoundedSliceArray[:, 0, 1] == TargetDarkGrayColor[1]) & 
                    (BoundedSliceArray[:, 0, 0] == TargetDarkGrayColor[2]))
        
        if not np.any(DarkGrayPixelMask):
            if not self.MouseButtonCurrentlyPressed:
                pyautogui.mouseDown()
                print("Panic Click Engaged - No Dark Gray Pixels Detected")
                self.MouseButtonCurrentlyPressed = True
                
            return True
        
        DarkGrayPixelYCoordinates = np.where(DarkGrayPixelMask)[0]
        MaximumAllowedGap = WhiteBarHeight * self.BarGroupingGapToleranceMultiplier
        
        PixelGroupCollections = []
        ActivePixelGroup = [DarkGrayPixelYCoordinates[0]]
        
        for IndexPosition in range(1, len(DarkGrayPixelYCoordinates)):
            if DarkGrayPixelYCoordinates[IndexPosition] - DarkGrayPixelYCoordinates[IndexPosition-1] <= MaximumAllowedGap:
                ActivePixelGroup.append(DarkGrayPixelYCoordinates[IndexPosition])
            else:
                PixelGroupCollections.append(ActivePixelGroup)
                ActivePixelGroup = [DarkGrayPixelYCoordinates[IndexPosition]]
        
        PixelGroupCollections.append(ActivePixelGroup)
        
        LargestPixelGroup = max(PixelGroupCollections, key=len)
        LargestGroupCenterPosition = (LargestPixelGroup[0] + LargestPixelGroup[-1]) // 2
        LargestGroupCenterScreenY = self.ScanningRegionBounds["y1"] + TopBoundaryPosition + LargestGroupCenterPosition
        
        ProportionalGain = self.ProportionalGainCoefficient
        DerivativeGain = self.DerivativeGainCoefficient
        MaximumControlClamp = self.ControlSignalMaximumClamp
        
        CurrentPositionError = WhiteBarCenterScreenY - LargestGroupCenterScreenY
        ProportionalControlTerm = ProportionalGain * CurrentPositionError
        DerivativeControlTerm = 0.0
        
        CurrentTimestamp = time.time()
        TimeDifference = CurrentTimestamp - self.LastImageScanTimestamp
        
        if self.PreviousControlLoopErrorValue is not None and self.PreviousTargetBarVerticalPosition is not None and TimeDifference > 0.001:
            TargetBarVelocity = (LargestGroupCenterScreenY - self.PreviousTargetBarVerticalPosition) / TimeDifference
            ErrorDecreasingInMagnitude = abs(CurrentPositionError) < abs(self.PreviousControlLoopErrorValue)
            TargetMovingTowardIndicator = (TargetBarVelocity > 0 and CurrentPositionError > 0) or (TargetBarVelocity < 0 and CurrentPositionError < 0)
            
            if ErrorDecreasingInMagnitude and TargetMovingTowardIndicator:
                AppliedDampingMultiplier = self.PDControllerApproachingStateDamping
                DerivativeControlTerm = -DerivativeGain * AppliedDampingMultiplier * TargetBarVelocity
            else:
                AppliedDampingMultiplier = self.PDControllerChasingStateDamping
                DerivativeControlTerm = -DerivativeGain * AppliedDampingMultiplier * TargetBarVelocity
        
        FinalControlSignal = ProportionalControlTerm + DerivativeControlTerm
        FinalControlSignal = max(-MaximumControlClamp, min(MaximumControlClamp, FinalControlSignal))
        ShouldHoldMouseButton = FinalControlSignal <= 0
        
        if ShouldHoldMouseButton and not self.MouseButtonCurrentlyPressed:
            pyautogui.mouseDown()
            self.MouseButtonCurrentlyPressed = True
            self.LastControlStateChangeTimestamp = CurrentTimestamp
            self.LastInputResendTimestamp = CurrentTimestamp
        elif not ShouldHoldMouseButton and self.MouseButtonCurrentlyPressed:
            pyautogui.mouseUp()
            self.MouseButtonCurrentlyPressed = False
            self.LastControlStateChangeTimestamp = CurrentTimestamp
            self.LastInputResendTimestamp = CurrentTimestamp
        else:
            TimeSinceLastResend = CurrentTimestamp - self.LastInputResendTimestamp
            
            if TimeSinceLastResend >= self.InputStateResendFrequency:
                if self.MouseButtonCurrentlyPressed:
                    pyautogui.mouseDown()
                else:
                    pyautogui.mouseUp()
                self.LastInputResendTimestamp = CurrentTimestamp
        
        self.PreviousControlLoopErrorValue = CurrentPositionError
        self.PreviousTargetBarVerticalPosition = LargestGroupCenterScreenY
        self.LastImageScanTimestamp = CurrentTimestamp
        
        return True
    
    def RetrieveCurrentSystemState(self):
        CalculatedFishPerHour = 0.0
        FormattedElapsedTime = "0:00:00"
        AccumulatedTime = self.CumulativeRunningTimeSeconds
        
        if self.CurrentSessionBeginTimestamp:
            CurrentActiveSessionTime = time.time() - self.CurrentSessionBeginTimestamp
            AccumulatedTime = self.CumulativeRunningTimeSeconds + CurrentActiveSessionTime
        
        if AccumulatedTime > 0:
            TotalHours = int(AccumulatedTime // 3600)
            TotalMinutes = int((AccumulatedTime % 3600) // 60)
            TotalSeconds = int(AccumulatedTime % 60)
            FormattedElapsedTime = f"{TotalHours}:{TotalMinutes:02d}:{TotalSeconds:02d}"
            CalculatedFishPerHour = (self.TotalFishSuccessfullyCaught / AccumulatedTime) * 3600
        
        return {
            "storeToBackpack": self.StoreToBackpackEnabled,
            "devilFruitLocationPoint": self.DevilFruitLocationPoint,
            "loopsPerStore": self.DevilFruitStorageFrequencyCounter,
            "isRunning": self.MacroCurrentlyExecuting,
            "fishCaught": self.TotalFishSuccessfullyCaught,
            "timeElapsed": FormattedElapsedTime,
            "fishPerHour": round(CalculatedFishPerHour, 1),
            "waterPoint": self.WaterCastingTargetLocation,
            "leftPoint": self.ShopLeftButtonLocation,
            "middlePoint": self.ShopCenterButtonLocation,
            "rightPoint": self.ShopRightButtonLocation,
            "storeFruitPoint": self.FruitStorageButtonLocation,
            "baitPoint": self.BaitSelectionButtonLocation,
            "hotkeys": self.GlobalHotkeyBindings,
            "rodHotkey": self.FishingRodInventorySlot,
            "anythingElseHotkey": self.AlternateInventorySlot,
            "devilFruitHotkey": self.DevilFruitInventorySlot,
            "alwaysOnTop": self.WindowAlwaysOnTopEnabled,
            "showDebugOverlay": self.DebugOverlayVisible,
            "autoBuyCommonBait": self.AutomaticBaitPurchaseEnabled,
            "autoStoreDevilFruit": self.AutomaticFruitStorageEnabled,
            "autoSelectTopBait": self.AutomaticTopBaitSelectionEnabled,
            "kp": self.ProportionalGainCoefficient,
            "kd": self.DerivativeGainCoefficient,
            "pdClamp": self.ControlSignalMaximumClamp,
            "castHoldDuration": self.MouseHoldDurationForCast,
            "recastTimeout": self.MaximumWaitTimeBeforeRecast,
            "fishEndDelay": self.DelayAfterFishCaptured,
            "loopsPerPurchase": self.BaitPurchaseFrequencyCounter,
            "pdApproachingDamping": self.PDControllerApproachingStateDamping,
            "pdChasingDamping": self.PDControllerChasingStateDamping,
            "gapToleranceMultiplier": self.BarGroupingGapToleranceMultiplier,
            "stateResendInterval": self.InputStateResendFrequency,
            "robloxFocusDelay": self.RobloxWindowFocusInitialDelay,
            "robloxPostFocusDelay": self.RobloxWindowFocusFollowupDelay,
            "preCastEDelay": self.PreCastDialogOpenDelay,
            "preCastClickDelay": self.PreCastMouseClickDelay,
            "preCastTypeDelay": self.PreCastKeyboardInputDelay,
            "preCastAntiDetectDelay": self.PreCastAntiDetectionDelay,
            "storeFruitHotkeyDelay": self.FruitStorageHotkeyActivationDelay,
            "storeFruitClickDelay": self.FruitStorageClickConfirmationDelay,
            "storeFruitShiftDelay": self.FruitStorageShiftKeyPressDelay,
            "storeFruitBackspaceDelay": self.FruitStorageBackspaceDeletionDelay,
            "autoSelectBaitDelay": self.BaitSelectionConfirmationDelay,
            "blackScreenThreshold": self.BlackScreenDetectionRatioThreshold,
            "antiMacroSpamDelay": self.AntiMacroDialogSpamDelay,
            "rodSelectDelay": self.InventorySlotSwitchingDelay,
            "cursorAntiDetectDelay": self.MouseMovementAntiDetectionDelay,
            "scanLoopDelay": self.ImageProcessingLoopDelay,
            "autoCraftBait": self.AutomaticBaitCraftingEnabled,
            "craftLeftPoint": self.CraftLeftButtonLocation,
            "craftMiddlePoint": self.CraftMiddleButtonLocation,
            "baitRecipePoint": self.BaitRecipeButtonLocation,
            "addRecipePoint": self.AddRecipeButtonLocation,
            "topRecipePoint": self.TopRecipeButtonLocation,
            "craftButtonPoint": self.CraftButtonLocation,
            "closeMenuPoint": self.CloseMenuButtonLocation,
            "craftsPerCycle": self.CraftsPerCycleCount,
            "loopsPerCraft": self.BaitCraftFrequencyCounter,
            "moveDuration": self.MoveDurationSeconds,
        }

MacroSystemInstance = AutomatedFishingSystem()

@FlaskApplication.route('/state', methods=['GET'])
def RetrieveSystemState():
    return jsonify(MacroSystemInstance.RetrieveCurrentSystemState())

@FlaskApplication.route('/set_window_property', methods=['POST'])
def ConfigureWindowProperty():
    try:
        IncomingData = request.json
        RequestedProperty = IncomingData.get('property')
        
        if RequestedProperty == 'always_on_top':
            return jsonify({"alwaysOnTop": MacroSystemInstance.WindowAlwaysOnTopEnabled})
        
        return jsonify({"status": "ok"})
    except Exception as ErrorDetails:
        return jsonify({"status": "error", "message": str(ErrorDetails)}), 500
    
@FlaskApplication.route('/command', methods=['POST'])
def ProcessIncomingCommand():
    try:
        IncomingData = request.json
        RequestedAction = IncomingData.get('action')
        ActionPayload = IncomingData.get('payload')
                
        if RequestedAction == 'rebind_hotkey':
            MacroSystemInstance.CurrentlyRebindingHotkey = ActionPayload
            keyboard.unhook_all_hotkeys()
            
            def HandleKeyboardEvent(PressedKeyEvent):
                if MacroSystemInstance.CurrentlyRebindingHotkey == ActionPayload:
                    NewHotkeyValue = PressedKeyEvent.name.lower()
                    MacroSystemInstance.GlobalHotkeyBindings[ActionPayload] = NewHotkeyValue
                    MacroSystemInstance.SaveConfigurationToDisk()
                    MacroSystemInstance.CurrentlyRebindingHotkey = None
                    MacroSystemInstance.RegisterAllHotkeyBindings()
            
            keyboard.on_release(HandleKeyboardEvent, suppress=False)
            return jsonify({"status": "waiting_for_key"})
        
        elif RequestedAction == 'set_water_point':
            MacroSystemInstance.InitiatePointSelectionMode('WaterCastingTargetLocation')
            return jsonify({"status": "waiting_for_click"})
        
        elif RequestedAction == 'set_devil_fruit_location_point':
            MacroSystemInstance.InitiatePointSelectionMode('DevilFruitLocationPoint')
            return jsonify({"status": "waiting_for_click"})

        elif RequestedAction == 'toggle_store_to_backpack':
            MacroSystemInstance.StoreToBackpackEnabled = ActionPayload.lower() == 'true'
            MacroSystemInstance.SaveConfigurationToDisk()
            return jsonify({"status": "success", "value": MacroSystemInstance.StoreToBackpackEnabled})

        elif RequestedAction == 'set_loops_per_store':
            MacroSystemInstance.DevilFruitStorageFrequencyCounter = int(ActionPayload)
            MacroSystemInstance.SaveConfigurationToDisk()
            return jsonify({"status": "success"})
        
        elif RequestedAction == 'set_left_point':
            MacroSystemInstance.InitiatePointSelectionMode('ShopLeftButtonLocation')
            return jsonify({"status": "waiting_for_click"})
        
        elif RequestedAction == 'set_middle_point':
            MacroSystemInstance.InitiatePointSelectionMode('ShopCenterButtonLocation')
            return jsonify({"status": "waiting_for_click"})
        
        elif RequestedAction == 'set_right_point':
            MacroSystemInstance.InitiatePointSelectionMode('ShopRightButtonLocation')
            return jsonify({"status": "waiting_for_click"})
        
        elif RequestedAction == 'set_store_fruit_point':
            MacroSystemInstance.InitiatePointSelectionMode('FruitStorageButtonLocation')
            return jsonify({"status": "waiting_for_click"})
        
        elif RequestedAction == 'set_bait_point':
            MacroSystemInstance.InitiatePointSelectionMode('BaitSelectionButtonLocation')
            return jsonify({"status": "waiting_for_click"})
        
        elif RequestedAction == 'set_rod_hotkey':
            MacroSystemInstance.FishingRodInventorySlot = ActionPayload
            MacroSystemInstance.SaveConfigurationToDisk()
            return jsonify({"status": "success"})
        
        elif RequestedAction == 'set_anything_else_hotkey':
            MacroSystemInstance.AlternateInventorySlot = ActionPayload
            MacroSystemInstance.SaveConfigurationToDisk()
            return jsonify({"status": "success"})
        
        elif RequestedAction == 'set_devil_fruit_hotkey':
            MacroSystemInstance.DevilFruitInventorySlot = ActionPayload
            MacroSystemInstance.SaveConfigurationToDisk()
            return jsonify({"status": "success"})
        
        elif RequestedAction == 'toggle_always_on_top':
            MacroSystemInstance.WindowAlwaysOnTopEnabled = ActionPayload.lower() == 'true'
            MacroSystemInstance.SaveConfigurationToDisk()
            return jsonify({"status": "success", "value": MacroSystemInstance.WindowAlwaysOnTopEnabled})

        elif RequestedAction == 'toggle_debug_overlay':
            MacroSystemInstance.DebugOverlayVisible = ActionPayload.lower() == 'true'
            MacroSystemInstance.SaveConfigurationToDisk()
            return jsonify({"status": "success", "value": MacroSystemInstance.DebugOverlayVisible})
        
        elif RequestedAction == 'toggle_auto_buy_bait':
            MacroSystemInstance.AutomaticBaitPurchaseEnabled = ActionPayload.lower() == 'true'
            MacroSystemInstance.SaveConfigurationToDisk()
            return jsonify({"status": "success", "value": MacroSystemInstance.AutomaticBaitPurchaseEnabled})
        
        elif RequestedAction == 'toggle_auto_store_fruit':
            MacroSystemInstance.AutomaticFruitStorageEnabled = ActionPayload.lower() == 'true'
            MacroSystemInstance.SaveConfigurationToDisk()
            return jsonify({"status": "success", "value": MacroSystemInstance.AutomaticFruitStorageEnabled})
        
        elif RequestedAction == 'toggle_auto_select_bait':
            MacroSystemInstance.AutomaticTopBaitSelectionEnabled = ActionPayload.lower() == 'true'
            MacroSystemInstance.SaveConfigurationToDisk()
            return jsonify({"status": "success", "value": MacroSystemInstance.AutomaticTopBaitSelectionEnabled})

        elif RequestedAction == 'toggle_auto_select_bait':
            MacroSystemInstance.AutomaticTopBaitSelectionEnabled = ActionPayload.lower() == 'true'
            MacroSystemInstance.SaveConfigurationToDisk()
            return jsonify({"status": "success", "value": MacroSystemInstance.AutomaticTopBaitSelectionEnabled})
        
        elif RequestedAction == 'set_kp':
            MacroSystemInstance.ProportionalGainCoefficient = float(ActionPayload)
            MacroSystemInstance.SaveConfigurationToDisk()
            return jsonify({"status": "success"})
        
        elif RequestedAction == 'set_kd':
            MacroSystemInstance.DerivativeGainCoefficient = float(ActionPayload)
            MacroSystemInstance.SaveConfigurationToDisk()
            return jsonify({"status": "success"})
        
        elif RequestedAction == 'set_pd_clamp':
            MacroSystemInstance.ControlSignalMaximumClamp = float(ActionPayload)
            MacroSystemInstance.SaveConfigurationToDisk()
            return jsonify({"status": "success"})
        
        elif RequestedAction == 'set_pd_approaching':
            MacroSystemInstance.PDControllerApproachingStateDamping = float(ActionPayload)
            MacroSystemInstance.SaveConfigurationToDisk()
            return jsonify({"status": "success"})
        
        elif RequestedAction == 'set_pd_chasing':
            MacroSystemInstance.PDControllerChasingStateDamping = float(ActionPayload)
            MacroSystemInstance.SaveConfigurationToDisk()
            return jsonify({"status": "success"})
        
        elif RequestedAction == 'set_gap_tolerance':
            MacroSystemInstance.BarGroupingGapToleranceMultiplier = float(ActionPayload)
            MacroSystemInstance.SaveConfigurationToDisk()
            return jsonify({"status": "success"})
        
        elif RequestedAction == 'set_cast_hold':
            MacroSystemInstance.MouseHoldDurationForCast = float(ActionPayload)
            MacroSystemInstance.SaveConfigurationToDisk()
            return jsonify({"status": "success"})
        
        elif RequestedAction == 'set_recast_timeout':
            MacroSystemInstance.MaximumWaitTimeBeforeRecast = float(ActionPayload)
            MacroSystemInstance.SaveConfigurationToDisk()
            return jsonify({"status": "success"})
        
        elif RequestedAction == 'set_fish_end_delay':
            MacroSystemInstance.DelayAfterFishCaptured = float(ActionPayload)
            MacroSystemInstance.SaveConfigurationToDisk()
            return jsonify({"status": "success"})
        
        elif RequestedAction == 'set_state_resend':
            MacroSystemInstance.InputStateResendFrequency = float(ActionPayload)
            MacroSystemInstance.SaveConfigurationToDisk()
            return jsonify({"status": "success"})
        
        elif RequestedAction == 'set_loops_per_purchase':
            MacroSystemInstance.BaitPurchaseFrequencyCounter = int(ActionPayload)
            MacroSystemInstance.SaveConfigurationToDisk()
            return jsonify({"status": "success"})
        
        elif RequestedAction == 'set_focus_delay':
            MacroSystemInstance.RobloxWindowFocusInitialDelay = float(ActionPayload)
            MacroSystemInstance.SaveConfigurationToDisk()
            return jsonify({"status": "success"})
        
        elif RequestedAction == 'set_post_focus_delay':
            MacroSystemInstance.RobloxWindowFocusFollowupDelay = float(ActionPayload)
            MacroSystemInstance.SaveConfigurationToDisk()
            return jsonify({"status": "success"})
        
        elif RequestedAction == 'set_precast_e_delay':
            MacroSystemInstance.PreCastDialogOpenDelay = float(ActionPayload)
            MacroSystemInstance.SaveConfigurationToDisk()
            return jsonify({"status": "success"})
    
        elif RequestedAction == 'set_precast_click_delay':
            MacroSystemInstance.PreCastMouseClickDelay = float(ActionPayload)
            MacroSystemInstance.SaveConfigurationToDisk()
            return jsonify({"status": "success"})
        
        elif RequestedAction == 'set_precast_type_delay':
            MacroSystemInstance.PreCastKeyboardInputDelay = float(ActionPayload)
            MacroSystemInstance.SaveConfigurationToDisk()
            return jsonify({"status": "success"})
        
        elif RequestedAction == 'set_anti_detect_delay':
            MacroSystemInstance.PreCastAntiDetectionDelay = float(ActionPayload)
            MacroSystemInstance.SaveConfigurationToDisk()
            return jsonify({"status": "success"})
        
        elif RequestedAction == 'set_fruit_hotkey_delay':
            MacroSystemInstance.FruitStorageHotkeyActivationDelay = float(ActionPayload)
            MacroSystemInstance.SaveConfigurationToDisk()
            return jsonify({"status": "success"})
        
        elif RequestedAction == 'set_fruit_click_delay':
            MacroSystemInstance.FruitStorageClickConfirmationDelay = float(ActionPayload)
            MacroSystemInstance.SaveConfigurationToDisk()
            return jsonify({"status": "success"})
        
        elif RequestedAction == 'set_fruit_shift_delay':
            MacroSystemInstance.FruitStorageShiftKeyPressDelay = float(ActionPayload)
            MacroSystemInstance.SaveConfigurationToDisk()
            return jsonify({"status": "success"})
        
        elif RequestedAction == 'set_fruit_backspace_delay':
            MacroSystemInstance.FruitStorageBackspaceDeletionDelay = float(ActionPayload)
            MacroSystemInstance.SaveConfigurationToDisk()
            return jsonify({"status": "success"})
        
        elif RequestedAction == 'set_rod_delay':
            MacroSystemInstance.InventorySlotSwitchingDelay = float(ActionPayload)
            MacroSystemInstance.SaveConfigurationToDisk()
            return jsonify({"status": "success"})
        
        elif RequestedAction == 'set_bait_delay':
            MacroSystemInstance.BaitSelectionConfirmationDelay = float(ActionPayload)
            MacroSystemInstance.SaveConfigurationToDisk()
            return jsonify({"status": "success"})
        
        elif RequestedAction == 'set_cursor_delay':
            MacroSystemInstance.MouseMovementAntiDetectionDelay = float(ActionPayload)
            MacroSystemInstance.SaveConfigurationToDisk()
            return jsonify({"status": "success"})
        
        elif RequestedAction == 'set_scan_delay':
            MacroSystemInstance.ImageProcessingLoopDelay = float(ActionPayload)
            MacroSystemInstance.SaveConfigurationToDisk()
            return jsonify({"status": "success"})
        
        elif RequestedAction == 'set_black_threshold':
            MacroSystemInstance.BlackScreenDetectionRatioThreshold = float(ActionPayload)
            MacroSystemInstance.SaveConfigurationToDisk()
            return jsonify({"status": "success"})
        
        elif RequestedAction == 'set_spam_delay':
            MacroSystemInstance.AntiMacroDialogSpamDelay = float(ActionPayload)
            MacroSystemInstance.SaveConfigurationToDisk()
            return jsonify({"status": "success"})
        
        elif RequestedAction == 'set_craft_left_point':
            MacroSystemInstance.InitiatePointSelectionMode('CraftLeftButtonLocation')
            return jsonify({"status": "waiting_for_click"})

        elif RequestedAction == 'set_craft_middle_point':
            MacroSystemInstance.InitiatePointSelectionMode('CraftMiddleButtonLocation')
            return jsonify({"status": "waiting_for_click"})
        
        elif RequestedAction == 'set_bait_recipe_point':
            MacroSystemInstance.InitiatePointSelectionMode('BaitRecipeButtonLocation')
            return jsonify({"status": "waiting_for_click"})

        elif RequestedAction == 'set_add_recipe_point':
            MacroSystemInstance.InitiatePointSelectionMode('AddRecipeButtonLocation')
            return jsonify({"status": "waiting_for_click"})

        elif RequestedAction == 'set_top_recipe_point':
            MacroSystemInstance.InitiatePointSelectionMode('TopRecipeButtonLocation')
            return jsonify({"status": "waiting_for_click"})

        elif RequestedAction == 'set_craft_button_point':
            MacroSystemInstance.InitiatePointSelectionMode('CraftButtonLocation')
            return jsonify({"status": "waiting_for_click"})

        elif RequestedAction == 'set_close_menu_point':
            MacroSystemInstance.InitiatePointSelectionMode('CloseMenuButtonLocation')
            return jsonify({"status": "waiting_for_click"})

        elif RequestedAction == 'toggle_auto_craft_bait':
            MacroSystemInstance.AutomaticBaitCraftingEnabled = ActionPayload.lower() == 'true'
            MacroSystemInstance.SaveConfigurationToDisk()
            return jsonify({"status": "success", "value": MacroSystemInstance.AutomaticBaitCraftingEnabled})

        elif RequestedAction == 'set_crafts_per_cycle':
            MacroSystemInstance.CraftsPerCycleCount = int(ActionPayload)
            MacroSystemInstance.SaveConfigurationToDisk()
            return jsonify({"status": "success"})

        elif RequestedAction == 'set_loops_per_craft':
            MacroSystemInstance.BaitCraftFrequencyCounter = int(ActionPayload)
            MacroSystemInstance.SaveConfigurationToDisk()
            return jsonify({"status": "success"})

        elif RequestedAction == 'set_move_duration':
            MacroSystemInstance.MoveDurationSeconds = float(ActionPayload)
            MacroSystemInstance.SaveConfigurationToDisk()
            return jsonify({"status": "success"})
        
        else:
            return jsonify({"status": "error", "message": f"Unknown action: {RequestedAction}"}), 400

    except Exception as ErrorDetails:
        return jsonify({"status": "error", "message": str(ErrorDetails)}), 500

@FlaskApplication.route('/health', methods=['GET'])
def PerformHealthCheck():
    return jsonify({"status": "ok", "message": "Backend running"})

def ExecuteFlaskServer():
    FlaskApplication.run(host='0.0.0.0', port=8765, debug=False, use_reloader=False)
    
if __name__ == "__main__":
    FlaskServerThread = threading.Thread(target=ExecuteFlaskServer, daemon=True)
    FlaskServerThread.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        os._exit(0)