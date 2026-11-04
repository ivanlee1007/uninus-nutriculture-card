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
files = ['uninus-nutriculture-card.js','tests/test_browser.py','tests/record_run.py','demo/index.html']
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
os.environ['BROWSER_EVIDENCE_DIR'] = str(out/'browser')
timed_out = False
with (out/'output.log').open('wb') as log:
    child = subprocess.Popen(command,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0)
    try:
        returncode = child.wait(timeout=120)
    except subprocess.TimeoutExpired:
        timed_out = True
        if os.name == 'nt':
            subprocess.run(['taskkill','/PID',str(child.pid),'/T','/F'],stdout=log,stderr=subprocess.STDOUT)
        else:
            child.kill()
        child.wait(timeout=15)
        returncode = 124
raw = (out/'output.log').read_bytes()
(out/'result.json').write_text(json.dumps({'command':command,'started_utc':started,'returncode':returncode,'timed_out':timed_out,'sha256':hashes,'python':sys.version,'chromium_executable':os.environ.get('CHROMIUM_EXECUTABLE')},indent=2),encoding='utf-8')
print(raw.decode('utf-8',errors='replace'))
sys.exit(returncode)
