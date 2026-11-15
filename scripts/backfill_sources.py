# Explicit development migration for current snapshots only; no invented historical text.
import sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from backend.store import Store
store=Store(Path(__file__).resolve().parents[1]/'work/clinic.sqlite');count=0
with store.tx() as c:
 for row in c.execute('SELECT tenant,id,body FROM encounters').fetchall():
  e=json.loads(row['body'])
  if not c.execute('SELECT 1 FROM source_versions WHERE tenant=? AND encounter=? AND version=?',(row['tenant'],row['id'],e['sourceVersion'])).fetchone():
   import time
   c.execute('INSERT INTO source_versions VALUES(?,?,?,?,?)',(row['tenant'],row['id'],e['sourceVersion'],e['transcript'],time.time()));store.event(c,row['tenant'],row['id'],'current_source_snapshot_backfilled');count+=1
print({'current_snapshots_backfilled':count,'unavailable_historical_versions_reconstructed':False})
