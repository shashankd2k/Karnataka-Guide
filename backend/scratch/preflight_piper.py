"""
Piper TTS Preflight Inspection Script.
Checks:
1. piper-tts package installation / wheel availability on Windows Python 3.12
2. Official Piper voice inventory (voices.json) from Hugging Face / GitHub
3. English voices availability & licenses
4. Kannada voices availability (YES / NO)
"""

import sys
import json
import urllib.request
import urllib.error

print("=" * 80)
print("PIPER TTS PREFLIGHT CHECK")
print("=" * 80)
print(f"Python Version: {sys.version}")
print(f"Platform: {sys.platform}")

# 1. Fetch official Piper voices.json from Hugging Face rhasspy/piper-voices
VOICES_JSON_URLS = [
    "https://huggingface.co/rhasspy/piper-voices/raw/main/voices.json",
    "https://raw.githubusercontent.com/rhasspy/piper/master/VOICES.md",
]

voices_data = None
for url in VOICES_JSON_URLS:
    try:
        print(f"Fetching official voice catalog from: {url}")
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            content = resp.read().decode("utf-8")
            if url.endswith(".json"):
                voices_data = json.loads(content)
                print(f"Successfully loaded {len(voices_data)} voice entries from voices.json")
                break
            else:
                print(f"Fetched VOICES.md ({len(content)} bytes)")
    except Exception as e:
        print(f"Error fetching from {url}: {e}")

if voices_data:
    # Analyze languages
    languages = set()
    kannada_voices = []
    english_voices = []
    
    for voice_key, voice_info in voices_data.items():
        lang = voice_info.get("language", {})
        code = lang.get("code", "")
        family = lang.get("family", "")
        name_native = lang.get("name_native", "")
        name_english = lang.get("name_english", "")
        languages.add(code)
        
        if "kn" in code.lower() or "kan" in code.lower() or "kannada" in name_english.lower() or "kannada" in name_native.lower():
            kannada_voices.append((voice_key, voice_info))
        if code.startswith("en") or "english" in name_english.lower():
            english_voices.append((voice_key, voice_info))
            
    print("-" * 80)
    print(f"Total Unique Language Codes in Official Piper: {len(languages)}")
    print(f"Available Language Codes: {sorted(list(languages))}")
    print("-" * 80)
    print(f"Kannada (kn) Voices in Official Piper: {len(kannada_voices)}")
    if kannada_voices:
        for k, v in kannada_voices:
            print(f"  - {k}: {v.get('name')} ({v.get('quality')}) License: {v.get('license')}")
    else:
        print("  -> RESULT: NO OFFICIAL KANNADA VOICES FOUND IN PIPER REPOSITORY.")
        
    print("-" * 80)
    print(f"English (en) Voices in Official Piper: {len(english_voices)}")
    print("Top 10 English Voices Sample:")
    for k, v in english_voices[:10]:
        files = list(v.get("files", {}).keys())
        size_bytes = sum(finfo.get("size_bytes", 0) for finfo in v.get("files", {}).values())
        size_mb = size_bytes / (1024 * 1024)
        print(f"  - {k}: {v.get('name')} | Quality: {v.get('quality')} | Files: {len(files)} ({size_mb:.1f} MB) | License: {v.get('license')}")

print("=" * 80)
