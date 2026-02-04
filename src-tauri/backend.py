import os
import sys
import time
import json
import threading
from threading import Lock
import subprocess
import platform
import re
import shutil
import uuid
import hashlib
from datetime import datetime, timezone
import traceback
import webbrowser

from flask import Flask, request, jsonify
from flask_cors import CORS
import numpy as np
import mss
import pyautogui
import keyboard
from pynput import mouse
from PIL import Image as PILImage
import requests
from difflib import get_close_matches
from scipy.fft import fft
import librosa
import sounddevice as sd
import pyaudiowpatch as pyaudio

import ctypes
from ctypes import wintypes
import win32gui
import win32con
import win32api
import win32ts

import tkinter as tk
from tkinter import ttk, filedialog, messagebox

FlaskApplication = Flask(__name__)
CORS(FlaskApplication)

class AutomatedFishingSystem:
    def __init__(self):
        pyautogui.PAUSE = 0

        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except:
            try:
                ctypes.windll.user32.SetProcessDPIAware()
            except:
                pass

        SystemDisplayMetrics = ctypes.windll.user32

        try:
            kernel32 = ctypes.windll.kernel32
            
            PROCESS_SET_INFORMATION = 0x0200
            pid = os.getpid()
            handle = kernel32.OpenProcess(PROCESS_SET_INFORMATION, False, pid)
            
            if handle:
                result = kernel32.SetPriorityClass(handle, 0x00000100)
                kernel32.CloseHandle(handle)
                
                if not result:
                    error_code = ctypes.get_last_error()
                    print(f"Failed to set priority. Error: {error_code}")
            else:
                print("Failed to open process handle")
                
        except Exception as e:
            print(f"Could not set process priority: {e}")
            
        MonitorWidth = SystemDisplayMetrics.GetSystemMetrics(0)
        MonitorHeight = SystemDisplayMetrics.GetSystemMetrics(1)

        if getattr(sys, 'frozen', False):
            ApplicationPath = os.path.dirname(sys.executable)
        else:
            ApplicationPath = os.path.dirname(os.path.abspath(__file__))

        self.ConfigurationFilePath = os.path.join(ApplicationPath, "Auto Fish Settings.json")

        self.GlobalHotkeyBindings = {"start_stop": "f1", "exit": "f3"}

        self.WindowAlwaysOnTopEnabled = True
        self.DebugOverlayVisible = False

        self.ScanningRegionBounds = {
            "x1": int(MonitorWidth * 0.52461),
            "y1": int(MonitorHeight * 0.29167),
            "x2": int(MonitorWidth * 0.68477),
            "y2": int(MonitorHeight * 0.79097)
        }

        self.RegionSelectorCurrentlyActive = False
        self.ActiveRegionSelectorInstance = None

        self.WaterCastingTargetLocation = None
        self.ShopLeftButtonLocation = None
        self.ShopCenterButtonLocation = None
        self.ShopRightButtonLocation = None
        self.FruitStorageButtonLocation = None
        self.DevilFruitLocationPoint = None
        self.BaitSelectionButtonLocation = None
        self.CraftLeftButtonLocation = None
        self.CraftMiddleButtonLocation = None
        self.CraftButtonLocation = None
        self.CloseMenuButtonLocation = None
        self.AddRecipeButtonLocation = None
        self.TopRecipeSlotLocation = None

        self.FishingRodInventorySlot = "1"
        self.AlternateInventorySlot = "2"
        self.DevilFruitInventorySlots = ["3"]

        self.AutomaticBaitPurchaseEnabled = True
        self.AutomaticBaitCraftingEnabled = False
        self.AutomaticFruitStorageEnabled = False
        self.AutomaticTopBaitSelectionEnabled = False

        self.StoreToBackpackEnabled = False
        self.LogDevilFruitEnabled = False
        self.WebhookUrl = ""

        self.LogRecastTimeouts = True
        self.LogPeriodicStats = True
        self.LogGeneralUpdates = True
        self.PeriodicStatsIntervalMinutes = 5

        self.TotalRecastTimeouts = 0
        self.ConsecutiveRecastTimeouts = 0
        self.LastPeriodicStatsTimestamp = None
        self.FishCaughtAtLastPeriodicStats = 0

        self.OCRReader = None
        self.TextDetectionEnabled = True

        self.BaitPurchaseFrequencyCounter = 100
        self.BaitPurchaseIterationCounter = 0
        self.DevilFruitStorageFrequencyCounter = 50
        self.DevilFruitStorageIterationCounter = 0
        self.FishCountPerCraft = 50
        self.FishCountSinceLastCraft = 0
        self.BaitCraftIterationCounter = 0
        self.CraftsPerCycleCount = 40
        self.BaitCraftFrequencyCounter = 5

        self.BaitRecipes = []
        self.CurrentRecipeIndex = 0

        self.ClientStats = {} 
        self.GlobalStats = {
            "TotalFishCaught": 0,
            "TotalUptime": 0,
            "ActiveClients": 0
        }

        self.CurrentClientId = str(uuid.uuid4())
        self.SessionLock = Lock()
        self.AllActiveSessions = {}

        self.ProportionalGainCoefficient = 1.4
        self.DerivativeGainCoefficient = 0.6
        self.ControlSignalMaximumClamp = 1.0
        self.PDControllerApproachingStateDamping = 2.0
        self.PDControllerChasingStateDamping = 0.5
        self.BarGroupingGapToleranceMultiplier = 2.0

        self.MouseHoldDurationForCast = 0.1
        self.MaximumWaitTimeBeforeRecast = 25.0
        self.DelayAfterFishCaptured = 0.5
        self.InputStateResendFrequency = 0.5

        self.RobloxWindowFocusInitialDelay = 0.2
        self.RobloxWindowFocusFollowupDelay = 0.2

        self.PreCastDialogOpenDelay = 1.25
        self.PreCastMouseClickDelay = 0.5
        self.PreCastKeyboardInputDelay = 0.25
        self.PreCastAntiDetectionDelay = 0.05

        self.FruitStorageHotkeyActivationDelay = 0.2
        self.FruitStorageClickConfirmationDelay = 0.25
        self.FruitStorageShiftKeyPressDelay = 0.35
        self.FruitStorageBackspaceDeletionDelay = 0.2

        self.BaitSelectionConfirmationDelay = 0.5
        self.InventorySlotSwitchingDelay = 0.2

        self.BlackScreenDetectionRatioThreshold = 0.5
        self.AntiMacroDialogSpamDelay = 0.25
        self.MouseMovementAntiDetectionDelay = 0.05
        self.ImageProcessingLoopDelay = 0.1

        self.MoveDurationSeconds = 0
        self.CraftMenuOpenDelay = 0.85
        self.CraftClickDelay = 0.2
        self.CraftRecipeSelectDelay = 0.2
        self.CraftAddRecipeDelay = 0.2
        self.CraftTopRecipeDelay = 0.2
        self.CraftButtonClickDelay = 0.025
        self.CraftCloseMenuDelay = 0.2

        self.MacroCurrentlyExecuting = False
        self.CurrentlyRebindingHotkey = None
        self.MouseButtonCurrentlyPressed = False
        self.RobloxWindowAlreadyFocused = False

        self.PreviousControlLoopErrorValue = None
        self.PreviousTargetBarVerticalPosition = None
        self.LastImageScanTimestamp = time.time()
        self.LastControlStateChangeTimestamp = time.time()
        self.LastInputResendTimestamp = time.time()

        self.TotalFishSuccessfullyCaught = 0
        self.CumulativeRunningTimeSeconds = 0
        self.CurrentSessionBeginTimestamp = None
        self.MostRecentFishCaptureTimestamp = None

        self.MouseEventListenerInstance = None
        self.CurrentlySettingPointName = None

        self.CurrentMacroStatus = "Idle"
        self.CurrentClientId = "unknown"

        self.MegalodonSoundRecognitionEnabled = False
        self.SoundMatchSensitivity = 0.05
        self.MegalodonSoundPath = os.path.join(ApplicationPath, "Sounds", "Megalodon.wav")
        
        self.AutoDetectRDP = True
        self.AllowRDPExecution = True
        self.PauseOnRDPDisconnect = True
        self.ResumeOnRDPReconnect = False
        self.RDPDetected = False
        self.RDPSessionState = 'unknown'

        self.EnableDeviceSync = False
        self.SyncSettings = True
        self.SyncStats = True
        self.ShareFishCount = False
        self.SyncIntervalSeconds = 5
        self.DeviceName = ""
        self.LastSyncTimestamp = None

        self.ConnectedDevices = []
        self.IsSyncing = False

        self.LoadConfigurationFromDisk()
        self.RegisterAllHotkeyBindings()
    
    def DetectRDPSession(self):
        try:
            SessionId = win32ts.WTSGetActiveConsoleSessionId()
            ServerHandle = win32ts.WTS_CURRENT_SERVER_HANDLE
            SessionInfo = win32ts.WTSQuerySessionInformation(
                ServerHandle, 
                SessionId, 
                win32ts.WTSClientProtocolType
            )
            IsRdp = (SessionInfo == 2)
            ConnectionState = win32ts.WTSQuerySessionInformation(
                ServerHandle,
                SessionId,
                win32ts.WTSConnectState
            )
            RdpState = 'connected' if ConnectionState == 0 else 'disconnected'
            
            SessionName = win32ts.WTSQuerySessionInformation(
                ServerHandle,
                SessionId,
                win32ts.WTSSessionInfo
            )
            
            return IsRdp, RdpState, SessionId, SessionName
        except Exception as E:
            print(f"RDP detection error: {E}")
            return False, 'unknown', -1, 'unknown'

    def UpdateStatus(self, StatusMessage):
        self.CurrentMacroStatus = StatusMessage
    
    def LoadConfigurationFromDisk(self):
        if not os.path.exists(self.ConfigurationFilePath):
            print(f"No configuration file found at {self.ConfigurationFilePath}. Creating new one with defaults.")
            self.SaveConfigurationToDisk()
            return
        
        try:
            with open(self.ConfigurationFilePath, 'r', encoding='utf-8') as ConfigurationFileHandle:
                FileContent = ConfigurationFileHandle.read().strip()
            
            if not FileContent:
                print(f"Configuration file at {self.ConfigurationFilePath} is empty. Initializing with defaults.")
                self.SaveConfigurationToDisk()
                return
            
            try:
                ParsedConfigurationData = json.loads(FileContent)
            except json.JSONDecodeError as JsonError:
                print(f"Configuration file corrupted: {JsonError}")
                print(f"File location: {self.ConfigurationFilePath}")
                print("Using defaults. Old file will be backed up.")
                
                try:
                    BackupPath = self.ConfigurationFilePath + f".backup_{int(time.time())}"
                    os.rename(self.ConfigurationFilePath, BackupPath)
                    print(f"Backup created at: {BackupPath}")
                except Exception as backup_error:
                    print(f"Could not create backup: {backup_error}")
                
                self.SaveConfigurationToDisk()
                return
            
            if "Hotkeys" in ParsedConfigurationData:
                self.GlobalHotkeyBindings.update(ParsedConfigurationData["Hotkeys"])
            
            if "WindowSettings" in ParsedConfigurationData:
                WindowSettings = ParsedConfigurationData["WindowSettings"]
                self.WindowAlwaysOnTopEnabled = WindowSettings.get("AlwaysOnTop", self.WindowAlwaysOnTopEnabled)
                self.DebugOverlayVisible = WindowSettings.get("ShowDebugOverlay", self.DebugOverlayVisible)
            
            if "ScanArea" in ParsedConfigurationData:
                self.ScanningRegionBounds.update(ParsedConfigurationData["ScanArea"])

            if "LoggingOptions" in ParsedConfigurationData:
                LogOpts = ParsedConfigurationData["LoggingOptions"]
                self.LogRecastTimeouts = LogOpts.get("LogRecastTimeouts", self.LogRecastTimeouts)
                self.LogPeriodicStats = LogOpts.get("LogPeriodicStats", self.LogPeriodicStats)
                self.LogGeneralUpdates = LogOpts.get("LogGeneralUpdates", self.LogGeneralUpdates)
                self.PeriodicStatsIntervalMinutes = LogOpts.get("PeriodicStatsIntervalMinutes", self.PeriodicStatsIntervalMinutes)
            
            if "RDPSettings" in ParsedConfigurationData:
                RDPSettings = ParsedConfigurationData["RDPSettings"]
                self.AutoDetectRDP = RDPSettings.get("AutoDetectRDP", self.AutoDetectRDP)
                self.AllowRDPExecution = RDPSettings.get("AllowRDPExecution", self.AllowRDPExecution)
                self.PauseOnRDPDisconnect = RDPSettings.get("PauseOnRDPDisconnect", self.PauseOnRDPDisconnect)
                self.ResumeOnRDPReconnect = RDPSettings.get("ResumeOnRDPReconnect", self.ResumeOnRDPReconnect)

            if "DeviceSyncSettings" in ParsedConfigurationData:
                DeviceSyncSettings = ParsedConfigurationData["DeviceSyncSettings"]
                self.EnableDeviceSync = DeviceSyncSettings.get("EnableDeviceSync", self.EnableDeviceSync)
                self.SyncSettings = DeviceSyncSettings.get("SyncSettings", self.SyncSettings)
                self.SyncStats = DeviceSyncSettings.get("SyncStats", self.SyncStats)
                self.ShareFishCount = DeviceSyncSettings.get("ShareFishCount", self.ShareFishCount)
                self.SyncIntervalSeconds = DeviceSyncSettings.get("SyncIntervalSeconds", self.SyncIntervalSeconds)
                self.DeviceName = DeviceSyncSettings.get("DeviceName", self.DeviceName)
            
            if "ClickPoints" in ParsedConfigurationData:
                ClickPoints = ParsedConfigurationData["ClickPoints"]
                
                self.WaterCastingTargetLocation = ClickPoints.get("WaterPoint", self.WaterCastingTargetLocation)
                
                if "Shop" in ClickPoints:
                    ShopPoints = ClickPoints["Shop"]
                    self.ShopLeftButtonLocation = ShopPoints.get("LeftPoint", self.ShopLeftButtonLocation)
                    self.ShopCenterButtonLocation = ShopPoints.get("MiddlePoint", self.ShopCenterButtonLocation)
                    self.ShopRightButtonLocation = ShopPoints.get("RightPoint", self.ShopRightButtonLocation)
                
                self.BaitSelectionButtonLocation = ClickPoints.get("BaitPoint", self.BaitSelectionButtonLocation)
                
                if "DevilFruit" in ClickPoints:
                    DevilFruitPoints = ClickPoints["DevilFruit"]
                    self.FruitStorageButtonLocation = DevilFruitPoints.get("StoreFruitPoint", self.FruitStorageButtonLocation)
                    self.DevilFruitLocationPoint = DevilFruitPoints.get("DevilFruitLocationPoint", self.DevilFruitLocationPoint)
                
                if "Crafting" in ClickPoints:
                    CraftingPoints = ClickPoints["Crafting"]
                    self.CraftLeftButtonLocation = CraftingPoints.get("CraftLeftPoint", self.CraftLeftButtonLocation)
                    self.CraftMiddleButtonLocation = CraftingPoints.get("CraftMiddlePoint", self.CraftMiddleButtonLocation)
                    self.CraftButtonLocation = CraftingPoints.get("CraftButtonPoint", self.CraftButtonLocation)
                    self.CloseMenuButtonLocation = CraftingPoints.get("CloseMenuPoint", self.CloseMenuButtonLocation)
                    self.AddRecipeButtonLocation = CraftingPoints.get("AddRecipePoint", self.AddRecipeButtonLocation)
                    self.TopRecipeSlotLocation = CraftingPoints.get("TopRecipePoint", self.TopRecipeSlotLocation)
                    self.BaitRecipes = CraftingPoints.get("BaitRecipes", self.BaitRecipes)
                    self.CurrentRecipeIndex = CraftingPoints.get("CurrentRecipeIndex", self.CurrentRecipeIndex)
            
            if "InventoryHotkeys" in ParsedConfigurationData:
                InventoryHotkeys = ParsedConfigurationData["InventoryHotkeys"]
                self.FishingRodInventorySlot = InventoryHotkeys.get("RodHotkey", self.FishingRodInventorySlot)
                self.AlternateInventorySlot = InventoryHotkeys.get("AnythingElseHotkey", self.AlternateInventorySlot)
                self.DevilFruitInventorySlots = InventoryHotkeys.get("DevilFruitHotkeys", self.DevilFruitInventorySlots)
            
            if "AutomationFeatures" in ParsedConfigurationData:
                Automation = ParsedConfigurationData["AutomationFeatures"]
                self.AutomaticBaitPurchaseEnabled = Automation.get("AutoBuyCommonBait", self.AutomaticBaitPurchaseEnabled)
                self.AutomaticFruitStorageEnabled = Automation.get("AutoStoreDevilFruit", self.AutomaticFruitStorageEnabled)
                self.AutomaticTopBaitSelectionEnabled = Automation.get("AutoSelectTopBait", self.AutomaticTopBaitSelectionEnabled)
                self.AutomaticBaitCraftingEnabled = Automation.get("AutoCraftBait", self.AutomaticBaitCraftingEnabled)
            
            if "AutomationFrequencies" in ParsedConfigurationData:
                Frequencies = ParsedConfigurationData["AutomationFrequencies"]
                self.BaitPurchaseFrequencyCounter = Frequencies.get("LoopsPerPurchase", self.BaitPurchaseFrequencyCounter)
                self.DevilFruitStorageFrequencyCounter = Frequencies.get("LoopsPerStore", self.DevilFruitStorageFrequencyCounter)
                self.BaitCraftFrequencyCounter = Frequencies.get("LoopsPerCraft", getattr(self, 'BaitCraftFrequencyCounter', 5))
                self.CraftsPerCycleCount = Frequencies.get("CraftsPerCycle", getattr(self, 'CraftsPerCycleCount', 40))
                self.FishCountPerCraft = Frequencies.get("FishCountPerCraft", self.FishCountPerCraft)
            
            if "DevilFruitStorage" in ParsedConfigurationData:
                DfStorage = ParsedConfigurationData["DevilFruitStorage"]
                self.StoreToBackpackEnabled = DfStorage.get("StoreToBackpack", self.StoreToBackpackEnabled)
                self.LogDevilFruitEnabled = DfStorage.get("LogDevilFruit", self.LogDevilFruitEnabled)
                self.WebhookUrl = DfStorage.get("WebhookUrl", self.WebhookUrl)

            if "FishingModes" in ParsedConfigurationData:
                FishingModes = ParsedConfigurationData["FishingModes"]
                self.MegalodonSoundRecognitionEnabled = FishingModes.get("MegalodonSound", self.MegalodonSoundRecognitionEnabled)
                self.SoundMatchSensitivity = FishingModes.get("SoundSensitivity", self.SoundMatchSensitivity)
            
            if "FishingControl" in ParsedConfigurationData:
                FishingControl = ParsedConfigurationData["FishingControl"]
                
                if "PdController" in FishingControl:
                    PdController = FishingControl["PdController"]
                    self.ProportionalGainCoefficient = PdController.get("Kp", self.ProportionalGainCoefficient)
                    self.DerivativeGainCoefficient = PdController.get("Kd", self.DerivativeGainCoefficient)
                    self.ControlSignalMaximumClamp = PdController.get("PdClamp", self.ControlSignalMaximumClamp)
                    self.PDControllerApproachingStateDamping = PdController.get("PdApproachingDamping", self.PDControllerApproachingStateDamping)
                    self.PDControllerChasingStateDamping = PdController.get("PdChasingDamping", self.PDControllerChasingStateDamping)
                
                if "Timing" in FishingControl:
                    Timing = FishingControl["Timing"]
                    self.MouseHoldDurationForCast = Timing.get("CastHoldDuration", self.MouseHoldDurationForCast)
                    self.MaximumWaitTimeBeforeRecast = Timing.get("RecastTimeout", self.MaximumWaitTimeBeforeRecast)
                    self.DelayAfterFishCaptured = Timing.get("FishEndDelay", self.DelayAfterFishCaptured)
                    self.InputStateResendFrequency = Timing.get("StateResendInterval", self.InputStateResendFrequency)
                
                if "Detection" in FishingControl:
                    Detection = FishingControl["Detection"]
                    self.BarGroupingGapToleranceMultiplier = Detection.get("GapToleranceMultiplier", self.BarGroupingGapToleranceMultiplier)
                    self.BlackScreenDetectionRatioThreshold = Detection.get("BlackScreenThreshold", self.BlackScreenDetectionRatioThreshold)
                    self.ImageProcessingLoopDelay = Detection.get("ScanLoopDelay", self.ImageProcessingLoopDelay)
            
            if "TimingDelays" in ParsedConfigurationData:
                TimingDelays = ParsedConfigurationData["TimingDelays"]
                
                if "RobloxWindow" in TimingDelays:
                    RobloxWindow = TimingDelays["RobloxWindow"]
                    self.RobloxWindowFocusInitialDelay = RobloxWindow.get("RobloxFocusDelay", self.RobloxWindowFocusInitialDelay)
                    self.RobloxWindowFocusFollowupDelay = RobloxWindow.get("RobloxPostFocusDelay", self.RobloxWindowFocusFollowupDelay)
                
                if "PreCast" in TimingDelays:
                    PreCast = TimingDelays["PreCast"]
                    self.PreCastDialogOpenDelay = PreCast.get("SetPrecastEDelay", self.PreCastDialogOpenDelay)
                    self.PreCastMouseClickDelay = PreCast.get("PreCastClickDelay", self.PreCastMouseClickDelay)
                    self.PreCastKeyboardInputDelay = PreCast.get("PreCastTypeDelay", self.PreCastKeyboardInputDelay)
                    self.PreCastAntiDetectionDelay = PreCast.get("PreCastAntiDetectDelay", self.PreCastAntiDetectionDelay)
                
                if "Inventory" in TimingDelays:
                    Inventory = TimingDelays["Inventory"]
                    self.InventorySlotSwitchingDelay = Inventory.get("RodSelectDelay", self.InventorySlotSwitchingDelay)
                    self.BaitSelectionConfirmationDelay = Inventory.get("AutoSelectBaitDelay", self.BaitSelectionConfirmationDelay)
                
                if "DevilFruitStorage" in TimingDelays:
                    DfStorageDelays = TimingDelays["DevilFruitStorage"]
                    self.FruitStorageHotkeyActivationDelay = DfStorageDelays.get("StoreFruitHotkeyDelay", self.FruitStorageHotkeyActivationDelay)
                    self.FruitStorageClickConfirmationDelay = DfStorageDelays.get("StoreFruitClickDelay", self.FruitStorageClickConfirmationDelay)
                    self.FruitStorageShiftKeyPressDelay = DfStorageDelays.get("StoreFruitShiftDelay", self.FruitStorageShiftKeyPressDelay)
                    self.FruitStorageBackspaceDeletionDelay = DfStorageDelays.get("StoreFruitBackspaceDelay", self.FruitStorageBackspaceDeletionDelay)
                
                if "AntiDetection" in TimingDelays:
                    AntiDetection = TimingDelays["AntiDetection"]
                    self.MouseMovementAntiDetectionDelay = AntiDetection.get("CursorAntiDetectDelay", self.MouseMovementAntiDetectionDelay)
                    self.AntiMacroDialogSpamDelay = AntiDetection.get("AntiMacroSpamDelay", self.AntiMacroDialogSpamDelay)
                
                if "Crafting" in TimingDelays:
                    CraftingDelays = TimingDelays["Crafting"]
                    self.MoveDurationSeconds = CraftingDelays.get("MoveDuration", self.MoveDurationSeconds)
                    self.CraftMenuOpenDelay = CraftingDelays.get("CraftMenuOpenDelay", self.CraftMenuOpenDelay)
                    self.CraftClickDelay = CraftingDelays.get("CraftClickDelay", self.CraftClickDelay)
                    self.CraftRecipeSelectDelay = CraftingDelays.get("CraftRecipeSelectDelay", self.CraftRecipeSelectDelay)
                    self.CraftAddRecipeDelay = CraftingDelays.get("CraftAddRecipeDelay", self.CraftAddRecipeDelay)
                    self.CraftTopRecipeDelay = CraftingDelays.get("CraftTopRecipeDelay", self.CraftTopRecipeDelay)
                    self.CraftButtonClickDelay = CraftingDelays.get("CraftButtonClickDelay", self.CraftButtonClickDelay)
                    self.CraftCloseMenuDelay = CraftingDelays.get("CraftCloseMenuDelay", self.CraftCloseMenuDelay)
            
            print(f"Configuration loaded successfully from {self.ConfigurationFilePath}")
            
        except Exception as LoadError:
            print(f"Error loading configuration: {LoadError}")
            print(f"File location: {self.ConfigurationFilePath}")
            traceback.print_exc()
            print("Using default values.")
            
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
                            "AddRecipePoint": self.AddRecipeButtonLocation,
                            "TopRecipePoint": self.TopRecipeSlotLocation,
                            "BaitRecipes": self.BaitRecipes,
                            "CurrentRecipeIndex": self.CurrentRecipeIndex
                        }
                    },
                    "InventoryHotkeys": {
                        "RodHotkey": self.FishingRodInventorySlot,
                        "AnythingElseHotkey": self.AlternateInventorySlot,
                        "DevilFruitHotkeys": self.DevilFruitInventorySlots,
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
                    "LoggingOptions": {
                        "LogRecastTimeouts": self.LogRecastTimeouts,
                        "LogPeriodicStats": self.LogPeriodicStats,
                        "LogGeneralUpdates": self.LogGeneralUpdates,
                        "PeriodicStatsIntervalMinutes": self.PeriodicStatsIntervalMinutes
                    },
                    "FishingModes": {
                        "MegalodonSound": self.MegalodonSoundRecognitionEnabled,
                        "SoundSensitivity": self.SoundMatchSensitivity
                    },
                    "RDPSettings": {
                        "AutoDetectRDP": self.AutoDetectRDP,
                        "AllowRDPExecution": self.AllowRDPExecution,
                        "PauseOnRDPDisconnect": self.PauseOnRDPDisconnect,
                        "ResumeOnRDPReconnect": self.ResumeOnRDPReconnect
                    },
                    "DeviceSyncSettings": {
                        "EnableDeviceSync": self.EnableDeviceSync,
                        "SyncSettings": self.SyncSettings,
                        "SyncStats": self.SyncStats,
                        "ShareFishCount": self.ShareFishCount,
                        "SyncIntervalSeconds": self.SyncIntervalSeconds,
                        "DeviceName": self.DeviceName
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
                def LoadOCRInBackground():
                    try:
                        import easyocr
                        self.OCRReader = easyocr.Reader(['en'], gpu=False, verbose=False)
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
                
                self.UpdateStatus("Initializing OCR...")
                self.InitializeOCR()
                
                WaitStartTime = time.time()
                MaxWaitTime = 30.0
                
                while self.OCRReader is None and (time.time() - WaitStartTime) < MaxWaitTime:
                    if not self.MacroCurrentlyExecuting:
                        return None
                    time.sleep(0.5)
                
                if self.OCRReader is None:
                    self.TextDetectionEnabled = False
                    return None
            
            self.UpdateStatus("Scanning for Devil Fruit...")
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
                DebugImage = PILImage.frombytes('RGB', ScreenshotData.size, ScreenshotData.rgb)
            except Exception as SaveError:
                pass

            ImageRGB = Image[:, :, [2, 1, 0]]
            
            Results = self.OCRReader.readtext(ImageRGB, detail=1, paragraph=False)
            
            FullText = ""
            for Index, (BBox, Text, Confidence) in enumerate(Results):
                if Confidence > 0.2:
                    FullText += Text + " "
            
            FullText = FullText.strip()
            FullTextLower = FullText.lower()
            
            HasNewKeyword = any(Keyword in FullTextLower for Keyword in [
                'new', 'nev', 'ncv', 'ncw', 'naw', 'ner'
            ])
            
            HasItemKeyword = 'item' in FullTextLower or 'ltem' in FullTextLower

            if FullText and HasNewKeyword and HasItemKeyword:
                BracketMatch = re.search(r'<([^>?]+)', FullText, re.IGNORECASE)
                if BracketMatch:
                    ItemName = BracketMatch.group(1).strip()
                    ItemName = ItemName.rstrip('?>')
                    
                    ClosestMatch = self.GetClosestFruit(ItemName, Cutoff=0.5)
                    if ClosestMatch:
                        return ClosestMatch
                    else:
                        return ItemName
                
                AfterItemMatch = re.search(r'(?:item|ltem)\s+(.+)', FullText, re.IGNORECASE)
                if AfterItemMatch:
                    ItemName = AfterItemMatch.group(1).strip()
                    ItemName = ItemName.replace('<', '').replace('>', '').replace('?', '').strip()
                    if ItemName:
                        ClosestMatch = self.GetClosestFruit(ItemName, Cutoff=0.5)
                        if ClosestMatch:
                            return ClosestMatch
                        else:
                            return ItemName
                
                return FullText
                        
            return None
            
        except Exception as OCRCheckError:
            print(f"OCR Check Error: {OCRCheckError}")
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
        
        with self.SessionLock:
            self.AllActiveSessions[self.CurrentClientId] = {
                'is_running': self.MacroCurrentlyExecuting,
                'last_updated': time.time(),
                'session_id': getattr(self, 'RDPSessionId', -1),
                'rdp_detected': getattr(self, 'RDPDetected', False),
                'rdp_state': getattr(self, 'RDPSessionState', 'unknown')
            }
        
        if self.MacroCurrentlyExecuting:
            self.UpdateStatus("Starting macro...")
            self.CurrentSessionBeginTimestamp = time.time()
            self.RobloxWindowAlreadyFocused = False
            self.ConsecutiveRecastTimeouts = 0
            self.LastPeriodicStatsTimestamp = time.time()
            self.FishCaughtAtLastPeriodicStats = self.TotalFishSuccessfullyCaught
            if self.WebhookUrl and self.LogGeneralUpdates:
                self.SendWebhookNotification("Macro started.")
            threading.Thread(target=self.ExecutePrimaryMacroLoop, daemon=True).start()
        else:
            self.UpdateStatus("Stopping macro...")
            if self.CurrentSessionBeginTimestamp:
                self.CumulativeRunningTimeSeconds += time.time() - self.CurrentSessionBeginTimestamp
                self.CurrentSessionBeginTimestamp = None
            if self.MouseButtonCurrentlyPressed:
                pyautogui.mouseUp()
                self.MouseButtonCurrentlyPressed = False
            if self.WebhookUrl and self.LogGeneralUpdates:
                self.SendWebhookNotification(f"Macro stopped. Fish this session: {self.TotalFishSuccessfullyCaught}")
            self.UpdateStatus("Idle")
    
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

    def HandleRecastTimeout(self):
        self.UpdateStatus("Recast timeout detected")
        self.TotalRecastTimeouts += 1
        self.ConsecutiveRecastTimeouts += 1
        if not self.WebhookUrl or not self.LogRecastTimeouts:
            return
        if self.ConsecutiveRecastTimeouts == 3:
            self.SendWebhookNotification(f"3 consecutive recast timeouts ({self.MaximumWaitTimeBeforeRecast}s). Total: {self.TotalRecastTimeouts}")
        elif self.ConsecutiveRecastTimeouts == 10:
            self.SendWebhookNotification(f"10 consecutive recast timeouts — macro may be stuck. Total: {self.TotalRecastTimeouts}")
        elif self.ConsecutiveRecastTimeouts > 10 and self.ConsecutiveRecastTimeouts % 10 == 0:
            self.SendWebhookNotification(f"{self.ConsecutiveRecastTimeouts} consecutive timeouts. Total: {self.TotalRecastTimeouts}")

    def CheckPeriodicStats(self):
        if not self.WebhookUrl or not self.LogPeriodicStats or self.LastPeriodicStatsTimestamp is None:
            return
        IntervalSeconds = self.PeriodicStatsIntervalMinutes * 60
        if (time.time() - self.LastPeriodicStatsTimestamp) < IntervalSeconds:
            return
        FishThisInterval = self.TotalFishSuccessfullyCaught - self.FishCaughtAtLastPeriodicStats
        FishPerMin = FishThisInterval / self.PeriodicStatsIntervalMinutes if self.PeriodicStatsIntervalMinutes > 0 else 0
        AccumulatedTime = self.CumulativeRunningTimeSeconds
        if self.CurrentSessionBeginTimestamp:
            AccumulatedTime += time.time() - self.CurrentSessionBeginTimestamp
        H = int(AccumulatedTime // 3600)
        M = int((AccumulatedTime % 3600) // 60)
        S = int(AccumulatedTime % 60)
        OverallFPH = (self.TotalFishSuccessfullyCaught / AccumulatedTime) * 3600 if AccumulatedTime > 0 else 0
        self.SendWebhookNotification(
            f"Stats (last {self.PeriodicStatsIntervalMinutes}m)\n"
            f"Caught: {FishThisInterval} ({FishPerMin:.1f}/min)\n"
            f"Total: {self.TotalFishSuccessfullyCaught} | Uptime: {H}:{M:02d}:{S:02d}\n"
            f"Rate: {OverallFPH:.1f}/hr | Timeouts: {self.TotalRecastTimeouts}"
        )
        self.LastPeriodicStatsTimestamp = time.time()
        self.FishCaughtAtLastPeriodicStats = self.TotalFishSuccessfullyCaught

    def SendWebhookNotification(self, Message, Color=None, Title=None):
        if not self.WebhookUrl:
            return
        
        try:
            WebhookColorInfo = 0x00d4ff
            WebhookColorSuccess = 0x10b981
            WebhookColorWarning = 0xf59e0b
            WebhookColorError = 0xef4444
            WebhookColorCraft = 0x8b5cf6
            WebhookColorFruit = 0xbf40bf
            WebhookColorStats = 0x3b82f6
            WebhookColorMega = 0xfbbf24
            
            if Color is None or Title is None:
                MessageLower = Message.lower()
                
                if "megalodon" in MessageLower:
                    Color = WebhookColorMega
                    Title = "🎣 Megalodon Detected"
                elif "crash" in MessageLower or "error" in MessageLower or "failed" in MessageLower or "blocked" in MessageLower or "10 consecutive" in MessageLower:
                    Color = WebhookColorError
                    Title = "🎣 Error" if "crash" in MessageLower or "error" in MessageLower else ("Storage Failed" if "failed" in MessageLower else ("RDP Blocked" if "blocked" in MessageLower else "Warning"))
                elif "started" in MessageLower or "reconnected" in MessageLower:
                    Color = WebhookColorSuccess
                    Title = "🎣 Success" if "started" in MessageLower else "RDP Status"
                elif "devil fruit" in MessageLower and "stored successfully" in MessageLower:
                    Color = WebhookColorFruit
                    Title = "🎣 Devil Fruit Found"
                elif "craft" in MessageLower:
                    Color = WebhookColorCraft
                    Title = "🎣 Crafting Update"
                elif "stats" in MessageLower or "caught:" in MessageLower or "total:" in MessageLower:
                    Color = WebhookColorStats
                    Title = "🎣 Fishing Statistics"
                elif "stopped" in MessageLower or "timeout" in MessageLower or "disconnected" in MessageLower or "paused" in MessageLower:
                    Color = WebhookColorWarning
                    Title = "🎣 Warning" if "timeout" in MessageLower else ("RDP Status" if "rdp" in MessageLower else "Notice")
                else:
                    Color = WebhookColorInfo
                    Title = "🎣 GPO Fishing Macro"
            
            EmbedData = {
                "title": Title,
                "description": f"**{Message}**",
                "color": Color,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "footer": {
                    "text": "Macro Notification System",
                    "icon_url": "https://cdn.discordapp.com/avatars/1351127835175288893/208dc6bfcc148a0c3ad2482b12520f43.webp"
                },
                "fields": [
                    {
                        "name": "Time",
                        "value": f"<t:{int(time.time())}:R>",
                        "inline": True
                    }
                ],
            }
            
            PayloadData = {
                "username": "K's GPO Macro Bot",
                "embeds": [EmbedData]
            }
            
            requests.post(self.WebhookUrl, json=PayloadData, timeout=5)
        except Exception as ErrorDetails:
            print(f"Webhook error: {ErrorDetails}")

    def InitiatePointSelectionMode(self, AttributeNameToSet):
        if self.MouseEventListenerInstance:
            self.MouseEventListenerInstance.stop()
        
        self.CurrentlySettingPointName = AttributeNameToSet
        PointSelectionStartTime = time.time()
        
        def ProcessMouseClickEvent(ClickPositionX, ClickPositionY, ButtonPressed, IsPressed):
            if IsPressed and self.CurrentlySettingPointName == AttributeNameToSet:
                if time.time() - PointSelectionStartTime < 0.25:
                    return True
                
                setattr(self, AttributeNameToSet, {"x": ClickPositionX, "y": ClickPositionY})
                self.SaveConfigurationToDisk()
                self.CurrentlySettingPointName = None
                return False
        
        self.MouseEventListenerInstance = mouse.Listener(on_click=ProcessMouseClickEvent)
        self.MouseEventListenerInstance.start()
    
    def GetClosestFruit(self, Name, Cutoff=0.6):
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
    
    def ExecutePrimaryMacroLoop(self):
        while self.MacroCurrentlyExecuting:
            try:
                if self.AutoDetectRDP:
                    self.RDPDetected, self.RDPSessionState, self.RDPSessionId, self.RDPSessionName = self.DetectRDPSession()
                    
                    with self.SessionLock:
                        self.AllActiveSessions[self.CurrentClientId]['rdp_detected'] = self.RDPDetected
                        self.AllActiveSessions[self.CurrentClientId]['rdp_state'] = self.RDPSessionState
                        self.AllActiveSessions[self.CurrentClientId]['session_id'] = self.RDPSessionId

                self.UpdateStatus("Starting new fishing cycle")
                self.PreviousControlLoopErrorValue = None
                self.PreviousTargetBarVerticalPosition = None
                self.LastImageScanTimestamp = time.time()
                
                if self.MouseButtonCurrentlyPressed:
                    self.UpdateStatus("Releasing mouse from previous cycle")
                    pyautogui.mouseUp()
                    self.MouseButtonCurrentlyPressed = False
                
                if not self.MacroCurrentlyExecuting:
                    break
                
                self.UpdateStatus("Beginning pre-cast sequence")
                if not self.ExecutePreCastSequence():
                    self.UpdateStatus("Pre-cast sequence failed - restarting cycle")
                    continue
                
                self.UpdateStatus("Pre-cast sequence complete")
                
                if not self.MacroCurrentlyExecuting:
                    break
                
                self.UpdateStatus("Waiting for bobber to appear")
                if not self.WaitForFishingBobberReady():
                    self.UpdateStatus("Bobber timeout - recasting")
                    self.HandleRecastTimeout()
                    continue

                self.ConsecutiveRecastTimeouts = 0
                self.UpdateStatus("Bobber ready - starting minigame")
                
                self.UpdateStatus("Entering minigame control loop")
                while self.MacroCurrentlyExecuting:
                    if not self.PerformActiveFishingControl():
                        self.UpdateStatus("Minigame control loop ended")
                        break
                
                if self.MacroCurrentlyExecuting:
                    self.UpdateStatus("Fish caught successfully!")
                    self.TotalFishSuccessfullyCaught += 1
                    self.FishCountSinceLastCraft += 1
                    self.MostRecentFishCaptureTimestamp = time.time()
                    self.UpdateStatus(f"Total fish: {self.TotalFishSuccessfullyCaught}")
                    self.CheckPeriodicStats()
                    
                    self.UpdateStatus(f"Waiting {self.DelayAfterFishCaptured}s before next cast")
                    RemainingDelayTime = self.DelayAfterFishCaptured
                    while RemainingDelayTime > 0 and self.MacroCurrentlyExecuting:
                        DelayIncrement = min(0.1, RemainingDelayTime)
                        time.sleep(DelayIncrement)
                        RemainingDelayTime -= DelayIncrement
            
            except Exception as MainLoopError:
                self.UpdateStatus(f"Error: {str(MainLoopError)[:30]}")
                print(f"Error in Main: {MainLoopError}")
                if self.WebhookUrl and self.LogGeneralUpdates:
                    self.SendWebhookNotification(f"Macro crashed: {MainLoopError}")
                break
        
        self.UpdateStatus("Idle")
    
    def ExecutePreCastSequence(self):
        if not self.RobloxWindowAlreadyFocused:
            self.UpdateStatus("Focusing Roblox window")
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
                self.UpdateStatus("Window focused")
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
                self.UpdateStatus("Starting crafting cycle")
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
                
                self.UpdateStatus("Opening craft menu")
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
                    self.UpdateStatus(f"Crafting recipe {RecipeIndex+1}/{len(self.BaitRecipes)}")
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
                            self.UpdateStatus(f"Crafting iteration {CraftIteration+1}/{RecipeCraftsPerCycle}")
                            if not self.MacroCurrentlyExecuting: return False
                            
                            ctypes.windll.user32.SetCursorPos(self.CraftButtonLocation['x'], self.CraftButtonLocation['y'])
                            time.sleep(self.PreCastAntiDetectionDelay)
                            ctypes.windll.user32.mouse_event(0x0001, 0, 1, 0, 0)
                            time.sleep(self.PreCastAntiDetectionDelay)
                            pyautogui.click()
                            time.sleep(0.025)
                
                self.UpdateStatus("Closing craft menu")
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
                self.UpdateStatus("Crafting complete")

                if self.WebhookUrl and self.LogGeneralUpdates:
                    self.SendWebhookNotification("Crafting cycle complete.")
        
        if self.AutomaticBaitPurchaseEnabled and self.ShopLeftButtonLocation and self.ShopCenterButtonLocation and self.ShopRightButtonLocation:
            if self.BaitPurchaseIterationCounter == 0 or self.BaitPurchaseIterationCounter >= self.BaitPurchaseFrequencyCounter:
                self.UpdateStatus("Opening Shop")
                keyboard.press_and_release('e')
                time.sleep(self.PreCastDialogOpenDelay)
                if not self.MacroCurrentlyExecuting:
                    return False
                
                self.UpdateStatus("Clicking shop left button")
                ctypes.windll.user32.SetCursorPos(self.ShopLeftButtonLocation['x'], self.ShopLeftButtonLocation['y'])
                time.sleep(self.PreCastAntiDetectionDelay)
                ctypes.windll.user32.mouse_event(0x0001, 0, 1, 0, 0)
                time.sleep(self.PreCastAntiDetectionDelay)
                pyautogui.click()
                time.sleep(self.PreCastMouseClickDelay)
                if not self.MacroCurrentlyExecuting:
                    return False
                
                self.UpdateStatus("Clicking shop center button")
                ctypes.windll.user32.SetCursorPos(self.ShopCenterButtonLocation['x'], self.ShopCenterButtonLocation['y'])
                time.sleep(self.PreCastAntiDetectionDelay)
                ctypes.windll.user32.mouse_event(0x0001, 0, 1, 0, 0)
                time.sleep(self.PreCastAntiDetectionDelay)
                pyautogui.click()
                time.sleep(self.PreCastMouseClickDelay)
                if not self.MacroCurrentlyExecuting:
                    return False
                
                self.UpdateStatus(f"Entering quantity: {self.BaitPurchaseFrequencyCounter}")
                keyboard.write(str(self.BaitPurchaseFrequencyCounter))
                time.sleep(self.PreCastKeyboardInputDelay)
                if not self.MacroCurrentlyExecuting:
                    return False
                
                self.UpdateStatus("Confirming left button")
                ctypes.windll.user32.SetCursorPos(self.ShopLeftButtonLocation['x'], self.ShopLeftButtonLocation['y'])
                time.sleep(self.PreCastAntiDetectionDelay)
                ctypes.windll.user32.mouse_event(0x0001, 0, 1, 0, 0)
                time.sleep(self.PreCastAntiDetectionDelay)
                pyautogui.click()
                time.sleep(self.PreCastMouseClickDelay)
                if not self.MacroCurrentlyExecuting:
                    return False
                
                self.UpdateStatus("Clicking shop right button")
                ctypes.windll.user32.SetCursorPos(self.ShopRightButtonLocation['x'], self.ShopRightButtonLocation['y'])
                time.sleep(self.PreCastAntiDetectionDelay)
                ctypes.windll.user32.mouse_event(0x0001, 0, 1, 0, 0)
                time.sleep(self.PreCastAntiDetectionDelay)
                pyautogui.click()
                time.sleep(self.PreCastMouseClickDelay)
                if not self.MacroCurrentlyExecuting:
                    return False
                
                self.UpdateStatus("Final shop center click")
                ctypes.windll.user32.SetCursorPos(self.ShopCenterButtonLocation['x'], self.ShopCenterButtonLocation['y'])
                time.sleep(self.PreCastAntiDetectionDelay)
                ctypes.windll.user32.mouse_event(0x0001, 0, 1, 0, 0)
                time.sleep(self.PreCastAntiDetectionDelay)
                pyautogui.click()
                time.sleep(self.PreCastMouseClickDelay)
                
                self.UpdateStatus("Bait purchased successfully")
                self.BaitPurchaseIterationCounter = 1
            else:
                self.UpdateStatus(f"Skipping bait purchase ({self.BaitPurchaseIterationCounter}/{self.BaitPurchaseFrequencyCounter})")
                self.BaitPurchaseIterationCounter += 1
        elif self.AutomaticBaitPurchaseEnabled:
            if not self.ShopLeftButtonLocation:
                self.UpdateStatus("Bait purchase skipped - left button not set")
            elif not self.ShopCenterButtonLocation:
                self.UpdateStatus("Bait purchase skipped - center button not set")
            elif not self.ShopRightButtonLocation:
                self.UpdateStatus("Bait purchase skipped - right button not set")

        if not self.MacroCurrentlyExecuting:
            return False
        
        if self.AutomaticFruitStorageEnabled:
            if self.DevilFruitStorageIterationCounter == 0 or self.DevilFruitStorageIterationCounter >= self.DevilFruitStorageFrequencyCounter:
                self.UpdateStatus("Storing Devil Fruit")
                if self.StoreToBackpackEnabled and self.DevilFruitLocationPoint:
                    self.UpdateStatus("Opening inventory")
                    keyboard.press_and_release('`')
                    time.sleep(self.FruitStorageHotkeyActivationDelay)
                    if not self.MacroCurrentlyExecuting: return False
                    
                    self.UpdateStatus("Clicking fruit location")
                    ctypes.windll.user32.SetCursorPos(self.DevilFruitLocationPoint['x'], self.DevilFruitLocationPoint['y'])
                    time.sleep(self.PreCastAntiDetectionDelay)
                    ctypes.windll.user32.mouse_event(0x0001, 0, 1, 0, 0)
                    time.sleep(self.PreCastAntiDetectionDelay)
                    pyautogui.click()
                    time.sleep(self.FruitStorageClickConfirmationDelay)
                    if not self.MacroCurrentlyExecuting: return False
                    
                    if self.FruitStorageButtonLocation:
                        self.UpdateStatus("Checking fruit status")
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
    
                        ctypes.windll.user32.SetCursorPos(self.DevilFruitLocationPoint['x'], self.DevilFruitLocationPoint['y'])
                        time.sleep(0.1)
                        if not self.MacroCurrentlyExecuting: return False

                        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
                        time.sleep(0.1)
                        if not self.MacroCurrentlyExecuting:
                            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
                            return False

                        start_y = self.DevilFruitLocationPoint['y']
                        target_y = start_y - 150
                        steps = 100
                        duration = 2.0

                        for i in range(steps + 1):
                            progress = i / steps
                            current_y = int(start_y + (progress * -150))
                            win32api.SetCursorPos(self.DevilFruitLocationPoint['x'], current_y)
                            time.sleep(duration / steps)
                            
                            if not self.MacroCurrentlyExecuting:
                                win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
                                return False

                        time.sleep(0.1)

                        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
                        time.sleep(0.15)
                        
                        keyboard.press_and_release('`')
                        time.sleep(self.FruitStorageHotkeyActivationDelay)
                                
                elif self.FruitStorageButtonLocation:
                    for Slot in self.DevilFruitInventorySlots:
                        keyboard.press_and_release(self.AlternateInventorySlot)
                        time.sleep(self.InventorySlotSwitchingDelay)

                        keyboard.press_and_release(self.FishingRodInventorySlot)
                        time.sleep(self.InventorySlotSwitchingDelay)

                        keyboard.press_and_release(self.FishingRodInventorySlot)
                        time.sleep(self.InventorySlotSwitchingDelay)

                        keyboard.press_and_release(Slot)
                        time.sleep(self.FruitStorageHotkeyActivationDelay)
                        if not self.MacroCurrentlyExecuting: return False

                        self.UpdateStatus("Checking fruit status")
                        InitGreenDetected = False
                        if self.DetectGreenishColor(self.FruitStorageButtonLocation):
                            InitGreenDetected = True
                                
                        ctypes.windll.user32.SetCursorPos(self.FruitStorageButtonLocation['x'], self.FruitStorageButtonLocation['y'])
                        time.sleep(self.PreCastAntiDetectionDelay)
                        ctypes.windll.user32.mouse_event(0x0001, 0, 1, 0, 0)
                        time.sleep(self.PreCastAntiDetectionDelay)
                        pyautogui.click()
                        time.sleep(self.FruitStorageClickConfirmationDelay)
                        if not self.MacroCurrentlyExecuting: return False
                        
                        if InitGreenDetected:
                            time.sleep(self.FruitStorageClickConfirmationDelay + 0.5)
                            print("now")
                            if self.WebhookUrl and not self.DetectGreenishColor(self.FruitStorageButtonLocation):
                                DetectedFruitName = None
                                if self.TextDetectionEnabled:
                                    DetectedFruitName = self.DetectNewItemNotification()

                                print(DetectedFruitName)
                                if DetectedFruitName:
                                    ClosestMatch = self.GetClosestFruit(DetectedFruitName)
                                    self.UpdateStatus("Fruit stored successfully")
                                    self.SendWebhookNotification(f"Devil Fruit {ClosestMatch or ""} stored successfully!")
                                else:
                                    self.UpdateStatus("Fruit stored successfully")
                                    self.SendWebhookNotification("Devil Fruit stored successfully!")
                            else:
                                if self.WebhookUrl:
                                    self.UpdateStatus("Fruit storage failed")
                                    self.SendWebhookNotification("Devil Fruit could not be stored.")

                                if self.AutomaticBaitPurchaseEnabled:
                                    keyboard.press_and_release('shift')
                                    time.sleep(self.FruitStorageShiftKeyPressDelay)
                                    if not self.MacroCurrentlyExecuting: return False
                                
                                keyboard.press_and_release('backspace')
                                time.sleep(self.FruitStorageBackspaceDeletionDelay)
                                if not self.MacroCurrentlyExecuting: return False

                                if self.AutomaticBaitPurchaseEnabled:
                                    keyboard.press_and_release('shift')
                
                self.DevilFruitStorageIterationCounter = 1
            else:
                self.DevilFruitStorageIterationCounter += 1

        self.UpdateStatus("Pre-cast complete")
        return True
    
    def WaitForFishingBobberReady(self):
        if not self.WaterCastingTargetLocation:
            return False
        
        self.UpdateStatus("Switching to alternate slot")
        keyboard.press_and_release(self.AlternateInventorySlot)
        time.sleep(self.InventorySlotSwitchingDelay)
        
        if not self.MacroCurrentlyExecuting:
            return False
        
        self.UpdateStatus("Switching to fishing rod")
        keyboard.press_and_release(self.FishingRodInventorySlot)
        time.sleep(self.InventorySlotSwitchingDelay)
        
        if not self.MacroCurrentlyExecuting:
            return False
        
        if self.AutomaticTopBaitSelectionEnabled and self.BaitSelectionButtonLocation:
            self.UpdateStatus("Selecting top bait")
            ctypes.windll.user32.SetCursorPos(self.BaitSelectionButtonLocation['x'], self.BaitSelectionButtonLocation['y'])
            time.sleep(self.PreCastAntiDetectionDelay)
            ctypes.windll.user32.mouse_event(0x0001, 0, 1, 0, 0)
            time.sleep(self.PreCastAntiDetectionDelay)
            pyautogui.click()
            time.sleep(self.BaitSelectionConfirmationDelay)
        
        if not self.MacroCurrentlyExecuting:
            return False
        
        self.UpdateStatus("Casting fishing line")
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
        
        self.UpdateStatus("Waiting for bobber...")
        CastingStartTime = time.time()
        BobberBlueColor = np.array([85, 170, 255])
        BobberWhiteColor = np.array([255, 255, 255])
        BobberDarkGrayColor = np.array([25, 25, 25])
        BobberGreenColor = np.array([127, 255, 170])
        GreenColorTolerance = 15

        while self.MacroCurrentlyExecuting:
            ElapsedWaitTime = time.time() - CastingStartTime
            
            if ElapsedWaitTime >= self.MaximumWaitTimeBeforeRecast:
                self.UpdateStatus(f"Bobber wait timeout after {ElapsedWaitTime:.1f}s")
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
                self.UpdateStatus("Black screen during bobber wait - checking anti-macro...")
                if not self.HandleAntiMacroDetection():
                    self.UpdateStatus("Anti-macro clear failed during bobber wait")
                    return False
                self.UpdateStatus("Anti-macro cleared, resuming bobber wait")
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
            GreenPixelMask = ((np.abs(ScreenImageArray[:, :, 2].astype(int) - BobberGreenColor[0]) <= GreenColorTolerance) & 
                        (np.abs(ScreenImageArray[:, :, 1].astype(int) - BobberGreenColor[1]) <= GreenColorTolerance) & 
                        (np.abs(ScreenImageArray[:, :, 0].astype(int) - BobberGreenColor[2]) <= GreenColorTolerance))
            
            BlueColorDetected = np.any(BluePixelMask)
            WhiteColorDetected = np.any(WhitePixelMask)
            DarkGrayColorDetected = np.any(DarkGrayPixelMask)
            GreenColorDetected = np.any(GreenPixelMask)
            
            if ElapsedWaitTime % 2 < 0.5:
                DetectedColors = []
                if BlueColorDetected: DetectedColors.append("Blue")
                if WhiteColorDetected: DetectedColors.append("White")
                if DarkGrayColorDetected: DetectedColors.append("DarkGray")
                if GreenColorDetected: DetectedColors.append("Green")
                if DetectedColors:
                    self.UpdateStatus(f"Waiting for bobber ({ElapsedWaitTime:.1f}s) - detected: {', '.join(DetectedColors)}")
                else:
                    self.UpdateStatus(f"Waiting for bobber ({ElapsedWaitTime:.1f}s) - no colors detected")
            
            if BlueColorDetected and WhiteColorDetected and DarkGrayColorDetected:
                self.UpdateStatus("Bobber detected! All colors present")

                if not self.ListenForMegalodonSound():
                    self.UpdateStatus("Megalodon sound check failed - recasting")
                    return False
                
                self.UpdateStatus("Megalodon sound check passed - starting minigame")
                return True
            
            time.sleep(self.ImageProcessingLoopDelay)

        self.UpdateStatus("Bobber wait interrupted - macro stopped")
        return False
    
    def ListenForMegalodonSound(self, TimeoutDuration=5.0):
        if not self.MegalodonSoundRecognitionEnabled:
            return True
        
        try:
            self.UpdateStatus("Listening for Megalodon...")
            
            AudioInterface = pyaudio.PyAudio()
            
            try:
                WasapiInformation = AudioInterface.get_host_api_info_by_type(pyaudio.paWASAPI)
                DefaultSpeakersDevice = AudioInterface.get_device_info_by_index(WasapiInformation["defaultOutputDevice"])
                
                if not DefaultSpeakersDevice["isLoopbackDevice"]:
                    for LoopbackDevice in AudioInterface.get_loopback_device_info_generator():
                        if DefaultSpeakersDevice["name"] in LoopbackDevice["name"]:
                            DefaultSpeakersDevice = LoopbackDevice
                            break
                
                
                AudioSampleRate = int(DefaultSpeakersDevice['defaultSampleRate'])
                
                RecordingDuration = 1.5
                
                AudioStream = AudioInterface.open(
                    format=pyaudio.paFloat32,
                    channels=1,
                    rate=AudioSampleRate,
                    input=True,
                    frames_per_buffer=1024,
                    input_device_index=DefaultSpeakersDevice["index"]
                )
                
                AudioFramesList = []
                for _ in range(int(AudioSampleRate * RecordingDuration / 1024)):
                    if not self.MacroCurrentlyExecuting:
                        AudioStream.stop_stream()
                        AudioStream.close()
                        AudioInterface.terminate()
                        return False
                    AudioFrameData = AudioStream.read(1024)
                    AudioFramesList.append(AudioFrameData)
                
                AudioStream.stop_stream()
                AudioStream.close()
                AudioInterface.terminate()
                
                RecordedAudioData = np.frombuffer(b''.join(AudioFramesList), dtype=np.float32)
                
            except Exception as AudioCaptureError:
                print(f"PyAudioWPatch error: {AudioCaptureError}")
                traceback.print_exc()
                AudioInterface.terminate()
                return True
            
            MaximumAudioValue = np.max(np.abs(RecordedAudioData))
            if MaximumAudioValue < 0.01:
                print(f"  Too quiet (level: {MaximumAudioValue:.4f})")
                return False
            
            RecordedAudioData = RecordedAudioData / MaximumAudioValue
            
            ModelCoefficients = [1.0902, 0.7471, 0.3720, -1.1829, -1.0433, -0.6251, -0.4898]
            ModelIntercept = -3.2025
            ScalerMeanValues = [0.1308, 0.1496, 0.0916, 0.0797, 0.1209, 0.1816, 0.2457]
            ScalerScaleValues = [0.0775, 0.0748, 0.0200, 0.0317, 0.0344, 0.0438, 0.0960]
            FrequencyBands = [(20, 60), (60, 120), (120, 250), (250, 500), (500, 1000), (1000, 2000), (2000, 4000)]
            
            WindowDurationSeconds = 0.5
            HopDurationSeconds = 0.1
            WindowSampleCount = int(WindowDurationSeconds * AudioSampleRate)
            HopSampleCount = int(HopDurationSeconds * AudioSampleRate)
            
            MaximumDetectionProbability = 0
            BestFeatureVector = None
            
            for WindowStartIndex in range(0, max(1, len(RecordedAudioData) - WindowSampleCount), HopSampleCount):
                if not self.MacroCurrentlyExecuting:
                    return False
                    
                AudioChunk = RecordedAudioData[WindowStartIndex:WindowStartIndex + WindowSampleCount]
                if len(AudioChunk) < WindowSampleCount:
                    continue
                
                FftMagnitudeData = np.abs(fft(AudioChunk))[:len(AudioChunk)//2]
                FrequencyArray = np.fft.fftfreq(len(AudioChunk), 1/AudioSampleRate)[:len(AudioChunk)//2]
                
                ExtractedFeatures = []
                for LowFrequency, HighFrequency in FrequencyBands:
                    FrequencyMask = (FrequencyArray >= LowFrequency) & (FrequencyArray < HighFrequency)
                    BandEnergy = np.sum(FftMagnitudeData[FrequencyMask]) if np.any(FrequencyMask) else 0
                    ExtractedFeatures.append(BandEnergy)
                
                TotalEnergy = sum(ExtractedFeatures) + 1e-10
                ExtractedFeatures = [FeatureValue/TotalEnergy for FeatureValue in ExtractedFeatures]
                
                ScaledFeatures = [(FeatureValue - MeanValue) / ScaleValue for FeatureValue, MeanValue, ScaleValue in zip(ExtractedFeatures, ScalerMeanValues, ScalerScaleValues)]
                
                LogitValue = ModelIntercept + sum(CoefficientValue * FeatureValue for CoefficientValue, FeatureValue in zip(ModelCoefficients, ScaledFeatures))
                DetectionProbability = 1 / (1 + np.exp(-LogitValue))
                
                if DetectionProbability > MaximumDetectionProbability:
                    MaximumDetectionProbability = DetectionProbability
                    BestFeatureVector = ExtractedFeatures
            
            if BestFeatureVector is None:
                return False
            
            DetectionThreshold = self.SoundMatchSensitivity
            
            if MaximumDetectionProbability > DetectionThreshold:
                self.UpdateStatus("Megalodon Caught")
                if self.WebhookUrl and self.LogGeneralUpdates:
                    self.SendWebhookNotification("Megalodon detected! Starting fishing minigame...")
                return True
            else:
                self.UpdateStatus("Not megalodon - recasting")
                return False
                
        except Exception as SoundRecognitionError:
            print(f"Sound recognition error: {SoundRecognitionError}")
            traceback.print_exc()
            return True
    
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
        
        if BlackPixelRatio >= self.BlackScreenDetectionRatioThreshold:
            self.UpdateStatus(f"Black screen: {BlackPixelRatio*100:.1f}%")
            return True
        
        return False
    
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
        self.UpdateStatus("Anti-macro detected - clearing")
        RetryAttemptCount = 0
        MaximumRetryAttempts = 20
        
        while self.MacroCurrentlyExecuting and RetryAttemptCount < MaximumRetryAttempts:
            if not self.DetectBlackScreenCondition():
                self.UpdateStatus("Anti-macro cleared")
                return True
            
            keyboard.press_and_release(self.AlternateInventorySlot)
            time.sleep(self.AntiMacroDialogSpamDelay)
            RetryAttemptCount += 1
        
        self.UpdateStatus("Anti-macro clear failed")
        return False
    
    def PerformActiveFishingControl(self):
        self.UpdateStatus("Capturing screen for analysis")
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
            self.UpdateStatus("Black screen detected - checking anti-macro")
            if self.MouseButtonCurrentlyPressed:
                pyautogui.mouseUp()
                self.MouseButtonCurrentlyPressed = False
            self.HandleAntiMacroDetection()
            return False
        
        self.UpdateStatus("Searching for blue bobber pixels")
        BobberBlueColor = np.array([85, 170, 255])
        BluePixelMask = ((ScreenImageArray[:, :, 2] == BobberBlueColor[0]) & 
                    (ScreenImageArray[:, :, 1] == BobberBlueColor[1]) & 
                    (ScreenImageArray[:, :, 0] == BobberBlueColor[2]))
        
        if not np.any(BluePixelMask):
            self.UpdateStatus("No blue pixels - fish escaped or caught")
            if self.MouseButtonCurrentlyPressed:
                pyautogui.mouseUp()
                self.MouseButtonCurrentlyPressed = False
            return False
        
        self.UpdateStatus("Blue pixels found - analyzing position")
        BluePixelYCoordinates, BluePixelXCoordinates = np.where(BluePixelMask)
        HorizontalCenterPosition = int(np.mean(BluePixelXCoordinates))
        
        VerticalSliceArray = ScreenImageArray[:, HorizontalCenterPosition:HorizontalCenterPosition+1, :]
        
        self.UpdateStatus("Searching for gray boundary pixels")
        BoundaryGrayColor = np.array([25, 25, 25])
        GrayPixelMask = ((VerticalSliceArray[:, 0, 2] == BoundaryGrayColor[0]) & 
                (VerticalSliceArray[:, 0, 1] == BoundaryGrayColor[1]) & 
                (VerticalSliceArray[:, 0, 0] == BoundaryGrayColor[2]))
        
        if not np.any(GrayPixelMask):
            self.UpdateStatus("No gray boundary - minigame not ready")
            return True
        
        self.UpdateStatus("Gray boundary found - extracting bar region")
        GrayPixelYCoordinates = np.where(GrayPixelMask)[0]
        TopBoundaryPosition = GrayPixelYCoordinates[0]
        BottomBoundaryPosition = GrayPixelYCoordinates[-1]
        BoundedSliceArray = VerticalSliceArray[TopBoundaryPosition:BottomBoundaryPosition+1, :, :]
        
        self.UpdateStatus("Searching for white indicator bar")
        IndicatorWhiteColor = np.array([255, 255, 255])
        WhitePixelMask = ((BoundedSliceArray[:, 0, 2] == IndicatorWhiteColor[0]) & 
                    (BoundedSliceArray[:, 0, 1] == IndicatorWhiteColor[1]) & 
                    (BoundedSliceArray[:, 0, 0] == IndicatorWhiteColor[2]))
        
        if not np.any(WhitePixelMask):
            self.UpdateStatus("No white indicator - holding mouse")
            if not self.MouseButtonCurrentlyPressed:
                pyautogui.mouseDown()
                self.MouseButtonCurrentlyPressed = True
            return True
        
        self.UpdateStatus("White indicator found - calculating position")
        WhitePixelYCoordinates = np.where(WhitePixelMask)[0]
        WhiteBarTopPosition = WhitePixelYCoordinates[0]
        WhiteBarBottomPosition = WhitePixelYCoordinates[-1]
        WhiteBarHeight = WhiteBarBottomPosition - WhiteBarTopPosition + 1
        WhiteBarCenterPosition = (WhiteBarTopPosition + WhiteBarBottomPosition) // 2
        WhiteBarCenterScreenY = self.ScanningRegionBounds["y1"] + TopBoundaryPosition + WhiteBarCenterPosition
        
        self.UpdateStatus("Searching for target dark gray bar")
        TargetDarkGrayColor = np.array([25, 25, 25])
        DarkGrayPixelMask = ((BoundedSliceArray[:, 0, 2] == TargetDarkGrayColor[0]) & 
                    (BoundedSliceArray[:, 0, 1] == TargetDarkGrayColor[1]) & 
                    (BoundedSliceArray[:, 0, 0] == TargetDarkGrayColor[2]))
        
        if not np.any(DarkGrayPixelMask):
            self.UpdateStatus("No target bar - panic click")
            if not self.MouseButtonCurrentlyPressed:
                pyautogui.mouseDown()
                print("Panic Click Engaged - No Dark Gray Pixels Detected")
                self.MouseButtonCurrentlyPressed = True
            return True
        
        self.UpdateStatus("Target bar found - grouping pixels")
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
        
        self.UpdateStatus("Finding largest target group")
        LargestPixelGroup = max(PixelGroupCollections, key=len)
        LargestGroupCenterPosition = (LargestPixelGroup[0] + LargestPixelGroup[-1]) // 2
        LargestGroupCenterScreenY = self.ScanningRegionBounds["y1"] + TopBoundaryPosition + LargestGroupCenterPosition
        
        self.UpdateStatus("Calculating PD control signal")
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
                self.UpdateStatus("Target approaching - applying damping")
                AppliedDampingMultiplier = self.PDControllerApproachingStateDamping
                DerivativeControlTerm = -DerivativeGain * AppliedDampingMultiplier * TargetBarVelocity
            else:
                self.UpdateStatus("Chasing target - normal control")
                AppliedDampingMultiplier = self.PDControllerChasingStateDamping
                DerivativeControlTerm = -DerivativeGain * AppliedDampingMultiplier * TargetBarVelocity
        
        FinalControlSignal = ProportionalControlTerm + DerivativeControlTerm
        FinalControlSignal = max(-MaximumControlClamp, min(MaximumControlClamp, FinalControlSignal))
        ShouldHoldMouseButton = FinalControlSignal <= 0
        
        if ShouldHoldMouseButton and not self.MouseButtonCurrentlyPressed:
            self.UpdateStatus("Holding mouse button")
            pyautogui.mouseDown()
            self.MouseButtonCurrentlyPressed = True
            self.LastControlStateChangeTimestamp = CurrentTimestamp
            self.LastInputResendTimestamp = CurrentTimestamp
        elif not ShouldHoldMouseButton and self.MouseButtonCurrentlyPressed:
            self.UpdateStatus("Releasing mouse button")
            pyautogui.mouseUp()
            self.MouseButtonCurrentlyPressed = False
            self.LastControlStateChangeTimestamp = CurrentTimestamp
            self.LastInputResendTimestamp = CurrentTimestamp
        else:
            TimeSinceLastResend = CurrentTimestamp - self.LastInputResendTimestamp
            
            if TimeSinceLastResend >= self.InputStateResendFrequency:
                self.UpdateStatus("Resending input state")
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
        
        with self.SessionLock:
            ActiveSessions = [
                {
                    'client_id': cid,
                    'is_running': sess.get('is_running', False),
                    'rdp_detected': sess.get('rdp_detected', False),
                    'rdp_state': sess.get('rdp_state', 'unknown'),
                    'session_id': sess.get('session_id', -1),
                    'last_updated': sess.get('last_updated', 0)
                }
                for cid, sess in self.AllActiveSessions.items()
                if time.time() - sess.get('last_updated', 0) < 10
            ]
        
        return {
            "clientId": self.CurrentClientId,
            "activeSessions": ActiveSessions,
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
            "topRecipePoint": self.TopRecipeSlotLocation,
            "addRecipePoint": self.AddRecipeButtonLocation,
            "hotkeys": self.GlobalHotkeyBindings,
            "rodHotkey": self.FishingRodInventorySlot,
            "anythingElseHotkey": self.AlternateInventorySlot,
            "devilFruitHotkeys": self.DevilFruitInventorySlots,
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
            "logRecastTimeouts": self.LogRecastTimeouts,
            "logPeriodicStats": self.LogPeriodicStats,
            "logGeneralUpdates": self.LogGeneralUpdates,
            "periodicStatsInterval": self.PeriodicStatsIntervalMinutes,
            "totalRecastTimeouts": self.TotalRecastTimeouts,
            "logDevilFruit": self.LogDevilFruitEnabled,
            "baitRecipes": self.BaitRecipes,
            "currentRecipeIndex": self.CurrentRecipeIndex,
            "currentStatus": self.CurrentMacroStatus,
            "megalodonSoundEnabled": self.MegalodonSoundRecognitionEnabled,
            "soundSensitivity": self.SoundMatchSensitivity,
            "rdp_detected": self.RDPDetected,
            "rdp_session_state": self.RDPSessionState,
            "auto_detect_rdp": self.AutoDetectRDP,
            "allow_rdp_execution": self.AllowRDPExecution,
            "pause_on_rdp_disconnect": self.PauseOnRDPDisconnect,
            "resume_on_rdp_reconnect": self.ResumeOnRDPReconnect,
            "enable_device_sync": self.EnableDeviceSync,
            "sync_settings": self.SyncSettings,
            "sync_stats": self.SyncStats,
            "share_fish_count": self.ShareFishCount,
            "sync_interval": self.SyncIntervalSeconds,
            "device_name": self.DeviceName,
            "connected_devices": self.ConnectedDevices,
            "is_syncing": self.IsSyncing,
        }

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

MacroSystemInstance = AutomatedFishingSystem()
MacroSystemInstance.InitializeOCR()

@FlaskApplication.route('/state', methods=['GET'])
def RetrieveSystemState():
    ClientId = request.args.get('clientId', 'unknown')
    
    if ClientId not in MacroSystemInstance.ClientStats:
        MacroSystemInstance.ClientStats[ClientId] = {
            "fish_caught": 0,
            "start_time": None,
            "is_running": False,
            "last_seen": time.time()
        }
    
    MacroSystemInstance.ClientStats[ClientId]["last_seen"] = time.time()
    if ClientId != 'unknown' and not MacroSystemInstance.MacroCurrentlyExecuting:
        MacroSystemInstance.CurrentClientId = ClientId
    
    IsThisClientRunning = (ClientId == MacroSystemInstance.CurrentClientId and MacroSystemInstance.MacroCurrentlyExecuting)
    
    MacroSystemInstance.ClientStats[ClientId]["is_running"] = IsThisClientRunning
    MacroSystemInstance.ClientStats[ClientId]["fish_caught"] = MacroSystemInstance.TotalFishSuccessfullyCaught
    
    TotalFish = sum(C["fish_caught"] for C in MacroSystemInstance.ClientStats.values())
    ActiveCount = sum(1 for C in MacroSystemInstance.ClientStats.values() if C["is_running"])
    
    TotalUptime = MacroSystemInstance.CumulativeRunningTimeSeconds
    if MacroSystemInstance.CurrentSessionBeginTimestamp:
        TotalUptime += time.time() - MacroSystemInstance.CurrentSessionBeginTimestamp
    
    GlobalFishPerHour = (TotalFish / TotalUptime * 3600) if TotalUptime > 0 else 0
    
    CalculatedFishPerHour = 0.0
    FormattedElapsedTime = "0:00:00"
    AccumulatedTime = MacroSystemInstance.CumulativeRunningTimeSeconds
    
    if MacroSystemInstance.CurrentSessionBeginTimestamp:
        CurrentActiveSessionTime = time.time() - MacroSystemInstance.CurrentSessionBeginTimestamp
        AccumulatedTime = MacroSystemInstance.CumulativeRunningTimeSeconds + CurrentActiveSessionTime
    
    if AccumulatedTime > 0:
        TotalHours = int(AccumulatedTime // 3600)
        TotalMinutes = int((AccumulatedTime % 3600) // 60)
        TotalSeconds = int(AccumulatedTime % 60)
        FormattedElapsedTime = f"{TotalHours}:{TotalMinutes:02d}:{TotalSeconds:02d}"
        CalculatedFishPerHour = (MacroSystemInstance.TotalFishSuccessfullyCaught / AccumulatedTime) * 3600
    
    with MacroSystemInstance.SessionLock:
        ActiveSessions = [
            {
                'client_id': cid,
                'is_running': sess.get('is_running', False),
                'rdp_detected': sess.get('rdp_detected', False),
                'rdp_state': sess.get('rdp_state', 'unknown'),
                'session_id': sess.get('session_id', -1),
                'last_updated': sess.get('last_updated', 0)
            }
            for cid, sess in MacroSystemInstance.AllActiveSessions.items()
            if time.time() - sess.get('last_updated', 0) < 10
        ]
    
    return jsonify({
        "clientId": ClientId,
        "currentActiveClientId": MacroSystemInstance.CurrentClientId,
        "activeSessions": ActiveSessions,
        "clientFishCaught": MacroSystemInstance.ClientStats[ClientId]["fish_caught"],
        "globalFishCaught": TotalFish,
        "globalFishPerHour": round(GlobalFishPerHour, 1),
        "activeClients": ActiveCount,
        "storeToBackpack": MacroSystemInstance.StoreToBackpackEnabled,
        "devilFruitLocationPoint": MacroSystemInstance.DevilFruitLocationPoint,
        "loopsPerStore": MacroSystemInstance.DevilFruitStorageFrequencyCounter,
        "isRunning": IsThisClientRunning,
        "fishCaught": MacroSystemInstance.TotalFishSuccessfullyCaught,
        "timeElapsed": FormattedElapsedTime,
        "moveDuration": MacroSystemInstance.MoveDurationSeconds,
        "fishPerHour": round(CalculatedFishPerHour, 1),
        "waterPoint": MacroSystemInstance.WaterCastingTargetLocation,
        "leftPoint": MacroSystemInstance.ShopLeftButtonLocation,
        "middlePoint": MacroSystemInstance.ShopCenterButtonLocation,
        "rightPoint": MacroSystemInstance.ShopRightButtonLocation,
        "storeFruitPoint": MacroSystemInstance.FruitStorageButtonLocation,
        "baitPoint": MacroSystemInstance.BaitSelectionButtonLocation,
        "topRecipePoint": MacroSystemInstance.TopRecipeSlotLocation,
        "addRecipePoint": MacroSystemInstance.AddRecipeButtonLocation,
        "hotkeys": MacroSystemInstance.GlobalHotkeyBindings,
        "rodHotkey": MacroSystemInstance.FishingRodInventorySlot,
        "anythingElseHotkey": MacroSystemInstance.AlternateInventorySlot,
        "devilFruitHotkeys": MacroSystemInstance.DevilFruitInventorySlots,
        "alwaysOnTop": MacroSystemInstance.WindowAlwaysOnTopEnabled,
        "showDebugOverlay": MacroSystemInstance.DebugOverlayVisible,
        "autoBuyCommonBait": MacroSystemInstance.AutomaticBaitPurchaseEnabled,
        "autoStoreDevilFruit": MacroSystemInstance.AutomaticFruitStorageEnabled,
        "autoSelectTopBait": MacroSystemInstance.AutomaticTopBaitSelectionEnabled,
        "kp": MacroSystemInstance.ProportionalGainCoefficient,
        "kd": MacroSystemInstance.DerivativeGainCoefficient,
        "pdClamp": MacroSystemInstance.ControlSignalMaximumClamp,
        "castHoldDuration": MacroSystemInstance.MouseHoldDurationForCast,
        "recastTimeout": MacroSystemInstance.MaximumWaitTimeBeforeRecast,
        "fishEndDelay": MacroSystemInstance.DelayAfterFishCaptured,
        "loopsPerPurchase": MacroSystemInstance.BaitPurchaseFrequencyCounter,
        "pdApproachingDamping": MacroSystemInstance.PDControllerApproachingStateDamping,
        "pdChasingDamping": MacroSystemInstance.PDControllerChasingStateDamping,
        "gapToleranceMultiplier": MacroSystemInstance.BarGroupingGapToleranceMultiplier,
        "stateResendInterval": MacroSystemInstance.InputStateResendFrequency,
        "robloxFocusDelay": MacroSystemInstance.RobloxWindowFocusInitialDelay,
        "robloxPostFocusDelay": MacroSystemInstance.RobloxWindowFocusFollowupDelay,
        "preCastEDelay": MacroSystemInstance.PreCastDialogOpenDelay,
        "preCastClickDelay": MacroSystemInstance.PreCastMouseClickDelay,
        "preCastTypeDelay": MacroSystemInstance.PreCastKeyboardInputDelay,
        "preCastAntiDetectDelay": MacroSystemInstance.PreCastAntiDetectionDelay,
        "storeFruitHotkeyDelay": MacroSystemInstance.FruitStorageHotkeyActivationDelay,
        "storeFruitClickDelay": MacroSystemInstance.FruitStorageClickConfirmationDelay,
        "storeFruitShiftDelay": MacroSystemInstance.FruitStorageShiftKeyPressDelay,
        "storeFruitBackspaceDelay": MacroSystemInstance.FruitStorageBackspaceDeletionDelay,
        "autoSelectBaitDelay": MacroSystemInstance.BaitSelectionConfirmationDelay,
        "blackScreenThreshold": MacroSystemInstance.BlackScreenDetectionRatioThreshold,
        "antiMacroSpamDelay": MacroSystemInstance.AntiMacroDialogSpamDelay,
        "rodSelectDelay": MacroSystemInstance.InventorySlotSwitchingDelay,
        "cursorAntiDetectDelay": MacroSystemInstance.MouseMovementAntiDetectionDelay,
        "scanLoopDelay": MacroSystemInstance.ImageProcessingLoopDelay,
        "autoCraftBait": MacroSystemInstance.AutomaticBaitCraftingEnabled,
        "craftLeftPoint": MacroSystemInstance.CraftLeftButtonLocation,
        "craftMiddlePoint": MacroSystemInstance.CraftMiddleButtonLocation,
        "craftButtonPoint": MacroSystemInstance.CraftButtonLocation,
        "closeMenuPoint": MacroSystemInstance.CloseMenuButtonLocation,
        "craftsPerCycle": MacroSystemInstance.CraftsPerCycleCount,
        "loopsPerCraft": MacroSystemInstance.BaitCraftFrequencyCounter,
        "fishCountPerCraft": MacroSystemInstance.FishCountPerCraft,
        "craftMenuOpenDelay": MacroSystemInstance.CraftMenuOpenDelay,
        "craftClickDelay": MacroSystemInstance.CraftClickDelay,
        "craftRecipeSelectDelay": MacroSystemInstance.CraftRecipeSelectDelay,
        "craftAddRecipeDelay": MacroSystemInstance.CraftAddRecipeDelay,
        "craftTopRecipeDelay": MacroSystemInstance.CraftTopRecipeDelay,
        "craftButtonClickDelay": MacroSystemInstance.CraftButtonClickDelay,
        "craftCloseMenuDelay": MacroSystemInstance.CraftCloseMenuDelay,
        "webhookUrl": MacroSystemInstance.WebhookUrl,
        "logRecastTimeouts": MacroSystemInstance.LogRecastTimeouts,
        "logPeriodicStats": MacroSystemInstance.LogPeriodicStats,
        "logGeneralUpdates": MacroSystemInstance.LogGeneralUpdates,
        "periodicStatsInterval": MacroSystemInstance.PeriodicStatsIntervalMinutes,
        "totalRecastTimeouts": MacroSystemInstance.TotalRecastTimeouts,
        "logDevilFruit": MacroSystemInstance.LogDevilFruitEnabled,
        "baitRecipes": MacroSystemInstance.BaitRecipes,
        "currentRecipeIndex": MacroSystemInstance.CurrentRecipeIndex,
        "currentStatus": MacroSystemInstance.CurrentMacroStatus,
        "megalodonSoundEnabled": MacroSystemInstance.MegalodonSoundRecognitionEnabled,
        "soundSensitivity": MacroSystemInstance.SoundMatchSensitivity,
        "rdp_detected": MacroSystemInstance.RDPDetected,
        "rdp_session_state": MacroSystemInstance.RDPSessionState,
        "auto_detect_rdp": MacroSystemInstance.AutoDetectRDP,
        "allow_rdp_execution": MacroSystemInstance.AllowRDPExecution,
        "pause_on_rdp_disconnect": MacroSystemInstance.PauseOnRDPDisconnect,
        "resume_on_rdp_reconnect": MacroSystemInstance.ResumeOnRDPReconnect,
        "enable_device_sync": MacroSystemInstance.EnableDeviceSync,
        "sync_settings": MacroSystemInstance.SyncSettings,
        "sync_stats": MacroSystemInstance.SyncStats,
        "share_fish_count": MacroSystemInstance.ShareFishCount,
        "sync_interval": MacroSystemInstance.SyncIntervalSeconds,
        "device_name": MacroSystemInstance.DeviceName,
        "connected_devices": MacroSystemInstance.ConnectedDevices,
        "is_syncing": MacroSystemInstance.IsSyncing,
    })

@FlaskApplication.route('/health', methods=['GET'])
def PerformHealthCheck():
    return jsonify({"status": "ok", "message": "Backend running"})

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
        
        ClientId = IncomingData.get('clientId', 'unknown')
        MacroSystemInstance.CurrentClientId = ClientId
        
        if ClientId in MacroSystemInstance.ClientStats:
            MacroSystemInstance.ClientStats[ClientId]["last_seen"] = time.time()
        
        if not RequestedAction:
            return jsonify({"status": "error", "message": "Missing action parameter"}), 400
        
        ActionHandlers = {
            'set_water_point': lambda: HandlePointSelection('WaterCastingTargetLocation'),
            'set_devil_fruit_location_point': lambda: HandlePointSelection('DevilFruitLocationPoint'),
            'set_left_point': lambda: HandlePointSelection('ShopLeftButtonLocation'),
            'set_middle_point': lambda: HandlePointSelection('ShopCenterButtonLocation'),
            'set_right_point': lambda: HandlePointSelection('ShopRightButtonLocation'),
            'set_store_fruit_point': lambda: HandlePointSelection('FruitStorageButtonLocation'),
            'set_bait_point': lambda: HandlePointSelection('BaitSelectionButtonLocation'),
            'set_craft_left_point': lambda: HandlePointSelection('CraftLeftButtonLocation'),
            'set_craft_middle_point': lambda: HandlePointSelection('CraftMiddleButtonLocation'),
            'set_bait_recipe_point': lambda: HandlePointSelection('BaitRecipeButtonLocation'),
            'set_add_recipe_point': lambda: HandlePointSelection('AddRecipeButtonLocation'),
            'set_top_recipe_point': lambda: HandlePointSelection('TopRecipeSlotLocation'),
            'set_craft_button_point': lambda: HandlePointSelection('CraftButtonLocation'),
            'set_close_menu_point': lambda: HandlePointSelection('CloseMenuButtonLocation'),
            'toggle_store_to_backpack': lambda: HandleBooleanToggle('StoreToBackpackEnabled'),
            'toggle_always_on_top': lambda: HandleBooleanToggle('WindowAlwaysOnTopEnabled'),
            'toggle_debug_overlay': lambda: HandleBooleanToggle('DebugOverlayVisible'),
            'toggle_auto_buy_bait': lambda: HandleBooleanToggle('AutomaticBaitPurchaseEnabled'),
            'toggle_auto_store_fruit': lambda: HandleBooleanToggle('AutomaticFruitStorageEnabled'),
            'toggle_auto_select_bait': lambda: HandleBooleanToggle('AutomaticTopBaitSelectionEnabled'),
            'toggle_auto_craft_bait': lambda: HandleBooleanToggle('AutomaticBaitCraftingEnabled'),
            'set_rod_hotkey': lambda: HandleStringValue('FishingRodInventorySlot'),
            'set_anything_else_hotkey': lambda: HandleStringValue('AlternateInventorySlot'),
            'set_devil_fruit_hotkeys': lambda: HandleDevilFruitSlots(ActionPayload),
            'set_loops_per_store': lambda: HandleIntegerValue('DevilFruitStorageFrequencyCounter'),
            'set_loops_per_purchase': lambda: HandleIntegerValue('BaitPurchaseFrequencyCounter'),
            'set_fish_count_per_craft': lambda: HandleIntegerValue('FishCountPerCraft'),
            'set_crafts_per_cycle': lambda: HandleIntegerValue('CraftsPerCycleCount'),
            'set_loops_per_craft': lambda: HandleIntegerValue('BaitCraftFrequencyCounter'),
            'set_periodic_stats_interval': lambda: HandleIntegerValue('PeriodicStatsIntervalMinutes'),
            'set_kp': lambda: HandleFloatValue('ProportionalGainCoefficient'),
            'set_kd': lambda: HandleFloatValue('DerivativeGainCoefficient'),
            'set_pd_clamp': lambda: HandleFloatValue('ControlSignalMaximumClamp'),
            'set_pd_approaching': lambda: HandleFloatValue('PDControllerApproachingStateDamping'),
            'set_pd_chasing': lambda: HandleFloatValue('PDControllerChasingStateDamping'),
            'set_gap_tolerance': lambda: HandleFloatValue('BarGroupingGapToleranceMultiplier'),
            'set_cast_hold': lambda: HandleFloatValue('MouseHoldDurationForCast'),
            'set_recast_timeout': lambda: HandleFloatValue('MaximumWaitTimeBeforeRecast'),
            'set_fish_end_delay': lambda: HandleFloatValue('DelayAfterFishCaptured'),
            'set_state_resend': lambda: HandleFloatValue('InputStateResendFrequency'),
            'set_focus_delay': lambda: HandleFloatValue('RobloxWindowFocusInitialDelay'),
            'set_post_focus_delay': lambda: HandleFloatValue('RobloxWindowFocusFollowupDelay'),
            'set_precast_e_delay': lambda: HandleFloatValue('PreCastDialogOpenDelay'),
            'set_precast_click_delay': lambda: HandleFloatValue('PreCastMouseClickDelay'),
            'set_precast_type_delay': lambda: HandleFloatValue('PreCastKeyboardInputDelay'),
            'set_anti_detect_delay': lambda: HandleFloatValue('PreCastAntiDetectionDelay'),
            'set_fruit_hotkey_delay': lambda: HandleFloatValue('FruitStorageHotkeyActivationDelay'),
            'set_fruit_click_delay': lambda: HandleFloatValue('FruitStorageClickConfirmationDelay'),
            'set_fruit_shift_delay': lambda: HandleFloatValue('FruitStorageShiftKeyPressDelay'),
            'set_fruit_backspace_delay': lambda: HandleFloatValue('FruitStorageBackspaceDeletionDelay'),
            'set_rod_delay': lambda: HandleFloatValue('InventorySlotSwitchingDelay'),
            'set_bait_delay': lambda: HandleFloatValue('BaitSelectionConfirmationDelay'),
            'set_cursor_delay': lambda: HandleFloatValue('MouseMovementAntiDetectionDelay'),
            'set_scan_delay': lambda: HandleFloatValue('ImageProcessingLoopDelay'),
            'set_black_threshold': lambda: HandleFloatValue('BlackScreenDetectionRatioThreshold'),
            'set_spam_delay': lambda: HandleFloatValue('AntiMacroDialogSpamDelay'),
            'set_move_duration': lambda: HandleFloatValue('MoveDurationSeconds'),
            'set_craft_menu_delay': lambda: HandleFloatValue('CraftMenuOpenDelay'),
            'set_craft_click_delay': lambda: HandleFloatValue('CraftClickDelay'),
            'set_craft_recipe_delay': lambda: HandleFloatValue('CraftRecipeSelectDelay'),
            'set_craft_add_delay': lambda: HandleFloatValue('CraftAddRecipeDelay'),
            'set_craft_top_delay': lambda: HandleFloatValue('CraftTopRecipeDelay'),
            'set_craft_button_delay': lambda: HandleFloatValue('CraftButtonClickDelay'),
            'set_craft_close_delay': lambda: HandleFloatValue('CraftCloseMenuDelay'),
            'set_webhook_url': lambda: HandleStringValue('WebhookUrl'),
            'toggle_log_recast_timeouts': lambda: HandleBooleanToggle('LogRecastTimeouts'),
            'toggle_log_periodic_stats': lambda: HandleBooleanToggle('LogPeriodicStats'),
            'toggle_log_general_updates': lambda: HandleBooleanToggle('LogGeneralUpdates'),
            'set_periodic_stats_interval': lambda: HandleIntegerValue('PeriodicStatsIntervalMinutes'),
            'toggle_log_devil_fruit': lambda: HandleBooleanToggle('LogDevilFruitEnabled'),
            'open_area_selector': lambda: HandleAreaSelector(),
            'open_browser': lambda: HandleOpenBrowser(ActionPayload),
            'toggle_megalodon_sound': lambda: HandleBooleanToggle('MegalodonSoundRecognitionEnabled'),
            'set_sound_sensitivity': lambda: HandleFloatValue('SoundMatchSensitivity'),
            'toggle_auto_detect_rdp': lambda: HandleBooleanToggle('AutoDetectRDP'),
            'toggle_allow_rdp_execution': lambda: HandleBooleanToggle('AllowRDPExecution'),
            'toggle_pause_on_rdp_disconnect': lambda: HandleBooleanToggle('PauseOnRDPDisconnect'),
            'toggle_resume_on_rdp_reconnect': lambda: HandleBooleanToggle('ResumeOnRDPReconnect'),
            'toggle_enable_device_sync': lambda: HandleBooleanToggle('EnableDeviceSync'),
            'toggle_sync_settings': lambda: HandleBooleanToggle('SyncSettings'),
            'toggle_sync_stats': lambda: HandleBooleanToggle('SyncStats'),
            'toggle_share_fish_count': lambda: HandleBooleanToggle('ShareFishCount'),
            'set_sync_interval': lambda: HandleIntegerValue('SyncIntervalSeconds'),
            'set_device_name': lambda: HandleStringValue('DeviceName'),
            'set_client_id': lambda: HandleStringValue('CurrentClientId'),
            'export_settings': lambda: HandleExportSettings(),
            'import_settings': lambda: HandleImportSettings(),
            'reset_settings': lambda: HandleResetSettings(ActionPayload),
            'open_config_folder': lambda: HandleOpenConfigFolder(),
            'view_config': lambda: HandleViewConfig(),
            'clear_cache': lambda: HandleClearCache(),
        }

        if RequestedAction == 'rebind_hotkey':
            return HandleHotkeyRebind(ActionPayload)

        if RequestedAction in ActionHandlers:
            return ActionHandlers[RequestedAction]()
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
            "CraftsPerCycle": 40,
            "SwitchFishCycle": 5 
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
    
def HandleDevilFruitSlots(ActionPayload):
    if ActionPayload is None:
        return jsonify({"status": "error", "message": "Missing payload"}), 400
    
    try:
        Slots = [S.strip() for S in ActionPayload.split(',') if S.strip()]
        MacroSystemInstance.DevilFruitInventorySlots = Slots
        MacroSystemInstance.SaveConfigurationToDisk()
        return jsonify({"status": "success", "slots": Slots})
    except Exception as E:
        return jsonify({"status": "error", "message": f"Invalid slots: {str(E)}"}), 400

def HandleExportSettings():
    try:
        Root = tk.Tk()
        Root.withdraw()
        Root.attributes('-topmost', True)
        
        DefaultFilename = f"fishing_macro_settings_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        FilePath = filedialog.asksaveasfilename(
            title="Export Settings",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            initialfile=DefaultFilename
        )
        
        Root.destroy()
        
        if FilePath:
            shutil.copy(MacroSystemInstance.ConfigurationFilePath, FilePath)
            messagebox.showinfo("Export Successful", f"Settings exported to:\n{FilePath}")
            return jsonify({"status": "success", "path": FilePath})
        
        return jsonify({"status": "cancelled"})
    except Exception as E:
        messagebox.showerror("Export Failed", f"Failed to export settings:\n{str(E)}")
        return jsonify({"status": "error", "message": str(E)}), 500

def HandleImportSettings():
    try:
        Root = tk.Tk()
        Root.withdraw()
        Root.attributes('-topmost', True)
        
        FilePath = filedialog.askopenfilename(
            title="Import Settings",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        Root.destroy()
        
        if FilePath:
            BackupPath = MacroSystemInstance.ConfigurationFilePath + ".backup"
            shutil.copy(MacroSystemInstance.ConfigurationFilePath, BackupPath)
            
            try:
                shutil.copy(FilePath, MacroSystemInstance.ConfigurationFilePath)
                MacroSystemInstance.LoadConfigurationFromDisk()
                messagebox.showinfo("Import Successful", "Settings imported successfully!\n\nOld settings backed up to:\n" + BackupPath)
                return jsonify({"status": "success"})
            except Exception as ImportError:
                shutil.copy(BackupPath, MacroSystemInstance.ConfigurationFilePath)
                raise ImportError
        
        return jsonify({"status": "cancelled"})
    except Exception as E:
        messagebox.showerror("Import Failed", f"Failed to import settings:\n{str(E)}")
        return jsonify({"status": "error", "message": str(E)}), 500

def HandleResetSettings(Payload):
    if Payload != "confirm":
        return jsonify({"status": "error", "message": "Reset not confirmed"}), 400
    
    try:
        BackupPath = MacroSystemInstance.ConfigurationFilePath + f".backup_{int(time.time())}"
        if os.path.exists(MacroSystemInstance.ConfigurationFilePath):
            shutil.copy(MacroSystemInstance.ConfigurationFilePath, BackupPath)
        
        if os.path.exists(MacroSystemInstance.ConfigurationFilePath):
            os.remove(MacroSystemInstance.ConfigurationFilePath)
        
        MacroSystemInstance.__init__()
        
        messagebox.showinfo("Reset Successful", f"Settings reset to defaults!\n\nBackup saved to:\n{BackupPath}")
        return jsonify({"status": "success"})
    except Exception as E:
        messagebox.showerror("Reset Failed", f"Failed to reset settings:\n{str(E)}")
        return jsonify({"status": "error", "message": str(E)}), 500

def HandleOpenConfigFolder():
    try:
        FolderPath = os.path.dirname(MacroSystemInstance.ConfigurationFilePath)
        
        if platform.system() == "Windows":
            os.startfile(FolderPath)
        elif platform.system() == "Darwin":
            subprocess.Popen(["open", FolderPath])
        else:
            subprocess.Popen(["xdg-open", FolderPath])
        
        return jsonify({"status": "success"})
    except Exception as E:
        return jsonify({"status": "error", "message": str(E)}), 500

def HandleViewConfig():
    try:
        if os.path.exists(MacroSystemInstance.ConfigurationFilePath):
            with open(MacroSystemInstance.ConfigurationFilePath, 'r') as F:
                ConfigContent = F.read()
            
            Root = tk.Tk()
            Root.title("Configuration File Viewer")
            Root.geometry("800x600")
            
            TextWidget = tk.Text(Root, wrap=tk.WORD, font=("Consolas", 10))
            TextWidget.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            TextWidget.insert(1.0, ConfigContent)
            TextWidget.config(state=tk.DISABLED)
            
            Scrollbar = tk.Scrollbar(TextWidget)
            Scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            TextWidget.config(yscrollcommand=Scrollbar.set)
            Scrollbar.config(command=TextWidget.yview)
            
            Root.mainloop()
            
            return jsonify({"status": "success"})
        else:
            messagebox.showwarning("File Not Found", "Configuration file does not exist yet.")
            return jsonify({"status": "error", "message": "Config file not found"}), 404
    except Exception as E:
        messagebox.showerror("View Failed", f"Failed to view config:\n{str(E)}")
        return jsonify({"status": "error", "message": str(E)}), 500

def HandleClearCache():
    try:
        MacroSystemInstance.BaitPurchaseIterationCounter = 0
        MacroSystemInstance.DevilFruitStorageIterationCounter = 0
        MacroSystemInstance.FishCountSinceLastCraft = 0
        MacroSystemInstance.BaitCraftIterationCounter = 0
        MacroSystemInstance.TotalRecastTimeouts = 0
        MacroSystemInstance.ConsecutiveRecastTimeouts = 0
        
        messagebox.showinfo("Cache Cleared", "Runtime cache and counters have been reset.")
        return jsonify({"status": "success"})
    except Exception as E:
        messagebox.showerror("Clear Failed", f"Failed to clear cache:\n{str(E)}")
        return jsonify({"status": "error", "message": str(E)}), 500
    
def HandlePointSelection(PointName):
    MacroSystemInstance.InitiatePointSelectionMode(PointName)
    return jsonify({"status": "waiting_for_click"})

def HandleAreaSelector():
    MacroSystemInstance.ModifyScanningRegion()
    return jsonify({"status": "opening_selector"})

def HandleOpenBrowser(Url):
    if not Url:
        return jsonify({"status": "error", "message": "Missing URL"}), 400
    
    try:
        webbrowser.open(Url)
        return jsonify({"status": "success"})
    except Exception as E:
        return jsonify({"status": "error", "message": str(E)}), 500

def HandleBooleanToggle(AttributeName):
    ActionPayload = request.json.get('payload')
    if ActionPayload is None:
        return jsonify({"status": "error", "message": "Missing payload"}), 400
    
    BooleanValue = ActionPayload.lower() == 'true'
    setattr(MacroSystemInstance, AttributeName, BooleanValue)
    MacroSystemInstance.SaveConfigurationToDisk()
    return jsonify({"status": "success", "value": BooleanValue})

def HandleStringValue(AttributeName):
    ActionPayload = request.json.get('payload')
    if ActionPayload is None:
        return jsonify({"status": "error", "message": "Missing payload"}), 400
    
    setattr(MacroSystemInstance, AttributeName, ActionPayload)
    MacroSystemInstance.SaveConfigurationToDisk()
    return jsonify({"status": "success"})

def HandleIntegerValue(AttributeName):
    ActionPayload = request.json.get('payload')
    if ActionPayload is None:
        return jsonify({"status": "error", "message": "Missing payload"}), 400
    
    try:
        IntegerValue = int(ActionPayload)
        setattr(MacroSystemInstance, AttributeName, IntegerValue)
        MacroSystemInstance.SaveConfigurationToDisk()
        return jsonify({"status": "success"})
    except (ValueError, TypeError) as E:
        return jsonify({"status": "error", "message": f"Invalid integer value: {str(E)}"}), 400

def HandleFloatValue(AttributeName):
    ActionPayload = request.json.get('payload')
    if ActionPayload is None:
        return jsonify({"status": "error", "message": "Missing payload"}), 400
    
    try:
        FloatValue = float(ActionPayload)
        setattr(MacroSystemInstance, AttributeName, FloatValue)
        MacroSystemInstance.SaveConfigurationToDisk()
        return jsonify({"status": "success"})
    except (ValueError, TypeError) as E:
        return jsonify({"status": "error", "message": f"Invalid float value: {str(E)}"}), 400

def HandleHotkeyRebind(ActionPayload):
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