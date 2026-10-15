import io
import json
import zipfile

from tests.test_web_api import clients, pdf
from app.web import api


def archive(entries):
    out=io.BytesIO()
    with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
        for name,data in entries:z.writestr(name,data)
    return out.getvalue()


def restore(client,data,**kwargs):
    return client.post('/api/workspace/restore',files={'file':('backup.zip',data,'application/zip')},**kwargs)


def test_roundtrip_after_server_restart_preserves_sources_history_and_transcript(clients):
    a,b=clients
    original=a.post('/api/documents',files={'files':('paper.pdf',pdf(),'application/pdf')}).json()
    answer=a.post('/api/ask',json={'question':'How does caching affect latency?','verifier':'lexical'}).json()
    a.post(f"/api/answers/{answer['id']}/feedback",json={'rating':'useful'})
    saved=a.post('/api/workspace/backup',json={'transcript':'My recorded thought.','workspace_revision':original['revision']})
    assert saved.status_code==200
    assert b.post('/api/workspace/backup',json={}).content!=saved.content
    api.cleanup();api._sessions.clear()
    result=restore(a,saved.content)
    assert result.status_code==200,result.text
    data=result.json()
    assert data['documents']==original['documents']
    assert data['history'][0]['final_answer']==answer['final_answer']
    assert data['feedback'][answer['id']]['rating']=='useful'
    assert data['transcript']=='My recorded thought.'
    assert data['revision']!=original['revision']
    doc=data['documents'][0]['document_id']
    assert a.get(f'/api/documents/{doc}/source').content.startswith(b'%PDF-')
    assert b.get(f'/api/documents/{doc}/source').status_code==404
    assert a.post('/api/ask',json={'question':'What reduces latency?','verifier':'lexical'}).status_code==200


def test_rejects_malformed_oversized_and_path_traversal_without_losing_workspace(clients,monkeypatch):
    a,_=clients
    original=a.post('/api/documents',files={'files':('paper.pdf',pdf(),'application/pdf')}).json()
    manifest=json.dumps({'format':'clario-workspace','version':1})
    for data in [b'not a zip',archive([('workspace.json',manifest),('../escape.pdf',pdf())]),archive([('workspace.json','{"version":99}')]),archive([('workspace.json',manifest),('documents/bad.pdf',b'bad')]),archive([('workspace.json',manifest),('workspace.json',manifest)])]:
        assert restore(a,data).status_code==422
        assert a.get('/api/workspace').json()['revision']==original['revision']
    monkeypatch.setattr(api,'MAX_ARCHIVE',20)
    assert restore(a,b'x'*21).status_code==413


def test_stale_restore_and_reindex_failure_preserve_workspace(clients,monkeypatch):
    a,_=clients
    original=a.post('/api/documents',files={'files':('paper.pdf',pdf(),'application/pdf')}).json()
    saved=a.post('/api/workspace/backup',json={}).content
    assert restore(a,saved,headers={'X-ADI-Workspace':'stale'}).status_code==409
    assert a.post('/api/workspace/backup',json={'workspace_revision':'stale'}).status_code==409
    def fail(*args,**kwargs):raise ValueError('failed indexing')
    monkeypatch.setattr(api,'build_local_workspace',fail)
    assert restore(a,saved).status_code==422
    assert a.get('/api/workspace').json()['revision']==original['revision']


def test_transcript_only_snapshot_and_invalid_history(clients):
    a,_=clients
    saved=a.post('/api/workspace/backup',json={'transcript':'Audio only'}).content
    assert restore(a,saved).json()['transcript']=='Audio only'
    bad=archive([('workspace.json',json.dumps({'history':[{'id':'x','verifications':'invalid'}]}))])
    assert restore(a,bad).status_code==422
