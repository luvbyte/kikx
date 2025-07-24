from neko.lib import panel, js
import json
from neko.lib.process import sh
from neko.lib.console import Console
from datetime import datetime

import subprocess

code = r"""
<div class="w-full h-full bg-black text-white font-mono flex flex-col">
  <!-- Top Banner -->
  <div class="h-[200px] bg-gray-900 border-b border-gray-700 p-1 overflow-auto">
    <pre class="flex w-full h-full text-xs leading-tight whitespace-pre-wrap text-center justify-center items-center">
_   __  __ ___ 
| \ | \ \/ / __|
|  \| |>  <\__ \
|_|\__/_/\_\___/

NXS: ui for nmap

Created for florix/neko
    </pre>
  </div>

  <!-- Bottom Panel -->
  <div class="flex-1 bg-black p-4 flex flex-col justify-between">
    <!-- Options Section -->
    <div class="space-y-3 text-sm overflow-y-auto">

      <div class="flex items-center justify-between">
        <label>Target IP / Host</label>
        <input id="target" type="text" value="localhost" class="bg-gray-700 text-white text-xs px-2 py-1 rounded w-40 focus:outline-none" />
      </div>

      <div class="flex items-center justify-between">
        <label>Port Range</label>
        <input id="ports" type="text" placeholder="ex: 1-1000" class="bg-gray-700 text-white text-xs px-2 py-1 rounded w-40 focus:outline-none" />
      </div>

      <!-- Scan Types -->
      <div class="flex flex-col gap-2">
        <label class="mb-1">Scan Types</label>
        <div class="grid grid-cols-2 gap-2">
          <label class="flex items-center gap-2"><input id="tcp-syn" type="checkbox" class="form-checkbox bg-gray-600" /> -sS SYN</label>
          <label class="flex items-center gap-2"><input id="udp-scan" type="checkbox" class="form-checkbox bg-gray-600" /> -sU UDP</label>
          <label class="flex items-center gap-2"><input id="os-detect" type="checkbox" class="form-checkbox bg-gray-600" /> -O OS</label>
          <label class="flex items-center gap-2"><input id="service-version" type="checkbox" class="form-checkbox bg-gray-600" /> -sV Version</label>
          <label class="flex items-center gap-2"><input id="aggressive" type="checkbox" class="form-checkbox bg-gray-600" /> -A Aggressive</label>
          <label class="flex items-center gap-2"><input id="ping" type="checkbox" class="form-checkbox bg-gray-600" /> -Pn No Ping</label>
        </div>
      </div>

      <!-- Performance & Verbosity -->
      <div class="flex flex-col gap-2">
        <label class="mb-1">Performance & Verbosity</label>
        <div class="grid grid-cols-2 gap-2">
          <label class="flex items-center gap-2"><input id="verbose" type="checkbox" class="form-checkbox bg-gray-600" /> -v Verbose</label>
          <label class="flex items-center gap-2"><input id="debug" type="checkbox" class="form-checkbox bg-gray-600" /> -d Debug</label>
          <label class="flex items-center gap-2"><input id="timing" type="checkbox" class="form-checkbox bg-gray-600" /> -T4 Timing</label>
          <label class="flex items-center gap-2"><input id="only-open" type="checkbox" class="form-checkbox bg-gray-600" /> --open</label>
        </div>
      </div>

      <!-- Extra Arguments -->
      <div class="flex flex-col gap-3">
        <label>Extra Args</label>
        <input id="extra" type="text" placeholder="e.g. --script=http-title" class="bg-gray-700 text-white text-xs px-2 py-1 rounded w-full focus:outline-none" />
      </div>

      <!-- Start Button -->
      <div class="pt-4">
        <button
          onclick="triggerScan()"
          class="w-full bg-green-500 hover:bg-green-600 text-black font-bold py-2 rounded transition"
        >
          ▶ Start Scan
        </button>
      </div>

    </div>
  </div>

  <!-- Script -->
  <script>
    function triggerScan() {
      const payload = {
        type: "nmap",
        target: document.getElementById("target").value.trim(),
        ports: document.getElementById("ports").value.trim(),
        flags: {
          syn: document.getElementById("tcp-syn").checked,
          udp: document.getElementById("udp-scan").checked,
          os: document.getElementById("os-detect").checked,
          service: document.getElementById("service-version").checked,
          aggressive: document.getElementById("aggressive").checked,
          ping: document.getElementById("ping").checked,
          verbose: document.getElementById("verbose").checked,
          debug: document.getElementById("debug").checked,
          timing: document.getElementById("timing").checked,
          onlyOpen: document.getElementById("only-open").checked
        },
        extra: document.getElementById("extra").value.trim()
      }

      sendInput(JSON.stringify(payload))
    }
  </script>
</div>
"""

def build_nmap_command(data: dict) -> str:
    target = data.get("target", "").strip()
    ports = data.get("ports", "").strip()
    extra = data.get("extra", "").strip()
    flags = data.get("flags", {})

    if not target:
        raise ValueError("Missing target for Nmap scan.")

    options = {
        "syn": "-sS",
        "udp": "-sU",
        "os": "-O",
        "service": "-sV",
        "aggressive": "-A",
        "ping": "-Pn",
        "verbose": "-v",
        "debug": "-d",
        "timing": "-T4",
        "onlyOpen": "--open"
    }

    command = ["nmap"]

    # Append selected flags
    command += [flag for key, flag in options.items() if flags.get(key)]

    # Ports
    if ports:
        command += ["-p", ports]

    # Extra args
    if extra:
        command += extra.split()

    # Target
    command.append(target)

    return " ".join(command)


console = Console()
console.panel.replace(code)

payload = json.loads(input().strip())
command = build_nmap_command(payload)

console.clear()

# password = console.input("Type sudo password: ")
#full_command = f"echo {password} | sudo -S {command}"

def run_nmap_smart(command: str, console) -> str:
    # 1. Try without sudo
    try:
        result = subprocess.run(
            command.split(),
            capture_output=True,
            text=True
        )
        # Check for permission issues
        if "requires root" in result.stderr or "Permission denied" in result.stderr:
            raise PermissionError(result.stderr)

        return result.stdout + result.stderr

    except PermissionError:
        # 2. Ask for sudo password if needed
        password = console.input("🔒 Sudo required for this scan. Enter password: ")

        sudo_command = ["sudo", "-S"] + command.split()
        proc = subprocess.Popen(
            sudo_command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        stdout, stderr = proc.communicate(input=password + "\n")
        return stdout + stderr

def generate_nmap_result_ui(result: str, target: str = "Unknown") -> str:
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    
    return f"""
<div class="w-full h-full bg-black text-white font-mono flex flex-col text-xs">
  <!-- Header -->
  <div class="p-4 border-b border-gray-800 bg-gray-900">
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-green-400 text-xl font-bold">📡 Nmap Scan Results</h1>
        <p class="text-xs text-gray-400">Target: <span class="text-white">{target}</span></p>
        <p class="text-xs text-gray-400">Scanned at: <span class="text-white">{timestamp}</span></p>
      </div>
    </div>
  </div>

  <!-- Scan Output -->
  <div class="flex-1 overflow-y-auto p-4 bg-black text-sm leading-snug">
    <pre class="whitespace-pre-wrap text-green-300 text-xs">{result}</pre>
  </div>

  <!-- Footer -->
  <div class="p-2 text-center text-xs text-gray-500 border-t border-gray-800 bg-gray-900">
    Press ▲ / ▼ to scroll
  </div>
</div>
"""


console.pre_center("Scanning please wait")

result = run_nmap_smart(command, console)
html = generate_nmap_result_ui(result, payload.get("target"))

console.clear()
console.append(html)
