import requests,json,time,hashlib
from pathlib import Path
import argparse
parser=argparse.ArgumentParser(description='Run the hosted 20-question PDF pilot. Downloads public arXiv PDFs and creates a temporary workspace.')
parser.add_argument('--output',type=Path,required=True)
parser.add_argument('--base-url',default='https://agentic-document-intelligence.vercel.app')
args=parser.parse_args()
root=args.output;root.mkdir(parents=True,exist_ok=True)
import fitz
for paper in ['1706.03762','1810.04805','2005.11401','2004.04906','1606.05250']:
 p=root/(paper+'.pdf')
 if not p.exists():
  response=requests.get('https://arxiv.org/pdf/'+paper,timeout=60);response.raise_for_status();p.write_bytes(response.content)
  doc=fitz.open(p);target=p.with_suffix('.compressed.pdf');doc.save(target,garbage=4,deflate=True);doc.close();target.replace(p)
case_specs={
'1706.03762': [('What architecture is proposed in Attention Is All You Need?','Transformer'),('What BLEU score is reported for WMT 2014 English-to-German translation?','28.4'),('What BLEU score is reported for English-to-French translation?','41.8')],
'1810.04805':[('What does BERT stand for?','Bidirectional Encoder Representations from Transformers'),('How many NLP tasks obtained new state-of-the-art results with BERT?','eleven'),('What GLUE score does BERT achieve?','80.5')],
'2005.11401':[('What is the parametric memory in the RAG model?','pre-trained seq2seq model'),('What is the non-parametric memory in the RAG model?','dense vector index of Wikipedia'),('Can one RAG formulation use different passages per token?','different passages per token')],
'2004.04906':[('What framework learns the dense question and passage embeddings?','dual-encoder'),('Which sparse retrieval baseline does the dense retriever outperform?','BM25'),('What absolute improvement in top-20 retrieval accuracy is reported?','9%-19%')],
'1606.05250':[('Who posed the questions in SQuAD?','crowdworkers'),('Where do the SQuAD reading passages come from?','Wikipedia'),('What F1 score does the logistic regression model achieve?','51.0')]
}
manifest=[]
for i in case_specs:
 p=root/(i+'.pdf');manifest.append({'paper_id':i,'pdf_url':'https://arxiv.org/pdf/'+i,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size})
(root/'manifest.json').write_text(json.dumps(manifest,indent=2))
s=requests.Session();s.headers['X-ADI-Request']='1';base=args.base_url.rstrip('/')+'/api'
r=s.get(base+'/workspace',timeout=60);r.raise_for_status()
files=[('files',(i+'.pdf',(root/(i+'.pdf')).read_bytes(),'application/pdf')) for i in case_specs]
t=time.time();r=s.post(base+'/documents',files=files,data={'ocr':'false'},timeout=300);print('UPLOAD',r.status_code,round(time.time()-t,2),r.text[:500],flush=True)
(root/'upload.json').write_text(r.text)
r.raise_for_status(); ws=r.json(); docs={d['filename'].split('_',1)[-1].removesuffix('.pdf'):d['document_id'] for d in ws['documents']}
records=[]
for i,qs in case_specs.items():
 for q,expected in qs+[("What was this research project's annual revenue in 2025?",None)]:
  payload={'question':q,'document_id':docs[i],'top_k':5,'budget':10,'retrieval':'dense','verifier':'lexical','generator':'offline'}
  start=time.time();r=s.post(base+'/ask',json=payload,timeout=180)
  record={'paper_id':i,'question':q,'reference_answer':expected,'reference_page':1 if expected else None,'expected_unanswerable':expected is None,'http_status':r.status_code,'wall_seconds':round(time.time()-start,3),'result':r.json()};records.append(record)
  (root/'results.json').write_text(json.dumps(records,indent=2));print(i,q,r.status_code,str(record['result'].get('final_answer',record['result']))[:240],flush=True)
