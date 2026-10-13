import React,{useEffect,useRef,useState} from 'react';

// Public scene URL used by Vox Trace's HeroAgent. Load the original scene rather
// than approximating its geometry or authored animation. Keep it externally hosted.
export const ROBOT_SCENE='https://prod.spline.design/kZDDjO5HuC9GJUM2/scene.splinecode';
export default function Robot(){
  const canvas=useRef(null),application=useRef(null);
  const [status,setStatus]=useState('loading'),[attempt,setAttempt]=useState(0);
  useEffect(()=>{
    let disposed=false,observer,frame=0,lastPointer=null;
    const target=canvas.current,reduceMotion=window.matchMedia('(prefers-reduced-motion: reduce)');
    let bounds=target.getBoundingClientRect();
    const measure=()=>{bounds=target.getBoundingClientRect();};
    const motion=()=>{if(!application.current)return;if(reduceMotion.matches)application.current.stop();else application.current.play();};
    const forward=()=>{
      frame=0;
      if(disposed||!lastPointer||reduceMotion.matches)return;
      const {x,y}=lastPointer;lastPointer=null;
      target.dispatchEvent(new PointerEvent('pointermove',{
        clientX:Math.min(Math.max(x,bounds.left-bounds.width),bounds.right+bounds.width),
        clientY:Math.min(Math.max(y,bounds.top-bounds.height),bounds.bottom+bounds.height),
        pointerType:'mouse',bubbles:false
      }));
    };
    const pointer=event=>{if(event.target===target||reduceMotion.matches)return;lastPointer={x:event.clientX,y:event.clientY};if(!frame)frame=requestAnimationFrame(forward);};
    async function start(){
      setStatus('loading');
      try{
        const {Application}=await import('@splinetool/runtime');
        if(disposed)return;
        const app=new Application(target);application.current=app;
        await app.load(ROBOT_SCENE);
        if(disposed)return;
        setStatus('ready');measure();motion();
        observer=new IntersectionObserver(([entry])=>{
          if(disposed)return;
          if(entry.isIntersecting&&!reduceMotion.matches)app.play();else app.stop();
        },{rootMargin:'120px'});
        observer.observe(target);
        window.addEventListener('pointermove',pointer,{passive:true});
        window.addEventListener('scroll',measure,{passive:true});
        window.addEventListener('resize',measure,{passive:true});
        reduceMotion.addEventListener('change',motion);
      }catch(error){if(!disposed){application.current?.dispose();application.current=null;setStatus('error');console.warn('Robot scene could not load:',error.message);}}
    }
    start();
    return()=>{
      disposed=true;observer?.disconnect();if(frame)cancelAnimationFrame(frame);
      window.removeEventListener('pointermove',pointer);window.removeEventListener('scroll',measure);window.removeEventListener('resize',measure);reduceMotion.removeEventListener('change',motion);
      application.current?.dispose();application.current=null;
    };
  },[attempt]);
  return <div className={`spline-robot spline-${status}`}>
    <canvas ref={canvas} role="img" aria-label="Interactive 3D robot — original Spline scene used by Vox Trace"/>
    {status==='loading'&&<div className="spline-loading" role="status"><span className="spline-loading-orb"/><small>Loading 3D robot…</small></div>}
    {status==='error'&&<div className="spline-loading" role="status"><small>The 3D scene could not load.</small><button onClick={()=>setAttempt(a=>a+1)}>Retry robot</button></div>}
  </div>;
}
