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
import requests
from datetime import datetime
from difflib import get_close_matches
import re

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
        self.RootWindow.attributes('-alpha', 0.85)
        self.RootWindow.attributes('-topmost', True)
        self.RootWindow.overrideredirect(True)

        self.LeftBoundary, self.TopBoundary = InitialBoundingBox["x1"], InitialBoundingBox["y1"]
        self.RightBoundary, self.BottomBoundary = InitialBoundingBox["x2"], InitialBoundingBox["y2"]

        WindowWidth = self.RightBoundary - self.LeftBoundary
        WindowHeight = self.BottomBoundary - self.TopBoundary

        self.RootWindow.geometry(f"{WindowWidth}x{WindowHeight}+{self.LeftBoundary}+{self.TopBoundary}")
        self.RootWindow.configure(bg='#1e293b')

        HeaderFrame = tk.Frame(self.RootWindow, bg='#0f172a', height=40)
        HeaderFrame.pack(side='top', fill='x')
        HeaderFrame.pack_propagate(False)

        TitleLabel = tk.Label(
            HeaderFrame,
            text="📐 Select Region",
            bg='#0f172a',
            fg='#e2e8f0',
            font=('Segoe UI', 10, 'bold'),
            padx=15
        )
        TitleLabel.pack(side='left', pady=10)

        ButtonContainer = tk.Frame(HeaderFrame, bg='#0f172a')
        ButtonContainer.pack(side='right', padx=10, pady=5)

        self.ConfirmButton = tk.Button(
            ButtonContainer,
            text="✓ Confirm",
            command=self.CloseWindow,
            bg='#10b981',
            fg='white',
            font=('Segoe UI', 9, 'bold'),
            padx=20,
            pady=8,
            cursor='hand2',
            relief='flat',
            borderwidth=0,
            activebackground='#059669',
            activeforeground='white'
        )
        self.ConfirmButton.pack(side='right')

        self.ConfirmButton.bind('<Enter>', lambda e: self.ConfirmButton.config(bg='#059669'))
        self.ConfirmButton.bind('<Leave>', lambda e: self.ConfirmButton.config(bg='#10b981'))

        self.DrawingCanvas = tk.Canvas(
            self.RootWindow,
            bg='#1e293b',
            highlightthickness=2,
            highlightbackground='#3b82f6',
            relief='flat'
        )
        self.DrawingCanvas.pack(fill='both', expand=True, padx=2, pady=2)

        self.CreateCornerIndicators()

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
        
        self.RootWindow.protocol("WM_DELETE_WINDOW", self.CloseWindow)
        
        self.RootWindow.mainloop()

    def CreateCornerIndicators(self):
        corner_size = 15
        corner_color = '#3b82f6'
        
        self.RootWindow.update_idletasks()
        canvas_width = self.DrawingCanvas.winfo_width()
        canvas_height = self.DrawingCanvas.winfo_height()
        
        self.DrawingCanvas.create_rectangle(0, 0, corner_size, corner_size, 
                                        fill=corner_color, outline='')
        
        self.DrawingCanvas.create_rectangle(canvas_width - corner_size, 0, 
                                        canvas_width, corner_size, 
                                        fill=corner_color, outline='')
        
        self.DrawingCanvas.create_rectangle(0, canvas_height - corner_size, 
                                        corner_size, canvas_height, 
                                        fill=corner_color, outline='')
        
        self.DrawingCanvas.create_rectangle(canvas_width - corner_size, 
                                        canvas_height - corner_size, 
                                        canvas_width, canvas_height, 
                                        fill=corner_color, outline='')

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
        self.GlobalHotkeyBindings = {"start_stop": "f1", "exit": "f3"}

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
        self.FishingRodInventorySlot = "1"
        self.AlternateInventorySlot = "2"
        self.AutomaticBaitPurchaseEnabled = True
        self.AutomaticFruitStorageEnabled = False
        self.AutomaticTopBaitSelectionEnabled = False

        self.OCRReader = None
        self.TextDetectionEnabled = True

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
        self.DevilFruitInventorySlot = "3"

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
        self.CraftButtonLocation = None
        self.CloseMenuButtonLocation = None

        self.FishCountPerCraft = 50
        self.FishCountSinceLastCraft = 0
        self.MoveDurationSeconds = 4.25
        self.CraftMenuOpenDelay = 0.85
        self.CraftClickDelay = 0.2
        self.CraftRecipeSelectDelay = 0.2
        self.CraftAddRecipeDelay = 0.2
        self.CraftTopRecipeDelay = 0.2
        self.CraftButtonClickDelay = 0.025
        self.CraftCloseMenuDelay = 0.2

        self.BaitCraftIterationCounter = 0
        self.CurrentRecipeIndex = 0
        self.BaitRecipes = []
        
        self.AddRecipeButtonLocation = None
        self.TopRecipeSlotLocation = None
        
        self.WebhookUrl = ""
        self.LogDevilFruitEnabled = False

        self.LoadConfigurationFromDisk()
        self.RegisterAllHotkeyBindings()
    
    def LoadConfigurationFromDisk(self):
        if os.path.exists(self.ConfigurationFilePath):
            try:
                with open(self.ConfigurationFilePath, 'r') as ConfigurationFileHandle:
                    ParsedConfigurationData = json.load(ConfigurationFileHandle)

                    self.GlobalHotkeyBindings.update(ParsedConfigurationData.get("Hotkeys", {}))
                    
                    WindowSettings = ParsedConfigurationData.get("WindowSettings", {})
                    self.WindowAlwaysOnTopEnabled = WindowSettings.get("AlwaysOnTop", True)
                    self.DebugOverlayVisible = WindowSettings.get("ShowDebugOverlay", False)
                    
                    self.ScanningRegionBounds.update(ParsedConfigurationData.get("ScanArea", {}))
                    
                    ClickPoints = ParsedConfigurationData.get("ClickPoints", {})
                    self.WaterCastingTargetLocation = ClickPoints.get("WaterPoint", None)
                    
                    ShopPoints = ClickPoints.get("Shop", {})
                    self.ShopLeftButtonLocation = ShopPoints.get("LeftPoint", None)
                    self.ShopCenterButtonLocation = ShopPoints.get("MiddlePoint", None)
                    self.ShopRightButtonLocation = ShopPoints.get("RightPoint", None)
                    
                    self.BaitSelectionButtonLocation = ClickPoints.get("BaitPoint", None)
                    
                    DevilFruitPoints = ClickPoints.get("DevilFruit", {})
                    self.FruitStorageButtonLocation = DevilFruitPoints.get("StoreFruitPoint", None)
                    self.DevilFruitLocationPoint = DevilFruitPoints.get("DevilFruitLocationPoint", None)


                    
                    CraftingPoints = ClickPoints.get("Crafting", {})
                    self.CraftLeftButtonLocation = CraftingPoints.get("CraftLeftPoint", None)
                    self.CraftMiddleButtonLocation = CraftingPoints.get("CraftMiddlePoint", None)
                    self.CraftButtonLocation = CraftingPoints.get("CraftButtonPoint", None)
                    self.CloseMenuButtonLocation = CraftingPoints.get("CloseMenuPoint", None)
                    self.BaitRecipes = CraftingPoints.get("BaitRecipes", [])
                    self.CurrentRecipeIndex = CraftingPoints.get("CurrentRecipeIndex", 0)
                    
                    InventoryHotkeys = ParsedConfigurationData.get("InventoryHotkeys", {})
                    self.FishingRodInventorySlot = InventoryHotkeys.get("RodHotkey", "1")
                    self.AlternateInventorySlot = InventoryHotkeys.get("AnythingElseHotkey", "2")
                    self.DevilFruitInventorySlot = InventoryHotkeys.get("DevilFruitHotkey", "3")
                    
                    Automation = ParsedConfigurationData.get("AutomationFeatures", {})
                    self.AutomaticBaitPurchaseEnabled = Automation.get("AutoBuyCommonBait", True)
                    self.AutomaticFruitStorageEnabled = Automation.get("AutoStoreDevilFruit", False)
                    self.AutomaticTopBaitSelectionEnabled = Automation.get("AutoSelectTopBait", False)
                    self.AutomaticBaitCraftingEnabled = Automation.get("AutoCraftBait", False)
                    
                    Frequencies = ParsedConfigurationData.get("AutomationFrequencies", {})
                    self.BaitPurchaseFrequencyCounter = Frequencies.get("LoopsPerPurchase", 100)
                    self.DevilFruitStorageFrequencyCounter = Frequencies.get("LoopsPerStore", 50)
                    self.BaitCraftFrequencyCounter = Frequencies.get("LoopsPerCraft", 5)
                    self.CraftsPerCycleCount = Frequencies.get("CraftsPerCycle", 40)
                    self.FishCountPerCraft = Frequencies.get("FishCountPerCraft", 50)
                    
                    DfStorage = ParsedConfigurationData.get("DevilFruitStorage", {})
                    self.StoreToBackpackEnabled = DfStorage.get("StoreToBackpack", False)
                    self.LogDevilFruitEnabled = DfStorage.get("LogDevilFruit", False)
                    self.WebhookUrl = DfStorage.get("WebhookUrl", "")
                    
                    FishingControl = ParsedConfigurationData.get("FishingControl", {})
                    
                    PdController = FishingControl.get("PdController", {})
                    self.ProportionalGainCoefficient = PdController.get("Kp", 1.4)
                    self.DerivativeGainCoefficient = PdController.get("Kd", 0.6)
                    self.ControlSignalMaximumClamp = PdController.get("PdClamp", 1.0)
                    self.PDControllerApproachingStateDamping = PdController.get("PdApproachingDamping", 2.0)
                    self.PDControllerChasingStateDamping = PdController.get("PdChasingDamping", 0.5)
                    
                    Timing = FishingControl.get("Timing", {})
                    self.MouseHoldDurationForCast = Timing.get("CastHoldDuration", 0.1)
                    self.MaximumWaitTimeBeforeRecast = Timing.get("RecastTimeout", 25.0)
                    self.DelayAfterFishCaptured = Timing.get("FishEndDelay", 0.5)
                    self.InputStateResendFrequency = Timing.get("StateResendInterval", 0.5)
                    
                    Detection = FishingControl.get("Detection", {})
                    self.BarGroupingGapToleranceMultiplier = Detection.get("GapToleranceMultiplier", 2.0)
                    self.BlackScreenDetectionRatioThreshold = Detection.get("BlackScreenThreshold", 0.5)
                    self.ImageProcessingLoopDelay = Detection.get("ScanLoopDelay", 0.1)
                    
                    TimingDelays = ParsedConfigurationData.get("TimingDelays", {})
                    
                    RobloxWindow = TimingDelays.get("RobloxWindow", {})
                    self.RobloxWindowFocusInitialDelay = RobloxWindow.get("RobloxFocusDelay", 0.2)
                    self.RobloxWindowFocusFollowupDelay = RobloxWindow.get("RobloxPostFocusDelay", 0.2)
                    
                    PreCast = TimingDelays.get("PreCast", {})
                    self.PreCastDialogOpenDelay = PreCast.get("SetPrecastEDelay", 1.25)
                    self.PreCastMouseClickDelay = PreCast.get("PreCastClickDelay", 0.5)
                    self.PreCastKeyboardInputDelay = PreCast.get("PreCastTypeDelay", 0.25)
                    self.PreCastAntiDetectionDelay = PreCast.get("PreCastAntiDetectDelay", 0.05)
                    
                    Inventory = TimingDelays.get("Inventory", {})
                    self.InventorySlotSwitchingDelay = Inventory.get("RodSelectDelay", 0.2)
                    self.BaitSelectionConfirmationDelay = Inventory.get("AutoSelectBaitDelay", 0.5)
                    
                    DfStorageDelays = TimingDelays.get("DevilFruitStorage", {})
                    self.FruitStorageHotkeyActivationDelay = DfStorageDelays.get("StoreFruitHotkeyDelay", 1.0)
                    self.FruitStorageClickConfirmationDelay = DfStorageDelays.get("StoreFruitClickDelay", 2.0)
                    self.FruitStorageShiftKeyPressDelay = DfStorageDelays.get("StoreFruitShiftDelay", 0.5)
                    self.FruitStorageBackspaceDeletionDelay = DfStorageDelays.get("StoreFruitBackspaceDelay", 1.5)
                    
                    AntiDetection = TimingDelays.get("AntiDetection", {})
                    self.MouseMovementAntiDetectionDelay = AntiDetection.get("CursorAntiDetectDelay", 0.05)
                    self.AntiMacroDialogSpamDelay = AntiDetection.get("AntiMacroSpamDelay", 0.25)
                    
                    CraftingDelays = TimingDelays.get("Crafting", {})
                    self.MoveDurationSeconds = CraftingDelays.get("MoveDuration", 4.25)
                    self.CraftMenuOpenDelay = CraftingDelays.get("CraftMenuOpenDelay", 0.85)
                    self.CraftClickDelay = CraftingDelays.get("CraftClickDelay", 0.2)
                    self.CraftRecipeSelectDelay = CraftingDelays.get("CraftRecipeSelectDelay", 0.2)
                    self.CraftAddRecipeDelay = CraftingDelays.get("CraftAddRecipeDelay", 0.2)
                    self.CraftTopRecipeDelay = CraftingDelays.get("CraftTopRecipeDelay", 0.2)
                    self.CraftButtonClickDelay = CraftingDelays.get("CraftButtonClickDelay", 0.025)
                    self.CraftCloseMenuDelay = CraftingDelays.get("CraftCloseMenuDelay", 0.2)
            except Exception as LoadError:
                import traceback
                traceback.print_exc()

    
    def SaveConfigurationToDisk(self):
        try:
            with open(self.ConfigurationFilePath, 'w') as ConfigurationFileHandle:
                json.dump({
                    "Hotkeys": self.GlobalHotkeyBindings,
                    "WindowSettings": {
                        "AlwaysOnTop": self.WindowAlwaysOnTopEnabled,
                        "ShowDebugOverlay": self.DebugOverlayVisible
                    },
                    "ScanArea": self.ScanningRegionBounds,
                    "ClickPoints": {
                        "WaterPoint": self.WaterCastingTargetLocation,
                        "Shop": {
                            "LeftPoint": self.ShopLeftButtonLocation,
                            "MiddlePoint": self.ShopCenterButtonLocation,
                            "RightPoint": self.ShopRightButtonLocation
                        },
                        "BaitPoint": self.BaitSelectionButtonLocation,
                        "DevilFruit": {
                            "StoreFruitPoint": self.FruitStorageButtonLocation,
                            "DevilFruitLocationPoint": self.DevilFruitLocationPoint
                        },
                        "Crafting": {
                            "CraftLeftPoint": self.CraftLeftButtonLocation,
                            "CraftMiddlePoint": self.CraftMiddleButtonLocation,
                            "CraftButtonPoint": self.CraftButtonLocation,
                            "CloseMenuPoint": self.CloseMenuButtonLocation,
                            "BaitRecipes": self.BaitRecipes,
                            "CurrentRecipeIndex": self.CurrentRecipeIndex
                        }
                    },
                    "InventoryHotkeys": {
                        "RodHotkey": self.FishingRodInventorySlot,
                        "AnythingElseHotkey": self.AlternateInventorySlot,
                        "DevilFruitHotkey": self.DevilFruitInventorySlot
                    },
                    "AutomationFeatures": {
                        "AutoBuyCommonBait": self.AutomaticBaitPurchaseEnabled,
                        "AutoStoreDevilFruit": self.AutomaticFruitStorageEnabled,
                        "AutoSelectTopBait": self.AutomaticTopBaitSelectionEnabled,
                        "AutoCraftBait": self.AutomaticBaitCraftingEnabled
                    },
                    "AutomationFrequencies": {
                        "LoopsPerPurchase": self.BaitPurchaseFrequencyCounter,
                        "LoopsPerStore": self.DevilFruitStorageFrequencyCounter,
                        "LoopsPerCraft": self.BaitCraftFrequencyCounter,
                        "CraftsPerCycle": self.CraftsPerCycleCount,
                        "FishCountPerCraft": self.FishCountPerCraft
                    },
                    "DevilFruitStorage": {
                        "StoreToBackpack": self.StoreToBackpackEnabled,
                        "LogDevilFruit": self.LogDevilFruitEnabled,
                        "WebhookUrl": self.WebhookUrl
                    },
                    "FishingControl": {
                        "PdController": {
                            "Kp": self.ProportionalGainCoefficient,
                            "Kd": self.DerivativeGainCoefficient,
                            "PdClamp": self.ControlSignalMaximumClamp,
                            "PdApproachingDamping": self.PDControllerApproachingStateDamping,
                            "PdChasingDamping": self.PDControllerChasingStateDamping
                        },
                        "Timing": {
                            "CastHoldDuration": self.MouseHoldDurationForCast,
                            "RecastTimeout": self.MaximumWaitTimeBeforeRecast,
                            "FishEndDelay": self.DelayAfterFishCaptured,
                            "StateResendInterval": self.InputStateResendFrequency
                        },
                        "Detection": {
                            "GapToleranceMultiplier": self.BarGroupingGapToleranceMultiplier,
                            "BlackScreenThreshold": self.BlackScreenDetectionRatioThreshold,
                            "ScanLoopDelay": self.ImageProcessingLoopDelay
                        }
                    },
                    "TimingDelays": {
                        "RobloxWindow": {
                            "RobloxFocusDelay": self.RobloxWindowFocusInitialDelay,
                            "RobloxPostFocusDelay": self.RobloxWindowFocusFollowupDelay
                        },
                        "PreCast": {
                            "SetPrecastEDelay": self.PreCastDialogOpenDelay,
                            "PreCastClickDelay": self.PreCastMouseClickDelay,
                            "PreCastTypeDelay": self.PreCastKeyboardInputDelay,
                            "PreCastAntiDetectDelay": self.PreCastAntiDetectionDelay
                        },
                        "Inventory": {
                            "RodSelectDelay": self.InventorySlotSwitchingDelay,
                            "AutoSelectBaitDelay": self.BaitSelectionConfirmationDelay
                        },
                        "DevilFruitStorage": {
                            "StoreFruitHotkeyDelay": self.FruitStorageHotkeyActivationDelay,
                            "StoreFruitClickDelay": self.FruitStorageClickConfirmationDelay,
                            "StoreFruitShiftDelay": self.FruitStorageShiftKeyPressDelay,
                            "StoreFruitBackspaceDelay": self.FruitStorageBackspaceDeletionDelay
                        },
                        "AntiDetection": {
                            "CursorAntiDetectDelay": self.MouseMovementAntiDetectionDelay,
                            "AntiMacroSpamDelay": self.AntiMacroDialogSpamDelay
                        },
                        "Crafting": {
                            "MoveDuration": self.MoveDurationSeconds,
                            "CraftMenuOpenDelay": self.CraftMenuOpenDelay,
                            "CraftClickDelay": self.CraftClickDelay,
                            "CraftRecipeSelectDelay": self.CraftRecipeSelectDelay,
                            "CraftAddRecipeDelay": self.CraftAddRecipeDelay,
                            "CraftTopRecipeDelay": self.CraftTopRecipeDelay,
                            "CraftButtonClickDelay": self.CraftButtonClickDelay,
                            "CraftCloseMenuDelay": self.CraftCloseMenuDelay
                        }
                    }
                }, ConfigurationFileHandle, indent=4)
        except Exception as SaveError:
            print(f"Error saving settings: {SaveError}")
    
    def InitializeOCR(self):
        if self.OCRReader is None and self.TextDetectionEnabled:
            try:
                print("Initializing OCR In Background...")
                def LoadOCRInBackground():
                    try:
                        import easyocr
                        self.OCRReader = easyocr.Reader(['en'], gpu=False, verbose=False)
                        print("OCR Initialized Successfully!")
                    except Exception as OCRInitError:
                        print(f"OCR Initialization Error: {OCRInitError}")
                        self.TextDetectionEnabled = False
                
                threading.Thread(target=LoadOCRInBackground, daemon=True).start()
            except Exception as OCRInitError:
                print(f"OCR Thread Error: {OCRInitError}")
                self.TextDetectionEnabled = False

    def DetectNewItemNotification(self):
        try:
            if self.OCRReader is None:
                if not self.TextDetectionEnabled:
                    return None
                
                self.InitializeOCR()
                
                print("Waiting For OCR To Initialize...")
                WaitStartTime = time.time()
                MaxWaitTime = 30.0
                
                while self.OCRReader is None and (time.time() - WaitStartTime) < MaxWaitTime:
                    if not self.MacroCurrentlyExecuting:
                        return None
                    time.sleep(0.5)
                
                if self.OCRReader is None:
                    print("OCR Initialization Timeout!")
                    self.TextDetectionEnabled = False
                    return None
                
                print("OCR Ready!")
                
            SystemDisplayMetrics = ctypes.windll.user32
            MonitorWidth = SystemDisplayMetrics.GetSystemMetrics(0)
            MonitorHeight = SystemDisplayMetrics.GetSystemMetrics(1)

            ScanRegion = {
                "top": 60,
                "left": int(MonitorWidth * 0.40),
                "width": int(MonitorWidth * 0.20),
                "height": int(MonitorHeight * 0.20)
            }

            with mss.mss() as ScreenCapture:
                ScreenshotData = ScreenCapture.grab(ScanRegion)
                Image = np.array(ScreenshotData)

            try:
                from PIL import Image as PILImage
                DebugImage = PILImage.frombytes('RGB', ScreenshotData.size, ScreenshotData.rgb)
                DebugImage.save("ocr_debug_scan.png")
                print("Debug Image Saved: ocr_debug_scan.png")
            except Exception as SaveError:
                print(f"Could Not Save Debug Image: {SaveError}")

            ImageRGB = Image[:, :, [2, 1, 0]]
            
            print("Running OCR...")
            Results = self.OCRReader.readtext(ImageRGB, detail=1, paragraph=False)
            
            print(f"OCR Found {len(Results)} Text Blocks")

            FullText = ""
            for Index, (BBox, Text, Confidence) in enumerate(Results):
                print(f"  Block {Index + 1}: '{Text}' (Confidence: {Confidence:.2f})")
                if Confidence > 0.2:
                    FullText += Text + " "
            
            FullText = FullText.strip()
            print(f"Combined Text: '{FullText}'")

            if FullText and ("new" in FullText.lower() or "nev" in FullText.lower()):
                if "item" in FullText.lower():
                    print(f"Found 'New Item' In Text!")
                    
                    BracketMatch = re.search(r'<([^>]+)>', FullText, re.IGNORECASE)
                    if BracketMatch:
                        ItemName = BracketMatch.group(1).strip()
                        print(f"✅ Extracted Fruit Name: {ItemName}")
                        return ItemName
                    
                    AfterItemMatch = re.search(r'item\s+(.+)', FullText, re.IGNORECASE)
                    if AfterItemMatch:
                        ItemName = AfterItemMatch.group(1).strip()
                        ItemName = ItemName.replace('<', '').replace('>', '').strip()
                        if ItemName:
                            print(f"✅ Extracted Fruit Name (No Brackets): {ItemName}")
                            return ItemName
                    
                    print(f"⚠️ Could Not Extract Name, Returning Full Text")
                    return FullText
            else:
                print("❌ No 'New Item' Text Found")
            
            return None
            
        except Exception as OCRCheckError:
            print(f"OCR Check Error: {OCRCheckError}")
            import traceback
            traceback.print_exc()
            return None
        
    def RegisterAllHotkeyBindings(self):
        try:
            keyboard.add_hotkey(self.GlobalHotkeyBindings["start_stop"], self.ToggleMacroExecution)
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

    def SendWebhookNotification(self, message, color=0x00d4ff):
        if not self.WebhookUrl:
            return
        
        try:
            if "successfully" in message.lower():
                emoji = "✅"
                color = 0x00ff00
            elif "could not" in message.lower() or "failed" in message.lower():
                emoji = "❌"
                color = 0xff0000
            else:
                emoji = "🎣"
                color = 0x00d4ff
            
            embed = {
                "title": f"{emoji} GPO Fishing Macro",
                "description": f"**{message}**",
                "color": color,
                "timestamp": datetime.utcnow().isoformat(),
                "footer": {
                    "text": "Macro Notification System",
                    "icon_url": "https://cdn.discordapp.com/avatars/1351127835175288893/208dc6bfcc148a0c3ad2482b12520f43.webp"
                },
                "fields": [
                    {
                        "name": "🕒 Time",
                        "value": f"<t:{int(time.time())}:R>",
                        "inline": True
                    }
                ],
            }
            
            payload = {
                "username": "GPO Macro Bot",
                "embeds": [embed]
            }
            
            requests.post(self.WebhookUrl, json=payload, timeout=5)
        except Exception as e:
            print(f"Webhook error: {e}")
    
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
                    self.FishCountSinceLastCraft += 1
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
            self.CraftButtonLocation,
            self.CloseMenuButtonLocation,
            self.AddRecipeButtonLocation,
            self.TopRecipeSlotLocation,
            len(self.BaitRecipes) > 0
        ]):
            if self.FishCountSinceLastCraft >= self.FishCountPerCraft:
                time.sleep(self.CraftMenuOpenDelay)
                if self.MoveDurationSeconds < 0:
                    keyboard.press_and_release('shift')
                    time.sleep(0.1)
                    if not self.MacroCurrentlyExecuting: return False
                    
                    keyboard.press('d')
                    time.sleep(abs(self.MoveDurationSeconds))
                    keyboard.release('d')

                    time.sleep(self.FruitStorageShiftKeyPressDelay)
                    if not self.MacroCurrentlyExecuting: return False
                    
                    keyboard.press_and_release('shift')
                    time.sleep(0.1)
                    if not self.MacroCurrentlyExecuting: return False
                
                keyboard.press_and_release('t')
                time.sleep(self.CraftMenuOpenDelay)
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
                
                for RecipeIndex in range(len(self.BaitRecipes)):
                    CurrentRecipe = self.BaitRecipes[RecipeIndex]
                    
                    if not CurrentRecipe.get('BaitRecipePoint'):
                        continue
                    
                    ctypes.windll.user32.SetCursorPos(CurrentRecipe['BaitRecipePoint']['x'], CurrentRecipe['BaitRecipePoint']['y'])
                    time.sleep(self.PreCastAntiDetectionDelay)
                    ctypes.windll.user32.mouse_event(0x0001, 0, 1, 0, 0)
                    time.sleep(self.PreCastAntiDetectionDelay)
                    pyautogui.click()
                    time.sleep(self.PreCastMouseClickDelay)
                    if not self.MacroCurrentlyExecuting: return False
                    
                    RecipeSwitchCycle = CurrentRecipe.get('SwitchFishCycle', 5)
                    RecipeCraftsPerCycle = CurrentRecipe.get('CraftsPerCycle', 40)
                    
                    for FishIteration in range(RecipeSwitchCycle):
                        if not self.MacroCurrentlyExecuting: return False
                        
                        ctypes.windll.user32.SetCursorPos(self.AddRecipeButtonLocation['x'], self.AddRecipeButtonLocation['y'])
                        time.sleep(self.PreCastAntiDetectionDelay)
                        ctypes.windll.user32.mouse_event(0x0001, 0, 1, 0, 0)
                        time.sleep(self.PreCastAntiDetectionDelay)
                        pyautogui.click()
                        time.sleep(self.PreCastMouseClickDelay)
                        if not self.MacroCurrentlyExecuting: return False
                        
                        ctypes.windll.user32.SetCursorPos(self.TopRecipeSlotLocation['x'], self.TopRecipeSlotLocation['y'])
                        time.sleep(self.PreCastAntiDetectionDelay)
                        ctypes.windll.user32.mouse_event(0x0001, 0, 1, 0, 0)
                        time.sleep(self.PreCastAntiDetectionDelay)
                        pyautogui.click()
                        time.sleep(self.PreCastMouseClickDelay)
                        if not self.MacroCurrentlyExecuting: return False
                        
                        for CraftIteration in range(RecipeCraftsPerCycle):
                            if not self.MacroCurrentlyExecuting: return False
                            
                            ctypes.windll.user32.SetCursorPos(self.CraftButtonLocation['x'], self.CraftButtonLocation['y'])
                            time.sleep(self.PreCastAntiDetectionDelay)
                            ctypes.windll.user32.mouse_event(0x0001, 0, 1, 0, 0)
                            time.sleep(self.PreCastAntiDetectionDelay)
                            pyautogui.click()
                            time.sleep(0.025)
                
                ctypes.windll.user32.SetCursorPos(self.CloseMenuButtonLocation['x'], self.CloseMenuButtonLocation['y'])
                time.sleep(self.PreCastAntiDetectionDelay)
                ctypes.windll.user32.mouse_event(0x0001, 0, 1, 0, 0)
                time.sleep(self.PreCastAntiDetectionDelay)
                pyautogui.click()
                time.sleep(self.PreCastMouseClickDelay)
                if not self.MacroCurrentlyExecuting: return False

                if self.MoveDurationSeconds < 0: 
                    keyboard.press_and_release('shift')
                    time.sleep(0.1)
                    if not self.MacroCurrentlyExecuting: return False
                    
                    keyboard.press('a')
                    time.sleep(abs(self.MoveDurationSeconds))
                    keyboard.release('a')
                    time.sleep(1.0)
                    if not self.MacroCurrentlyExecuting: return False
                    
                    keyboard.press_and_release('shift')
                    time.sleep(0.1)
                    if not self.MacroCurrentlyExecuting: return False
                
                self.FishCountSinceLastCraft = 0
        
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
                        InitGreenDetected = False
                        if self.LogDevilFruitEnabled and self.DetectGreenishColor(self.FruitStorageButtonLocation):
                            InitGreenDetected = True
                            
                        ctypes.windll.user32.SetCursorPos(self.FruitStorageButtonLocation['x'], self.FruitStorageButtonLocation['y'])
                        time.sleep(self.PreCastAntiDetectionDelay)
                        ctypes.windll.user32.mouse_event(0x0001, 0, 1, 0, 0)
                        time.sleep(self.PreCastAntiDetectionDelay)
                        pyautogui.click()
                        time.sleep(self.FruitStorageClickConfirmationDelay)
                        if not self.MacroCurrentlyExecuting: return False
                        
                        start_x = self.DevilFruitLocationPoint['x']
                        start_y = self.DevilFruitLocationPoint['y']
                        end_x = self.DevilFruitLocationPoint['x']
                        end_y = self.DevilFruitLocationPoint['y'] - 150
                        
                        ctypes.windll.user32.SetCursorPos(start_x, start_y)
                        time.sleep(0.03)
                        ctypes.windll.user32.mouse_event(0x0001, 0, 1, 0, 0)
                        time.sleep(0.08)
                        if not self.MacroCurrentlyExecuting: return False
                        
                        pyautogui.mouseDown()
                        time.sleep(0.15)
                        if not self.MacroCurrentlyExecuting:
                            pyautogui.mouseUp()
                            return False
                        
                        ctypes.windll.user32.SetCursorPos(end_x, end_y)
                        time.sleep(0.03)
                        ctypes.windll.user32.mouse_event(0x0001, 0, 1, 0, 0)
                        time.sleep(0.25)
                        if not self.MacroCurrentlyExecuting:
                            pyautogui.mouseUp()
                            return False
                        
                        pyautogui.mouseUp()
                        
                        time.sleep(self.PreCastAntiDetectionDelay)
                        if not self.MacroCurrentlyExecuting: return False
                        
                        keyboard.press_and_release('`')
                        time.sleep(self.FruitStorageHotkeyActivationDelay)
                    
                        if InitGreenDetected and self.WebhookUrl:
                            time.sleep(1.0)
                            if not self.MacroCurrentlyExecuting: return False
                            if not self.DetectGreenishColor(self.FruitStorageButtonLocation):
                                self.SendWebhookNotification("Devil Fruit stored successfully!")
                            else:
                                self.SendWebhookNotification("Devil Fruit could not be stored.")
                                
                elif self.FruitStorageButtonLocation:
                    keyboard.press_and_release(self.AlternateInventorySlot)
                    time.sleep(self.InventorySlotSwitchingDelay)

                    keyboard.press_and_release(self.FishingRodInventorySlot)
                    time.sleep(self.InventorySlotSwitchingDelay)

                    keyboard.press_and_release(self.FishingRodInventorySlot)
                    time.sleep(self.InventorySlotSwitchingDelay)

                    keyboard.press_and_release(self.DevilFruitInventorySlot)
                    time.sleep(self.FruitStorageHotkeyActivationDelay)
                    if not self.MacroCurrentlyExecuting: return False

                    InitGreenDetected = False
                    if self.LogDevilFruitEnabled and self.DetectGreenishColor(self.FruitStorageButtonLocation):
                        InitGreenDetected = True
                            
                    ctypes.windll.user32.SetCursorPos(self.FruitStorageButtonLocation['x'], self.FruitStorageButtonLocation['y'])
                    time.sleep(self.PreCastAntiDetectionDelay)
                    ctypes.windll.user32.mouse_event(0x0001, 0, 1, 0, 0)
                    time.sleep(self.PreCastAntiDetectionDelay)
                    pyautogui.click()
                    time.sleep(self.FruitStorageClickConfirmationDelay)
                    if not self.MacroCurrentlyExecuting: return False
                    
                    if InitGreenDetected and self.WebhookUrl:
                        DetectedFruitName = None
                        if self.TextDetectionEnabled:
                            DetectedFruitName = self.DetectNewItemNotification()

                        if not self.MacroCurrentlyExecuting: return False

                        if not self.DetectGreenishColor(self.FruitStorageButtonLocation):
                            def GetClosestFruit(Name, Cutoff=0.6):
                                KnownFruits = {
                                    "Soul", "Dragon", "Mochi", "Ope", "Tori", "Buddha",
                                    "Pika", "Kage", "Magu", "Gura", "Yuki", "Smoke",
                                    "Goru", "Suna", "Mera", "Goro", "Ito", "Paw",
                                    "Yami", "Zushi", "Kira", "Spring", "Yomi",
                                    "Bomu", "Bari", "Mero", "Horo", "Gomu", "Suke", "Heal",
                                    "Kilo", "Spin", "Hie", "Venom", "Pteranodon",
                                }

                                Matches = get_close_matches(Name, KnownFruits, n=1, cutoff=Cutoff)
                                return Matches[0] if Matches else None

                            if DetectedFruitName:
                                ClosestMatch = GetClosestFruit(DetectedFruitName)
                                self.SendWebhookNotification(f"Devil Fruit {ClosestMatch or DetectedFruitName} stored successfully!")
                            else:
                                self.SendWebhookNotification("Devil Fruit stored successfully!")
                        else:
                            self.SendWebhookNotification("Devil Fruit could not be stored.")
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
    
    def DetectGreenishColor(self, TargetPoint, ToleranceRadius=20):
        if not TargetPoint:
            return False
        
        try:
            with mss.mss() as ScreenCapture:
                CaptureRegion = {
                    "top": TargetPoint['y'] - ToleranceRadius,
                    "left": TargetPoint['x'] - ToleranceRadius,
                    "width": ToleranceRadius * 2,
                    "height": ToleranceRadius * 2
                }
                CapturedScreen = ScreenCapture.grab(CaptureRegion)
                ScreenImageArray = np.array(CapturedScreen)
            
            GreenChannel = ScreenImageArray[:, :, 1]
            RedChannel = ScreenImageArray[:, :, 2]
            BlueChannel = ScreenImageArray[:, :, 0]
            
            GreenishMask = (
                (GreenChannel > RedChannel + 20) & 
                (GreenChannel > BlueChannel + 20) &
                (GreenChannel > 80)
            )
            
            GreenPixelCount = np.sum(GreenishMask)
            TotalPixels = ScreenImageArray.shape[0] * ScreenImageArray.shape[1]
            GreenRatio = GreenPixelCount / TotalPixels
            
            return GreenRatio > 0.10
            
        except Exception as e:
            print(f"Error detecting green color: {e}")
            return False
    
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
            "moveDuration": self.MoveDurationSeconds,
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
            "craftButtonPoint": self.CraftButtonLocation,
            "closeMenuPoint": self.CloseMenuButtonLocation,
            "craftsPerCycle": self.CraftsPerCycleCount,
            "loopsPerCraft": self.BaitCraftFrequencyCounter,
            "fishCountPerCraft": self.FishCountPerCraft,
            "craftMenuOpenDelay": self.CraftMenuOpenDelay,
            "craftClickDelay": self.CraftClickDelay,
            "craftRecipeSelectDelay": self.CraftRecipeSelectDelay,
            "craftAddRecipeDelay": self.CraftAddRecipeDelay,
            "craftTopRecipeDelay": self.CraftTopRecipeDelay,
            "craftButtonClickDelay": self.CraftButtonClickDelay,
            "craftCloseMenuDelay": self.CraftCloseMenuDelay,
            "webhookUrl": self.WebhookUrl,
            "logDevilFruit": self.LogDevilFruitEnabled,
            "baitRecipes": self.BaitRecipes,
            "currentRecipeIndex": self.CurrentRecipeIndex,
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
        
        if not RequestedAction:
            return jsonify({"status": "error", "message": "Missing action parameter"}), 400
        
        action_handlers = {
            'set_water_point': lambda: handle_point_selection('WaterCastingTargetLocation'),
            'set_devil_fruit_location_point': lambda: handle_point_selection('DevilFruitLocationPoint'),
            'set_left_point': lambda: handle_point_selection('ShopLeftButtonLocation'),
            'set_middle_point': lambda: handle_point_selection('ShopCenterButtonLocation'),
            'set_right_point': lambda: handle_point_selection('ShopRightButtonLocation'),
            'set_store_fruit_point': lambda: handle_point_selection('FruitStorageButtonLocation'),
            'set_bait_point': lambda: handle_point_selection('BaitSelectionButtonLocation'),
            'set_craft_left_point': lambda: handle_point_selection('CraftLeftButtonLocation'),
            'set_craft_middle_point': lambda: handle_point_selection('CraftMiddleButtonLocation'),
            'set_bait_recipe_point': lambda: handle_point_selection('BaitRecipeButtonLocation'),
            'set_add_recipe_point': lambda: handle_point_selection('AddRecipeButtonLocation'),
            'set_top_recipe_point': lambda: handle_point_selection('TopRecipeButtonLocation'),
            'set_craft_button_point': lambda: handle_point_selection('CraftButtonLocation'),
            'set_close_menu_point': lambda: handle_point_selection('CloseMenuButtonLocation'),
            'toggle_store_to_backpack': lambda: handle_boolean_toggle('StoreToBackpackEnabled'),
            'toggle_always_on_top': lambda: handle_boolean_toggle('WindowAlwaysOnTopEnabled'),
            'toggle_debug_overlay': lambda: handle_boolean_toggle('DebugOverlayVisible'),
            'toggle_auto_buy_bait': lambda: handle_boolean_toggle('AutomaticBaitPurchaseEnabled'),
            'toggle_auto_store_fruit': lambda: handle_boolean_toggle('AutomaticFruitStorageEnabled'),
            'toggle_auto_select_bait': lambda: handle_boolean_toggle('AutomaticTopBaitSelectionEnabled'),
            'toggle_auto_craft_bait': lambda: handle_boolean_toggle('AutomaticBaitCraftingEnabled'),
            'set_rod_hotkey': lambda: handle_string_value('FishingRodInventorySlot'),
            'set_anything_else_hotkey': lambda: handle_string_value('AlternateInventorySlot'),
            'set_devil_fruit_hotkey': lambda: handle_string_value('DevilFruitInventorySlot'),
            'set_loops_per_store': lambda: handle_integer_value('DevilFruitStorageFrequencyCounter'),
            'set_loops_per_purchase': lambda: handle_integer_value('BaitPurchaseFrequencyCounter'),
            'set_fish_count_per_craft': lambda: handle_integer_value('FishCountPerCraft'),
            'set_crafts_per_cycle': lambda: handle_integer_value('CraftsPerCycleCount'),
            'set_loops_per_craft': lambda: handle_integer_value('BaitCraftFrequencyCounter'),
            'set_kp': lambda: handle_float_value('ProportionalGainCoefficient'),
            'set_kd': lambda: handle_float_value('DerivativeGainCoefficient'),
            'set_pd_clamp': lambda: handle_float_value('ControlSignalMaximumClamp'),
            'set_pd_approaching': lambda: handle_float_value('PDControllerApproachingStateDamping'),
            'set_pd_chasing': lambda: handle_float_value('PDControllerChasingStateDamping'),
            'set_gap_tolerance': lambda: handle_float_value('BarGroupingGapToleranceMultiplier'),
            'set_cast_hold': lambda: handle_float_value('MouseHoldDurationForCast'),
            'set_recast_timeout': lambda: handle_float_value('MaximumWaitTimeBeforeRecast'),
            'set_fish_end_delay': lambda: handle_float_value('DelayAfterFishCaptured'),
            'set_state_resend': lambda: handle_float_value('InputStateResendFrequency'),
            'set_focus_delay': lambda: handle_float_value('RobloxWindowFocusInitialDelay'),
            'set_post_focus_delay': lambda: handle_float_value('RobloxWindowFocusFollowupDelay'),
            'set_precast_e_delay': lambda: handle_float_value('PreCastDialogOpenDelay'),
            'set_precast_click_delay': lambda: handle_float_value('PreCastMouseClickDelay'),
            'set_precast_type_delay': lambda: handle_float_value('PreCastKeyboardInputDelay'),
            'set_anti_detect_delay': lambda: handle_float_value('PreCastAntiDetectionDelay'),
            'set_fruit_hotkey_delay': lambda: handle_float_value('FruitStorageHotkeyActivationDelay'),
            'set_fruit_click_delay': lambda: handle_float_value('FruitStorageClickConfirmationDelay'),
            'set_fruit_shift_delay': lambda: handle_float_value('FruitStorageShiftKeyPressDelay'),
            'set_fruit_backspace_delay': lambda: handle_float_value('FruitStorageBackspaceDeletionDelay'),
            'set_rod_delay': lambda: handle_float_value('InventorySlotSwitchingDelay'),
            'set_bait_delay': lambda: handle_float_value('BaitSelectionConfirmationDelay'),
            'set_cursor_delay': lambda: handle_float_value('MouseMovementAntiDetectionDelay'),
            'set_scan_delay': lambda: handle_float_value('ImageProcessingLoopDelay'),
            'set_black_threshold': lambda: handle_float_value('BlackScreenDetectionRatioThreshold'),
            'set_spam_delay': lambda: handle_float_value('AntiMacroDialogSpamDelay'),
            'set_move_duration': lambda: handle_float_value('MoveDurationSeconds'),
            'set_craft_menu_delay': lambda: handle_float_value('CraftMenuOpenDelay'),
            'set_craft_click_delay': lambda: handle_float_value('CraftClickDelay'),
            'set_craft_recipe_delay': lambda: handle_float_value('CraftRecipeSelectDelay'),
            'set_craft_add_delay': lambda: handle_float_value('CraftAddRecipeDelay'),
            'set_craft_top_delay': lambda: handle_float_value('CraftTopRecipeDelay'),
            'set_craft_button_delay': lambda: handle_float_value('CraftButtonClickDelay'),
            'set_craft_close_delay': lambda: handle_float_value('CraftCloseMenuDelay'),
            'set_webhook_url': lambda: handle_string_value('WebhookUrl'),
            'toggle_log_devil_fruit': lambda: handle_boolean_toggle('LogDevilFruitEnabled'),
            'open_area_selector': lambda: handle_area_selector(),
        }
        
        if RequestedAction == 'rebind_hotkey':
            return handle_hotkey_rebind(ActionPayload)
        
        if RequestedAction in action_handlers:
            return action_handlers[RequestedAction]()
        else:
            return jsonify({"status": "error", "message": f"Unknown action: {RequestedAction}"}), 400
    
    except ValueError as e:
        return jsonify({"status": "error", "message": f"Invalid value format: {str(e)}"}), 400
    except Exception as ErrorDetails:
        return jsonify({"status": "error", "message": str(ErrorDetails)}), 500

@FlaskApplication.route('/add_recipe', methods=['POST'])
def AddNewRecipe():
    try:
        MacroSystemInstance.BaitRecipes.append({
            "BaitRecipePoint": None,
            "CraftsPerCycle": 40,  # Add this
            "SwitchFishCycle": 5   # Add this
        })
        MacroSystemInstance.SaveConfigurationToDisk()
        return jsonify({"status": "success", "recipeIndex": len(MacroSystemInstance.BaitRecipes) - 1})
    except Exception as ErrorDetails:
        return jsonify({"status": "error", "message": str(ErrorDetails)}), 500

@FlaskApplication.route('/remove_recipe', methods=['POST'])
def RemoveRecipe():
    try:
        IncomingData = request.json
        RecipeIndex = int(IncomingData.get('index'))
        if 0 <= RecipeIndex < len(MacroSystemInstance.BaitRecipes):
            MacroSystemInstance.BaitRecipes.pop(RecipeIndex)
            MacroSystemInstance.SaveConfigurationToDisk()
            return jsonify({"status": "success"})
        return jsonify({"status": "error", "message": "Invalid index"}), 400
    except Exception as ErrorDetails:
        return jsonify({"status": "error", "message": str(ErrorDetails)}), 500
    
@FlaskApplication.route('/update_recipe_value', methods=['POST'])
def UpdateRecipeValue():
    try:
        IncomingData = request.json
        RecipeIndex = int(IncomingData.get('recipeIndex'))
        FieldName = IncomingData.get('fieldName')
        Value = int(IncomingData.get('value'))
        
        if 0 <= RecipeIndex < len(MacroSystemInstance.BaitRecipes):
            MacroSystemInstance.BaitRecipes[RecipeIndex][FieldName] = Value
            MacroSystemInstance.SaveConfigurationToDisk()
            return jsonify({"status": "success"})
        return jsonify({"status": "error", "message": "Invalid index"}), 400
    except Exception as ErrorDetails:
        return jsonify({"status": "error", "message": str(ErrorDetails)}), 500
    
@FlaskApplication.route('/set_recipe_point', methods=['POST'])
def SetRecipePoint():
    try:
        IncomingData = request.json
        RecipeIndex = int(IncomingData.get('recipeIndex'))
        PointType = IncomingData.get('pointType')
        
        MacroSystemInstance.CurrentlySettingPointName = (RecipeIndex, PointType)
        
        def ProcessMouseClickEvent(ClickPositionX, ClickPositionY, ButtonPressed, IsPressed):
            if IsPressed and MacroSystemInstance.CurrentlySettingPointName == (RecipeIndex, PointType):
                MacroSystemInstance.BaitRecipes[RecipeIndex][PointType] = {
                    "x": ClickPositionX, 
                    "y": ClickPositionY
                }
                MacroSystemInstance.SaveConfigurationToDisk()
                MacroSystemInstance.CurrentlySettingPointName = None
                return False
        
        if MacroSystemInstance.MouseEventListenerInstance:
            MacroSystemInstance.MouseEventListenerInstance.stop()
        
        MacroSystemInstance.MouseEventListenerInstance = mouse.Listener(on_click=ProcessMouseClickEvent)
        MacroSystemInstance.MouseEventListenerInstance.start()
        
        return jsonify({"status": "waiting_for_click"})
    except Exception as ErrorDetails:
        return jsonify({"status": "error", "message": str(ErrorDetails)}), 500

def handle_point_selection(point_name):
    MacroSystemInstance.InitiatePointSelectionMode(point_name)
    return jsonify({"status": "waiting_for_click"})

def handle_area_selector():
    MacroSystemInstance.ModifyScanningRegion()
    return jsonify({"status": "opening_selector"})

def handle_boolean_toggle(attribute_name):
    ActionPayload = request.json.get('payload')
    if ActionPayload is None:
        return jsonify({"status": "error", "message": "Missing payload"}), 400
    
    boolean_value = ActionPayload.lower() == 'true'
    setattr(MacroSystemInstance, attribute_name, boolean_value)
    MacroSystemInstance.SaveConfigurationToDisk()
    return jsonify({"status": "success", "value": boolean_value})


def handle_string_value(attribute_name):
    ActionPayload = request.json.get('payload')
    if ActionPayload is None:
        return jsonify({"status": "error", "message": "Missing payload"}), 400
    
    setattr(MacroSystemInstance, attribute_name, ActionPayload)
    MacroSystemInstance.SaveConfigurationToDisk()
    return jsonify({"status": "success"})


def handle_integer_value(attribute_name):
    ActionPayload = request.json.get('payload')
    if ActionPayload is None:
        return jsonify({"status": "error", "message": "Missing payload"}), 400
    
    try:
        integer_value = int(ActionPayload)
        setattr(MacroSystemInstance, attribute_name, integer_value)
        MacroSystemInstance.SaveConfigurationToDisk()
        return jsonify({"status": "success"})
    except (ValueError, TypeError) as e:
        return jsonify({"status": "error", "message": f"Invalid integer value: {str(e)}"}), 400


def handle_float_value(attribute_name):
    ActionPayload = request.json.get('payload')
    if ActionPayload is None:
        return jsonify({"status": "error", "message": "Missing payload"}), 400
    
    try:
        float_value = float(ActionPayload)
        setattr(MacroSystemInstance, attribute_name, float_value)
        MacroSystemInstance.SaveConfigurationToDisk()
        return jsonify({"status": "success"})
    except (ValueError, TypeError) as e:
        return jsonify({"status": "error", "message": f"Invalid float value: {str(e)}"}), 400


def handle_hotkey_rebind(ActionPayload):
    if ActionPayload is None:
        return jsonify({"status": "error", "message": "Missing payload"}), 400
    
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