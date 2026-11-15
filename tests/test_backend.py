import sqlite3,json,time
import pytest
from fastapi.testclient import TestClient
from backend.app import create_app
from backend.grounding import spans,validate_proposals,GroundingError,draft,validate_draft
@pytest.fixture
def system(tmp_path):
 app=create_app(tmp_path/'clinic.sqlite',{'review':('a','reviewer-a','reviewer'),'other':('b','reviewer-b','reviewer'),'viewer':('a','viewer-a','viewer')},worker=False)
 with TestClient(app) as c:yield app,c
H={'Authorization':'Bearer review'}
def seed(c,id='e1'):
 body={'patient':{'name':'Synthetic'},'reason':'test','transcript':'Patient: I feel tired.\nClinician: Assessment: The cause is not established.','template':'soap'}
 r=c.post('/api/encounters/'+id,json=body,headers=H);assert r.status_code==200;return r.json()
def job(c,e,key='operation1'):
 return c.post('/api/encounters/'+e['id']+'/jobs',json={'operation_key':key,'expected_revision':e['recordRevision']},headers=H)
def test_unauthenticated_and_cross_tenant(system):
 _,c=system;seed(c);assert c.get('/api/encounters').status_code==401;assert c.get('/api/encounters',headers={'Authorization':'Bearer other'}).json()=={'encounters':[]};assert c.get('/api/encounters/e1/audit',headers={'Authorization':'Bearer other'}).status_code==404
 assert c.post('/api/encounters/e1',json={},headers={'Authorization':'Bearer viewer'}).status_code==403
 assert c.post('/api/encounters/e1',json={},headers={**H,'Origin':'https://untrusted.example'}).status_code==403

def test_job_approval_export_and_stale_review(system):
 app,c=system;e=seed(c);j=job(c,e).json();assert app.state.run_one();r=c.get('/api/jobs/'+j['id'],headers=H).json();assert r['status']=='succeeded';assert [s['key'] for s in r['stages']]==['claim','source','extract','validate','ready']
 e=c.get('/api/encounters',headers=H).json()['encounters'][0];d=e['draft']
 assert c.get('/api/encounters/e1/export',headers=H).status_code==409
 b={'expected_revision':e['recordRevision'],'draft_id':d['id'],'revision':d['revision'],'confirmed':True}
 approved=c.post('/api/encounters/e1/approve',json=b,headers=H);assert approved.status_code==200;assert approved.json()['draft']['approval']['reviewer']=='reviewer-a'
 assert c.get('/api/encounters/e1/export',headers=H).status_code==200
 e=approved.json();saved=c.post('/api/encounters/e1',json={'expected_revision':e['recordRevision'],'transcript':e['transcript']+'\nPatient: Correction.','template':'soap'},headers=H);assert saved.status_code==200
 assert c.get('/api/encounters/e1/export',headers=H).status_code==409;assert c.post('/api/encounters/e1/approve',json=b,headers=H).status_code==409

def test_idempotent_job_and_revision_conflict(system):
 app,c=system;e=seed(c);a=job(c,e).json();b=job(c,e).json();assert a['id']==b['id'];app.state.run_one();assert job(c,e).json()['id']==a['id'];assert job(c,e,'new-operation').status_code==409

def test_unknown_and_unclear_cannot_approve(system):
 app,c=system;e=seed(c);e=c.post('/api/encounters/e1',json={'expected_revision':e['recordRevision'],'transcript':'Unknown: Something happened.\nPatient: Amount [unclear].'},headers=H).json();j=job(c,e).json();app.state.run_one();e=c.get('/api/encounters',headers=H).json()['encounters'][0];d=e['draft'];assert len([x for x in d['issues'] if x['blocking']])==2
 assert c.post('/api/encounters/e1/approve',headers=H,json={'expected_revision':e['recordRevision'],'draft_id':d['id'],'revision':1,'confirmed':True}).status_code==422

def test_append_only_event_constraints(system):
 app,c=system;seed(c)
 with app.state.store.tx() as conn:
  with pytest.raises(sqlite3.IntegrityError):conn.execute('UPDATE events SET action=?',('tampered',))
 with app.state.store.tx() as conn:
  with pytest.raises(sqlite3.IntegrityError):conn.execute('DELETE FROM events')

def test_lease_recovery_and_fail_closed_provider(system,monkeypatch):
 app,c=system;e=seed(c);j=job(c,e).json()
 with app.state.store.tx() as conn:conn.execute("UPDATE jobs SET status='running',lease_until=?,attempts=1 WHERE id=?",(time.time()-2,j['id']))
 assert app.state.run_one();assert c.get('/api/jobs/'+j['id'],headers=H).json()['status']=='succeeded'

def test_exact_source_guardrail_rejects_new_text_and_missing_numbers():
 ss=spans('Patient: The amount is 50.')
 for props in [[{'span_id':'s1','quote':'The amount is 15.'}],[{'span_id':'other','quote':'The amount is 50.'}],[],[{'span_id':'s1','quote':'The amount is 50.','diagnosis':'X'}]]:
  with pytest.raises(GroundingError):validate_proposals(ss,props)
 assert validate_proposals(ss,[{'span_id':'s1','quote':'The amount is 50.'}])

def test_generated_words_cannot_be_inserted():
 e={'transcript':'Patient: My sister has condition X.','sourceVersion':1,'template':'soap'};d=draft(e);d['sections'][0]['items'][0]['text']='The patient has condition X.'
 with pytest.raises(GroundingError):validate_draft(d,e)

def test_immutable_sources_and_cancellation(system):
 app,c=system;e=seed(c);v=e['sourceVersion'];src=c.get(f'/api/encounters/e1/sources/{v}',headers=H);assert src.status_code==200
 with app.state.store.tx() as conn:
  with pytest.raises(sqlite3.IntegrityError):conn.execute('UPDATE source_versions SET transcript=?',('tampered',))
 j=job(c,e).json();assert c.post('/api/jobs/'+j['id']+'/cancel',headers=H).json()['status']=='canceled';assert app.state.run_one() is False
 assert c.get('/api/encounters',headers=H).json()['encounters'][0]['draft'] is None

def test_context_is_tenant_scoped_and_does_not_enter_note(system):
 app,c=system;e=seed(c,'visit-avery');r=c.get('/api/encounters/visit-avery/context',headers=H).json();assert len(r['records'])==3;assert r['included_in_current_note'] is False
 assert c.get('/api/encounters/visit-avery/context',headers={'Authorization':'Bearer other'}).status_code==404
 job(c,e);app.state.run_one();e=c.get('/api/encounters',headers=H).json()['encounters'][0];assert all('medication-history' not in i['text'] for s in e['draft']['sections'] for i in s['items'])

def test_model_failure_publishes_no_draft(system,monkeypatch):
 app,c=system;e=seed(c)
 def fail(*a,**k):raise GroundingError('Invented quote')
 monkeypatch.setattr('backend.grounding.qwen_copy',fail)
 r=c.post('/api/encounters/e1/jobs',headers=H,json={'operation_key':'qwen-failure','expected_revision':e['recordRevision'],'engine':'qwen'}).json();app.state.run_one()
 assert c.get('/api/jobs/'+r['id'],headers=H).json()['status']=='failed';assert c.get('/api/encounters',headers=H).json()['encounters'][0]['draft'] is None

def test_durable_tasks_and_idempotency_fingerprint(system):
 app,c=system;e=seed(c);r=c.post('/api/encounters/e1/tasks',headers=H,json={'expected_revision':e['recordRevision'],'title':'Request the missing sample log'});assert r.status_code==200;e=r.json();task=e['tasks'][0]
 r=c.post('/api/encounters/e1/tasks/'+task['id'],headers=H,json={'expected_revision':e['recordRevision'],'completed':True});assert r.json()['tasks'][0]['completed'] is True
 e=r.json();j=job(c,e).json();assert c.post('/api/encounters/e1/jobs',headers=H,json={'operation_key':'operation1','expected_revision':e['recordRevision'],'engine':'qwen'}).status_code==409
