"""Owned immutable source/child evidence, frontend-only."""
import sys,os,subprocess,json,hashlib,shutil
from pathlib import Path
root=Path(__file__).resolve().parents[1]
out=root/'test-results'/sys.argv[1];out.mkdir(parents=True,exist_ok=False)
files=['uninus-nutriculture-card.js','tests/test_browser.py','tests/test_contract.cjs','tests/p3c_fixture.cjs','tests/p3b_fixture.cjs','tests/p3c_run.py','demo/index.html','docs/P3C_WIRE.json','docs/P3C_FLOW_CONTRACT.md']
files += [str(p.relative_to(root)) for p in (root/'tests/fixtures').rglob('*') if p.is_file()]
sha={}
for f in files:
 b=(root/f).read_bytes();t=out/'snapshot'/f;t.parent.mkdir(parents=True,exist_ok=True);t.write_bytes(b);sha[f]=hashlib.sha256(b).hexdigest()
env=os.environ.copy();env['CHROMIUM_EXECUTABLE']='C:/Users/ivanl/AppData/Local/ms-playwright/chromium-1248/chrome-win64/chrome.exe';env['BROWSER_EVIDENCE_DIR']=str(out/'browser')
python='D:/UNiNUS Projects/AI project/uninus-nutriculture-card/.venv/Scripts/python.exe'
cmd=[python,'-m','unittest','discover','-s','tests','-p','test_browser.py','-v'] if len(sys.argv)<3 else [python,'-m','unittest',sys.argv[2],'-v']
if len(sys.argv)>2 and sys.argv[2]=='node':cmd=[shutil.which('node'),'tests/test_contract.cjs']
with (out/'raw.log').open('wb') as log:
 p=subprocess.Popen(cmd,cwd=root,env=env,stdout=log,stderr=subprocess.STDOUT)
 try:rc=p.wait(timeout=120)
 except subprocess.TimeoutExpired:
  subprocess.run(['taskkill','/PID',str(p.pid),'/T','/F'],stdout=log,stderr=subprocess.STDOUT);rc=124
raw=(out/'raw.log').read_bytes()
(out/'result.json').write_text(json.dumps({'command':cmd,'returncode':rc,'source_sha256':sha,'raw_sha256':hashlib.sha256(raw).hexdigest()},indent=2))
print(raw.decode('utf8',errors='replace'));print('EVIDENCE',out);sys.exit(rc)
