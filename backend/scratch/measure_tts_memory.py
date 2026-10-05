"""
Measure exact memory for Piper English and MMS-TTS Kannada.
"""

import os
import sys
import ctypes
from ctypes import wintypes
from pathlib import Path

class PROCESS_MEMORY_COUNTERS_EX(ctypes.Structure):
    _fields_ = [
        ("cb", wintypes.DWORD),
        ("PageFaultCount", wintypes.DWORD),
        ("PeakWorkingSetSize", ctypes.c_size_t),
        ("WorkingSetSize", ctypes.c_size_t),
        ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
        ("QuotaPagedPoolUsage", ctypes.c_size_t),
        ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
        ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
        ("PagefileUsage", ctypes.c_size_t),
        ("PeakPagefileUsage", ctypes.c_size_t),
        ("PrivateUsage", ctypes.c_size_t),
    ]

GetProcessMemoryInfo = ctypes.windll.psapi.GetProcessMemoryInfo
GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(PROCESS_MEMORY_COUNTERS_EX), wintypes.DWORD]
GetProcessMemoryInfo.restype = wintypes.BOOL

def get_ram_mb():
    p = ctypes.windll.kernel32.GetCurrentProcess()
    c = PROCESS_MEMORY_COUNTERS_EX()
    c.cb = ctypes.sizeof(PROCESS_MEMORY_COUNTERS_EX)
    GetProcessMemoryInfo(p, ctypes.byref(c), c.cb)
    return c.WorkingSetSize / (1024 * 1024), c.PrivateUsage / (1024 * 1024)

print("=" * 80)
print("TTS MEMORY FOOTPRINT MEASUREMENT")
print("=" * 80)

# Step 0: Baseline
ws0, priv0 = get_ram_mb()
print(f"1. Baseline Process RAM:         WS={ws0:6.2f} MB | Private={priv0:6.2f} MB")

# Step 1: Load Piper English
from piper.voice import PiperVoice
BASE_DIR = Path(__file__).resolve().parent.parent
piper_model = BASE_DIR / "storage" / "models" / "voices" / "en" / "en_US-lessac-medium.onnx"
piper_config = BASE_DIR / "storage" / "models" / "voices" / "en" / "en_US-lessac-medium.onnx.json"

voice_en = PiperVoice.load(str(piper_model), config_path=str(piper_config), use_cuda=False)
ws1, priv1 = get_ram_mb()
print(f"2. After Piper (en_US-lessac):   WS={ws1:6.2f} MB | Private={priv1:6.2f} MB | Delta: +{ws1 - ws0:.2f} MB")

# Step 2: Load MMS-TTS Kannada
from transformers import VitsModel, AutoTokenizer
tok_kn = AutoTokenizer.from_pretrained("facebook/mms-tts-kan", local_files_only=True)
mod_kn = VitsModel.from_pretrained("facebook/mms-tts-kan", local_files_only=True)
mod_kn.eval()
ws2, priv2 = get_ram_mb()
print(f"3. After MMS-TTS (kan):          WS={ws2:6.2f} MB | Private={priv2:6.2f} MB | Delta: +{ws2 - ws1:.2f} MB")
print(f"4. Total TTS Resident Overhead:  WS=+{ws2 - ws0:.2f} MB | Private=+{priv2 - priv0:.2f} MB")
print("=" * 80)
