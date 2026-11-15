"""Prepare provenance-linked candidates; never treats a public target as clinically approved."""
import csv,json,hashlib
from pathlib import Path
root=Path(__file__).resolve().parents[1];base=root/'work/datasets/mts-dialog';manifest=json.loads((base/'manifest.json').read_text());counts={}
for split,name in [('train','MTS-Dialog-TrainingSet.csv'),('validation','MTS-Dialog-ValidationSet.csv')]:
 records=[]
 expected=next(x['sha256'] for x in manifest['files'] if Path(x['file']).name==name)
 if hashlib.sha256((base/name).read_bytes()).hexdigest()!=expected:raise ValueError('Dataset source checksum changed')
 with (base/name).open(encoding='utf-8-sig') as f:
  for row in csv.DictReader(f):records.append({'dataset':'MTS-Dialog','split':split,'upstream_commit':manifest['commit'],'id':row['ID'],'dialogue':row['dialogue'],'reference_section':row['section_header'],'reference_text':row['section_text'],'review_state':'unreviewed','eligible_for_finetuning':False,'source_hash':hashlib.sha256(row['dialogue'].encode()).hexdigest()})
 with (base/f'{split}-candidates.jsonl').open('w') as f:
  for row in records:f.write(json.dumps(row)+'\n')
 counts[split]=len(records)
print(json.dumps({'prepared':counts,'fine_tuning_started':False,'test_data_downloaded':False}))
