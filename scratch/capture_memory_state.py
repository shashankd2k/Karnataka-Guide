import json
import subprocess
import os
import sys

def get_memory_telemetry():
    # Windows Free RAM
    win_free_mb = 0.0
    try:
        out = subprocess.check_output(
            ["powershell", "-Command", "[math]::Round((Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory / 1024, 1)"],
            text=True, timeout=10
        ).strip()
        win_free_mb = float(out)
    except Exception as e:
        win_free_mb = str(e)

    # WSL MemAvailable and Swap
    wsl_avail_mb = 0.0
    wsl_swap_used_mb = 0.0
    try:
        out = subprocess.check_output(
            ["docker", "exec", "karnatakaguide-backend-1", "cat", "/proc/meminfo"],
            text=True, timeout=10
        )
        meminfo = {}
        for line in out.splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                parts = v.strip().split()
                if parts and parts[0].isdigit():
                    meminfo[k.strip()] = int(parts[0])
        wsl_avail_mb = round(meminfo.get("MemAvailable", 0) / 1024.0, 1)
        swap_total = meminfo.get("SwapTotal", 0)
        swap_free = meminfo.get("SwapFree", 0)
        wsl_swap_used_mb = round((swap_total - swap_free) / 1024.0, 1)
    except Exception as e:
        wsl_avail_mb = str(e)

    # Container RSS using docker stats
    backend_rss_mb = 0.0
    ollama_rss_mb = 0.0
    mysql_rss_mb = 0.0
    try:
        out = subprocess.check_output(
            ["docker", "stats", "--no-stream", "--format", "{{.Name}}:{{.MemUsage}}"],
            text=True, timeout=15
        )
        for line in out.strip().splitlines():
            if ":" in line:
                name, usage = line.split(":", 1)
                # usage format: "498.1MiB / 3.696GiB"
                mem_part = usage.split("/")[0].strip()
                val = 0.0
                if "GiB" in mem_part:
                    val = float(mem_part.replace("GiB", "").strip()) * 1024.0
                elif "MiB" in mem_part:
                    val = float(mem_part.replace("MiB", "").strip())
                elif "KiB" in mem_part:
                    val = float(mem_part.replace("KiB", "").strip()) / 1024.0

                if "backend" in name:
                    backend_rss_mb = round(val, 1)
                elif "ollama" in name:
                    ollama_rss_mb = round(val, 1)
                elif "mysql" in name:
                    mysql_rss_mb = round(val, 1)
    except Exception as e:
        pass

    # Runner PID in ollama container
    runner_pid = None
    try:
        out = subprocess.check_output(
            ["docker", "exec", "karnatakaguide-ollama-1", "sh", "-c", "ps -o pid,comm 2>/dev/null || cat /proc/[0-9]*/cmdline 2>/dev/null"],
            text=True, timeout=10
        )
        for line in out.splitlines():
            if "runner" in line or "llama" in line:
                parts = line.strip().split()
                if parts and parts[0].isdigit():
                    runner_pid = parts[0]
                    break
        if not runner_pid:
            # Check pgrep or directory check in /proc
            check_pids = subprocess.check_output(
                ["docker", "exec", "karnatakaguide-ollama-1", "sh", "-c", 
                 "for p in /proc/[0-9]*; do if grep -q 'runner' $p/cmdline 2>/dev/null; then basename $p; fi; done"],
                text=True, timeout=10
            ).strip()
            if check_pids:
                runner_pid = check_pids.split()[0]
    except Exception:
        pass

    # Loaded models in Ollama via backend curl
    loaded_models = []
    try:
        out = subprocess.check_output(
            ["docker", "exec", "karnatakaguide-backend-1", "curl", "-s", "http://ollama:11434/api/ps"],
            text=True, timeout=10
        )
        data = json.loads(out)
        loaded_models = [m.get("name") for m in data.get("models", [])]
    except Exception as e:
        loaded_models = str(e)

    return {
        "windows_free_ram_mb": win_free_mb,
        "wsl_avail_mem_mb": wsl_avail_mb,
        "wsl_swap_used_mb": wsl_swap_used_mb,
        "backend_rss_mb": backend_rss_mb,
        "ollama_rss_mb": ollama_rss_mb,
        "mysql_rss_mb": mysql_rss_mb,
        "runner_pid": runner_pid,
        "ollama_loaded_models": loaded_models
    }

if __name__ == "__main__":
    telem = get_memory_telemetry()
    print(json.dumps(telem, indent=2))
