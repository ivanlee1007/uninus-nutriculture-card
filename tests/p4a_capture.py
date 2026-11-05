"""Owned immutable source/test snapshots and bounded raw child capture."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from datetime import datetime, timezone
ROOT=Path(__file__).resolve().parents[1]
out=ROOT.parent/'_card-work'/sys.argv[1]
out.mkdir(parents=True,exist_ok=False)
files=['uninus-nutriculture-card.js','tests/p4a_browser.py','tests/p4a_capture.py','tests/check.py']
hashes={}
for name in files:
    data=(ROOT/name).read_bytes();dest=out/'snapshot'/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data)
    hashes[name]=hashlib.sha256(data).hexdigest()
env=dict(os.environ,CHROMIUM_EXECUTABLE='C:/Users/ivanl/AppData/Local/ms-playwright/chromium-1248/chrome-win64/chrome.exe',BROWSER_EVIDENCE_DIR=str(out/'browser'))
cmd=['D:/UNiNUS Projects/AI project/uninus-nutriculture-card/.venv/Scripts/python.exe','-m','unittest','discover','-s','tests','-p','p4a_browser.py','-v']
if len(sys.argv)>2:cmd=['npm.cmd','test']
with (out/'child.log').open('wb') as f:
    p=subprocess.Popen(cmd,cwd=ROOT,env=env,stdout=f,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
    try:code=p.wait(timeout=180)
    except subprocess.TimeoutExpired:
        subprocess.run(['taskkill','/PID',str(p.pid),'/T','/F'],stdout=f,stderr=subprocess.STDOUT);p.wait(timeout=15);code=124
raw=(out/'child.log').read_text(encoding='utf-8',errors='replace')
(out/'result.json').write_text(json.dumps({'command':cmd,'returncode':code,'timestamp':datetime.now(timezone.utc).isoformat(),'sha256':hashes},indent=2))
print(raw);print('CHILD_EXIT='+str(code));print('EVIDENCE='+str(out));sys.exit(code)
