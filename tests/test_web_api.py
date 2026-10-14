"""HTTP/session integration tests; no network or downloaded ML models needed."""
import json
from pathlib import Path
from types import SimpleNamespace

import fitz
import pytest
from fastapi.testclient import TestClient

from app.web import api
from app.ui.workspace import prepare_uploaded_pdfs, WorkspaceBuildResult
from app.retrieval import RetrievalHit


class FixtureRetriever:
    def __init__(self, path):
        self.chunks = [json.loads(line) for line in Path(path).read_text().splitlines()]

    def search(self, query, *, top_k=5):
        return [RetrievalHit(rank=i+1, score=.9, **{key:c[key] for key in ('dataset','document_id','chunk_id','source_id','text','page_number','section','metadata')}) for i,c in enumerate(self.chunks[:top_k])]

    def search_many_scoped(self, queries, document_ids, *, top_k=5):
        return [[h for h in self.search(q, top_k=top_k) if h.document_id==d] for q,d in zip(queries,document_ids)]


@pytest.fixture
def clients(monkeypatch):
    api.cleanup()
    api._sessions.clear()
    def build(uploads,directory,**kwargs):
        chunks,docs,total=prepare_uploaded_pdfs(uploads,directory,ocr_fallback=False)
        return WorkspaceBuildResult(directory,directory,chunks,docs,total,{})
    monkeypatch.setattr(api,'build_local_workspace',build)
    monkeypatch.setattr(api.SemanticRetriever,'load',lambda directory: FixtureRetriever(directory/'processed'/'chunks.jsonl'))
    yield TestClient(api.app,headers={'X-ADI-Request':'1'}),TestClient(api.app,headers={'X-ADI-Request':'1'})
    api.cleanup()
    api._sessions.clear()


def pdf():
    doc=fitz.open()
    page=doc.new_page()
    page.insert_text((50,50),'The study found that caching reduces latency by 30 percent. Cached answers avoid repeated computation.')
    data=doc.tobytes()
    doc.close()
    return data


def test_upload_question_source_feedback_and_session_isolation(clients):
    a,b=clients
    assert a.get('/api/workspace').json()['documents']==[]
    upload=a.post('/api/documents',files={'files':('paper.pdf',pdf(),'application/pdf')},data={'ocr':'false'})
    assert upload.status_code==200, upload.text
    document=upload.json()['documents'][0]
    doc_id=document['document_id']
    assert a.get(f'/api/documents/{doc_id}/source').content.startswith(b'%PDF-')
    assert 'caching' in a.get(f'/api/documents/{doc_id}/chunks').json()[0]['text']
    assert b.get('/api/workspace').json()['documents']==[]
    assert b.get(f'/api/documents/{doc_id}/source').status_code==404
    answer=a.post('/api/ask',json={'question':'How does caching affect latency?','document_id':doc_id,'verifier':'lexical'})
    assert answer.status_code==200, answer.text
    data=answer.json()
    assert data['citations'] and data['verifications']
    assert '30 percent' in data['final_answer']
    assert a.post(f"/api/answers/{data['id']}/feedback",json={'rating':'useful'}).status_code==200
    assert a.get('/api/workspace').json()['feedback'][data['id']]['rating']=='useful'
    assert b.post('/api/ask',json={'question':'Question'}).status_code==409
    assert a.delete('/api/workspace').json()['documents']==[]
    assert a.get(f'/api/documents/{doc_id}/source').status_code==404


def test_failed_replacement_preserves_original_and_validates_requests(clients,monkeypatch):
    a,_=clients
    original=a.post('/api/documents',files={'files':('paper.pdf',pdf(),'application/pdf')}).json()
    assert a.post('/api/documents',files={'files':('bad.pdf',b'not a pdf','application/pdf')}).status_code==400
    def fail(*args,**kwargs):
        raise ValueError('extraction failed')
    monkeypatch.setattr(api,'build_local_workspace',fail)
    assert a.post('/api/documents',files={'files':('paper.pdf',pdf(),'application/pdf')}).status_code==422
    assert a.get('/api/workspace').json()['documents']==original['documents']
    assert a.post('/api/ask',json={'question':'   '}).status_code==400
    assert a.post('/api/ask',json={'question':'hi','top_k':99}).status_code==422
    assert a.post('/api/ask',json={'question':'hi','document_id':'other-session'}).status_code==404
    outsider=TestClient(api.app)
    assert outsider.post('/api/ask',json={'question':'hi'}).status_code==403


def test_revision_prevents_stale_question_and_destructive_actions(clients):
    a,_=clients
    first=a.post('/api/documents',files={'files':('one.pdf',pdf(),'application/pdf')}).json()
    second=a.post('/api/documents',files={'files':('two.pdf',pdf(),'application/pdf')},headers={'X-ADI-Workspace':first['revision']}).json()
    assert second['revision'] != first['revision']
    stale={'X-ADI-Workspace':first['revision']}
    assert a.delete('/api/workspace',headers=stale).status_code==409
    assert a.post('/api/documents',files={'files':('three.pdf',pdf(),'application/pdf')},headers=stale).status_code==409
    answer=a.post('/api/ask',json={'question':'What reduces latency?','workspace_revision':first['revision']})
    assert answer.status_code==409
    assert answer.json()['detail']['code']=='workspace_changed'
    assert a.get('/api/workspace').json()['documents']==second['documents']


def test_question_retry_is_idempotent_and_rejects_reused_id(clients,monkeypatch):
    a,_=clients
    workspace=a.post('/api/documents',files={'files':('one.pdf',pdf(),'application/pdf')}).json()
    calls=[]
    def answer(*args):
        calls.append(1)
        return {'question':'What reduces latency?', 'final_answer':'Caching reduces latency. [S1]'}
    monkeypatch.setattr(api,'answer_question',answer)
    payload={'question':'What reduces latency?','request_id':'test-retry-123','workspace_revision':workspace['revision']}
    first=a.post('/api/ask',json=payload)
    second=a.post('/api/ask',json=payload)
    assert first.status_code==second.status_code==200
    assert first.json()==second.json()
    assert len(calls)==1
    assert len(a.get('/api/workspace').json()['history'])==1
    conflict=a.post('/api/ask',json={**payload,'question':'A different question?'})
    assert conflict.status_code==409
    assert conflict.json()['detail']['code']=='request_conflict'


def test_capabilities_and_unconfigured_local_model(clients,monkeypatch):
    a,_=clients
    monkeypatch.delenv('ADI_LOCAL_LLM_URL',raising=False)
    caps=a.get('/api/capabilities')
    assert caps.status_code==200
    assert caps.json()['limits']['pdf_bytes']==api.MAX_BYTES
    assert caps.json()['storage']=='temporary'
    assert not caps.json()['local_model_configured']
    a.post('/api/documents',files={'files':('one.pdf',pdf(),'application/pdf')})
    response=a.post('/api/ask',json={'question':'What reduces latency?','generator':'local'})
    assert response.status_code==400
    assert 'not configured' in response.json()['detail']
