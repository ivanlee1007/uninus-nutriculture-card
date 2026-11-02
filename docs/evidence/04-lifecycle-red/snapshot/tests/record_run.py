"""Capture exact source/test bytes and raw child output for each TDD gate."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
label = sys.argv[1]
out = ROOT / 'docs' / 'evidence' / label
out.mkdir(parents=True, exist_ok=False)
files = ['uninus-nutriculture-card.js','tests/test_browser.py','tests/record_run.py']
hashes = {}
for name in files:
    content = (ROOT/name).read_bytes()
    target = out/'snapshot'/name
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_bytes(content)
    hashes[name] = hashlib.sha256(content).hexdigest()
command = [sys.executable,'-m','unittest','discover','-s','tests','-p','test_browser.py','-v']
if len(sys.argv)>2:
    command = [sys.executable,'tests/test_browser.py',*sys.argv[2:],'-v']
started = datetime.datetime.now(datetime.timezone.utc).isoformat()
result = subprocess.run(command,cwd=ROOT,capture_output=True,timeout=150)
raw = result.stdout + result.stderr
(out/'output.log').write_bytes(raw)
(out/'result.json').write_text(json.dumps({'command':command,'started_utc':started,'returncode':result.returncode,'sha256':hashes,'python':sys.version,'chromium_executable':os.environ.get('CHROMIUM_EXECUTABLE')},indent=2),encoding='utf-8')
print(raw.decode('utf-8',errors='replace'))
sys.exit(result.returncode)
