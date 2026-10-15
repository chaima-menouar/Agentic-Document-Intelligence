import React,{useRef,useState} from 'react';

export default function WorkspaceBackup({workspace,transcript,locked,onBusy,onError,onRestored,onConflict}) {
  const input=useRef(null);
  const [pending,setPending]=useState(null),[message,setMessage]=useState('');
  async function checked(response){
    if(response.ok)return response;
    let data;try{data=await response.json();}catch{}
    const error=new Error(typeof data?.detail==='string'?data.detail:data?.detail?.message||`Request failed (${response.status}).`);
    error.status=response.status;throw error;
  }
  async function run(label,action){
    onBusy(label);onError('');setMessage('');
    try{await action();}catch(error){if(error.status===409)await onConflict();else onError(error.message);}finally{onBusy('');}
  }
  function download(){run('Preparing your workspace backup…',async()=>{
    const response=await checked(await fetch('/api/workspace/backup',{method:'POST',headers:{'X-ADI-Request':'1','Content-Type':'application/json'},body:JSON.stringify({transcript,workspace_revision:workspace.revision})}));
    const url=URL.createObjectURL(await response.blob());const link=document.createElement('a');
    link.href=url;link.download=`clario-workspace-${new Date().toISOString().slice(0,10)}.zip`;link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
    setMessage('Backup download started. Keep this file somewhere safe; it contains your PDFs, answers, feedback and transcript.');
  });}
  function choose(file){
    if(!file)return;
    if(!file.name.toLowerCase().endsWith('.zip')||file.size>4*1024*1024){onError('Choose a Clario ZIP backup up to 4 MB.');return;}
    setPending({file,revision:workspace.revision});setMessage('');
  }
  function restore(){
    const choice=pending;setPending(null);
    run('Restoring PDFs and rebuilding the searchable index…',async()=>{
      const form=new FormData();form.append('file',choice.file);
      const response=await checked(await fetch('/api/workspace/restore',{method:'POST',headers:{'X-ADI-Request':'1',...(choice.revision?{'X-ADI-Workspace':choice.revision}:{})},body:form}));
      onRestored(await response.json());setMessage('Backup restored. Imported answers are saved results; review them against the PDFs or ask again to verify.');
    });
  }
  return <section className="backup-panel" aria-label="Workspace backup"><div><p className="eyebrow small">KEEP YOUR RESEARCH</p><h3>Pick up where you left off.</h3><p>Server sessions are temporary. Download a complete backup and restore it later, even after a restart.</p><small>Includes PDFs, answer history, feedback and the Audio Studio transcript. Up to 4 MB. Audio recordings and generated voice notes are not included. Store backups privately.</small></div><div className="backup-actions"><button className="secondary" disabled={locked||(!workspace.documents.length&&!workspace.history.length&&!transcript)} onClick={download}>Download workspace backup</button><button className="secondary" disabled={locked} onClick={()=>input.current.click()}>Restore a backup</button><input ref={input} type="file" accept=".zip,application/zip" aria-label="Select workspace backup" className="visually-hidden" disabled={locked} onChange={e=>{choose(e.target.files[0]);e.target.value='';}}/></div>{message&&<p role="status">{message}</p>}{pending&&<div className="backup-confirm" role="alertdialog" aria-labelledby="restore-title"><h4 id="restore-title">Replace your current workspace?</h4><p>Restore “{pending.file.name}”? This replaces the current PDFs, answers, feedback and audio transcript. Download a backup first if you want to keep them.</p><div className="backup-actions"><button className="secondary" disabled={locked} onClick={()=>setPending(null)}>Cancel restore</button><button className="primary" disabled={locked} onClick={restore}>Replace and restore</button></div></div>}</section>;
}
