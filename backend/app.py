import asyncio,contextlib,json,os,secrets,time,uuid
from pathlib import Path
from fastapi import FastAPI,Request,HTTPException
from fastapi.responses import FileResponse,JSONResponse
from pydantic import BaseModel,ConfigDict,Field
from .store import Store,Conflict
from .grounding import draft,approvable,exportable,validate_draft,spans
ROOT=Path(__file__).resolve().parents[1]
class Save(BaseModel):
 model_config=ConfigDict(extra='forbid')
 expected_revision:int|None=None
 patient:dict|None=None
 reason:str=Field(default='',max_length=200)
 visitType:str=Field(default='Primary care',max_length=150)
 time:str='';date:str=''
 transcript:str=Field(default='',max_length=18000)
 template:str='soap'
 edits:dict[str,str]=Field(default_factory=dict,max_length=100)
class Start(BaseModel):
 model_config=ConfigDict(extra='forbid')
 operation_key:str=Field(min_length=8,max_length=120)
 expected_revision:int
 engine:str='rules'
class Approve(BaseModel):
 model_config=ConfigDict(extra='forbid')
 expected_revision:int
 draft_id:str
 revision:int
 confirmed:bool

def create_app(db=None,test_sessions=None,worker=True):
 store=Store(db or ROOT/'work/clinic.sqlite');token=secrets.token_urlsafe(32);sessions=test_sessions or {token:('demo-clinic','local-demo-clinician','reviewer')};app=FastAPI(docs_url=None,redoc_url=None);app.state.store=store
 def actor(req,write=False):
  value=req.headers.get('authorization','').removeprefix('Bearer ') or req.cookies.get('clinic_session','');a=sessions.get(value)
  if not a:raise HTTPException(401,'Authenticated local session required')
  if write and a[2]!='reviewer':raise HTTPException(403,'Reviewer permission required')
  return a
 def need(c,tenant,id):
  e=store.get(tenant,id,c)
  if not e:raise HTTPException(404,'Encounter not found')
  return e
 @app.exception_handler(Conflict)
 async def conflict(req,exc):return JSONResponse({'detail':str(exc)},409)
 @app.middleware('http')
 async def boundary(req,call):
  host=req.headers.get('host','').split(':')[0]
  if host not in ('127.0.0.1','localhost','testserver'):return JSONResponse({'detail':'Loopback host required'},403)
  origin=req.headers.get('origin')
  if origin and origin not in ('http://'+req.headers.get('host',''),'https://'+req.headers.get('host','')):return JSONResponse({'detail':'Cross-origin request rejected'},403)
  length=req.headers.get('content-length')
  if length and int(length)>30_000_000:return JSONResponse({'detail':'Payload too large'},413)
  response=await call(req);response.headers.update({'Cache-Control':'no-store','X-Content-Type-Options':'nosniff','Referrer-Policy':'no-referrer','X-Frame-Options':'SAMEORIGIN'});return response
 @app.get('/api/health')
 def health(req:Request):
  actor(req);return {'service':'clinicnote-local','storage':'sqlite','engine':'rules + optional local qwen3.5:4b exact-copy audit','speech':'optional faster-whisper','production_ready':False}
 @app.get('/api/encounters')
 def listing(req:Request):
  t,_,_=actor(req);c=store.connect()
  try:return {'encounters':[store.get(t,r['id'],c) for r in c.execute('SELECT id FROM encounters WHERE tenant=? ORDER BY rowid',(t,)).fetchall()]}
  finally:c.close()
 @app.post('/api/encounters/{id}')
 def save(id:str,body:Save,req:Request):
  t,a,_=actor(req,True)
  if body.template not in ('soap','visit'):raise HTTPException(422,'Unsupported template')
  with store.tx() as c:
   e=store.get(t,id,c);created=e is None
   if not e:
    if body.expected_revision is not None:raise Conflict('Encounter absent')
    e={'id':id,'patient':body.patient or {'name':'Synthetic patient','initials':'SP','recordId':'DEMO'},'sourceVersion':1,'draft':None,'previousDraft':None,'audit':[],'exportCount':0,'historyRecords':[]}
   elif e['recordRevision']!=body.expected_revision:raise Conflict('Stale encounter revision')
   source_changed=created or e.get('transcript','')!=body.transcript
   if source_changed and not created:e['sourceVersion']+=1
   for k in ('reason','visitType','time','date','transcript','template'):e[k]=getattr(body,k)
   if e.get('draft') and body.edits:
    byid={i['id']:i for s in e['draft']['sections'] for i in s['items']};changed=False
    for k,v in body.edits.items():
     if len(v)>5000 or k not in byid:raise HTTPException(422,'Invalid draft edit')
     if byid[k]['text']!=v:byid[k].update(text=v,origin='manual');changed=True
    if changed:e['draft']['revision']+=1;e['draft']['approval']=None
   if source_changed:c.execute('INSERT INTO source_versions VALUES(?,?,?,?,?)',(t,id,e['sourceVersion'],body.transcript,time.time()))
   if created:
    records=json.loads((ROOT/'backend/demo_context.json').read_text()).get(id,[])
    for record in records:c.execute('INSERT OR IGNORE INTO context_records VALUES(?,?,?,?)',(t,e['patient'].get('recordId',id),record['id'],json.dumps(record)))
   store.put(c,t,e,body.expected_revision);store.event(c,t,id,'encounter_saved')
  return store.get(t,id)
 @app.post('/api/encounters/{id}/jobs')
 def start(id:str,body:Start,req:Request):
  t,_,_=actor(req,True)
  if body.engine not in ('rules','qwen'):raise HTTPException(422,'Unsupported engine')
  with store.tx() as c:
   e=need(c,t,id)
   # Retry returns the same operation even if the encounter revision advanced after completion.
   old=c.execute('SELECT id,body FROM jobs WHERE tenant=? AND encounter=? AND operation_key=?',(t,id,body.operation_key)).fetchone()
   if old:
    existing=json.loads(old['body'])
    if existing['engine']!=body.engine or existing['recordRevision']!=body.expected_revision:raise Conflict('Idempotency key reused with different inputs')
    return existing
   if e['recordRevision']!=body.expected_revision:raise Conflict('Stale encounter revision')
   if not e['transcript'].strip():raise HTTPException(422,'Transcript required')
   job={'id':str(uuid.uuid4()),'status':'queued','stages':[],'engine':body.engine,'sourceVersion':e['sourceVersion'],'recordRevision':e['recordRevision']}
   c.execute('INSERT INTO jobs(id,tenant,encounter,source_version,operation_key,status,body) VALUES(?,?,?,?,?,?,?)',(job['id'],t,id,e['sourceVersion'],body.operation_key,'queued',json.dumps(job)));store.event(c,t,id,'job_queued')
  return job
 @app.get('/api/jobs/{id}')
 def job(id:str,req:Request):
  t,_,_=actor(req);c=store.connect()
  try:r=c.execute('SELECT body FROM jobs WHERE id=? AND tenant=?',(id,t)).fetchone();
  finally:c.close()
  if not r:raise HTTPException(404,'Job not found')
  return json.loads(r['body'])
 @app.post('/api/encounters/{id}/approve')
 def approval(id:str,b:Approve,req:Request):
  t,a,_=actor(req,True)
  with store.tx() as c:
   e=need(c,t,id);d=e.get('draft')
   if e['recordRevision']!=b.expected_revision or not d or d['id']!=b.draft_id or d['revision']!=b.revision:raise Conflict('Review version changed')
   if not b.confirmed or not approvable(e):raise HTTPException(422,'Current resolved draft and explicit confirmation required')
   validate_draft(d,e);d['approval']={'reviewer':a,'at':time.time(),'revision':d['revision'],'sourceVersion':e['sourceVersion']};store.put(c,t,e,e['recordRevision']);store.event(c,t,id,'reviewer_approved_exact_version')
  return store.get(t,id)
 @app.get('/api/encounters/{id}/export')
 def export(id:str,req:Request):
  t,_,_=actor(req,True)
  with store.tx() as c:
   e=need(c,t,id)
   if not exportable(e):raise Conflict('Approve the current version before export')
   store.event(c,t,id,'local_export_prepared')
  return {'schema':'clinicnote-local-export/2','syntheticDemo':True,'encounterId':id,'draft':e['draft'],'patient':e['patient'],'integrationStatus':'not_sent_to_ehr'}
 @app.get('/api/encounters/{id}/audit')
 def events(id:str,req:Request):
  t,_,_=actor(req);c=store.connect()
  try:need(c,t,id);return {'events':[dict(r) for r in c.execute('SELECT seq,action,created FROM events WHERE tenant=? AND encounter=? ORDER BY seq',(t,id))]}
  finally:c.close()
 @app.post('/api/jobs/{id}/cancel')
 def cancel(id:str,req:Request):
  t,_,_=actor(req,True)
  with store.tx() as c:
   row=c.execute('SELECT body,status FROM jobs WHERE id=? AND tenant=?',(id,t)).fetchone()
   if not row:raise HTTPException(404,'Job not found')
   body=json.loads(row['body'])
   if row['status'] in ('queued','running'):body['status']='canceled';c.execute("UPDATE jobs SET status='canceled',body=? WHERE id=?",(json.dumps(body),id))
  return body
 @app.get('/api/encounters/{id}/sources/{version}')
 def source(id:str,version:int,req:Request):
  t,_,_=actor(req);c=store.connect()
  try:
   need(c,t,id);row=c.execute('SELECT transcript,created FROM source_versions WHERE tenant=? AND encounter=? AND version=?',(t,id,version)).fetchone()
   if not row:raise HTTPException(404,'Source version not found')
   return {'version':version,'transcript':row['transcript'],'created':row['created']}
  finally:c.close()
 @app.get('/api/encounters/{id}/context')
 def context(id:str,req:Request):
  t,_,_=actor(req);c=store.connect()
  try:
   e=need(c,t,id);patient=e['patient'].get('recordId',id)
   return {'patient':patient,'records':[json.loads(r['body']) for r in c.execute('SELECT body FROM context_records WHERE tenant=? AND patient=? ORDER BY id',(t,patient))],'included_in_current_note':False}
  finally:c.close()
 @app.post('/api/encounters/{id}/tasks')
 async def task(id:str,req:Request):
  t,a,_=actor(req,True);b=await req.json()
  if not isinstance(b.get('title'),str) or not b['title'].strip() or len(b['title'])>160:raise HTTPException(422,'Short task title required')
  with store.tx() as c:
   e=need(c,t,id)
   if e['recordRevision']!=b.get('expected_revision'):raise Conflict('Task version changed')
   e.setdefault('tasks',[]).append({'id':str(uuid.uuid4()),'title':b['title'].strip(),'completed':False,'actor':a});store.put(c,t,e,e['recordRevision']);store.event(c,t,id,'clerical_task_added')
  return store.get(t,id)
 @app.post('/api/encounters/{id}/tasks/{taskid}')
 async def task_status(id:str,taskid:str,req:Request):
  t,a,_=actor(req,True);b=await req.json()
  with store.tx() as c:
   e=need(c,t,id)
   if e['recordRevision']!=b.get('expected_revision') or not isinstance(b.get('completed'),bool):raise Conflict('Task version or status invalid')
   task=next((x for x in e.get('tasks',[]) if x['id']==taskid),None)
   if not task:raise HTTPException(404,'Task not found')
   task['completed']=b['completed'];store.put(c,t,e,e['recordRevision']);store.event(c,t,id,'clerical_task_status_changed')
  return store.get(t,id)
 @app.post('/api/transcribe')
 async def transcribe(req:Request):
  actor(req,True);chunks=[];n=0
  async for chunk in req.stream():
   n+=len(chunk)
   if n>25_000_000:raise HTTPException(413,'Audio limit 25 MB')
   chunks.append(chunk)
  from .speech import transcribe_bytes
  try:return await asyncio.to_thread(transcribe_bytes,b''.join(chunks))
  except Exception:raise HTTPException(503,'Local transcription unavailable or media invalid; use transcript input and inspect server diagnostics')
 def run_one():
  with store.tx() as c:
   for expired in c.execute("SELECT id,body FROM jobs WHERE status='running' AND lease_until<? AND attempts>=2",(time.time(),)).fetchall():
    body=json.loads(expired['body']);body.update(status='failed',error='LeaseExhausted',message='Worker recovery limit reached; explicit redrive required');c.execute("UPDATE jobs SET status='failed',body=? WHERE id=?",(json.dumps(body),expired['id']))
   row=c.execute("SELECT * FROM jobs WHERE (status='queued' OR (status='running' AND lease_until<?)) AND attempts<2 ORDER BY rowid LIMIT 1",(time.time(),)).fetchone()
   if not row:return False
   job=json.loads(row['body']);job['status']='running';job['stages'].append({'key':'claim','label':'Worker claimed job','at':time.time()});c.execute("UPDATE jobs SET status='running',attempts=attempts+1,lease_until=?,body=? WHERE id=?",(time.time()+240,json.dumps(job),row['id']));e=need(c,row['tenant'],row['encounter'])
  def step(key,label):
   job['stages'].append({'key':key,'label':label,'at':time.time()})
   with store.tx() as c:c.execute('UPDATE jobs SET body=? WHERE id=?',(json.dumps(job),job['id']))
  try:
   result=draft(e,job['engine']=='qwen',step)
   with store.tx() as c:
    jobrow=c.execute('SELECT status FROM jobs WHERE id=?',(job['id'],)).fetchone()
    if not jobrow or jobrow['status']!='running':raise Conflict('Job canceled or no longer leased')
    fresh=need(c,row['tenant'],row['encounter'])
    if fresh['recordRevision']!=job['recordRevision']:raise Conflict('Source or review changed during processing')
    fresh['previousDraft']=fresh.get('draft');fresh['draft']=result;store.put(c,row['tenant'],fresh,fresh['recordRevision']);job['status']='succeeded';store.event(c,row['tenant'],row['encounter'],'draft_prepared')
  except Exception as exc:job.update(status='failed',error=type(exc).__name__,message='Draft was not accepted. Inspect source or local model; no unverified fallback was approved.')
  with store.tx() as c:c.execute("UPDATE jobs SET status=?,body=?,lease_until=NULL WHERE id=? AND status='running'",(job['status'],json.dumps(job),job['id']))
  return True
 app.state.run_one=run_one
 @contextlib.asynccontextmanager
 async def lifespan(app):
  async def loop():
   while True:
    try:await asyncio.to_thread(run_one)
    except Exception as exc:
     import logging
     logging.error('worker_cycle_failed:%s',type(exc).__name__)
    await asyncio.sleep(.2)
  task=asyncio.create_task(loop()) if worker else None
  yield
  if task:task.cancel()
 app.router.lifespan_context=lifespan
 @app.get('/')
 def index():
  response=FileResponse(ROOT/'dist/index.html');response.set_cookie('clinic_session',token,httponly=True,samesite='strict',max_age=8*3600);return response
 @app.get('/{file}')
 def asset(file:str):
  p=ROOT/'dist'/file
  if '/' in file or file.startswith('.') or p.suffix not in ('.js','.css','.md','.html','.ttf','.txt') or not p.is_file():raise HTTPException(404)
  return FileResponse(p)
 return app
app=create_app()
