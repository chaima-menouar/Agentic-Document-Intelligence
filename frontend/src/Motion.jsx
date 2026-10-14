import React,{useEffect,useRef,useState} from 'react';
import {Glyph} from './Visuals';

// Purely decorative pointer light and reading progress; no React render per frame.
export function MotionLayer(){
  const bar=useRef(null);
  useEffect(()=>{
    const preference=matchMedia('(prefers-reduced-motion: reduce)');let frame=0;
    const update=()=>{frame=0;const total=document.documentElement.scrollHeight-innerHeight;if(bar.current)bar.current.style.transform=`scaleX(${total>0?scrollY/total:0})`;};
    const scroll=()=>{if(!frame)frame=requestAnimationFrame(update);};
    const move=e=>{if(preference.matches||e.pointerType==='touch')return;const card=e.target.closest('.step-card,.tools-grid article');if(!card)return;const rect=card.getBoundingClientRect();card.style.setProperty('--pointer-x',`${e.clientX-rect.left}px`);card.style.setProperty('--pointer-y',`${e.clientY-rect.top}px`);};
    addEventListener('scroll',scroll,{passive:true});document.addEventListener('pointermove',move,{passive:true});update();
    return()=>{removeEventListener('scroll',scroll);document.removeEventListener('pointermove',move);cancelAnimationFrame(frame);};
  },[]);
  return <div ref={bar} className="reading-progress" aria-hidden="true"/>;
}
const stages=[
  {name:'Read',icon:'file',title:'A document becomes passages.',copy:'The pilot launches on 12 November. Three teams will take part.',tag:'PROJECT BRIEF · PAGE 2'},
  {name:'Retrieve',icon:'spark',title:'Find the detail that matters.',copy:'When does the pilot launch?',tag:'QUESTION → RELEVANT PASSAGE'},
  {name:'Check',icon:'shield',title:'Keep the answer tied to its source.',copy:'The pilot launches on 12 November. [S1]',tag:'SOURCE SUPPORT · NOT A GUARANTEE'},
  {name:'Explore',icon:'external',title:'Your evidence stays in reach.',copy:'Open page 2 to review the original passage and its context.',tag:'[S1] → PROJECT BRIEF · PAGE 2'}
];
export function EvidenceFlow(){
  const [active,setActive]=useState(0),[playing,setPlaying]=useState(false),[visible,setVisible]=useState(false);const root=useRef(null);
  useEffect(()=>{const media=matchMedia('(prefers-reduced-motion: reduce)');setPlaying(!media.matches);const change=()=>setPlaying(!media.matches);media.addEventListener('change',change);const obs=new IntersectionObserver(([entry])=>setVisible(entry.isIntersecting),{threshold:.3});obs.observe(root.current);return()=>{obs.disconnect();media.removeEventListener('change',change);};},[]);
  useEffect(()=>{if(!playing||!visible)return;const timer=setInterval(()=>{if(!document.hidden)setActive(i=>(i+1)%4);},4000);return()=>clearInterval(timer);},[playing,visible]);
  const item=stages[active];
  return <section ref={root} className={`evidence-flow ${playing&&visible?'flow-playing':''}`} aria-label="Illustrated document journey">
    <div className="flow-heading"><div><p className="eyebrow">WATCH THE EVIDENCE CONNECT</p><h3>A little clarity, step by step.</h3></div><button className="flow-toggle" onClick={()=>setPlaying(v=>!v)} aria-label={playing?'Pause document journey':'Play document journey'}>{playing?<svg viewBox="0 0 24 24" width="14" height="14" aria-hidden="true"><path d="M8 5v14M16 5v14" stroke="currentColor" strokeWidth="3"/></svg>:<Glyph name="play" size={14}/>} {playing?'Pause':'Play'}</button></div>
    <div className="flow-track" role="group" aria-label="Journey steps">{stages.map((stage,i)=><button key={stage.name} aria-pressed={active===i} onClick={()=>{setActive(i);setPlaying(false);}} className={active===i?'flow-node is-current':'flow-node'}><span className="flow-node-icon"><Glyph name={stage.icon} size={22}/></span><span>{stage.name}</span><small>0{i+1}</small></button>)}</div>
    <div className="flow-detail" key={active}><div className="flow-paper" aria-hidden="true"><Glyph name={item.icon} size={30}/><i/><i/><i/><span className="flow-scan"/></div><div><p className="flow-tag">{item.tag}</p><h4>{item.title}</h4><p>{item.copy}</p></div></div>
    <div className="flow-footnote"><span>Illustrative example · your files are processed in the workspace below.</span><a href="#workspace">Try your document <Glyph name="arrow" size={15}/></a></div>
  </section>;
}
