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
import psutil

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
import sounddevice as sd
import pyaudiowpatch as pyaudio
import argparse
import socket

import ctypes
from ctypes import wintypes
import win32gui
import win32con
import win32api
import win32ts
import cv2

import tkinter as tk
from tkinter import ttk, filedialog, messagebox

def FindFreePort(Start=8765, MaxAttempts=50):
    for Port in range(Start, Start + MaxAttempts):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as S:
            try:
                S.bind(('0.0.0.0', Port))
                return Port
            except OSError:
                continue
    raise RuntimeError("No free port found in range")

def CleanupOrphanedPortFiles(AppPath):
    for FileName in os.listdir(AppPath):
        if FileName.startswith('port_') and FileName.endswith('.json'):
            try:
                Pid = int(FileName.replace('port_', '').replace('.json', ''))
                if not psutil.pid_exists(Pid):
                    os.remove(os.path.join(AppPath, FileName))
            except (ValueError, OSError):
                pass

ArgParser = argparse.ArgumentParser()
ArgParser.add_argument('--pid', type=str, default='unknown')
ParsedArgs, _ = ArgParser.parse_known_args()
LauncherPid = ParsedArgs.pid

class ConfigurationManager:

    def __init__(self, ConfigPath):
        self.ConfigPath = ConfigPath
        self.Settings = self.InitializeDefaults()
    
    def InitializeDefaults(self):
        DisplayMetrics = ctypes.windll.user32
        MonitorWidth = DisplayMetrics.GetSystemMetrics(0)
        MonitorHeight = DisplayMetrics.GetSystemMetrics(1)
        
        return {
            'Hotkeys': {'StartStop': 'f1', 'Exit': 'f3'},
            'WindowSettings': {'AlwaysOnTop': True, 'ShowDebugOverlay': False},
            'ScanArea': {
                'X1': int(MonitorWidth * 0.52461),
                'Y1': int(MonitorHeight * 0.29167),
                'X2': int(MonitorWidth * 0.68477),
                'Y2': int(MonitorHeight * 0.79097)
            },
            'ClickPoints': {
                'Water': None,
                'ShopLeft': None,
                'ShopCenter': None,
                'ShopRight': None,
                'Bait': None,
                'StoreFruit': None,
                'DevilFruitLocation': None,
                'CraftLeft': None,
                'CraftMiddle': None,
                'CraftButton': None,
                'CraftConfirm': None,
                'CloseMenu': None,
                'AddRecipe': None,
                'TopRecipe': None
            },
            'InventoryHotkeys': {
                'Rod': '1',
                'Alternate': '2',
                'DevilFruits': ['3']
            },
            'AutomationFeatures': {
                'AutoBuyBait': False,
                'AutoCraftBait': False,
                'AutoStoreFruit': False,
                'AutoSelectTopBait': False
            },
            'AutomationFrequencies': {
                'LoopsPerPurchase': 100,
                'LoopsPerStore': 50,
                'LoopsPerCraft': 5,
                'CraftsPerCycle': 40,
                'FishCountPerCraft': 50
            },
            'DevilFruitStorage': {
                'StoreToBackpack': False,
                'WebhookUrl': ''
            },
            'LoggingOptions': {
                'DiscordUserId': '',
                'LogDevilFruit': False,
                'PingDevilFruit': False,
                'LogRecastTimeouts': True,
                'PingRecastTimeouts': False,
                'LogPeriodicStats': True,
                'PingPeriodicStats': False,
                'LogGeneralUpdates': True,
                'PingGeneralUpdates': False,
                'LogMacroState': False,
                'PingMacroState': False,
                'LogErrors': True,
                'PingErrors': False,
                'PeriodicStatsIntervalMinutes': 5
            },
            'FishingModes': {
                'MegalodonSound': False,
                'SoundSensitivity': 0.1
            },
            'AudioDevice': {
                'SelectedDeviceIndex': None,
                'DeviceName': ''
            },
            'RDPSettings': {
                'AutoDetectRDP': True,
                'AllowRDPExecution': True,
                'PauseOnRDPDisconnect': True,
                'ResumeOnRDPReconnect': False
            },
            'DeviceSyncSettings': {
                'EnableDeviceSync': False,
                'SyncSettings': True,
                'SyncStats': True,
                'ShareFishCount': False,
                'SyncIntervalSeconds': 5,
                'DeviceName': ''
            },
            'FishingControl': {
                'PdController': {
                    'Kp': 1.4,
                    'Kd': 0.6,
                    'PdClamp': 1.0,
                    'PdApproachingDamping': 2.0,
                    'PdChasingDamping': 0.5
                },
                'Timing': {
                    'CastHoldDuration': 0.1,
                    'RecastTimeout': 25.0,
                    'FishEndDelay': 0.5,
                    'StateResendInterval': 0.5
                },
                'Detection': {
                    'GapToleranceMultiplier': 2.0,
                    'BlackScreenThreshold': 0.5,
                    'ScanLoopDelay': 0.1
                }
            },
            'TimingDelays': {
                'RobloxWindow': {
                    'RobloxFocusDelay': 0.2,
                    'RobloxPostFocusDelay': 0.2
                },
                'PreCast': {
                    'SetPrecastEDelay': 1.25,
                    'PreCastClickDelay': 0.5,
                    'PreCastTypeDelay': 0.25,
                    'PreCastAntiDetectDelay': 0.05
                },
                'Inventory': {
                    'RodSelectDelay': 0.2,
                    'AutoSelectBaitDelay': 0.5
                },
                'DevilFruitStorage': {
                    'StoreFruitHotkeyDelay': 0.2,
                    'StoreFruitClickDelay': 0.25,
                    'StoreFruitShiftDelay': 0.35,
                    'StoreFruitBackspaceDelay': 0.2
                },
                'AntiDetection': {
                    'CursorAntiDetectDelay': 0.05,
                    'AntiMacroSpamDelay': 0.25
                },
                'Crafting': {
                    'MoveDuration': 0,
                    'CraftMenuOpenDelay': 0.85,
                    'CraftClickDelay': 0.2,
                    'CraftRecipeSelectDelay': 0.2,
                    'CraftAddRecipeDelay': 0.2,
                    'CraftTopRecipeDelay': 0.2,
                    'CraftButtonClickDelay': 0.025,
                    'CraftCloseMenuDelay': 0.2
                }
            },
            'SpawnDetection': {
                'EnableSpawnDetection': False,
                'ScanInterval': 5.0,
                'LogSpawns': True,
                'PingSpawns': False
            },
            'OCRSettings': {
                'X1': int(MonitorWidth * 0.40),
                'Y1': 60,
                'X2': int(MonitorWidth * 0.60),
                'Y2': int(MonitorHeight * 0.20)
            },
            'BaitRecipes': [],
            'CurrentRecipeIndex': 0
        }
    
    def LoadFromDisk(self):
        if not os.path.exists(self.ConfigPath):
            print(f"No configuration file found at {self.ConfigPath}. Creating new one with defaults.")
            self.SaveToDisk()
            return
        
        try:
            with open(self.ConfigPath, 'r', encoding='utf-8') as ConfigFile:
                FileContent = ConfigFile.read().strip()
            
            if not FileContent:
                print(f"Configuration file at {self.ConfigPath} is empty. Initializing with defaults.")
                self.SaveToDisk()
                return
            
            try:
                ParsedData = json.loads(FileContent)
            except json.JSONDecodeError as JsonError:
                print(f"Configuration file corrupted: {JsonError}")
                print(f"File location: {self.ConfigPath}")
                print("Using defaults. Old file will be backed up.")
                
                try:
                    BackupPath = self.ConfigPath + f".backup_{int(time.time())}"
                    os.rename(self.ConfigPath, BackupPath)
                    print(f"Backup created at: {BackupPath}")
                except Exception as BackupError:
                    print(f"Could not create backup: {BackupError}")
                
                self.SaveToDisk()
                return
            
            self._MergeSettings(ParsedData)
            print(f"Configuration loaded successfully from {self.ConfigPath}")
            
        except Exception as LoadError:
            print(f"Error loading configuration: {LoadError}")
            print(f"File location: {self.ConfigPath}")
            traceback.print_exc()
            print("Using default values.")
    
    def _MergeSettings(self, LoadedData):
        if "Hotkeys" in LoadedData:
            self.Settings['Hotkeys'].update(LoadedData["Hotkeys"])
        
        if "WindowSettings" in LoadedData:
            self.Settings['WindowSettings'].update(LoadedData["WindowSettings"])
        
        if "ScanArea" in LoadedData:
            self.Settings['ScanArea'].update(LoadedData["ScanArea"])
        
        if "ClickPoints" in LoadedData:
            ClickPoints = LoadedData["ClickPoints"]
            self.Settings['ClickPoints']['Water'] = ClickPoints.get("WaterPoint", None)
            self.Settings['ClickPoints']['Bait'] = ClickPoints.get("BaitPoint", None)
            
            if "Shop" in ClickPoints:
                Shop = ClickPoints["Shop"]
                self.Settings['ClickPoints']['ShopLeft'] = Shop.get("LeftPoint", None)
                self.Settings['ClickPoints']['ShopCenter'] = Shop.get("MiddlePoint", None)
                self.Settings['ClickPoints']['ShopRight'] = Shop.get("RightPoint", None)
            
            if "DevilFruit" in ClickPoints:
                Fruit = ClickPoints["DevilFruit"]
                self.Settings['ClickPoints']['StoreFruit'] = Fruit.get("StoreFruitPoint", None)
                self.Settings['ClickPoints']['DevilFruitLocation'] = Fruit.get("DevilFruitLocationPoint", None)
            
            if "Crafting" in ClickPoints:
                Craft = ClickPoints["Crafting"]
                self.Settings['ClickPoints']['CraftLeft'] = Craft.get("CraftLeftPoint", None)
                self.Settings['ClickPoints']['CraftMiddle'] = Craft.get("CraftMiddlePoint", None)
                self.Settings['ClickPoints']['CraftButton'] = Craft.get("CraftButtonPoint", None)
                self.Settings['ClickPoints']['CraftConfirm'] = Craft.get("CraftConfirmPoint", None)
                self.Settings['ClickPoints']['CloseMenu'] = Craft.get("CloseMenuPoint", None)
                self.Settings['ClickPoints']['AddRecipe'] = Craft.get("AddRecipePoint", None)
                self.Settings['ClickPoints']['TopRecipe'] = Craft.get("TopRecipePoint", None)
                self.Settings['BaitRecipes'] = Craft.get("BaitRecipes", [])
                self.Settings['CurrentRecipeIndex'] = Craft.get("CurrentRecipeIndex", 0)
        
        if "InventoryHotkeys" in LoadedData:
            Inv = LoadedData["InventoryHotkeys"]
            self.Settings['InventoryHotkeys']['Rod'] = Inv.get("RodHotkey", '1')
            self.Settings['InventoryHotkeys']['Alternate'] = Inv.get("AnythingElseHotkey", '2')
            self.Settings['InventoryHotkeys']['DevilFruits'] = Inv.get("DevilFruitHotkeys", ['3'])
        
        if "AutomationFeatures" in LoadedData:
            Auto = LoadedData["AutomationFeatures"]
            self.Settings['AutomationFeatures']['AutoBuyBait'] = Auto.get("AutoBuyCommonBait", False)
            self.Settings['AutomationFeatures']['AutoCraftBait'] = Auto.get("AutoCraftBait", False)
            self.Settings['AutomationFeatures']['AutoStoreFruit'] = Auto.get("AutoStoreDevilFruit", False)
            self.Settings['AutomationFeatures']['AutoSelectTopBait'] = Auto.get("AutoSelectTopBait", False)
        
        if "AutomationFrequencies" in LoadedData:
            Freq = LoadedData["AutomationFrequencies"]
            self.Settings['AutomationFrequencies']['LoopsPerPurchase'] = Freq.get("LoopsPerPurchase", 100)
            self.Settings['AutomationFrequencies']['LoopsPerStore'] = Freq.get("LoopsPerStore", 50)
            self.Settings['AutomationFrequencies']['LoopsPerCraft'] = Freq.get("LoopsPerCraft", 5)
            self.Settings['AutomationFrequencies']['CraftsPerCycle'] = Freq.get("CraftsPerCycle", 40)
            self.Settings['AutomationFrequencies']['FishCountPerCraft'] = Freq.get("FishCountPerCraft", 50)
        
        if "DevilFruitStorage" in LoadedData:
            Df = LoadedData["DevilFruitStorage"]
            self.Settings['DevilFruitStorage']['StoreToBackpack'] = Df.get("StoreToBackpack", False)
            self.Settings['DevilFruitStorage']['WebhookUrl'] = Df.get("WebhookUrl", '')
        
        if "LoggingOptions" in LoadedData:
            Log = LoadedData["LoggingOptions"]
            self.Settings['LoggingOptions'].update({
                'DiscordUserId': Log.get("DiscordUserId", ""),
                'LogDevilFruit': Log.get("LogDevilFruit", False),
                'PingDevilFruit': Log.get("PingDevilFruit", False),
                'LogRecastTimeouts': Log.get("LogRecastTimeouts", True),
                'PingRecastTimeouts': Log.get("PingRecastTimeouts", False),
                'LogPeriodicStats': Log.get("LogPeriodicStats", True),
                'PingPeriodicStats': Log.get("PingPeriodicStats", False),
                'LogGeneralUpdates': Log.get("LogGeneralUpdates", True),
                'PingGeneralUpdates': Log.get("PingGeneralUpdates", False),
                'PeriodicStatsIntervalMinutes': Log.get("PeriodicStatsIntervalMinutes", 5),
                'LogMacroState': Log.get("LogMacroState", False),
                'PingMacroState': Log.get("PingMacroState", False),
                'LogErrors': Log.get("LogErrors", True),
                'PingErrors': Log.get("PingErrors", False)
            })
        
        if "SpawnDetection" in LoadedData:
            Spawn = LoadedData["SpawnDetection"]
            self.Settings['SpawnDetection'].update({
                'EnableSpawnDetection': Spawn.get("EnableSpawnDetection", False),
                'ScanInterval': Spawn.get("ScanInterval", 5.0),
                'LogSpawns': Spawn.get("LogSpawns", True),
                'PingSpawns': Spawn.get("PingSpawns", False)
            })

        if "FishingModes" in LoadedData:
            Modes = LoadedData["FishingModes"]
            self.Settings['FishingModes']['MegalodonSound'] = Modes.get("MegalodonSound", False)
            self.Settings['FishingModes']['SoundSensitivity'] = Modes.get("SoundSensitivity", 0.1)
        
        if "RDPSettings" in LoadedData:
            Rdp = LoadedData["RDPSettings"]
            self.Settings['RDPSettings'].update({
                'AutoDetectRDP': Rdp.get("AutoDetectRDP", True),
                'AllowRDPExecution': Rdp.get("AllowRDPExecution", True),
                'PauseOnRDPDisconnect': Rdp.get("PauseOnRDPDisconnect", True),
                'ResumeOnRDPReconnect': Rdp.get("ResumeOnRDPReconnect", False)
            })
        
        if "DeviceSyncSettings" in LoadedData:
            Sync = LoadedData["DeviceSyncSettings"]
            self.Settings['DeviceSyncSettings'].update({
                'EnableDeviceSync': Sync.get("EnableDeviceSync", False),
                'SyncSettings': Sync.get("SyncSettings", True),
                'SyncStats': Sync.get("SyncStats", True),
                'ShareFishCount': Sync.get("ShareFishCount", False),
                'SyncIntervalSeconds': Sync.get("SyncIntervalSeconds", 5),
                'DeviceName': Sync.get("DeviceName", "")
            })
        
        if "FishingControl" in LoadedData:
            Control = LoadedData["FishingControl"]
            if "PdController" in Control:
                self.Settings['FishingControl']['PdController'].update(Control["PdController"])
            if "Timing" in Control:
                self.Settings['FishingControl']['Timing'].update(Control["Timing"])
            if "Detection" in Control:
                self.Settings['FishingControl']['Detection'].update(Control["Detection"])
        
        if "TimingDelays" in LoadedData:
            Timing = LoadedData["TimingDelays"]
            for Category in ['RobloxWindow', 'PreCast', 'Inventory', 'DevilFruitStorage', 'AntiDetection', 'Crafting']:
                if Category in Timing:
                    self.Settings['TimingDelays'][Category].update(Timing[Category])
        
        if "OCRSettings" in LoadedData:
            self.Settings['OCRSettings'].update(LoadedData["OCRSettings"])
    
    def SaveToDisk(self):
        try:
            OutputData = {
                "Hotkeys": self.Settings['Hotkeys'],
                "WindowSettings": self.Settings['WindowSettings'],
                "ScanArea": self.Settings['ScanArea'],
                "ClickPoints": {
                    "WaterPoint": self.Settings['ClickPoints']['Water'],
                    "Shop": {
                        "LeftPoint": self.Settings['ClickPoints']['ShopLeft'],
                        "MiddlePoint": self.Settings['ClickPoints']['ShopCenter'],
                        "RightPoint": self.Settings['ClickPoints']['ShopRight']
                    },
                    "BaitPoint": self.Settings['ClickPoints']['Bait'],
                    "DevilFruit": {
                        "StoreFruitPoint": self.Settings['ClickPoints']['StoreFruit'],
                        "DevilFruitLocationPoint": self.Settings['ClickPoints']['DevilFruitLocation']
                    },
                    "Crafting": {
                        "CraftLeftPoint": self.Settings['ClickPoints']['CraftLeft'],
                        "CraftMiddlePoint": self.Settings['ClickPoints']['CraftMiddle'],
                        "CraftButtonPoint": self.Settings['ClickPoints']['CraftButton'],
                        "CraftConfirmPoint": self.Settings['ClickPoints']['CraftConfirm'],
                        "CloseMenuPoint": self.Settings['ClickPoints']['CloseMenu'],
                        "AddRecipePoint": self.Settings['ClickPoints']['AddRecipe'],
                        "TopRecipePoint": self.Settings['ClickPoints']['TopRecipe'],
                        "BaitRecipes": self.Settings['BaitRecipes'],
                        "CurrentRecipeIndex": self.Settings['CurrentRecipeIndex']
                    }
                },
                "InventoryHotkeys": {
                    "RodHotkey": self.Settings['InventoryHotkeys']['Rod'],
                    "AnythingElseHotkey": self.Settings['InventoryHotkeys']['Alternate'],
                    "DevilFruitHotkeys": self.Settings['InventoryHotkeys']['DevilFruits']
                },
                "AutomationFeatures": {
                    "AutoBuyCommonBait": self.Settings['AutomationFeatures']['AutoBuyBait'],
                    "AutoStoreDevilFruit": self.Settings['AutomationFeatures']['AutoStoreFruit'],
                    "AutoSelectTopBait": self.Settings['AutomationFeatures']['AutoSelectTopBait'],
                    "AutoCraftBait": self.Settings['AutomationFeatures']['AutoCraftBait']
                },
                "AutomationFrequencies": self.Settings['AutomationFrequencies'],
                "DevilFruitStorage": self.Settings['DevilFruitStorage'],
                "LoggingOptions": self.Settings['LoggingOptions'],
                "FishingModes": self.Settings['FishingModes'],
                "RDPSettings": self.Settings['RDPSettings'],
                "DeviceSyncSettings": self.Settings['DeviceSyncSettings'],
                "FishingControl": self.Settings['FishingControl'],
                "TimingDelays": self.Settings['TimingDelays'],
                "SpawnDetection": self.Settings['SpawnDetection'],
                "OCRSettings": self.Settings['OCRSettings'],
            }
            
            with open(self.ConfigPath, 'w') as ConfigFile:
                json.dump(OutputData, ConfigFile, indent=4)
                
        except Exception as SaveError:
            print(f"Error saving settings: {SaveError}")


class MacroStateManager:
    
    def __init__(self):
        self.IsRunning = False
        self.CurrentStatus = "Idle"
        self.ClientId = str(uuid.uuid4())
        
        self.TotalFishCaught = 0
        self.TotalDevilFruits = 0
        self.CumulativeUptime = 0
        self.SessionStartTime = None
        self.LastFishCaptureTime = None
        
        self.TotalRecastTimeouts = 0
        self.ConsecutiveRecastTimeouts = 0
        self.LastPeriodicStatsTime = None
        self.FishAtLastStats = 0
        
        self.BaitPurchaseCounter = 0
        self.FruitStorageCounter = 0
        self.FishSinceLastCraft = 0
        self.BaitCraftCounter = 0
        
        self.RobloxWindowFocused = False
        self.FastModeEnabled = False
        self.MousePressed = False
        
        self.PreviousError = None
        self.PreviousTargetY = None
        self.LastScanTime = time.time()
        self.LastStateChangeTime = time.time()
        self.LastInputResendTime = time.time()
        
        self.SessionLock = Lock()
        
        self.ClientStats = {}
        self.GlobalStats = {
            "TotalFishCaught": 0,
            "TotalUptime": 0,
            "ActiveClients": 0
        }
        
        self.RDPDetected = False
        self.RDPSessionState = 'unknown'
        self.RDPSessionId = -1
        
        self.ConnectedDevices = []
        self.IsSyncing = False
    
    def UpdateStatus(self, Status):
        self.CurrentStatus = Status
    
    def IncrementFishCount(self):
        self.TotalFishCaught += 1
        self.FishSinceLastCraft += 1
        self.LastFishCaptureTime = time.time()

    def IncrementDevilFruitCount(self):
        self.TotalDevilFruits += 1
    
    def HandleRecastTimeout(self):
        self.TotalRecastTimeouts += 1
        self.ConsecutiveRecastTimeouts += 1
    
    def ResetConsecutiveTimeouts(self):
        self.ConsecutiveRecastTimeouts = 0
    
    def GetElapsedTime(self):
        Accumulated = self.CumulativeUptime
        if self.SessionStartTime:
            Accumulated += time.time() - self.SessionStartTime
        return Accumulated
    
    def GetFormattedElapsedTime(self):
        Total = self.GetElapsedTime()
        Hours = int(Total // 3600)
        Minutes = int((Total % 3600) // 60)
        Seconds = int(Total % 60)
        return f"{Hours}:{Minutes:02d}:{Seconds:02d}"
    
    def GetFishPerHour(self):
        Elapsed = self.GetElapsedTime()
        if Elapsed > 0:
            return (self.TotalFishCaught / Elapsed) * 3600
        return 0.0


class RDPDetector:
    
    @staticmethod
    def DetectRDPSession():
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
                win32ts.WTSWinStationName
            )
            
            return IsRdp, RdpState, SessionId, SessionName
        except Exception as E:
            print(f"RDP detection error: {E}")
            return False, 'unknown', -1, 'unknown'


class OCRManager:
    
    def __init__(self):
        self.Reader = None
        self.Enabled = True
    
    def Initialize(self):
        if self.Reader is None and self.Enabled:
            try:
                def LoadOCR():
                    try:
                        import easyocr
                        self.Reader = easyocr.Reader(
                            ['en'],
                            gpu=True,
                            verbose=False,
                            recognizer='standard',
                        )
                    except Exception as E:
                        print(f"OCR Initialization Error: {E}")
                        self.Enabled = False
                
                threading.Thread(target=LoadOCR, daemon=True).start()
            except Exception as E:
                print(f"OCR Thread Error: {E}")
                self.Enabled = False
    
    def WaitForInitialization(self, TimeoutSeconds=30):
        StartTime = time.time()
        while self.Reader is None and (time.time() - StartTime) < TimeoutSeconds:
            time.sleep(0.5)
        
        if self.Reader is None:
            self.Enabled = False
            return False
        return True


class DevilFruitDetector:
    
    def __init__(self, OcrManager, Config):
        self.OcrManager = OcrManager
        self.Config = Config
        self.KnownFruits = {
            "Soul", "Dragon", "Mochi", "Ope", "Tori", "Buddha",
            "Pika", "Kage", "Magu", "Gura", "Yuki", "Smoke",
            "Goru", "Suna", "Mera", "Goro", "Ito", "Paw",
            "Yami", "Zushi", "Kira", "Spring", "Yomi",
            "Bomu", "Bari", "Mero", "Horo", "Gomu", "Suke", "Heal",
            "Kilo", "Spin", "Hie", "Venom", "Pteranodon",
        }
    
    def DetectNewItem(self):
        try:
            if self.OcrManager.Reader is None:
                if not self.OcrManager.Enabled:
                    return None
                self.OcrManager.Initialize()
                if not self.OcrManager.WaitForInitialization():
                    return None

            ScanRegion = {
                "top": self.Config.Settings['OCRSettings']['Y1'],
                "left": self.Config.Settings['OCRSettings']['X1'],
                "width": self.Config.Settings['OCRSettings']['X2'] - self.Config.Settings['OCRSettings']['X1'],
                "height": self.Config.Settings['OCRSettings']['Y2'] - self.Config.Settings['OCRSettings']['Y1']
            }

            with mss.mss() as ScreenCapture:
                Screenshot = ScreenCapture.grab(ScanRegion)
                Image = np.array(Screenshot)

            ImageRGB = Image[:, :, [2, 1, 0]]

            Img = PILImage.fromarray(ImageRGB)
            W, H = Img.size
            Img = Img.resize((W * 3, H * 3), PILImage.LANCZOS)
            ImgCV = np.array(Img)
            Gray = cv2.cvtColor(ImgCV, cv2.COLOR_RGB2GRAY)
            _, WhiteOnly = cv2.threshold(Gray, 180, 255, cv2.THRESH_BINARY)
            Kernel = np.ones((2, 2), np.uint8)
            Dilated = cv2.dilate(WhiteOnly, Kernel, iterations=1)
            ProcessedImage = cv2.cvtColor(Dilated, cv2.COLOR_GRAY2RGB)

            Results = self.OcrManager.Reader.readtext(
                ProcessedImage,
                detail=1,
                paragraph=True,
                text_threshold=0.6,
                contrast_ths=0.1,
                adjust_contrast=0.8,
                blocklist='@#$%^&*()+=[]{}|\\~`',
            )

            FullText = " ".join(Text for _, Text, Conf in Results if Conf > 0.4)
            FullText = FullText.strip()
            FullTextLower = FullText.lower()

            HasNew = any(Keyword in FullTextLower for Keyword in [
                'new', 'nev', 'ncv', 'ncw', 'naw', 'ner'
            ])
            HasItem = 'item' in FullTextLower or 'ltem' in FullTextLower

            if not (FullText and HasNew and HasItem):
                return None

            BracketMatch = re.search(r'[<(\[{]([A-Za-z]+)[>\)\]}]?', FullText)
            if BracketMatch:
                Candidate = BracketMatch.group(1).strip()
                if len(Candidate) >= 3:
                    ClosestMatch = self.GetClosestFruit(Candidate, Cutoff=0.55)
                    if ClosestMatch:
                        return ClosestMatch

            AfterItemMatch = re.search(r'(?:item|ltem)\s+(.+)', FullText, re.IGNORECASE)
            if AfterItemMatch:
                Remainder = AfterItemMatch.group(1).strip()
                Remainder = re.sub(r'[<>(\[{\])}?]', '', Remainder).strip()
                Words = Remainder.split()
                for Word in Words:
                    if len(Word) >= 3:
                        ClosestMatch = self.GetClosestFruit(Word, Cutoff=0.55)
                        if ClosestMatch:
                            return ClosestMatch

            return None

        except Exception as E:
            print(f"OCR Check Error: {E}")
            traceback.print_exc()
            return None
    
    def DetectSpawn(self):
        try:
            if self.OcrManager.Reader is None:
                if not self.OcrManager.Enabled:
                    return None
                self.OcrManager.Initialize()
                if not self.OcrManager.WaitForInitialization():
                    return None

            ScanRegion = {
                "top": self.Config.Settings['OCRSettings']['Y1'],
                "left": self.Config.Settings['OCRSettings']['X1'],
                "width": self.Config.Settings['OCRSettings']['X2'] - self.Config.Settings['OCRSettings']['X1'],
                "height": self.Config.Settings['OCRSettings']['Y2'] - self.Config.Settings['OCRSettings']['Y1']
            }

            with mss.mss() as ScreenCapture:
                Screenshot = ScreenCapture.grab(ScanRegion)
                Image = np.array(Screenshot)

            ImageRGB = Image[:, :, [2, 1, 0]]

            Img = PILImage.fromarray(ImageRGB)
            W, H = Img.size
            Img = Img.resize((W * 3, H * 3), PILImage.LANCZOS)
            ImgCV = np.array(Img)
            Gray = cv2.cvtColor(ImgCV, cv2.COLOR_RGB2GRAY)
            _, WhiteOnly = cv2.threshold(Gray, 180, 255, cv2.THRESH_BINARY)
            Kernel = np.ones((2, 2), np.uint8)
            Dilated = cv2.dilate(WhiteOnly, Kernel, iterations=1)
            ProcessedImage = cv2.cvtColor(Dilated, cv2.COLOR_GRAY2RGB)

            Results = self.OcrManager.Reader.readtext(
                ProcessedImage,
                detail=1,
                paragraph=True,
                text_threshold=0.6,
                contrast_ths=0.1,
                adjust_contrast=0.8,
                blocklist='@#$%^&*()+=[]{}|\\~`',
            )

            FullText = " ".join(Text for _, Text, Conf in Results if Conf > 0.4)
            FullText = FullText.strip()
            FullTextLower = FullText.lower()

            HasSpawn = 'spawn' in FullTextLower

            if not (FullText and HasSpawn):
                return None

            Words = FullText.split()
            for Word in Words:
                Clean = re.sub(r'[^A-Za-z]', '', Word)
                if len(Clean) >= 3:
                    Match = self.GetClosestFruit(Clean, Cutoff=0.6)
                    if Match:
                        return Match

            return None

        except Exception as E:
            print(f"Spawn detection error: {E}")
            traceback.print_exc()
            return None
        
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


class WebhookNotifier:
    
    def __init__(self, Config, State):
        self.Config = Config
        self.State = State
    
    def SendNotification(self, Message, Color=None, Title=None, Category=None):
        WebhookUrl = self.Config.Settings['DevilFruitStorage']['WebhookUrl']
        if not WebhookUrl:
            return
        
        try:
            ColorInfo = 0x00d4ff
            ColorSuccess = 0x10b981
            ColorWarning = 0xf59e0b
            ColorError = 0xef4444
            ColorCraft = 0x8b5cf6
            ColorFruit = 0xbf40bf
            ColorStats = 0x3b82f6
            ColorMega = 0xfbbf24
            
            PingUser = False
            ShouldSend = True
            
            LogOpts = self.Config.Settings['LoggingOptions']
            
            if Color is None or Title is None:
                MessageLower = Message.lower()
                
                if "megalodon" in MessageLower:
                    Color = ColorMega
                    Title = "🎣 Megalodon Detected"
                    Category = "general"
                    ShouldSend = LogOpts['LogGeneralUpdates']
                    PingUser = LogOpts['PingGeneralUpdates']
                elif "devil fruit" in MessageLower and "stored successfully" in MessageLower:
                    Color = ColorFruit
                    Title = "🎣 Devil Fruit Found"
                    Category = "devil_fruit"
                    ShouldSend = LogOpts['LogDevilFruit']
                    PingUser = LogOpts['PingDevilFruit']
                elif "craft" in MessageLower:
                    Color = ColorCraft
                    Title = "🎣 Crafting Update"
                    Category = "general"
                    ShouldSend = LogOpts['LogGeneralUpdates']
                    PingUser = LogOpts['PingGeneralUpdates']
                elif "stats" in MessageLower or "caught:" in MessageLower or "total:" in MessageLower:
                    Color = ColorStats
                    Title = "🎣 Fishing Statistics"
                    Category = "periodic_stats"
                    ShouldSend = LogOpts['LogPeriodicStats']
                    PingUser = LogOpts['PingPeriodicStats']
                elif "started" in MessageLower or "stopped" in MessageLower:
                    Color = ColorSuccess if "started" in MessageLower else ColorWarning
                    Title = "🎣 Macro State"
                    Category = "macro_state"
                    ShouldSend = LogOpts['LogMacroState']
                    PingUser = LogOpts['PingMacroState']
                elif "crash" in MessageLower or "error" in MessageLower or "failed" in MessageLower:
                    Color = ColorError
                    Title = "🎣 Error"
                    Category = "errors"
                    ShouldSend = LogOpts['LogErrors']
                    PingUser = LogOpts['PingErrors']
                elif "timeout" in MessageLower and "consecutive" in MessageLower:
                    Color = ColorWarning
                    Title = "🎣 Warning"
                    Category = "recast_timeouts"
                    ShouldSend = LogOpts['LogRecastTimeouts']
                    PingUser = LogOpts['PingRecastTimeouts']
                elif "reconnected" in MessageLower or "disconnected" in MessageLower or "rdp" in MessageLower:
                    Color = ColorWarning
                    Title = "🎣 RDP Status"
                    Category = "general"
                    ShouldSend = LogOpts['LogGeneralUpdates']
                    PingUser = LogOpts['PingGeneralUpdates']
                else:
                    Color = ColorInfo
                    Title = "🎣 GPO Fishing Macro"
                    Category = "general"
                    ShouldSend = LogOpts['LogGeneralUpdates']
                    PingUser = LogOpts['PingGeneralUpdates']
            
            if not ShouldSend:
                return
            
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

            DiscordUserId = LogOpts['DiscordUserId']
            if PingUser and DiscordUserId and DiscordUserId.strip():
                PayloadData["content"] = f"<@{DiscordUserId.strip()}>"
            
            requests.post(WebhookUrl, json=PayloadData, timeout=5)
        except Exception as E:
            print(f"Webhook error: {E}")


class ColorDetector:
    
    @staticmethod
    def DetectBlackScreen(ScanRegion, ImageArray=None):
        if ImageArray is None:
            with mss.mss() as ScreenCapture:
                CaptureRegion = {
                    "top": ScanRegion["Y1"],
                    "left": ScanRegion["X1"],
                    "width": ScanRegion["X2"] - ScanRegion["X1"],
                    "height": ScanRegion["Y2"] - ScanRegion["Y1"]
                }
                Captured = ScreenCapture.grab(CaptureRegion)
                ImageArray = np.array(Captured)
        
        BlackMask = ((ImageArray[:, :, 2] == 0) & (ImageArray[:, :, 1] == 0) & (ImageArray[:, :, 0] == 0))
        TotalBlack = np.sum(BlackMask)
        TotalPixels = ImageArray.shape[0] * ImageArray.shape[1]
        BlackRatio = TotalBlack / TotalPixels
        
        return BlackRatio >= 0.5
    
    @staticmethod
    def DetectGreenish(TargetPoint, Tolerance=20):
        if not TargetPoint:
            return False
        
        try:
            with mss.mss() as ScreenCapture:
                CaptureRegion = {
                    "top": TargetPoint['y'] - Tolerance,
                    "left": TargetPoint['x'] - Tolerance,
                    "width": Tolerance * 2,
                    "height": Tolerance * 2
                }
                Captured = ScreenCapture.grab(CaptureRegion)
                ImageArray = np.array(Captured)
            
            Green = ImageArray[:, :, 1]
            Red = ImageArray[:, :, 2]
            Blue = ImageArray[:, :, 0]
            
            GreenMask = (
                (Green > Red + 20) & 
                (Green > Blue + 20) &
                (Green > 80)
            )
            
            GreenCount = np.sum(GreenMask)
            Total = ImageArray.shape[0] * ImageArray.shape[1]
            GreenRatio = GreenCount / Total
            
            return GreenRatio > 0.10
            
        except Exception as E:
            print(f"Error detecting green color: {E}")
            return False


class MegalodonSoundDetector:
    
    def __init__(self, Config):
        self.Config = Config
        
        if getattr(sys, 'frozen', False):
            AppPath = os.path.dirname(sys.executable)
        else:
            AppPath = os.path.dirname(os.path.abspath(__file__))
        
        self.SoundPath = os.path.join(AppPath, "Sounds", "Megalodon.wav")
        
        self.ModelCoefficients = [1.0902, 0.7471, 0.3720, -1.1829, -1.0433, -0.6251, -0.4898]
        self.ModelIntercept = -3.2025
        self.ScalerMeans = [0.1308, 0.1496, 0.0916, 0.0797, 0.1209, 0.1816, 0.2457]
        self.ScalerScales = [0.0775, 0.0748, 0.0200, 0.0317, 0.0344, 0.0438, 0.0960]
        self.FrequencyBands = [(20, 60), (60, 120), (120, 250), (250, 500), (500, 1000), (1000, 2000), (2000, 4000)]
        
        self.NoiseFloor = 0.02
    
    def ReduceNoise(self, AudioData):
        Magnitude = np.abs(AudioData)
        Mask = Magnitude > self.NoiseFloor
        return AudioData * Mask
    
    def CalculateSignalQuality(self, AudioData):
        SignalPower = np.mean(AudioData ** 2)
        NoisePower = np.var(AudioData)
        
        if NoisePower < 1e-10:
            return 1.0
        
        SNR = 10 * np.log10(SignalPower / NoisePower) if NoisePower > 0 else 0
        Quality = np.clip((SNR + 10) / 40, 0, 1)
        return Quality
    
    def ExtractFeatures(self, AudioData, AudioSampleRate):
        FftMag = np.abs(fft(AudioData))[:len(AudioData)//2]
        FreqArray = np.fft.fftfreq(len(AudioData), 1/AudioSampleRate)[:len(AudioData)//2]
        
        Features = []
        for LowFreq, HighFreq in self.FrequencyBands:
            Mask = (FreqArray >= LowFreq) & (FreqArray < HighFreq)
            Energy = np.sum(FftMag[Mask]) if np.any(Mask) else 0
            Features.append(Energy)
        
        TotalEnergy = sum(Features) + 1e-10
        Features = [F/TotalEnergy for F in Features]
        
        return Features
    
    def PredictProbability(self, Features):
        Scaled = [(F - M) / S for F, M, S in zip(Features, self.ScalerMeans, self.ScalerScales)]
        Logit = self.ModelIntercept + sum(C * F for C, F in zip(self.ModelCoefficients, Scaled))
        Prob = 1 / (1 + np.exp(-Logit))
        return Prob
    
    def Listen(self, TimeoutDuration=5.0):
        if not self.Config.Settings['FishingModes']['MegalodonSound']:
            return True
        
        try:
            AudioInterface = pyaudio.PyAudio()
            AudioStream = None
            
            try:
                AudioSampleRate = 44100
                RecordingDuration = 2.0
                MultipleAttempts = 2
                DeviceToUse = None
                
                SelectedIndex = self.Config.Settings['AudioDevice']['SelectedDeviceIndex']

                if SelectedIndex is not None:
                    try:
                        DeviceToUse = AudioInterface.get_device_info_by_index(SelectedIndex)
                        print(f"Using manually selected device: {DeviceToUse.get('name', 'Unknown')}")
                    except Exception as E:
                        print(f"Selected device not available: {E}")
                        print("Falling back to auto-detect")

                if DeviceToUse is None:
                    try:
                        WasapiInfo = AudioInterface.get_host_api_info_by_type(pyaudio.paWASAPI)
                        DefaultOutputIndex = WasapiInfo.get("defaultOutputDevice")
                        
                        if DefaultOutputIndex is not None and DefaultOutputIndex >= 0:
                            try:
                                DefaultDevice = AudioInterface.get_device_info_by_index(DefaultOutputIndex)
                                DefaultName = DefaultDevice.get("name", "")
                                
                                for Loopback in AudioInterface.get_loopback_device_info_generator():
                                    if DefaultName in Loopback.get("name", ""):
                                        if Loopback.get('maxInputChannels', 0) > 0:
                                            DeviceToUse = Loopback
                                            print(f"Found matching loopback device: {Loopback.get('name', 'Unknown')}")
                                            break
                            except Exception as E:
                                print(f"Error matching default output device: {E}")
                        
                        if DeviceToUse is None:
                            print("No matching loopback device found, trying any available loopback device...")
                            try:
                                for Loopback in AudioInterface.get_loopback_device_info_generator():
                                    if Loopback.get('maxInputChannels', 0) > 0:
                                        DeviceToUse = Loopback
                                        print(f"Using loopback device: {Loopback.get('name', 'Unknown')}")
                                        break
                            except Exception as E:
                                print(f"Error finding any loopback device: {E}")
                        
                    except Exception as E:
                        print(f"WASAPI not available: {E}")
                
                if DeviceToUse is None:
                    print("No loopback device found - Megalodon sound detection disabled")
                    print("Make sure you have audio output devices enabled in Windows Sound settings")
                    AudioInterface.terminate()
                    return True
                
                DeviceIndex = DeviceToUse.get("index")
                if DeviceIndex is None:
                    print("Invalid device index - Megalodon sound detection disabled")
                    AudioInterface.terminate()
                    return True
                
                AudioSampleRate = int(DeviceToUse.get('defaultSampleRate', 44100))
                if AudioSampleRate < 8000 or AudioSampleRate > 192000:
                    AudioSampleRate = 44100
                
                MaxChannels = DeviceToUse.get('maxInputChannels', 0)
                if MaxChannels < 1:
                    print("Device has no input channels - Megalodon sound detection disabled")
                    AudioInterface.terminate()
                    return True
                
                Channels = min(2, MaxChannels)
                
                FormatToUse = pyaudio.paFloat32
                IsInt16 = False
                
                try:
                    AudioStream = AudioInterface.open(
                        format=pyaudio.paFloat32,
                        channels=Channels,
                        rate=AudioSampleRate,
                        input=True,
                        frames_per_buffer=1024,
                        input_device_index=DeviceIndex
                    )
                except OSError as E:
                    print(f"paFloat32 failed, trying paInt16: {E}")
                    try:
                        AudioStream = AudioInterface.open(
                            format=pyaudio.paInt16,
                            channels=Channels,
                            rate=AudioSampleRate,
                            input=True,
                            frames_per_buffer=1024,
                            input_device_index=DeviceIndex
                        )
                        FormatToUse = pyaudio.paInt16
                        IsInt16 = True
                        print("Using paInt16 format")
                    except Exception as E2:
                        print(f"paInt16 also failed, trying single channel: {E2}")
                        try:
                            AudioStream = AudioInterface.open(
                                format=pyaudio.paFloat32,
                                channels=1,
                                rate=AudioSampleRate,
                                input=True,
                                frames_per_buffer=1024,
                                input_device_index=DeviceIndex
                            )
                            Channels = 1
                            print("Using single channel")
                        except Exception as E3:
                            print(f"All formats failed: {E3}")
                            AudioInterface.terminate()
                            return True
                
                PositiveDetections = 0
                
                for Attempt in range(MultipleAttempts):
                    Frames = []
                    
                    for _ in range(int(AudioSampleRate * RecordingDuration / 1024)):
                        try:
                            Data = AudioStream.read(1024, exception_on_overflow=False)
                            Frames.append(Data)
                        except Exception as E:
                            print(f"Error reading audio data: {E}")
                            break
                    
                    if not Frames:
                        print("No audio data captured - skipping detection")
                        continue
                    
                    if IsInt16:
                        AudioData = np.frombuffer(b''.join(Frames), dtype=np.int16).astype(np.float32) / 32768.0
                    else:
                        AudioData = np.frombuffer(b''.join(Frames), dtype=np.float32)
                    
                    if Channels == 2:
                        AudioData = AudioData.reshape(-1, 2).mean(axis=1)
                    
                    MaxAudio = np.max(np.abs(AudioData))
                    if MaxAudio < 0.01:
                        print(f"  Attempt {Attempt+1}: Too quiet (level: {MaxAudio:.4f})")
                        continue
                    
                    AudioData = AudioData / MaxAudio
                    AudioData = self.ReduceNoise(AudioData)
                    SignalQuality = self.CalculateSignalQuality(AudioData)
                    
                    WindowDuration = 0.5
                    HopDuration = 0.1
                    WindowSamples = int(WindowDuration * AudioSampleRate)
                    HopSamples = int(HopDuration * AudioSampleRate)
                    
                    MaxProb = 0
                    
                    for WindowStart in range(0, max(1, len(AudioData) - WindowSamples), HopSamples):
                        Chunk = AudioData[WindowStart:WindowStart + WindowSamples]
                        if len(Chunk) < WindowSamples:
                            continue
                        
                        Features = self.ExtractFeatures(Chunk, AudioSampleRate)
                        Prob = self.PredictProbability(Features)
                        
                        if Prob > MaxProb:
                            MaxProb = Prob
                    
                    BaseSensitivity = self.Config.Settings['FishingModes']['SoundSensitivity']
                    AdaptiveThreshold = BaseSensitivity * (0.7 + 0.3 * SignalQuality)
                    
                    print(f"  Attempt {Attempt+1}: MaxProb={MaxProb:.4f}, Threshold={AdaptiveThreshold:.4f}, Quality={SignalQuality:.2f}")
                    
                    if MaxProb > AdaptiveThreshold:
                        PositiveDetections += 1
                
                if AudioStream:
                    AudioStream.stop_stream()
                    AudioStream.close()
                AudioInterface.terminate()
                
                RequiredPositive = max(1, MultipleAttempts // 2)
                IsMegalodon = PositiveDetections >= RequiredPositive
                
                print(f"Final result: {PositiveDetections}/{MultipleAttempts} positive detections (need {RequiredPositive})")
                
                return IsMegalodon
                
            except Exception as E:
                print(f"PyAudioWPatch error: {E}")
                traceback.print_exc()
                if AudioStream:
                    try:
                        AudioStream.stop_stream()
                        AudioStream.close()
                    except:
                        pass
                AudioInterface.terminate()
                return True
                
        except Exception as E:
            print(f"Sound recognition error: {E}")
            traceback.print_exc()
            return True


class InputController:
    
    def __init__(self, Config):
        self.Config = Config
    
    def FocusRobloxWindow(self):
        def FindRobloxWindow(Handle, Windows):
            if win32gui.IsWindowVisible(Handle):
                Title = win32gui.GetWindowText(Handle)
                if "Roblox" in Title:
                    Windows.append(Handle)
        
        Windows = []
        win32gui.EnumWindows(FindRobloxWindow, Windows)
        
        if Windows:
            win32gui.SetForegroundWindow(Windows[0])
            time.sleep(self.Config.Settings['TimingDelays']['RobloxWindow']['RobloxFocusDelay'])
            return True
        return False
    
    def ClickPoint(self, Point):
        if not Point:
            return False
        
        ctypes.windll.user32.SetCursorPos(Point['x'], Point['y'])
        time.sleep(self.Config.Settings['TimingDelays']['PreCast']['PreCastAntiDetectDelay'])
        ctypes.windll.user32.mouse_event(0x0001, 0, 1, 0, 0)
        time.sleep(self.Config.Settings['TimingDelays']['PreCast']['PreCastAntiDetectDelay'])
        pyautogui.click()
        time.sleep(self.Config.Settings['TimingDelays']['PreCast']['PreCastClickDelay'])
        return True
    
    def FastClickPoint(self, Point):
        if not Point:
            return False
        
        ctypes.windll.user32.SetCursorPos(Point['x'], Point['y'])
        time.sleep(0.015)
        ctypes.windll.user32.mouse_event(0x0001, 0, 1, 0, 0)
        time.sleep(0.015)
        pyautogui.click()
        return True
    
    def PressKey(self, Key):
        keyboard.press_and_release(Key)
    
    def TypeText(self, Text):
        keyboard.write(Text)


class RegionSelectionWindow:
    
    def __init__(self, ParentWindow, InitialBounds, CompletionCallback):
        self.CompletionCallback = CompletionCallback
        self.ParentWindow = ParentWindow
        self.IsWindowClosed = False

        self.RootWindow = tk.Tk()
        self.RootWindow.attributes('-alpha', 0.85)
        self.RootWindow.attributes('-topmost', True)
        self.RootWindow.overrideredirect(True)

        self.LeftBoundary = InitialBounds["X1"]
        self.TopBoundary = InitialBounds["Y1"]
        self.RightBoundary = InitialBounds["X2"]
        self.BottomBoundary = InitialBounds["Y2"]

        Width = self.RightBoundary - self.LeftBoundary
        Height = self.BottomBoundary - self.TopBoundary

        self.RootWindow.geometry(f"{Width}x{Height}+{self.LeftBoundary}+{self.TopBoundary}")
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

        self.Canvas = tk.Canvas(
            self.RootWindow,
            bg='#1e293b',
            highlightthickness=2,
            highlightbackground='#3b82f6',
            relief='flat'
        )
        self.Canvas.pack(fill='both', expand=True, padx=2, pady=2)

        self.CreateCornerIndicators()

        self.IsDragging = False
        self.IsResizing = False
        self.ActiveEdge = None

        self.MouseDownX = 0
        self.MouseDownY = 0
        self.EdgeThreshold = 10

        self.Canvas.bind('<Button-1>', self.HandleMousePress)
        self.Canvas.bind('<B1-Motion>', self.HandleMouseDrag)
        self.Canvas.bind('<ButtonRelease-1>', self.HandleMouseRelease)
        self.Canvas.bind('<Motion>', self.HandleMouseHover)
        
        self.RootWindow.protocol("WM_DELETE_WINDOW", self.CloseWindow)
        
        self.RootWindow.mainloop()

    def CreateCornerIndicators(self):
        Size = 15
        Color = '#3b82f6'
        
        self.RootWindow.update_idletasks()
        W = self.Canvas.winfo_width()
        H = self.Canvas.winfo_height()
        
        self.Canvas.create_rectangle(0, 0, Size, Size, fill=Color, outline='')
        self.Canvas.create_rectangle(W - Size, 0, W, Size, fill=Color, outline='')
        self.Canvas.create_rectangle(0, H - Size, Size, H, fill=Color, outline='')
        self.Canvas.create_rectangle(W - Size, H - Size, W, H, fill=Color, outline='')

    def HandleMouseHover(self, Event):
        X, Y = Event.x, Event.y
        W = self.RootWindow.winfo_width()
        H = self.RootWindow.winfo_height()
        
        Left = X < self.EdgeThreshold
        Right = X > W - self.EdgeThreshold
        Top = Y < self.EdgeThreshold
        Bottom = Y > H - self.EdgeThreshold

        if Left and Top:
            self.Canvas.config(cursor='top_left_corner')
        elif Right and Top:
            self.Canvas.config(cursor='top_right_corner')
        elif Left and Bottom:
            self.Canvas.config(cursor='bottom_left_corner')
        elif Right and Bottom:
            self.Canvas.config(cursor='bottom_right_corner')
        elif Left or Right:
            self.Canvas.config(cursor='sb_h_double_arrow')
        elif Top or Bottom:
            self.Canvas.config(cursor='sb_v_double_arrow')
        else:
            self.Canvas.config(cursor='fleur')

    def HandleMousePress(self, Event):
        self.MouseDownX = Event.x
        self.MouseDownY = Event.y
        X, Y = Event.x, Event.y
        W = self.RootWindow.winfo_width()
        H = self.RootWindow.winfo_height()
        
        Left = X < self.EdgeThreshold
        Right = X > W - self.EdgeThreshold
        Top = Y < self.EdgeThreshold
        Bottom = Y > H - self.EdgeThreshold

        if Left or Right or Top or Bottom:
            self.IsResizing = True
            self.ActiveEdge = {'left': Left, 'right': Right, 'top': Top, 'bottom': Bottom}
        else:
            self.IsDragging = True

    def HandleMouseDrag(self, Event):
        if self.IsDragging:
            Dx = Event.x - self.MouseDownX
            Dy = Event.y - self.MouseDownY
            NewX = self.RootWindow.winfo_x() + Dx
            NewY = self.RootWindow.winfo_y() + Dy
            self.RootWindow.geometry(f"+{NewX}+{NewY}")
        elif self.IsResizing:
            X = self.RootWindow.winfo_x()
            Y = self.RootWindow.winfo_y()
            W = self.RootWindow.winfo_width()
            H = self.RootWindow.winfo_height()
            NewX = X
            NewY = Y
            NewW = W
            NewH = H

            if self.ActiveEdge['left']:
                Dx = Event.x - self.MouseDownX
                NewX = X + Dx
                NewW = W - Dx
            elif self.ActiveEdge['right']:
                NewW = Event.x

            if self.ActiveEdge['top']:
                Dy = Event.y - self.MouseDownY
                NewY = Y + Dy
                NewH = H - Dy
            elif self.ActiveEdge['bottom']:
                NewH = Event.y

            if NewW < 50:
                NewW = 50
                NewX = X
            if NewH < 50:
                NewH = 50
                NewY = Y

            self.RootWindow.geometry(f"{NewW}x{NewH}+{NewX}+{NewY}")

    def HandleMouseRelease(self, Event):
        self.IsDragging = False
        self.IsResizing = False
        self.ActiveEdge = None

    def CloseWindow(self):
        if self.IsWindowClosed:
            return
        self.IsWindowClosed = True
        
        try:
            Left = self.RootWindow.winfo_x()
            Top = self.RootWindow.winfo_y()
            Right = Left + self.RootWindow.winfo_width()
            Bottom = Top + self.RootWindow.winfo_height()
            Coords = {"X1": Left, "Y1": Top, "X2": Right, "Y2": Bottom}
            
            self.RootWindow.quit()
            self.RootWindow.destroy()
            
            if self.CompletionCallback:
                self.CompletionCallback(Coords)
        except Exception as E:
            print(f"Error closing area selector: {E}")


class PointSelector:
    
    def __init__(self):
        self.MouseListener = None
        self.CurrentlySettingPoint = None
    
    def StartSelection(self, PointName, Callback):
        if self.MouseListener:
            self.MouseListener.stop()
        
        self.CurrentlySettingPoint = PointName
        StartTime = time.time()
        
        def HandleClick(X, Y, Button, Pressed):
            if Pressed and self.CurrentlySettingPoint == PointName:
                if time.time() - StartTime < 0.25:
                    return True
                
                Callback(PointName, {"x": X, "y": Y})
                self.CurrentlySettingPoint = None
                return False
        
        self.MouseListener = mouse.Listener(on_click=HandleClick)
        self.MouseListener.start()
    
    def StopSelection(self):
        if self.MouseListener:
            self.MouseListener.stop()
            self.MouseListener = None


class FishingMinigameController:
    
    def __init__(self, Config, State):
        self.Config = Config
        self.State = State
    
    def WaitForBobber(self):
        StartTime = time.time()
        BlueColor = np.array([85, 170, 255])
        WhiteColor = np.array([255, 255, 255])
        DarkGrayColor = np.array([25, 25, 25])
        GreenColor = np.array([127, 255, 170])
        GreenTolerance = 15
        
        ScanArea = self.Config.Settings['ScanArea']
        MaxTimeout = self.Config.Settings['FishingControl']['Timing']['RecastTimeout']

        while self.State.IsRunning:
            Elapsed = time.time() - StartTime
            
            if Elapsed >= MaxTimeout:
                return False
            
            with mss.mss() as Capture:
                Region = {
                    "top": ScanArea["Y1"],
                    "left": ScanArea["X1"],
                    "width": ScanArea["X2"] - ScanArea["X1"],
                    "height": ScanArea["Y2"] - ScanArea["Y1"]
                }
                Screenshot = Capture.grab(Region)
                Image = np.array(Screenshot)
            
            if ColorDetector.DetectBlackScreen(ScanArea, Image):
                BlackScreenCount = BlackScreenCount + 1 if 'BlackScreenCount' in locals() else 1
                if BlackScreenCount >= 3:
                    self.State.UpdateStatus("Multiple black screens detected - recasting")
                    return False
                time.sleep(0.5)
                continue
            else:
                BlackScreenCount = 0
            
            BlueMask = ((Image[:, :, 2] == BlueColor[0]) & 
                       (Image[:, :, 1] == BlueColor[1]) & 
                       (Image[:, :, 0] == BlueColor[2]))
            WhiteMask = ((Image[:, :, 2] == WhiteColor[0]) & 
                        (Image[:, :, 1] == WhiteColor[1]) & 
                        (Image[:, :, 0] == WhiteColor[2]))
            DarkGrayMask = ((Image[:, :, 2] == DarkGrayColor[0]) & 
                           (Image[:, :, 1] == DarkGrayColor[1]) & 
                           (Image[:, :, 0] == DarkGrayColor[2]))
            GreenMask = ((np.abs(Image[:, :, 2].astype(int) - GreenColor[0]) <= GreenTolerance) & 
                        (np.abs(Image[:, :, 1].astype(int) - GreenColor[1]) <= GreenTolerance) & 
                        (np.abs(Image[:, :, 0].astype(int) - GreenColor[2]) <= GreenTolerance))
            
            BlueDetected = np.any(BlueMask)
            WhiteDetected = np.any(WhiteMask)
            DarkGrayDetected = np.any(DarkGrayMask)
            
            if BlueDetected and WhiteDetected and DarkGrayDetected:
                return True
            
            SleepTime = self.Config.Settings['FishingControl']['Detection']['ScanLoopDelay']
            if self.State.FastModeEnabled:
                SleepTime += 0.2
            time.sleep(SleepTime)

        return False
    
    def ControlMinigame(self):
        ScanArea = self.Config.Settings['ScanArea']
        
        with mss.mss() as Capture:
            Region = {
                "top": ScanArea["Y1"],
                "left": ScanArea["X1"],
                "width": ScanArea["X2"] - ScanArea["X1"],
                "height": ScanArea["Y2"] - ScanArea["Y1"]
            }
            Screenshot = Capture.grab(Region)
            Image = np.array(Screenshot)
        
        if ColorDetector.DetectBlackScreen(ScanArea, Image):
            if self.State.MousePressed:
                try:
                    pyautogui.mouseUp()
                    self.State.MousePressed = False
                except:
                    pass
            time.sleep(0.2)
            return True
        
        BlueColor = np.array([85, 170, 255])
        BlueMask = ((Image[:, :, 2] == BlueColor[0]) & 
                   (Image[:, :, 1] == BlueColor[1]) & 
                   (Image[:, :, 0] == BlueColor[2]))
        
        if not np.any(BlueMask):
            if self.State.MousePressed:
                pyautogui.mouseUp()
                self.State.MousePressed = False
            return False
        
        BlueY, BlueX = np.where(BlueMask)
        CenterX = int(np.mean(BlueX))
        
        Slice = Image[:, CenterX:CenterX+1, :]
        
        GrayColor = np.array([25, 25, 25])
        GrayMask = ((Slice[:, 0, 2] == GrayColor[0]) & 
                   (Slice[:, 0, 1] == GrayColor[1]) & 
                   (Slice[:, 0, 0] == GrayColor[2]))
        
        if not np.any(GrayMask):
            return True
        
        GrayY = np.where(GrayMask)[0]
        TopBound = GrayY[0]
        BottomBound = GrayY[-1]
        BoundedSlice = Slice[TopBound:BottomBound+1, :, :]
        
        WhiteColor = np.array([255, 255, 255])
        WhiteMask = ((BoundedSlice[:, 0, 2] == WhiteColor[0]) & 
                    (BoundedSlice[:, 0, 1] == WhiteColor[1]) & 
                    (BoundedSlice[:, 0, 0] == WhiteColor[2]))
        
        if not np.any(WhiteMask):
            if not self.State.MousePressed:
                pyautogui.mouseDown()
                self.State.MousePressed = True
            return True
        
        WhiteY = np.where(WhiteMask)[0]
        WhiteTop = WhiteY[0]
        WhiteBottom = WhiteY[-1]
        WhiteHeight = WhiteBottom - WhiteTop + 1
        WhiteCenter = (WhiteTop + WhiteBottom) // 2
        WhiteCenterScreenY = ScanArea["Y1"] + TopBound + WhiteCenter
        
        DarkGrayColor = np.array([25, 25, 25])
        DarkGrayMask = ((BoundedSlice[:, 0, 2] == DarkGrayColor[0]) & 
                       (BoundedSlice[:, 0, 1] == DarkGrayColor[1]) & 
                       (BoundedSlice[:, 0, 0] == DarkGrayColor[2]))
        
        if not np.any(DarkGrayMask):
            if not self.State.MousePressed:
                pyautogui.mouseDown()
                self.State.MousePressed = True
            return True
        
        DarkGrayY = np.where(DarkGrayMask)[0]
        MaxGap = WhiteHeight * self.Config.Settings['FishingControl']['Detection']['GapToleranceMultiplier']
        
        Groups = []
        CurrentGroup = [DarkGrayY[0]]
        
        for I in range(1, len(DarkGrayY)):
            if DarkGrayY[I] - DarkGrayY[I-1] <= MaxGap:
                CurrentGroup.append(DarkGrayY[I])
            else:
                Groups.append(CurrentGroup)
                CurrentGroup = [DarkGrayY[I]]
        
        Groups.append(CurrentGroup)
        
        LargestGroup = max(Groups, key=len)
        TargetCenter = (LargestGroup[0] + LargestGroup[-1]) // 2
        TargetCenterScreenY = ScanArea["Y1"] + TopBound + TargetCenter
        
        Kp = self.Config.Settings['FishingControl']['PdController']['Kp']
        Kd = self.Config.Settings['FishingControl']['PdController']['Kd']
        MaxClamp = self.Config.Settings['FishingControl']['PdController']['PdClamp']
        
        Error = WhiteCenterScreenY - TargetCenterScreenY
        PTerm = Kp * Error
        DTerm = 0.0
        
        CurrentTime = time.time()
        TimeDiff = CurrentTime - self.State.LastScanTime
        
        if self.State.PreviousError is not None and self.State.PreviousTargetY is not None and TimeDiff > 0.001:
            TargetVelocity = (TargetCenterScreenY - self.State.PreviousTargetY) / TimeDiff
            ErrorDecreasing = abs(Error) < abs(self.State.PreviousError)
            TargetMovingToward = (TargetVelocity > 0 and Error > 0) or (TargetVelocity < 0 and Error < 0)
            
            if ErrorDecreasing and TargetMovingToward:
                Damping = self.Config.Settings['FishingControl']['PdController']['PdApproachingDamping']
                DTerm = -Kd * Damping * TargetVelocity
            else:
                Damping = self.Config.Settings['FishingControl']['PdController']['PdChasingDamping']
                DTerm = -Kd * Damping * TargetVelocity
        
        ControlSignal = PTerm + DTerm
        ControlSignal = max(-MaxClamp, min(MaxClamp, ControlSignal))
        ShouldHold = ControlSignal <= 0
        
        if ShouldHold and not self.State.MousePressed:
            pyautogui.mouseDown()
            self.State.MousePressed = True
            self.State.LastStateChangeTime = CurrentTime
            self.State.LastInputResendTime = CurrentTime
        elif not ShouldHold and self.State.MousePressed:
            pyautogui.mouseUp()
            self.State.MousePressed = False
            self.State.LastStateChangeTime = CurrentTime
            self.State.LastInputResendTime = CurrentTime
        else:
            ResendInterval = self.Config.Settings['FishingControl']['Timing']['StateResendInterval']
            if CurrentTime - self.State.LastInputResendTime >= ResendInterval:
                if self.State.MousePressed:
                    pyautogui.mouseDown()
                else:
                    pyautogui.mouseUp()
                self.State.LastInputResendTime = CurrentTime
        
        self.State.PreviousError = Error
        self.State.PreviousTargetY = TargetCenterScreenY
        self.State.LastScanTime = CurrentTime
        
        return True


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

        try:
            kernel32 = ctypes.windll.kernel32
            PROCESS_SET_INFORMATION = 0x0200
            Pid = os.getpid()
            Handle = kernel32.OpenProcess(PROCESS_SET_INFORMATION, False, Pid)
            
            if Handle:
                Result = kernel32.SetPriorityClass(Handle, 0x00000100)
                kernel32.CloseHandle(Handle)
                
                if not Result:
                    ErrorCode = ctypes.get_last_error()
                    print(f"Failed to set priority. Error: {ErrorCode}")
            else:
                print("Failed to open process handle")
                
        except Exception as E:
            print(f"Could not set process priority: {E}")

        if getattr(sys, 'frozen', False):
            AppPath = os.path.dirname(sys.executable)
        else:
            AppPath = os.path.dirname(os.path.abspath(__file__))

        ConfigPath = os.path.join(AppPath, "Auto Fish Settings.json")
        
        self.Config = ConfigurationManager(ConfigPath)
        self.Config.LoadFromDisk()
        
        self.State = MacroStateManager()
        
        self.OcrManager = OCRManager()
        self.FruitDetector = DevilFruitDetector(self.OcrManager, self.Config)
        self.Notifier = WebhookNotifier(self.Config, self.State)
        self.SoundDetector = MegalodonSoundDetector(self.Config)
        self.InputController = InputController(self.Config)
        self.MinigameController = FishingMinigameController(self.Config, self.State)
        self.PointSelector = PointSelector()
        self.IsAdmin = self.CheckAdminStatus()
        
        self.RegionSelectorActive = False
        self.ActiveRegionSelector = None
        self.FastMode = False
        
        self.CurrentlyRebindingHotkey = None

        self.SpawnDetectionRunning = False
        self.LastSpawnCheck = time.time()
        
        self.RegisterHotkeys()

        threading.Thread(target=self.SpawnDetectionLoop, daemon=True).start()

    def SpawnDetectionLoop(self):
        while True:
            try:
                if not self.Config.Settings['SpawnDetection']['EnableSpawnDetection']:
                    time.sleep(1)
                    continue
                
                CurrentTime = time.time()
                if CurrentTime - self.LastSpawnCheck < self.Config.Settings['SpawnDetection']['ScanInterval']:
                    time.sleep(0.5)
                    continue
                
                self.LastSpawnCheck = CurrentTime
                
                DetectedFruit = self.FruitDetector.DetectSpawn()
                
                if DetectedFruit:
                    LogOpts = self.Config.Settings['SpawnDetection']
                    if LogOpts['LogSpawns'] and self.Config.Settings['DevilFruitStorage']['WebhookUrl']:
                        Message = f"Devil Fruit Spawned: {DetectedFruit}"
                        
                        PingUser = LogOpts['PingSpawns']
                        
                        EmbedData = {
                            "title": "🍎 Devil Fruit Spawn Detected",
                            "description": f"**{Message}**",
                            "color": 0xbf40bf,
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

                        DiscordUserId = self.Config.Settings['LoggingOptions']['DiscordUserId']
                        if PingUser and DiscordUserId and DiscordUserId.strip():
                            PayloadData["content"] = f"<@{DiscordUserId.strip()}>"
                        
                        try:
                            requests.post(self.Config.Settings['DevilFruitStorage']['WebhookUrl'], json=PayloadData, timeout=5)
                        except Exception as E:
                            print(f"Webhook error: {E}")
                    
                    time.sleep(5)
                
            except Exception as E:
                print(f"Spawn detection loop error: {E}")
                traceback.print_exc()
                time.sleep(1)
    
    def RegisterHotkeys(self):
        try:
            Hotkeys = self.Config.Settings['Hotkeys']
            keyboard.add_hotkey(Hotkeys['StartStop'], self.ToggleMacro)
            keyboard.add_hotkey(Hotkeys['Exit'], self.TerminateApp)
        except Exception as E:
            print(f"Error setting up hotkeys: {E}")
    
    def ToggleMacro(self):
        self.State.IsRunning = not self.State.IsRunning
        
        if self.Config.Settings['RDPSettings']['AutoDetectRDP']:
            self.State.RDPDetected, self.State.RDPSessionState, self.State.RDPSessionId, RDPSessionName = RDPDetector.DetectRDPSession()
        
        if self.State.ClientId not in self.State.ClientStats:
            self.State.ClientStats[self.State.ClientId] = {
                "fish_caught": 0,
                "start_time": None,
                "last_seen": time.time(),
                "rdp_detected": self.State.RDPDetected,
                "rdp_state": self.State.RDPSessionState
            }
        
        self.State.ClientStats[self.State.ClientId]["last_seen"] = time.time()
        self.State.ClientStats[self.State.ClientId]["rdp_detected"] = self.State.RDPDetected
        self.State.ClientStats[self.State.ClientId]["rdp_state"] = self.State.RDPSessionState
        
        if self.State.IsRunning:
            self.State.UpdateStatus("Starting macro...")
            self.State.SessionStartTime = time.time()
            self.State.ClientStats[self.State.ClientId]["start_time"] = time.time()
            self.State.ClientStats[self.State.ClientId]["fish_caught"] = self.State.TotalFishCaught
            self.State.RobloxWindowFocused = False
            self.State.ConsecutiveRecastTimeouts = 0
            self.State.LastPeriodicStatsTime = time.time()
            self.State.FishAtLastStats = self.State.TotalFishCaught
            
            if self.Config.Settings['DevilFruitStorage']['WebhookUrl'] and self.Config.Settings['LoggingOptions']['LogMacroState']:
                self.Notifier.SendNotification("Macro started.")
            
            threading.Thread(target=self.ExecuteMacroLoop, daemon=True).start()
        else:
            self.State.UpdateStatus("Stopping macro...")
            if self.State.SessionStartTime:
                self.State.CumulativeUptime += time.time() - self.State.SessionStartTime
                self.State.SessionStartTime = None
            if self.State.MousePressed:
                pyautogui.mouseUp()
                self.State.MousePressed = False
            
            if self.Config.Settings['DevilFruitStorage']['WebhookUrl'] and self.Config.Settings['LoggingOptions']['LogMacroState']:
                self.Notifier.SendNotification(f"Macro stopped. Fish this session: {self.State.TotalFishCaught} | Devil Fruits: {self.State.TotalDevilFruits}")
            
            self.State.UpdateStatus("Idle")
    
    def ModifyScanArea(self):
        if self.RegionSelectorActive:
            if self.ActiveRegionSelector:
                try:
                    self.ActiveRegionSelector.RootWindow.after(10, self.ActiveRegionSelector.CloseWindow)
                except:
                    pass
            return
        
        self.RegionSelectorActive = True
        
        def RunSelector():
            try:
                self.ActiveRegionSelector = RegionSelectionWindow(None, self.Config.Settings['ScanArea'], self.HandleRegionComplete)
            finally:
                self.RegionSelectorActive = False
                self.ActiveRegionSelector = None
        
        threading.Thread(target=RunSelector, daemon=True).start()

    def HandleRegionComplete(self, Coords):
        self.Config.Settings['ScanArea'] = Coords
        self.Config.SaveToDisk()
        self.ActiveRegionSelector = None
        self.RegionSelectorActive = False
    
    def TerminateApp(self):
        os._exit(0)
    
    def CheckAdminStatus(self):
        try:
            return ctypes.windll.shell32.IsUserAnAdmin() != 0
        except:
            return False

    def CheckPeriodicStats(self):
        LogOpts = self.Config.Settings['LoggingOptions']
        if not self.Config.Settings['DevilFruitStorage']['WebhookUrl'] or not LogOpts['LogPeriodicStats'] or self.State.LastPeriodicStatsTime is None:
            return
        
        IntervalSeconds = LogOpts['PeriodicStatsIntervalMinutes'] * 60
        if (time.time() - self.State.LastPeriodicStatsTime) < IntervalSeconds:
            return
        
        FishThisInterval = self.State.TotalFishCaught - self.State.FishAtLastStats
        FishPerMin = FishThisInterval / LogOpts['PeriodicStatsIntervalMinutes'] if LogOpts['PeriodicStatsIntervalMinutes'] > 0 else 0
        
        Elapsed = self.State.GetElapsedTime()
        H = int(Elapsed // 3600)
        M = int((Elapsed % 3600) // 60)
        S = int(Elapsed % 60)
        
        OverallFPH = self.State.GetFishPerHour()
        
        self.Notifier.SendNotification(
            f"Stats (last {LogOpts['PeriodicStatsIntervalMinutes']}m)\n"
            f"Caught: {FishThisInterval} ({FishPerMin:.1f}/min)\n"
            f"Total: {self.State.TotalFishCaught} | Uptime: {H}:{M:02d}:{S:02d}\n"
            f"Rate: {OverallFPH:.1f}/hr | Timeouts: {self.State.TotalRecastTimeouts}\n"
            f"Devil Fruits: {self.State.TotalDevilFruits}"
        )
        
        self.State.LastPeriodicStatsTime = time.time()
        self.State.FishAtLastStats = self.State.TotalFishCaught
    
    def ExecuteMacroLoop(self):
        LastActivity = time.time()
        ErrorCount = 0
        MaxConsecutiveErrors = 5
        
        while self.State.IsRunning:
            try:
                LastActivity = time.time()
                
                if self.Config.Settings['RDPSettings']['AutoDetectRDP']:
                    self.State.RDPDetected, self.State.RDPSessionState, self.State.RDPSessionId, RDPSessionName = RDPDetector.DetectRDPSession()
                    
                    if self.State.ClientId in self.State.ClientStats:
                        self.State.ClientStats[self.State.ClientId]['rdp_detected'] = self.State.RDPDetected
                        self.State.ClientStats[self.State.ClientId]['rdp_state'] = self.State.RDPSessionState

                self.State.UpdateStatus("Starting new fishing cycle")
                LastActivity = time.time()
                self.State.PreviousError = None
                self.State.PreviousTargetY = None
                self.State.LastScanTime = time.time()
                
                if self.State.MousePressed:
                    self.State.UpdateStatus("Releasing mouse from previous cycle")
                    pyautogui.mouseUp()
                    self.State.MousePressed = False
                
                if not self.State.IsRunning:
                    break
                
                self.State.UpdateStatus("Beginning pre-cast sequence")
                if not self.ExecutePreCast():
                    self.State.UpdateStatus("Pre-cast sequence failed - restarting cycle")
                    continue
                
                self.State.UpdateStatus("Pre-cast sequence complete")
                
                if not self.State.IsRunning:
                    break

                self.State.UpdateStatus("Casting fishing line")
                if not self.ExecuteCastSequence():
                    self.State.UpdateStatus("Cast failed - restarting cycle")
                    continue
                
                self.State.UpdateStatus("Waiting for bobber to appear")
                if not self.MinigameController.WaitForBobber():
                    self.State.UpdateStatus("Bobber timeout - recasting")
                    self.State.HandleRecastTimeout()
                    
                    LogOpts = self.Config.Settings['LoggingOptions']
                    if self.Config.Settings['DevilFruitStorage']['WebhookUrl'] and LogOpts['LogRecastTimeouts']:
                        if self.State.ConsecutiveRecastTimeouts == 3:
                            self.Notifier.SendNotification(f"3 consecutive recast timeouts ({self.Config.Settings['FishingControl']['Timing']['RecastTimeout']}s). Total: {self.State.TotalRecastTimeouts}")
                        elif self.State.ConsecutiveRecastTimeouts == 10:
                            self.Notifier.SendNotification(f"10 consecutive recast timeouts — macro may be stuck. Total: {self.State.TotalRecastTimeouts}")
                        elif self.State.ConsecutiveRecastTimeouts > 10 and self.State.ConsecutiveRecastTimeouts % 10 == 0:
                            self.Notifier.SendNotification(f"{self.State.ConsecutiveRecastTimeouts} consecutive timeouts. Total: {self.State.TotalRecastTimeouts}")
                    continue

                self.State.ResetConsecutiveTimeouts()
                self.State.UpdateStatus("Bobber ready - starting minigame")
                
                if self.Config.Settings['FishingModes']['MegalodonSound']:
                    SoundDetectionComplete = threading.Event()
                    IsMegalodon = [True]
                    
                    def CheckSound():
                        if not self.SoundDetector.Listen():
                            IsMegalodon[0] = False
                        SoundDetectionComplete.set()
                    
                    SoundThread = threading.Thread(target=CheckSound, daemon=True)
                    SoundThread.start()
                    
                    self.State.UpdateStatus("Entering minigame control loop (checking for megalodon)")
                    while self.State.IsRunning:
                        if not self.MinigameController.ControlMinigame():
                            self.State.UpdateStatus("Minigame control loop ended")
                            break
                        
                        if SoundDetectionComplete.is_set():
                            if not IsMegalodon[0]:
                                self.State.UpdateStatus("Not megalodon - recasting")
                                if self.State.MousePressed:
                                    pyautogui.mouseUp()
                                    self.State.MousePressed = False
                                break
                            else:
                                self.State.UpdateStatus("Megalodon detected - continuing minigame")
                                SoundDetectionComplete.clear()
                    
                    if not IsMegalodon[0]:
                        continue
                else:
                    self.State.UpdateStatus("Entering minigame control loop")
                    while self.State.IsRunning:
                        if not self.MinigameController.ControlMinigame():
                            self.State.UpdateStatus("Minigame control loop ended")
                            break
                
                if self.State.IsRunning:
                    self.State.UpdateStatus("Fish caught successfully!")
                    self.State.IncrementFishCount()
                    self.State.UpdateStatus(f"Total fish: {self.State.TotalFishCaught}")
                    self.CheckPeriodicStats()
                    
                    FishEndDelay = self.Config.Settings['FishingControl']['Timing']['FishEndDelay']
                    self.State.UpdateStatus(f"Waiting {FishEndDelay}s before next cast")
                    Remaining = FishEndDelay
                    while Remaining > 0 and self.State.IsRunning:
                        Increment = min(0.1, Remaining)
                        time.sleep(Increment)
                        Remaining -= Increment
            
            except Exception as E:
                ErrorCount += 1
                self.State.UpdateStatus(f"Error: {str(E)[:30]}")
                print(f"Error in Main: {E}")
                print(f"Error occurred after {time.time() - LastActivity:.1f}s of inactivity")
                print(f"Last status: {self.State.CurrentStatus}")
                traceback.print_exc()
                
                LogOpts = self.Config.Settings['LoggingOptions']
                if self.Config.Settings['DevilFruitStorage']['WebhookUrl'] and LogOpts['LogErrors']:
                    self.Notifier.SendNotification(f"Macro error (#{ErrorCount}): {E}")
                
                if self.State.MousePressed:
                    try:
                        pyautogui.mouseUp()
                        self.State.MousePressed = False
                    except:
                        pass
                
                if ErrorCount >= MaxConsecutiveErrors:
                    self.State.UpdateStatus(f"Too many errors ({MaxConsecutiveErrors}) - stopping")
                    if self.Config.Settings['DevilFruitStorage']['WebhookUrl'] and LogOpts['LogErrors']:
                        self.Notifier.SendNotification(f"Macro stopped after {MaxConsecutiveErrors} consecutive errors")
                    break
                
                self.State.UpdateStatus(f"Recovering from error... ({ErrorCount}/{MaxConsecutiveErrors})")
                time.sleep(2)
                self.State.RobloxWindowFocused = False
                continue
        
        if self.State.SessionStartTime:
            self.State.CumulativeUptime += time.time() - self.State.SessionStartTime
            self.State.SessionStartTime = None
        
        if self.State.MousePressed:
            try:
                pyautogui.mouseUp()
                self.State.MousePressed = False
            except:
                pass
        
        self.State.UpdateStatus("Idle")

    def ExecutePreCast(self):
        if not self.State.RobloxWindowFocused:
            self.State.UpdateStatus("Focusing Roblox window")
            FocusRetries = 0
            MaxFocusRetries = 3
            
            while FocusRetries < MaxFocusRetries and self.State.IsRunning:
                if self.InputController.FocusRobloxWindow():
                    self.State.RobloxWindowFocused = True
                    self.State.UpdateStatus("Window focused")
                    time.sleep(self.Config.Settings['TimingDelays']['RobloxWindow']['RobloxPostFocusDelay'])
                    break
                else:
                    FocusRetries += 1
                    self.State.UpdateStatus(f"Failed to focus window (attempt {FocusRetries}/{MaxFocusRetries})")
                    time.sleep(1)
            
            if not self.State.RobloxWindowFocused:
                self.State.UpdateStatus("Could not focus Roblox window - will retry next cycle")
                return False

        if not self.State.IsRunning:
            return False

        if self.Config.Settings['AutomationFeatures']['AutoCraftBait']:
            Points = self.Config.Settings['ClickPoints']
            if all([Points['CraftLeft'], Points['CraftMiddle'], Points['CraftButton'], Points['CloseMenu'], Points['AddRecipe'], Points['TopRecipe'], len(self.Config.Settings['BaitRecipes']) > 0]):
                if self.State.FishSinceLastCraft >= self.Config.Settings['AutomationFrequencies']['FishCountPerCraft']:
                    self.ExecuteCraftingCycle()
                    if not self.State.IsRunning:
                        return False
        
        if self.Config.Settings['AutomationFeatures']['AutoBuyBait']:
            Points = self.Config.Settings['ClickPoints']
            if Points['ShopLeft'] and Points['ShopCenter'] and Points['ShopRight']:
                if self.State.BaitPurchaseCounter == 0 or self.State.BaitPurchaseCounter >= self.Config.Settings['AutomationFrequencies']['LoopsPerPurchase']:
                    self.ExecuteBaitPurchase()
                    if not self.State.IsRunning:
                        return False
                    self.State.BaitPurchaseCounter = 1
                else:
                    self.State.UpdateStatus(f"Skipping bait purchase ({self.State.BaitPurchaseCounter}/{self.Config.Settings['AutomationFrequencies']['LoopsPerPurchase']})")
                    self.State.BaitPurchaseCounter += 1

        if not self.State.IsRunning:
            return False
        
        if self.Config.Settings['AutomationFeatures']['AutoStoreFruit']:
            if self.State.FruitStorageCounter == 0 or self.State.FruitStorageCounter >= self.Config.Settings['AutomationFrequencies']['LoopsPerStore']:
                self.ExecuteFruitStorage()
                if not self.State.IsRunning:
                    return False
                self.State.FruitStorageCounter = 1
            else:
                self.State.FruitStorageCounter += 1

        self.State.UpdateStatus("Pre-cast complete")
        return True
    
    def ExecuteCraftingCycle(self):
        self.State.UpdateStatus("Starting crafting cycle")
        
        Delays = self.Config.Settings['TimingDelays']['Crafting']
        time.sleep(Delays['CraftMenuOpenDelay'])
        
        if Delays['MoveDuration'] < 0:
            keyboard.press_and_release('shift')
            time.sleep(0.1)
            if not self.State.IsRunning:
                return
            
            keyboard.press('d')
            time.sleep(abs(Delays['MoveDuration']))
            keyboard.release('d')
            time.sleep(self.Config.Settings['TimingDelays']['DevilFruitStorage']['StoreFruitShiftDelay'])
            if not self.State.IsRunning:
                return
            
            keyboard.press_and_release('shift')
            time.sleep(0.1)
            if not self.State.IsRunning:
                return
        
        keyboard.press_and_release(self.Config.Settings['InventoryHotkeys']['Alternate'])
        time.sleep(self.Config.Settings['TimingDelays']['Inventory']['RodSelectDelay'])

        keyboard.press_and_release(self.Config.Settings['InventoryHotkeys']['Rod'])
        time.sleep(self.Config.Settings['TimingDelays']['Inventory']['RodSelectDelay'])

        keyboard.press_and_release(self.Config.Settings['InventoryHotkeys']['Rod'])
        time.sleep(self.Config.Settings['TimingDelays']['Inventory']['RodSelectDelay'])
        
        self.State.UpdateStatus("Opening craft menu")
        keyboard.press_and_release('t')
        time.sleep(Delays['CraftMenuOpenDelay'])
        if not self.State.IsRunning:
            return
        
        Points = self.Config.Settings['ClickPoints']
        self.InputController.ClickPoint(Points['CraftLeft'])
        if not self.State.IsRunning:
            return
        
        self.InputController.ClickPoint(Points['CraftMiddle'])
        if not self.State.IsRunning:
            return
        
        for RecipeIndex in range(len(self.Config.Settings['BaitRecipes'])):
            self.State.UpdateStatus(f"Crafting recipe {RecipeIndex+1}/{len(self.Config.Settings['BaitRecipes'])}")
            Recipe = self.Config.Settings['BaitRecipes'][RecipeIndex]
            
            if not Recipe.get('BaitRecipePoint'):
                continue
            
            self.InputController.ClickPoint(Recipe['BaitRecipePoint'])
            if not self.State.IsRunning:
                return
            
            RecipeCycle = Recipe.get('SwitchFishCycle', 5)
            SelectMaxPoint = Recipe.get('SelectMaxPoint')
            
            for FishIter in range(RecipeCycle):
                if not self.State.IsRunning:
                    return
                
                self.InputController.ClickPoint(Points['AddRecipe'])
                if not self.State.IsRunning:
                    return
                
                self.InputController.ClickPoint(Points['TopRecipe'])
                if not self.State.IsRunning:
                    return
                
                self.State.UpdateStatus(f"Opening craft dialog {FishIter+1}/{RecipeCycle}")
                self.InputController.ClickPoint(Points['CraftButton'])
                time.sleep(Delays['CraftClickDelay'])
                if not self.State.IsRunning:
                    return
                
                if SelectMaxPoint:
                    self.State.UpdateStatus(f"Clicking Select Max for recipe {RecipeIndex+1}")
                    self.InputController.ClickPoint(SelectMaxPoint)
                    time.sleep(Delays['CraftClickDelay'])
                    if not self.State.IsRunning:
                        return
                    
                if Points['CraftConfirm']:
                    self.InputController.ClickPoint(Points['CraftConfirm'])

                self.State.UpdateStatus(f"Confirming craft batch {FishIter+1}/{RecipeCycle}")
                time.sleep(Delays['CraftClickDelay'])     

        self.State.UpdateStatus("Closing craft menu")
        self.InputController.ClickPoint(Points['CloseMenu'])
        if not self.State.IsRunning:
            return

        if Delays['MoveDuration'] < 0: 
            keyboard.press_and_release('shift')
            time.sleep(0.1)
            if not self.State.IsRunning:
                return
            
            keyboard.press('a')
            time.sleep(abs(Delays['MoveDuration']))
            keyboard.release('a')
            time.sleep(1.0)
            if not self.State.IsRunning:
                return
            
            keyboard.press_and_release('shift')
            time.sleep(0.1)
            if not self.State.IsRunning:
                return
        
        self.State.FishSinceLastCraft = 0
        self.State.UpdateStatus("Crafting complete")

        LogOpts = self.Config.Settings['LoggingOptions']
        if self.Config.Settings['DevilFruitStorage']['WebhookUrl'] and LogOpts['LogGeneralUpdates']:
            self.Notifier.SendNotification("Crafting cycle complete.")
    
    def ExecuteBaitPurchase(self):
        self.State.UpdateStatus("Opening Shop")
        keyboard.press_and_release('e')
        time.sleep(self.Config.Settings['TimingDelays']['PreCast']['SetPrecastEDelay'])
        if not self.State.IsRunning:
            return
        
        Points = self.Config.Settings['ClickPoints']
        
        self.State.UpdateStatus("Clicking shop left button")
        self.InputController.ClickPoint(Points['ShopLeft'])
        if not self.State.IsRunning:
            return
        
        self.State.UpdateStatus("Clicking shop center button")
        self.InputController.ClickPoint(Points['ShopCenter'])
        if not self.State.IsRunning:
            return
        
        Quantity = self.Config.Settings['AutomationFrequencies']['LoopsPerPurchase']
        self.State.UpdateStatus(f"Entering quantity: {Quantity}")
        keyboard.write(str(Quantity))
        time.sleep(self.Config.Settings['TimingDelays']['PreCast']['PreCastTypeDelay'])
        if not self.State.IsRunning:
            return
        
        self.State.UpdateStatus("Confirming left button")
        self.InputController.ClickPoint(Points['ShopLeft'])
        if not self.State.IsRunning:
            return
        
        self.State.UpdateStatus("Clicking shop right button")
        self.InputController.ClickPoint(Points['ShopRight'])
        if not self.State.IsRunning:
            return
        
        self.State.UpdateStatus("Final shop center click")
        self.InputController.ClickPoint(Points['ShopCenter'])
        
        self.State.UpdateStatus("Bait purchased successfully")
    
    def ExecuteFruitStorage(self):
        self.State.UpdateStatus("Storing Devil Fruit")
        
        Points = self.Config.Settings['ClickPoints']
        
        if self.Config.Settings['DevilFruitStorage']['StoreToBackpack'] and Points['DevilFruitLocation']:
            self.State.UpdateStatus("Opening inventory")
            keyboard.press_and_release('`')
            time.sleep(self.Config.Settings['TimingDelays']['DevilFruitStorage']['StoreFruitHotkeyDelay'])
            if not self.State.IsRunning:
                return
            
            self.State.UpdateStatus("Clicking fruit location")
            self.InputController.ClickPoint(Points['DevilFruitLocation'])
            time.sleep(self.Config.Settings['TimingDelays']['DevilFruitStorage']['StoreFruitClickDelay'])
            if not self.State.IsRunning:
                return
            
            if Points['StoreFruit']:
                self.State.UpdateStatus("Checking fruit status")
                InitGreen = ColorDetector.DetectGreenish(Points['StoreFruit'])
                    
                self.InputController.ClickPoint(Points['StoreFruit'])
                if not self.State.IsRunning:
                    return

                FruitLoc = Points['DevilFruitLocation']
                ctypes.windll.user32.SetCursorPos(FruitLoc['x'], FruitLoc['y'])
                time.sleep(0.1)
                if not self.State.IsRunning:
                    return

                win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
                time.sleep(0.1)
                if not self.State.IsRunning:
                    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
                    return

                StartY = FruitLoc['y']
                TargetY = StartY - 150
                Steps = 100
                Duration = 2.0

                for I in range(Steps + 1):
                    Progress = I / Steps
                    CurrentY = int(StartY + (Progress * -150))
                    win32api.SetCursorPos(FruitLoc['x'], CurrentY)
                    time.sleep(Duration / Steps)
                    
                    if not self.State.IsRunning:
                        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
                        return

                time.sleep(0.1)

                win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
                time.sleep(0.15)
                
                keyboard.press_and_release('`')
                time.sleep(self.Config.Settings['TimingDelays']['DevilFruitStorage']['StoreFruitHotkeyDelay'])
                
        elif Points['StoreFruit']:
            for Slot in self.Config.Settings['InventoryHotkeys']['DevilFruits']:
                keyboard.press_and_release(self.Config.Settings['InventoryHotkeys']['Alternate'])
                time.sleep(self.Config.Settings['TimingDelays']['Inventory']['RodSelectDelay'])

                keyboard.press_and_release(self.Config.Settings['InventoryHotkeys']['Rod'])
                time.sleep(self.Config.Settings['TimingDelays']['Inventory']['RodSelectDelay'])

                keyboard.press_and_release(self.Config.Settings['InventoryHotkeys']['Rod'])
                time.sleep(self.Config.Settings['TimingDelays']['Inventory']['RodSelectDelay'])

                keyboard.press_and_release(Slot)
                time.sleep(self.Config.Settings['TimingDelays']['DevilFruitStorage']['StoreFruitHotkeyDelay'])
                if not self.State.IsRunning:
                    return

                self.State.UpdateStatus("Checking fruit status")
                InitGreen = False
                if ColorDetector.DetectGreenish(Points['StoreFruit']):
                    InitGreen = True
                        
                self.InputController.ClickPoint(Points['StoreFruit'])
                if not self.State.IsRunning:
                    return
                
                if InitGreen:
                    time.sleep(self.Config.Settings['TimingDelays']['DevilFruitStorage']['StoreFruitClickDelay'] + 0.5)
                    if self.Config.Settings['DevilFruitStorage']['WebhookUrl'] and not ColorDetector.DetectGreenish(Points['StoreFruit']):
                        DetectedFruit = None
                        if self.OcrManager.Enabled:
                            RawDetection = self.FruitDetector.DetectNewItem()
                            if RawDetection:
                                ClosestMatch = self.FruitDetector.GetClosestFruit(RawDetection, Cutoff=0.6)
                                if ClosestMatch:
                                    DetectedFruit = ClosestMatch

                        if DetectedFruit:
                            self.State.UpdateStatus("Fruit stored successfully")
                            self.State.IncrementDevilFruitCount()
                            self.Notifier.SendNotification(f"Devil Fruit {DetectedFruit} stored successfully!")
                        else:
                            self.State.UpdateStatus("Fruit stored successfully")
                            self.State.IncrementDevilFruitCount()
                            self.Notifier.SendNotification("Devil Fruit stored successfully!")
                    else:
                        if self.Config.Settings['DevilFruitStorage']['WebhookUrl']:
                            self.State.UpdateStatus("Fruit storage failed")
                            self.State.IncrementDevilFruitCount()
                            self.Notifier.SendNotification("Devil Fruit could not be stored.")

                        if self.Config.Settings['AutomationFeatures']['AutoBuyBait']:
                            keyboard.press_and_release('shift')
                            time.sleep(self.Config.Settings['TimingDelays']['DevilFruitStorage']['StoreFruitShiftDelay'])
                            if not self.State.IsRunning:
                                return
                        
                        keyboard.press_and_release('backspace')
                        time.sleep(self.Config.Settings['TimingDelays']['DevilFruitStorage']['StoreFruitBackspaceDelay'])
                        if not self.State.IsRunning:
                            return

                        if self.Config.Settings['AutomationFeatures']['AutoBuyBait']:
                            keyboard.press_and_release('shift')
    
    def ExecuteCastSequence(self):
        Points = self.Config.Settings['ClickPoints']
        
        if not Points['Water']:
            return False
        
        self.State.UpdateStatus("Switching to alternate slot")
        keyboard.press_and_release(self.Config.Settings['InventoryHotkeys']['Alternate'])
        time.sleep(self.Config.Settings['TimingDelays']['Inventory']['RodSelectDelay'])
        
        if not self.State.IsRunning:
            return False
        
        self.State.UpdateStatus("Switching to fishing rod")
        keyboard.press_and_release(self.Config.Settings['InventoryHotkeys']['Rod'])
        time.sleep(self.Config.Settings['TimingDelays']['Inventory']['RodSelectDelay'])
        
        if not self.State.IsRunning:
            return False
        
        if self.Config.Settings['AutomationFeatures']['AutoSelectTopBait'] and Points['Bait']:
            self.State.UpdateStatus("Selecting top bait")
            self.InputController.ClickPoint(Points['Bait'])
            time.sleep(self.Config.Settings['TimingDelays']['Inventory']['AutoSelectBaitDelay'])
        
        if not self.State.IsRunning:
            return False
        
        self.State.UpdateStatus("Casting fishing line")
        ctypes.windll.user32.SetCursorPos(Points['Water']['x'], Points['Water']['y'])
        time.sleep(self.Config.Settings['TimingDelays']['AntiDetection']['CursorAntiDetectDelay'])
        ctypes.windll.user32.mouse_event(0x0001, 0, 1, 0, 0)
        
        if not self.State.IsRunning:
            return False
        
        pyautogui.mouseDown()
        time.sleep(self.Config.Settings['FishingControl']['Timing']['CastHoldDuration'])
        
        if not self.State.IsRunning:
            pyautogui.mouseUp()
            return False
        
        pyautogui.mouseUp()
        return True
    
    def GetStateForAPI(self, clientId=None):
        CurrentTime = time.time()
        ActiveSessions = [
            {
                'client_id': Cid,
                'rdp_detected': Stats.get('rdp_detected', False),
                'rdp_state': Stats.get('rdp_state', 'unknown'),
                'session_id': self.State.RDPSessionId if Cid == self.State.ClientId else -1,
                'last_updated': Stats.get('last_seen', 0)
            }

            for Cid, Stats in self.State.ClientStats.items()
            if Cid and Cid != 'unknown' and (CurrentTime - Stats.get('last_seen', 0)) < 30
        ]
        
        if clientId is None:
            clientId = self.State.ClientId
        
        return {
            "clientId": self.State.ClientId,
            "activeSessions": ActiveSessions,
            "storeToBackpack": self.Config.Settings['DevilFruitStorage']['StoreToBackpack'],
            "devilFruitLocationPoint": self.Config.Settings['ClickPoints']['DevilFruitLocation'],
            "loopsPerStore": self.Config.Settings['AutomationFrequencies']['LoopsPerStore'],
            "isRunning": self.State.IsRunning,
            "fishCaught": self.State.TotalFishCaught,
            "devilFruitsCaught": self.State.TotalDevilFruits,
            "timeElapsed": self.State.GetFormattedElapsedTime(),
            "moveDuration": self.Config.Settings['TimingDelays']['Crafting']['MoveDuration'],
            "fishPerHour": round(self.State.GetFishPerHour(), 1),
            "waterPoint": self.Config.Settings['ClickPoints']['Water'],
            "leftPoint": self.Config.Settings['ClickPoints']['ShopLeft'],
            "middlePoint": self.Config.Settings['ClickPoints']['ShopCenter'],
            "rightPoint": self.Config.Settings['ClickPoints']['ShopRight'],
            "storeFruitPoint": self.Config.Settings['ClickPoints']['StoreFruit'],
            "baitPoint": self.Config.Settings['ClickPoints']['Bait'],
            "topRecipePoint": self.Config.Settings['ClickPoints']['TopRecipe'],
            "addRecipePoint": self.Config.Settings['ClickPoints']['AddRecipe'],
            "craftConfirmPoint": self.Config.Settings['ClickPoints']['CraftConfirm'],
            "hotkeys": self.Config.Settings['Hotkeys'],
            "rodHotkey": self.Config.Settings['InventoryHotkeys']['Rod'],
            "anythingElseHotkey": self.Config.Settings['InventoryHotkeys']['Alternate'],
            "devilFruitHotkeys": self.Config.Settings['InventoryHotkeys']['DevilFruits'],
            "alwaysOnTop": self.Config.Settings['WindowSettings']['AlwaysOnTop'],
            "showDebugOverlay": self.Config.Settings['WindowSettings']['ShowDebugOverlay'],
            "autoBuyCommonBait": self.Config.Settings['AutomationFeatures']['AutoBuyBait'],
            "autoStoreDevilFruit": self.Config.Settings['AutomationFeatures']['AutoStoreFruit'],
            "autoSelectTopBait": self.Config.Settings['AutomationFeatures']['AutoSelectTopBait'],
            "kp": self.Config.Settings['FishingControl']['PdController']['Kp'],
            "kd": self.Config.Settings['FishingControl']['PdController']['Kd'],
            "pdClamp": self.Config.Settings['FishingControl']['PdController']['PdClamp'],
            "castHoldDuration": self.Config.Settings['FishingControl']['Timing']['CastHoldDuration'],
            "recastTimeout": self.Config.Settings['FishingControl']['Timing']['RecastTimeout'],
            "fishEndDelay": self.Config.Settings['FishingControl']['Timing']['FishEndDelay'],
            "loopsPerPurchase": self.Config.Settings['AutomationFrequencies']['LoopsPerPurchase'],
            "pdApproachingDamping": self.Config.Settings['FishingControl']['PdController']['PdApproachingDamping'],
            "pdChasingDamping": self.Config.Settings['FishingControl']['PdController']['PdChasingDamping'],
            "gapToleranceMultiplier": self.Config.Settings['FishingControl']['Detection']['GapToleranceMultiplier'],
            "stateResendInterval": self.Config.Settings['FishingControl']['Timing']['StateResendInterval'],
            "robloxFocusDelay": self.Config.Settings['TimingDelays']['RobloxWindow']['RobloxFocusDelay'],
            "robloxPostFocusDelay": self.Config.Settings['TimingDelays']['RobloxWindow']['RobloxPostFocusDelay'],
            "preCastEDelay": self.Config.Settings['TimingDelays']['PreCast']['SetPrecastEDelay'],
            "preCastClickDelay": self.Config.Settings['TimingDelays']['PreCast']['PreCastClickDelay'],
            "preCastTypeDelay": self.Config.Settings['TimingDelays']['PreCast']['PreCastTypeDelay'],
            "preCastAntiDetectDelay": self.Config.Settings['TimingDelays']['PreCast']['PreCastAntiDetectDelay'],
            "storeFruitHotkeyDelay": self.Config.Settings['TimingDelays']['DevilFruitStorage']['StoreFruitHotkeyDelay'],
            "storeFruitClickDelay": self.Config.Settings['TimingDelays']['DevilFruitStorage']['StoreFruitClickDelay'],
            "storeFruitShiftDelay": self.Config.Settings['TimingDelays']['DevilFruitStorage']['StoreFruitShiftDelay'],
            "storeFruitBackspaceDelay": self.Config.Settings['TimingDelays']['DevilFruitStorage']['StoreFruitBackspaceDelay'],
            "autoSelectBaitDelay": self.Config.Settings['TimingDelays']['Inventory']['AutoSelectBaitDelay'],
            "blackScreenThreshold": self.Config.Settings['FishingControl']['Detection']['BlackScreenThreshold'],
            "antiMacroSpamDelay": self.Config.Settings['TimingDelays']['AntiDetection']['AntiMacroSpamDelay'],
            "rodSelectDelay": self.Config.Settings['TimingDelays']['Inventory']['RodSelectDelay'],
            "cursorAntiDetectDelay": self.Config.Settings['TimingDelays']['AntiDetection']['CursorAntiDetectDelay'],
            "scanLoopDelay": self.Config.Settings['FishingControl']['Detection']['ScanLoopDelay'],
            "autoCraftBait": self.Config.Settings['AutomationFeatures']['AutoCraftBait'],
            "craftLeftPoint": self.Config.Settings['ClickPoints']['CraftLeft'],
            "craftMiddlePoint": self.Config.Settings['ClickPoints']['CraftMiddle'],
            "craftButtonPoint": self.Config.Settings['ClickPoints']['CraftButton'],
            "closeMenuPoint": self.Config.Settings['ClickPoints']['CloseMenu'],
            "craftsPerCycle": self.Config.Settings['AutomationFrequencies']['CraftsPerCycle'],
            "loopsPerCraft": self.Config.Settings['AutomationFrequencies']['LoopsPerCraft'],
            "fishCountPerCraft": self.Config.Settings['AutomationFrequencies']['FishCountPerCraft'],
            "craftMenuOpenDelay": self.Config.Settings['TimingDelays']['Crafting']['CraftMenuOpenDelay'],
            "craftClickDelay": self.Config.Settings['TimingDelays']['Crafting']['CraftClickDelay'],
            "craftRecipeSelectDelay": self.Config.Settings['TimingDelays']['Crafting']['CraftRecipeSelectDelay'],
            "craftAddRecipeDelay": self.Config.Settings['TimingDelays']['Crafting']['CraftAddRecipeDelay'],
            "craftTopRecipeDelay": self.Config.Settings['TimingDelays']['Crafting']['CraftTopRecipeDelay'],
            "craftButtonClickDelay": self.Config.Settings['TimingDelays']['Crafting']['CraftButtonClickDelay'],
            "craftCloseMenuDelay": self.Config.Settings['TimingDelays']['Crafting']['CraftCloseMenuDelay'],
            "webhookUrl": self.Config.Settings['DevilFruitStorage']['WebhookUrl'],
            "discordUserId": self.Config.Settings['LoggingOptions']['DiscordUserId'],
            "logDevilFruit": self.Config.Settings['LoggingOptions']['LogDevilFruit'],
            "pingDevilFruit": self.Config.Settings['LoggingOptions']['PingDevilFruit'],
            "logRecastTimeouts": self.Config.Settings['LoggingOptions']['LogRecastTimeouts'],
            "pingRecastTimeouts": self.Config.Settings['LoggingOptions']['PingRecastTimeouts'],
            "logPeriodicStats": self.Config.Settings['LoggingOptions']['LogPeriodicStats'],
            "pingPeriodicStats": self.Config.Settings['LoggingOptions']['PingPeriodicStats'],
            "logGeneralUpdates": self.Config.Settings['LoggingOptions']['LogGeneralUpdates'],
            "pingGeneralUpdates": self.Config.Settings['LoggingOptions']['PingGeneralUpdates'],
            "periodicStatsInterval": self.Config.Settings['LoggingOptions']['PeriodicStatsIntervalMinutes'],
            "logMacroState": self.Config.Settings['LoggingOptions']['LogMacroState'],
            "pingMacroState": self.Config.Settings['LoggingOptions']['PingMacroState'],
            "logErrors": self.Config.Settings['LoggingOptions']['LogErrors'],
            "pingErrors": self.Config.Settings['LoggingOptions']['PingErrors'],
            "totalRecastTimeouts": self.State.TotalRecastTimeouts,
            "enableSpawnDetection": self.Config.Settings['SpawnDetection']['EnableSpawnDetection'],
            "spawnScanInterval": self.Config.Settings['SpawnDetection']['ScanInterval'],
            "logSpawns": self.Config.Settings['SpawnDetection']['LogSpawns'],
            "pingSpawns": self.Config.Settings['SpawnDetection']['PingSpawns'],
            "baitRecipes": self.Config.Settings['BaitRecipes'],
            "currentRecipeIndex": self.Config.Settings['CurrentRecipeIndex'],
            "currentStatus": self.State.CurrentStatus,
            "megalodonSoundEnabled": self.Config.Settings['FishingModes']['MegalodonSound'],
            "soundSensitivity": self.Config.Settings['FishingModes']['SoundSensitivity'],
            "rdp_detected": self.State.RDPDetected,
            "rdp_session_state": self.State.RDPSessionState,
            "auto_detect_rdp": self.Config.Settings['RDPSettings']['AutoDetectRDP'],
            "allow_rdp_execution": self.Config.Settings['RDPSettings']['AllowRDPExecution'],
            "pause_on_rdp_disconnect": self.Config.Settings['RDPSettings']['PauseOnRDPDisconnect'],
            "resume_on_rdp_reconnect": self.Config.Settings['RDPSettings']['ResumeOnRDPReconnect'],
            "enable_device_sync": self.Config.Settings['DeviceSyncSettings']['EnableDeviceSync'],
            "sync_settings": self.Config.Settings['DeviceSyncSettings']['SyncSettings'],
            "sync_stats": self.Config.Settings['DeviceSyncSettings']['SyncStats'],
            "share_fish_count": self.Config.Settings['DeviceSyncSettings']['ShareFishCount'],
            "sync_interval": self.Config.Settings['DeviceSyncSettings']['SyncIntervalSeconds'],
            "device_name": self.Config.Settings['DeviceSyncSettings']['DeviceName'],
            "connected_devices": self.State.ConnectedDevices,
            "is_syncing": self.State.IsSyncing,
            "is_admin": self.IsAdmin,
        }
    

FlaskApp = Flask(__name__)
CORS(FlaskApp)

MacroSystem = AutomatedFishingSystem()
MacroSystem.OcrManager.Initialize()

Port = FindFreePort()

if getattr(sys, 'frozen', False):
    AppPath = os.path.dirname(sys.executable)
else:
    AppPath = os.path.dirname(os.path.abspath(__file__))

CleanupOrphanedPortFiles(AppPath)

PortFile = os.path.join(AppPath, f"port_{LauncherPid}.json")
with open(PortFile, 'w') as Pf:
    json.dump({"port": Port, "pid": LauncherPid}, Pf)

@FlaskApp.route('/state', methods=['GET'])
def GetState():
    ClientId = request.args.get('clientId', MacroSystem.State.ClientId)
    
    if ClientId not in MacroSystem.State.ClientStats:
        MacroSystem.State.ClientStats[ClientId] = {
            "fish_caught": 0,
            "start_time": None,
            "last_seen": time.time(),
            "rdp_detected": False,
            "rdp_state": "unknown"
        }
    
    MacroSystem.State.ClientStats[ClientId]["last_seen"] = time.time()
    
    if ClientId == MacroSystem.State.ClientId:
        MacroSystem.State.ClientStats[ClientId]["fish_caught"] = MacroSystem.State.TotalFishCaught
        MacroSystem.State.ClientStats[ClientId]["rdp_detected"] = MacroSystem.State.RDPDetected
        MacroSystem.State.ClientStats[ClientId]["rdp_state"] = MacroSystem.State.RDPSessionState
    
    CurrentTime = time.time()
    StaleClients = [
        Cid for Cid, Stats in MacroSystem.State.ClientStats.items()
        if CurrentTime - Stats.get('last_seen', 0) > 30
    ]
    for Cid in StaleClients:
        del MacroSystem.State.ClientStats[Cid]
    
    ActiveSessions = []
    for Cid, Stats in MacroSystem.State.ClientStats.items():
        if Cid and Cid != 'unknown':
            ActiveSessions.append({
                'client_id': Cid,
                'rdp_detected': Stats.get('rdp_detected', False),
                'rdp_state': Stats.get('rdp_state', 'unknown'),
                'session_id': MacroSystem.State.RDPSessionId if Cid == MacroSystem.State.ClientId else -1,
                'last_updated': Stats.get('last_seen', 0)
            })
    
    TotalFish = MacroSystem.State.TotalFishCaught
    
    if MacroSystem.Config.Settings['DeviceSyncSettings']['EnableDeviceSync'] and MacroSystem.Config.Settings['DeviceSyncSettings']['ShareFishCount']:
        TotalFish = sum(C.get("fish_caught", 0) for C in MacroSystem.State.ClientStats.values())
    
    TotalUptime = MacroSystem.State.GetElapsedTime()
    GlobalFPH = (TotalFish / TotalUptime * 3600) if TotalUptime > 0 else 0
    
    BaseResponse = MacroSystem.GetStateForAPI(ClientId)
    
    BaseResponse.update({
        "clientId": MacroSystem.State.ClientId,
        "currentActiveClientId": MacroSystem.State.ClientId,
        "activeSessions": ActiveSessions,
        "clientFishCaught": MacroSystem.State.ClientStats[ClientId].get("fish_caught", 0),
        "globalFishCaught": TotalFish,
        "globalFishPerHour": round(GlobalFPH, 1),
    })
    
    return jsonify(BaseResponse)


@FlaskApp.route('/health', methods=['GET'])
def HealthCheck():
    return jsonify({"status": "ok", "message": "Backend running"})


@FlaskApp.route('/check_audio_device', methods=['GET'])
def CheckAudioDevice():
    try:
        AudioInterface = pyaudio.PyAudio()
        DeviceFound = False
        DeviceName = None
        
        try:
            WasapiInfo = AudioInterface.get_host_api_info_by_type(pyaudio.paWASAPI)
            DefaultOutputIndex = WasapiInfo.get("defaultOutputDevice")
            
            if DefaultOutputIndex is not None and DefaultOutputIndex >= 0:
                try:
                    DefaultDevice = AudioInterface.get_device_info_by_index(DefaultOutputIndex)
                    DefaultName = DefaultDevice.get("name", "")
                    
                    for Loopback in AudioInterface.get_loopback_device_info_generator():
                        if DefaultName in Loopback.get("name", ""):
                            if Loopback.get('maxInputChannels', 0) > 0:
                                DeviceFound = True
                                DeviceName = Loopback.get("name", "Unknown")
                                break
                except Exception:
                    pass
            
            if not DeviceFound:
                for Loopback in AudioInterface.get_loopback_device_info_generator():
                    if Loopback.get('maxInputChannels', 0) > 0:
                        DeviceFound = True
                        DeviceName = Loopback.get("name", "Unknown")
                        break
                        
        except Exception:
            DeviceFound = False
        finally:
            AudioInterface.terminate()
        
        return jsonify({"found": DeviceFound, "deviceName": DeviceName})
    except Exception as E:
        return jsonify({"found": False, "deviceName": None, "error": str(E)})


@FlaskApp.route('/get_audio_devices', methods=['GET'])
def GetAudioDevices():
    try:
        AudioInterface = pyaudio.PyAudio()
        Devices = []
        
        try:
            WasapiInfo = AudioInterface.get_host_api_info_by_type(pyaudio.paWASAPI)
            
            for Loopback in AudioInterface.get_loopback_device_info_generator():
                if Loopback.get('maxInputChannels', 0) > 0:
                    Devices.append({
                        'index': Loopback.get('index'),
                        'name': Loopback.get('name', 'Unknown Device'),
                        'sampleRate': int(Loopback.get('defaultSampleRate', 44100))
                    })
        except Exception as E:
            print(f"Error getting audio devices: {E}")
        finally:
            AudioInterface.terminate()
        
        return jsonify({"devices": Devices})
    except Exception as E:
        return jsonify({"devices": [], "error": str(E)})
    

@FlaskApp.route('/set_fast_mode', methods=['POST'])
def SetFastMode():
    try:
        Data = request.json
        Enabled = Data.get('enabled', False)
        
        if Enabled:
            MacroSystem.OcrManager.Enabled = False
            MacroSystem.State.FastModeEnabled = True

            kernel32 = ctypes.windll.kernel32
            Pid = os.getpid()
            Handle = kernel32.OpenProcess(0x0200, False, Pid)
            if Handle:
                kernel32.SetPriorityClass(Handle, 0x00000020)
                kernel32.CloseHandle(Handle)
        else:
            MacroSystem.Config.LoadFromDisk()
            MacroSystem.OcrManager.Enabled = True
            MacroSystem.State.FastModeEnabled = False
            
            kernel32 = ctypes.windll.kernel32
            Pid = os.getpid()
            Handle = kernel32.OpenProcess(0x0200, False, Pid)
            if Handle:
                kernel32.SetPriorityClass(Handle, 0x00000080)
                kernel32.CloseHandle(Handle)
        
        return jsonify({"status": "success", "fastMode": Enabled})
    except Exception as E:
        return jsonify({"status": "error", "message": str(E)}), 500


@FlaskApp.route('/set_window_property', methods=['POST'])
def SetWindowProperty():
    try:
        Data = request.json
        Prop = Data.get('property')
        
        if Prop == 'always_on_top':
            return jsonify({"alwaysOnTop": MacroSystem.Config.Settings['WindowSettings']['AlwaysOnTop']})
        
        return jsonify({"status": "ok"})
    except Exception as E:
        return jsonify({"status": "error", "message": str(E)}), 500


@FlaskApp.route('/command', methods=['POST'])
def ProcessCommand():
    try:
        Data = request.json
        Action = Data.get('action')
        Payload = Data.get('payload')
        
        ClientId = Data.get('clientId', 'unknown')
        MacroSystem.State.ClientId = ClientId
        
        if ClientId in MacroSystem.State.ClientStats:
            MacroSystem.State.ClientStats[ClientId]["last_seen"] = time.time()
        
        if not Action:
            return jsonify({"status": "error", "message": "Missing action parameter"}), 400
        
        def HandlePointSelection(AttrName):
            def OnPointSelected(PointName, Point):
                if AttrName.startswith('ClickPoints.'):
                    Key = AttrName.split('.')[1]
                    MacroSystem.Config.Settings['ClickPoints'][Key] = Point
                MacroSystem.Config.SaveToDisk()
            
            MacroSystem.PointSelector.StartSelection(AttrName, OnPointSelected)
            return jsonify({"status": "waiting_for_click"})
        
        def HandleBoolToggle(Path):
            if Payload is None:
                return jsonify({"status": "error", "message": "Missing payload"}), 400
            
            Value = Payload.lower() == 'true'
            Parts = Path.split('.')
            Current = MacroSystem.Config.Settings
            for Part in Parts[:-1]:
                Current = Current[Part]
            Current[Parts[-1]] = Value
            MacroSystem.Config.SaveToDisk()
            return jsonify({"status": "success", "value": Value})
        
        def HandleStringValue(Path):
            if Payload is None:
                return jsonify({"status": "error", "message": "Missing payload"}), 400
            
            Parts = Path.split('.')
            Current = MacroSystem.Config.Settings
            for Part in Parts[:-1]:
                Current = Current[Part]
            Current[Parts[-1]] = Payload
            MacroSystem.Config.SaveToDisk()
            return jsonify({"status": "success"})
        
        def HandleIntValue(Path):
            if Payload is None:
                return jsonify({"status": "error", "message": "Missing payload"}), 400
            
            try:
                Value = int(Payload)
                Parts = Path.split('.')
                Current = MacroSystem.Config.Settings
                for Part in Parts[:-1]:
                    Current = Current[Part]
                Current[Parts[-1]] = Value
                MacroSystem.Config.SaveToDisk()
                return jsonify({"status": "success"})
            except (ValueError, TypeError) as E:
                return jsonify({"status": "error", "message": f"Invalid integer: {str(E)}"}), 400
        
        def HandleFloatValue(Path):
            if Payload is None:
                return jsonify({"status": "error", "message": "Missing payload"}), 400
            
            try:
                Value = float(Payload)
                Parts = Path.split('.')
                Current = MacroSystem.Config.Settings
                for Part in Parts[:-1]:
                    Current = Current[Part]
                Current[Parts[-1]] = Value
                MacroSystem.Config.SaveToDisk()
                return jsonify({"status": "success"})
            except (ValueError, TypeError) as E:
                return jsonify({"status": "error", "message": f"Invalid float: {str(E)}"}), 400
        
        ActionMap = {
            'set_water_point': lambda: HandlePointSelection('ClickPoints.Water'),
            'set_devil_fruit_location_point': lambda: HandlePointSelection('ClickPoints.DevilFruitLocation'),
            'set_left_point': lambda: HandlePointSelection('ClickPoints.ShopLeft'),
            'set_middle_point': lambda: HandlePointSelection('ClickPoints.ShopCenter'),
            'set_right_point': lambda: HandlePointSelection('ClickPoints.ShopRight'),
            'set_store_fruit_point': lambda: HandlePointSelection('ClickPoints.StoreFruit'),
            'set_bait_point': lambda: HandlePointSelection('ClickPoints.Bait'),
            'set_craft_left_point': lambda: HandlePointSelection('ClickPoints.CraftLeft'),
            'set_craft_middle_point': lambda: HandlePointSelection('ClickPoints.CraftMiddle'),
            'set_bait_recipe_point': lambda: HandlePointSelection('BaitRecipePoint'),
            'set_add_recipe_point': lambda: HandlePointSelection('ClickPoints.AddRecipe'),
            'set_top_recipe_point': lambda: HandlePointSelection('ClickPoints.TopRecipe'),
            'set_craft_button_point': lambda: HandlePointSelection('ClickPoints.CraftButton'),
            'set_close_menu_point': lambda: HandlePointSelection('ClickPoints.CloseMenu'),
            
            'toggle_always_on_top': lambda: HandleBoolToggle('WindowSettings.AlwaysOnTop'),
            'toggle_debug_overlay': lambda: HandleBoolToggle('WindowSettings.ShowDebugOverlay'),
            'toggle_auto_buy_bait': lambda: HandleBoolToggle('AutomationFeatures.AutoBuyBait'),
            'toggle_auto_store_fruit': lambda: HandleBoolToggle('AutomationFeatures.AutoStoreFruit'),
            'toggle_auto_select_bait': lambda: HandleBoolToggle('AutomationFeatures.AutoSelectTopBait'),
            'toggle_auto_craft_bait': lambda: HandleBoolToggle('AutomationFeatures.AutoCraftBait'),
            'toggle_store_to_backpack': lambda: HandleBoolToggle('DevilFruitStorage.StoreToBackpack'),
            'toggle_log_devil_fruit': lambda: HandleBoolToggle('LoggingOptions.LogDevilFruit'),
            'toggle_log_recast_timeouts': lambda: HandleBoolToggle('LoggingOptions.LogRecastTimeouts'),
            'toggle_log_periodic_stats': lambda: HandleBoolToggle('LoggingOptions.LogPeriodicStats'),
            'toggle_log_general_updates': lambda: HandleBoolToggle('LoggingOptions.LogGeneralUpdates'),
            'toggle_log_macro_state': lambda: HandleBoolToggle('LoggingOptions.LogMacroState'),
            'toggle_log_errors': lambda: HandleBoolToggle('LoggingOptions.LogErrors'),
            'toggle_ping_devil_fruit': lambda: HandleBoolToggle('LoggingOptions.PingDevilFruit'),
            'toggle_ping_recast_timeouts': lambda: HandleBoolToggle('LoggingOptions.PingRecastTimeouts'),
            'toggle_ping_periodic_stats': lambda: HandleBoolToggle('LoggingOptions.PingPeriodicStats'),
            'toggle_ping_general_updates': lambda: HandleBoolToggle('LoggingOptions.PingGeneralUpdates'),
            'toggle_ping_macro_state': lambda: HandleBoolToggle('LoggingOptions.PingMacroState'),
            'toggle_ping_errors': lambda: HandleBoolToggle('LoggingOptions.PingErrors'),
            'toggle_megalodon_sound': lambda: HandleBoolToggle('FishingModes.MegalodonSound'),
            'toggle_auto_detect_rdp': lambda: HandleBoolToggle('RDPSettings.AutoDetectRDP'),
            'toggle_allow_rdp_execution': lambda: HandleBoolToggle('RDPSettings.AllowRDPExecution'),
            'toggle_pause_on_rdp_disconnect': lambda: HandleBoolToggle('RDPSettings.PauseOnRDPDisconnect'),
            'toggle_resume_on_rdp_reconnect': lambda: HandleBoolToggle('RDPSettings.ResumeOnRDPReconnect'),
            'toggle_enable_device_sync': lambda: HandleBoolToggle('DeviceSyncSettings.EnableDeviceSync'),
            'toggle_sync_settings': lambda: HandleBoolToggle('DeviceSyncSettings.SyncSettings'),
            'toggle_sync_stats': lambda: HandleBoolToggle('DeviceSyncSettings.SyncStats'),
            'toggle_share_fish_count': lambda: HandleBoolToggle('DeviceSyncSettings.ShareFishCount'),
            'toggle_enable_spawn_detection': lambda: HandleBoolToggle('SpawnDetection.EnableSpawnDetection'),
            'toggle_log_spawns': lambda: HandleBoolToggle('SpawnDetection.LogSpawns'),
            'toggle_ping_spawns': lambda: HandleBoolToggle('SpawnDetection.PingSpawns'),

            'set_rod_hotkey': lambda: HandleStringValue('InventoryHotkeys.Rod'),
            'set_anything_else_hotkey': lambda: HandleStringValue('InventoryHotkeys.Alternate'),
            'set_webhook_url': lambda: HandleStringValue('DevilFruitStorage.WebhookUrl'),
            'set_discord_user_id': lambda: HandleStringValue('LoggingOptions.DiscordUserId'),
            'set_device_name': lambda: HandleStringValue('DeviceSyncSettings.DeviceName'),
            'set_client_id': lambda: HandleStringValue('ClientId'),
            
            'set_loops_per_store': lambda: HandleIntValue('AutomationFrequencies.LoopsPerStore'),
            'set_loops_per_purchase': lambda: HandleIntValue('AutomationFrequencies.LoopsPerPurchase'),
            'set_fish_count_per_craft': lambda: HandleIntValue('AutomationFrequencies.FishCountPerCraft'),
            'set_crafts_per_cycle': lambda: HandleIntValue('AutomationFrequencies.CraftsPerCycle'),
            'set_craft_confirm_point': lambda: HandlePointSelection('ClickPoints.CraftConfirm'),
            'set_loops_per_craft': lambda: HandleIntValue('AutomationFrequencies.LoopsPerCraft'),
            'set_periodic_stats_interval': lambda: HandleIntValue('LoggingOptions.PeriodicStatsIntervalMinutes'),
            'set_sync_interval': lambda: HandleIntValue('DeviceSyncSettings.SyncIntervalSeconds'),
            
            'set_kp': lambda: HandleFloatValue('FishingControl.PdController.Kp'),
            'set_kd': lambda: HandleFloatValue('FishingControl.PdController.Kd'),
            'set_pd_clamp': lambda: HandleFloatValue('FishingControl.PdController.PdClamp'),
            'set_pd_approaching': lambda: HandleFloatValue('FishingControl.PdController.PdApproachingDamping'),
            'set_pd_chasing': lambda: HandleFloatValue('FishingControl.PdController.PdChasingDamping'),
            'set_gap_tolerance': lambda: HandleFloatValue('FishingControl.Detection.GapToleranceMultiplier'),
            'set_cast_hold': lambda: HandleFloatValue('FishingControl.Timing.CastHoldDuration'),
            'set_recast_timeout': lambda: HandleFloatValue('FishingControl.Timing.RecastTimeout'),
            'set_fish_end_delay': lambda: HandleFloatValue('FishingControl.Timing.FishEndDelay'),
            'set_state_resend': lambda: HandleFloatValue('FishingControl.Timing.StateResendInterval'),
            'set_focus_delay': lambda: HandleFloatValue('TimingDelays.RobloxWindow.RobloxFocusDelay'),
            'set_post_focus_delay': lambda: HandleFloatValue('TimingDelays.RobloxWindow.RobloxPostFocusDelay'),
            'set_precast_e_delay': lambda: HandleFloatValue('TimingDelays.PreCast.SetPrecastEDelay'),
            'set_precast_click_delay': lambda: HandleFloatValue('TimingDelays.PreCast.PreCastClickDelay'),
            'set_precast_type_delay': lambda: HandleFloatValue('TimingDelays.PreCast.PreCastTypeDelay'),
            'set_anti_detect_delay': lambda: HandleFloatValue('TimingDelays.PreCast.PreCastAntiDetectDelay'),
            'set_fruit_hotkey_delay': lambda: HandleFloatValue('TimingDelays.DevilFruitStorage.StoreFruitHotkeyDelay'),
            'set_fruit_click_delay': lambda: HandleFloatValue('TimingDelays.DevilFruitStorage.StoreFruitClickDelay'),
            'set_fruit_shift_delay': lambda: HandleFloatValue('TimingDelays.DevilFruitStorage.StoreFruitShiftDelay'),
            'set_fruit_backspace_delay': lambda: HandleFloatValue('TimingDelays.DevilFruitStorage.StoreFruitBackspaceDelay'),
            'set_rod_delay': lambda: HandleFloatValue('TimingDelays.Inventory.RodSelectDelay'),
            'set_bait_delay': lambda: HandleFloatValue('TimingDelays.Inventory.AutoSelectBaitDelay'),
            'set_cursor_delay': lambda: HandleFloatValue('TimingDelays.AntiDetection.CursorAntiDetectDelay'),
            'set_scan_delay': lambda: HandleFloatValue('FishingControl.Detection.ScanLoopDelay'),
            'set_black_threshold': lambda: HandleFloatValue('FishingControl.Detection.BlackScreenThreshold'),
            'set_spam_delay': lambda: HandleFloatValue('TimingDelays.AntiDetection.AntiMacroSpamDelay'),
            'set_move_duration': lambda: HandleFloatValue('TimingDelays.Crafting.MoveDuration'),
            'set_sound_sensitivity': lambda: HandleFloatValue('FishingModes.SoundSensitivity'),
            'set_craft_menu_delay': lambda: HandleFloatValue('TimingDelays.Crafting.CraftMenuOpenDelay'),
            'set_craft_click_delay': lambda: HandleFloatValue('TimingDelays.Crafting.CraftClickDelay'),
            'set_craft_recipe_delay': lambda: HandleFloatValue('TimingDelays.Crafting.CraftRecipeSelectDelay'),
            'set_craft_add_delay': lambda: HandleFloatValue('TimingDelays.Crafting.CraftAddRecipeDelay'),
            'set_craft_top_delay': lambda: HandleFloatValue('TimingDelays.Crafting.CraftTopRecipeDelay'),
            'set_craft_button_delay': lambda: HandleFloatValue('TimingDelays.Crafting.CraftButtonClickDelay'),
            'set_craft_close_delay': lambda: HandleFloatValue('TimingDelays.Crafting.CraftCloseMenuDelay'),
            'set_spawn_scan_interval': lambda: HandleFloatValue('SpawnDetection.ScanInterval'),
            
            'test_webhook': lambda: HandleTestWebhook(),
            'open_ocr_area_selector': lambda: HandleOCRAreaSelector(),
            'open_area_selector': lambda: HandleAreaSelector(),
            'open_browser': lambda: HandleOpenBrowser(Payload),
            'export_settings': lambda: HandleExportSettings(),
            'import_settings': lambda: HandleImportSettings(),
            'reset_settings': lambda: HandleResetSettings(Payload),
            'open_config_folder': lambda: HandleOpenFolder(),
            'view_config': lambda: HandleViewConfig(),
            'clear_cache': lambda: HandleClearCache(),
        }
        
        if Action == 'rebind_hotkey':
            return HandleHotkeyRebind(Payload)
        
        if Action == 'set_devil_fruit_hotkeys':
            return HandleDevilFruitSlots(Payload)

        if Action == 'set_audio_device':
            if Payload is None:
                return jsonify({"status": "error", "message": "Missing payload"}), 400
            
            try:
                DeviceData = json.loads(Payload)
                MacroSystem.Config.Settings['AudioDevice']['SelectedDeviceIndex'] = DeviceData.get('index')
                MacroSystem.Config.Settings['AudioDevice']['DeviceName'] = DeviceData.get('name', '')
                MacroSystem.Config.SaveToDisk()
                return jsonify({"status": "success"})
            except Exception as E:
                return jsonify({"status": "error", "message": str(E)}), 500
        
        if Action in ActionMap:
            return ActionMap[Action]()
        else:
            return jsonify({"status": "error", "message": f"Unknown action: {Action}"}), 400
    
    except ValueError as E:
        return jsonify({"status": "error", "message": f"Invalid value: {str(E)}"}), 400
    except Exception as E:
        return jsonify({"status": "error", "message": str(E)}), 500


@FlaskApp.route('/add_recipe', methods=['POST'])
def AddRecipe():
    try:
        MacroSystem.Config.Settings['BaitRecipes'].append({
            "BaitRecipePoint": None,
            "SelectMaxPoint": None,
            "SwitchFishCycle": 5 
        })
        MacroSystem.Config.SaveToDisk()
        return jsonify({"status": "success", "recipeIndex": len(MacroSystem.Config.Settings['BaitRecipes']) - 1})
    except Exception as E:
        return jsonify({"status": "error", "message": str(E)}), 500


@FlaskApp.route('/remove_recipe', methods=['POST'])
def RemoveRecipe():
    try:
        Data = request.json
        Index = int(Data.get('index'))
        if 0 <= Index < len(MacroSystem.Config.Settings['BaitRecipes']):
            MacroSystem.Config.Settings['BaitRecipes'].pop(Index)
            MacroSystem.Config.SaveToDisk()
            return jsonify({"status": "success"})
        return jsonify({"status": "error", "message": "Invalid index"}), 400
    except Exception as E:
        return jsonify({"status": "error", "message": str(E)}), 500


@FlaskApp.route('/update_recipe_value', methods=['POST'])
def UpdateRecipeValue():
    try:
        Data = request.json
        Index = int(Data.get('recipeIndex'))
        Field = Data.get('fieldName')
        Value = int(Data.get('value'))
        
        if 0 <= Index < len(MacroSystem.Config.Settings['BaitRecipes']):
            MacroSystem.Config.Settings['BaitRecipes'][Index][Field] = Value
            MacroSystem.Config.SaveToDisk()
            return jsonify({"status": "success"})
        return jsonify({"status": "error", "message": "Invalid index"}), 400
    except Exception as E:
        return jsonify({"status": "error", "message": str(E)}), 500


@FlaskApp.route('/set_recipe_point', methods=['POST'])
def SetRecipePoint():
    try:
        Data = request.json
        Index = int(Data.get('recipeIndex'))
        PointType = Data.get('pointType')
        
        def OnPointSet(Name, Point):
            MacroSystem.Config.Settings['BaitRecipes'][Index][PointType] = Point
            MacroSystem.Config.SaveToDisk()
        
        MacroSystem.PointSelector.StartSelection(f"Recipe{Index}.{PointType}", OnPointSet)
        
        return jsonify({"status": "waiting_for_click"})
    except Exception as E:
        return jsonify({"status": "error", "message": str(E)}), 500


def HandleDevilFruitSlots(Payload):
    if Payload is None:
        return jsonify({"status": "error", "message": "Missing payload"}), 400
    
    try:
        Slots = [S.strip() for S in Payload.split(',') if S.strip()]
        MacroSystem.Config.Settings['InventoryHotkeys']['DevilFruits'] = Slots
        MacroSystem.Config.SaveToDisk()
        return jsonify({"status": "success", "slots": Slots})
    except Exception as E:
        return jsonify({"status": "error", "message": f"Invalid slots: {str(E)}"}), 400


def HandleExportSettings():
    try:
        Root = tk.Tk()
        Root.withdraw()
        Root.attributes('-topmost', True)
        
        DefaultName = f"fishing_macro_settings_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        Path = filedialog.asksaveasfilename(
            title="Export Settings",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            initialfile=DefaultName
        )
        
        Root.destroy()
        
        if Path:
            shutil.copy(MacroSystem.Config.ConfigPath, Path)
            messagebox.showinfo("Export Successful", f"Settings exported to:\n{Path}")
            return jsonify({"status": "success", "path": Path})
        
        return jsonify({"status": "cancelled"})
    except Exception as E:
        messagebox.showerror("Export Failed", f"Failed to export settings:\n{str(E)}")
        return jsonify({"status": "error", "message": str(E)}), 500


def HandleImportSettings():
    try:
        Root = tk.Tk()
        Root.withdraw()
        Root.attributes('-topmost', True)
        
        Path = filedialog.askopenfilename(
            title="Import Settings",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        Root.destroy()
        
        if Path:
            BackupPath = MacroSystem.Config.ConfigPath + ".backup"
            shutil.copy(MacroSystem.Config.ConfigPath, BackupPath)
            
            try:
                shutil.copy(Path, MacroSystem.Config.ConfigPath)
                MacroSystem.Config.LoadFromDisk()
                messagebox.showinfo("Import Successful", f"Settings imported successfully!\n\nOld settings backed up to:\n{BackupPath}")
                return jsonify({"status": "success"})
            except Exception as E:
                shutil.copy(BackupPath, MacroSystem.Config.ConfigPath)
                raise E
        
        return jsonify({"status": "cancelled"})
    except Exception as E:
        messagebox.showerror("Import Failed", f"Failed to import settings:\n{str(E)}")
        return jsonify({"status": "error", "message": str(E)}), 500


def HandleResetSettings(Payload):
    if Payload != "confirm":
        return jsonify({"status": "error", "message": "Reset not confirmed"}), 400
    
    try:
        BackupPath = MacroSystem.Config.ConfigPath + f".backup_{int(time.time())}"
        if os.path.exists(MacroSystem.Config.ConfigPath):
            shutil.copy(MacroSystem.Config.ConfigPath, BackupPath)
        
        if os.path.exists(MacroSystem.Config.ConfigPath):
            os.remove(MacroSystem.Config.ConfigPath)
        
        MacroSystem.Config.Settings = MacroSystem.Config.InitializeDefaults()
        MacroSystem.Config.SaveToDisk()
        
        return jsonify({"status": "success"})
    except Exception as E:
        messagebox.showerror("Reset Failed", f"Failed to reset settings:\n{str(E)}")
        return jsonify({"status": "error", "message": str(E)}), 500


def HandleOpenFolder():
    try:
        Folder = os.path.dirname(MacroSystem.Config.ConfigPath)
        
        if platform.system() == "Windows":
            os.startfile(Folder)
        elif platform.system() == "Darwin":
            subprocess.Popen(["open", Folder])
        else:
            subprocess.Popen(["xdg-open", Folder])
        
        return jsonify({"status": "success"})
    except Exception as E:
        return jsonify({"status": "error", "message": str(E)}), 500


def HandleViewConfig():
    try:
        if os.path.exists(MacroSystem.Config.ConfigPath):
            with open(MacroSystem.Config.ConfigPath, 'r') as F:
                Content = F.read()
            
            Root = tk.Tk()
            Root.title("Configuration File Viewer")
            Root.geometry("800x600")
            
            Text = tk.Text(Root, wrap=tk.WORD, font=("Consolas", 10))
            Text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            Text.insert(1.0, Content)
            Text.config(state=tk.DISABLED)
            
            Scroll = tk.Scrollbar(Text)
            Scroll.pack(side=tk.RIGHT, fill=tk.Y)
            Text.config(yscrollcommand=Scroll.set)
            Scroll.config(command=Text.yview)
            
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
        MacroSystem.State.BaitPurchaseCounter = 0
        MacroSystem.State.FruitStorageCounter = 0
        MacroSystem.State.FishSinceLastCraft = 0
        MacroSystem.State.BaitCraftCounter = 0
        MacroSystem.State.TotalRecastTimeouts = 0
        MacroSystem.State.ConsecutiveRecastTimeouts = 0
        
        messagebox.showinfo("Cache Cleared", "Runtime cache and counters have been reset.")
        return jsonify({"status": "success"})
    except Exception as E:
        messagebox.showerror("Clear Failed", f"Failed to clear cache:\n{str(E)}")
        return jsonify({"status": "error", "message": str(E)}), 500


def HandleAreaSelector():
    MacroSystem.ModifyScanArea()
    return jsonify({"status": "opening_selector"})


def HandleOpenBrowser(Url):
    if not Url:
        return jsonify({"status": "error", "message": "Missing URL"}), 400
    
    try:
        webbrowser.open(Url)
        return jsonify({"status": "success"})
    except Exception as E:
        return jsonify({"status": "error", "message": str(E)}), 500


def HandleHotkeyRebind(Payload):
    if Payload is None:
        return jsonify({"status": "error", "message": "Missing payload"}), 400
    
    MacroSystem.CurrentlyRebindingHotkey = Payload
    keyboard.unhook_all_hotkeys()
    
    def HandleKey(Event):
        if MacroSystem.CurrentlyRebindingHotkey == Payload:
            NewKey = Event.name.lower()
            MacroSystem.Config.Settings['Hotkeys'][Payload.title().replace('_', '')] = NewKey
            MacroSystem.Config.SaveToDisk()
            MacroSystem.CurrentlyRebindingHotkey = None
            keyboard.unhook_all()
            MacroSystem.RegisterHotkeys()
    
    keyboard.on_release(HandleKey, suppress=False)
    return jsonify({"status": "waiting_for_key"})


def HandleTestWebhook():
    if not MacroSystem.Config.Settings['DevilFruitStorage']['WebhookUrl']:
        return jsonify({"status": "error", "message": "No webhook URL configured"}), 400
    
    try:
        MacroSystem.Notifier.SendNotification(
            "Test webhook notification sent successfully! Your webhook is working correctly.",
            Color=0x3b82f6,
            Title="🎣 Webhook Test"
        )
        return jsonify({"status": "success"})
    except Exception as E:
        return jsonify({"status": "error", "message": str(E)}), 500


def HandleOCRAreaSelector():
    def OnOCRRegionComplete(Coords):
        MacroSystem.Config.Settings['OCRSettings'] = Coords
        MacroSystem.Config.SaveToDisk()
        MacroSystem.ActiveRegionSelector = None
        MacroSystem.RegionSelectorActive = False
    
    if MacroSystem.RegionSelectorActive:
        if MacroSystem.ActiveRegionSelector:
            try:
                MacroSystem.ActiveRegionSelector.RootWindow.after(10, MacroSystem.ActiveRegionSelector.CloseWindow)
            except:
                pass
        return jsonify({"status": "already_open"})
    
    MacroSystem.RegionSelectorActive = True
    
    def RunSelector():
        try:
            MacroSystem.ActiveRegionSelector = RegionSelectionWindow(None, MacroSystem.Config.Settings['OCRSettings'], OnOCRRegionComplete)
        finally:
            MacroSystem.RegionSelectorActive = False
            MacroSystem.ActiveRegionSelector = None
    
    threading.Thread(target=RunSelector, daemon=True).start()
    return jsonify({"status": "opening_selector"})

def RunFlaskServer():
    FlaskApp.run(host='0.0.0.0', port=Port, debug=False, use_reloader=False)


if __name__ == "__main__":
    ServerThread = threading.Thread(target=RunFlaskServer, daemon=True)
    ServerThread.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        os._exit(0)