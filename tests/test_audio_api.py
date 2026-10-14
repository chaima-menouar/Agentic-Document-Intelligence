from fastapi.testclient import TestClient
from app.web.api import app
from app.audio import routes
from app.audio.service import summarize_transcript

client = TestClient(app, headers={'X-ADI-Request':'1'})


def test_extractive_notes_do_not_invent_tasks():
    text='The pilot launches on 12 November. We will send the report on Friday. What is the budget?'
    result=summarize_transcript(text)
    assert result['summary']
    assert all(line in text for line in result['summary'])
    assert result['action_candidates']==['We will send the report on Friday.']
    assert result['questions']==['What is the budget?']
    assert summarize_transcript('The pilot has three teams.')['action_candidates']==[]


def test_summary_validation_and_app_header():
    assert client.post('/api/audio/summary',json={'text':'   '}).status_code==400
    assert client.post('/api/audio/summary',json={'text':'a'*20001}).status_code==422
    assert TestClient(app).post('/api/audio/summary',json={'text':'test'}).status_code==403
    result=client.post('/api/audio/summary',json={'text':'The pilot starts in November. We must confirm the schedule.'})
    assert result.status_code==200
    assert result.json()['method']=='extractive'


def test_transcription_validation_and_tempfile_cleanup(monkeypatch):
    monkeypatch.setattr(routes,'audio_available',lambda:True)
    saved=[]
    def fake(path, language):
        from pathlib import Path
        p=Path(path);assert p.exists();saved.append(p)
        assert language=='fr'
        return {'text':'Bonjour.', 'segments':[], 'language':'fr'}
    monkeypatch.setattr(routes,'transcribe_audio',fake)
    assert client.post('/api/audio/transcribe',files={'file':('bad.txt',b'audio')}).status_code==400
    assert client.post('/api/audio/transcribe',files={'file':('empty.wav',b'')}).status_code==400
    assert client.post('/api/audio/transcribe',files={'file':('big.wav',b'x'*(routes.MAX_AUDIO_BYTES+1))}).status_code==413
    result=client.post('/api/audio/transcribe',files={'file':('clip.wav',b'fake audio')},data={'language':'fr'})
    assert result.status_code==200
    assert result.json()['text']=='Bonjour.'
    assert all(not p.exists() for p in saved)
    assert client.post('/api/audio/transcribe',files={'file':('clip.wav',b'audio')},data={'language':'xx'}).status_code==422


def test_disabled_audio_is_honest(monkeypatch):
    monkeypatch.setattr(routes,'audio_available',lambda:False)
    assert not client.get('/api/audio/capabilities').json()['transcription']
    assert client.post('/api/audio/transcribe',files={'file':('clip.wav',b'audio')}).status_code==503
