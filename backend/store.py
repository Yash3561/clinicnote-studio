import sqlite3,json,time,contextlib
from pathlib import Path
SCHEMA='''
CREATE TABLE IF NOT EXISTS encounters (tenant TEXT NOT NULL,id TEXT NOT NULL,revision INTEGER NOT NULL,body TEXT NOT NULL,PRIMARY KEY(tenant,id));
CREATE TABLE IF NOT EXISTS jobs (id TEXT PRIMARY KEY,tenant TEXT NOT NULL,encounter TEXT NOT NULL,source_version INTEGER NOT NULL,operation_key TEXT NOT NULL,status TEXT NOT NULL,lease_until REAL,attempts INTEGER NOT NULL DEFAULT 0,body TEXT NOT NULL,UNIQUE(tenant,encounter,operation_key));
CREATE TABLE IF NOT EXISTS events (seq INTEGER PRIMARY KEY AUTOINCREMENT,tenant TEXT NOT NULL,encounter TEXT,action TEXT NOT NULL,created REAL NOT NULL);
CREATE TRIGGER IF NOT EXISTS events_no_update BEFORE UPDATE ON events BEGIN SELECT RAISE(ABORT,'Append-only events'); END;
CREATE TRIGGER IF NOT EXISTS events_no_delete BEFORE DELETE ON events BEGIN SELECT RAISE(ABORT,'Append-only events'); END;
PRAGMA user_version=1;
'''
MIGRATION2='CREATE TABLE IF NOT EXISTS context_records(tenant TEXT NOT NULL,patient TEXT NOT NULL,id TEXT NOT NULL,body TEXT NOT NULL,PRIMARY KEY(tenant,patient,id));\nCREATE INDEX IF NOT EXISTS jobs_ready ON jobs(status,lease_until);\nPRAGMA user_version=2;'
MIGRATION3="CREATE TABLE IF NOT EXISTS source_versions(tenant TEXT NOT NULL,encounter TEXT NOT NULL,version INTEGER NOT NULL,transcript TEXT NOT NULL,created REAL NOT NULL,PRIMARY KEY(tenant,encounter,version));\nCREATE TRIGGER IF NOT EXISTS sources_no_update BEFORE UPDATE ON source_versions BEGIN SELECT RAISE(ABORT,'Immutable source version'); END;\nCREATE TRIGGER IF NOT EXISTS sources_no_delete BEFORE DELETE ON source_versions BEGIN SELECT RAISE(ABORT,'Immutable source version'); END;\nPRAGMA user_version=3;"
class Conflict(Exception):pass
class Store:
 def __init__(self,path):
  self.path=str(path);Path(path).parent.mkdir(parents=True,exist_ok=True);c=self.connect()
  version=c.execute('PRAGMA user_version').fetchone()[0]
  if version==0:c.executescript(SCHEMA);version=1
  if version==1:c.executescript(MIGRATION2);version=2
  if version==2:c.executescript(MIGRATION3);version=3
  if version!=3:raise RuntimeError('Unsupported schema revision')
  c.close()
 def connect(self):
  c=sqlite3.connect(self.path,timeout=10);c.row_factory=sqlite3.Row;c.execute('PRAGMA journal_mode=WAL');return c
 @contextlib.contextmanager
 def tx(self):
  c=self.connect()
  try:c.execute('BEGIN IMMEDIATE');yield c;c.commit()
  except: c.rollback();raise
  finally:c.close()
 def event(self,c,tenant,id,action):c.execute('INSERT INTO events(tenant,encounter,action,created) VALUES(?,?,?,?)',(tenant,id,action,time.time()))
 def get(self,tenant,id,c=None):
  own=c is None;c=c or self.connect()
  try:
   row=c.execute('SELECT revision,body FROM encounters WHERE tenant=? AND id=?',(tenant,id)).fetchone()
   if not row:return None
   e=json.loads(row['body']);e['recordRevision']=row['revision'];return e
  finally:
   if own:c.close()
 def put(self,c,tenant,e,expected=None):
  body=json.dumps({k:v for k,v in e.items() if k!='recordRevision'})
  if expected is None:c.execute('INSERT INTO encounters VALUES(?,?,1,?)',(tenant,e['id'],body));return 1
  n=c.execute('UPDATE encounters SET revision=revision+1,body=? WHERE tenant=? AND id=? AND revision=?',(body,tenant,e['id'],expected)).rowcount
  if n!=1:raise Conflict('Record changed; reload before saving')
  return expected+1
