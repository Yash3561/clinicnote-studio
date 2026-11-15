"""Optional local CPU int8 transcription. No automatic speaker identity inference."""
import io,os,threading
from pathlib import Path
_model=None
_lock=threading.Lock()
def transcribe_bytes(content):
 global _model
 if not content:raise ValueError('Audio required')
 with _lock:
  from faster_whisper import WhisperModel
  if _model is None:_model=WhisperModel(os.environ.get('CLINIC_WHISPER_MODEL','small.en'),device='cpu',compute_type='int8',cpu_threads=4,download_root=str(Path(__file__).resolve().parents[1]/'work/speech-models'))
  segments,info=_model.transcribe(io.BytesIO(content),beam_size=1,vad_filter=True,condition_on_previous_text=False)
  output=[{'start':s.start,'end':s.end,'text':s.text.strip(),'speaker':'unknown'} for s in segments]
  if not output:raise ValueError('No speech detected; do not generate an empty successful note')
  return {'model':os.environ.get('CLINIC_WHISPER_MODEL','small.en'),'segments':output,'transcript':'\n'.join('Unknown: '+s['text'] for s in output),'speaker_confirmation_required':True,'clinical_validated':False}
