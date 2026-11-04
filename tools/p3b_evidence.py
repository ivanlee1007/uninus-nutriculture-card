"""Append-only child evidence with pre/post source receipts."""
import sys,os,json,hashlib,datetime,subprocess,shutil
from pathlib import Path
root=Path(__file__).resolve().parents[1]
dest=root/'docs/evidence'/sys.argv[1]
dest.mkdir(parents=True,exist_ok=False)
files=[root/'demo/index.html',*list((root/'tests/fixtures').glob('*.json')),root/'uninus-nutriculture-card.js',*list((root/'tests').rglob('*.cjs')),*list((root/'tests').rglob('*.py'))]
def receipt():return {str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
before=receipt()
for p in files:
 t=dest/'snapshot'/p.relative_to(root);t.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,t)
r=subprocess.run(sys.argv[2:],cwd=root,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=150)
(dest/'raw.log').write_bytes(r.stdout)
(dest/'run.json').write_text(json.dumps({'timestamp':datetime.datetime.now(datetime.UTC).isoformat(),'command':sys.argv[2:],'child_exit':r.returncode,'source_before':before,'source_after':receipt()},indent=2))
print(r.stdout.decode(errors='replace'));sys.exit(r.returncode)
