import React,{useEffect,useRef,useState} from 'react';

/** Browser-native voice recording and live dictation. No microphone audio leaves the browser. */
export default function VoiceStudio(){
 const [recording,setRecording]=useState(false),[transcript,setTranscript]=useState(''),[summary,setSummary]=useState(''),[error,setError]=useState(''),[supported,setSupported]=useState(false);
 const recognition=useRef(null);
 useEffect(()=>{setSupported(Boolean(window.SpeechRecognition||window.webkitSpeechRecognition));return()=>recognition.current?.stop();},[]);
 function start(){
  setError('');const Engine=window.SpeechRecognition||window.webkitSpeechRecognition;
  if(!Engine){setError('Live speech recognition is unavailable in this browser. Try Chrome or Edge.');return;}
  const r=new Engine();recognition.current=r;r.continuous=true;r.interimResults=true;r.lang=navigator.language||'en-US';
  let finalText=transcript.trim();
  r.onresult=e=>{let interim='';for(let i=e.resultIndex;i<e.results.length;i++){const part=e.results[i][0].transcript;if(e.results[i].isFinal)finalText+=' '+part;else interim+=part;}setTranscript((finalText+' '+interim).trim());};
  r.onerror=e=>{setError('Microphone recognition: '+e.error);setRecording(false);};
  r.onend=()=>setRecording(false);
  try{r.start();setRecording(true);}catch(e){setError(e.message);}
 }
 function stop(){recognition.current?.stop();setRecording(false);}
 function summarize(){
  const sentences=transcript.match(/[^.!?\n]+[.!?]?/g)?.map(s=>s.trim()).filter(Boolean)||[];
  if(!sentences.length){setError('Record or paste a transcript first.');return;}
  const keywords=/\b(need to|must|should|will|action|deadline|decided|agreed|next step|important)\b/i;
  const actions=sentences.filter(s=>keywords.test(s)).slice(0,6);
  const main=sentences.slice(0,Math.min(5,sentences.length)).join(' ');
  setSummary('Quick extractive recap (not AI-generated):\n'+main+(actions.length?'\n\nPotential action items:\n'+actions.map(s=>'• '+s).join('\n'):''));
 }
 return <section className="voice-studio" aria-label="Voice intelligence"><p className="eyebrow">VOICE INTELLIGENCE · BETA</p><h2>Talk. Capture. Summarize.</h2><p>Record speech using browser dictation, edit the transcript, and generate a quick extractive recap. Microphone audio is not uploaded to our server.</p><div className="voice-actions"><button type="button" onClick={recording?stop:start} disabled={!supported}>{recording?'■ Stop listening':'◉ Start listening'}</button><button type="button" onClick={summarize}>Summarize transcript</button></div>{!supported&&<p role="status">Live dictation is not supported in this browser.</p>}{error&&<p role="alert">{error}</p>}<label htmlFor="voice-transcript">Transcript</label><textarea id="voice-transcript" rows={7} value={transcript} onChange={e=>setTranscript(e.target.value)} placeholder="Your live transcript will appear here. You can also paste a transcript."/><label htmlFor="voice-summary">Summary</label><textarea id="voice-summary" rows={6} readOnly value={summary} placeholder="Select Summarize transcript to see a quick recap."/><small>Browser speech recognition availability and processing depend on the browser; some browsers send speech to their speech service. This is not yet real-time AI conversation or model-based summarization.</small></section>;
}
