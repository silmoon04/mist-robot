/* Connect microphone utterances to transcription and accepted chat turns. */
(function(root){
  'use strict';

  function abortError(){
    const error=new Error('Talk stopped.');
    error.name='AbortError';
    return error;
  }

  function abortable(value,signal){
    const promise=Promise.resolve(value);
    return new Promise((resolve,reject)=>{
      const cancel=()=>finish(reject,abortError());
      const finish=(settle,result)=>{
        signal.removeEventListener('abort',cancel);
        settle(result);
      };
      promise.then(value=>finish(resolve,value),error=>finish(reject,error));
      if(signal.aborted) cancel();
      else signal.addEventListener('abort',cancel,{once:true});
    });
  }

  function create({captureFactory,transcribe,submit,interrupt=async()=>{},stopSpeech=()=>{},
                   isReplyBusy=()=>false,isPlaybackActive=()=>false,
                   onState=()=>{},onTranscript=()=>{},onError=()=>{}}={}){
    if(typeof captureFactory!=='function' || typeof transcribe!=='function' || typeof submit!=='function'){
      throw new TypeError('Talk requires capture, transcription and submission callbacks.');
    }
    let current=null;
    let state={status:'idle',active:false};
    const live=run=>current===run && !run.controller.signal.aborted;

    function report(error,run=current){
      if(current!==run || (run && !live(run))) return;
      const message=error?.message || String(error || 'Talk failed.');
      try{ Promise.resolve(onError(message)).catch(()=>{}); }catch(_){}
    }

    function notify(callback,args,run=current){
      try{ Promise.resolve(callback(...args)).catch(error=>report(error,run)); }
      catch(error){ report(error,run); }
    }

    function setState(status,details={},run=current){
      if(run && !live(run)) return;
      state={...details,status,active:current!==null};
      notify(onState,[{...state}],run);
    }

    function closeCapture(run){
      try{ return Promise.resolve(run.capture?.stop()).catch(()=>{}); }
      catch(_){ return Promise.resolve(); }
    }

    function stop(){
      const run=current;
      current=null;
      if(run) run.controller.abort();
      const closed=run ? closeCapture(run) : Promise.resolve();
      setState('idle');
      return closed;
    }

    function captureError(error,run){
      if(!live(run)) return;
      stop();
      if(current) return;
      setState('error',{message:error?.message || String(error || 'Microphone unavailable.')});
      report(error,null);
    }

    function beginInterruption(run,speech){
      if(speech.interrupted) return speech.ready;
      speech.interrupted=true;
      try{
        speech.ready=abortable(interrupt({signal:run.controller.signal}),run.controller.signal)
          .then(()=>true,error=>{
            if(live(run) && error?.name!=='AbortError') report(error,run);
            return false;
          });
      }catch(error){
        report(error,run);
        speech.ready=Promise.resolve(false);
      }
      return speech.ready;
    }

    function speechStart(run,meta={}){
      if(!live(run) || run.operation) return Promise.resolve(false);
      const speech={ready:Promise.resolve(true),interrupted:false};
      run.speech=speech;
      setState('speaking',{bargeIn:!!meta.bargeIn},run);
      if(!live(run)) return Promise.resolve(false);
      try{
        stopSpeech();
        if(live(run) && isReplyBusy()) beginInterruption(run,speech);
      }catch(error){
        report(error,run);
        speech.ready=Promise.resolve(false);
      }
      return speech.ready;
    }

    function utterance(run,blob,meta={}){
      if(!live(run) || !blob || typeof blob!=='object' || blob.size===0 || meta.signal?.aborted){
        return Promise.resolve(false);
      }
      if(run.seen.has(blob)) return run.seen.get(blob);
      if(run.operation) return Promise.resolve(false);

      const controller=new AbortController();
      const cancel=()=>controller.abort();
      const signals=[run.controller.signal,meta.signal].filter(Boolean);
      for(const signal of signals) signal.addEventListener('abort',cancel,{once:true});
      const operation={controller};
      const speech=run.speech || {ready:Promise.resolve(true),interrupted:false};
      run.speech=null;
      run.operation=operation;
      const valid=()=>live(run) && run.operation===operation && !controller.signal.aborted;

      const task=Promise.resolve().then(async()=>{
        try{
          if(!valid()) return false;
          setState('transcribing',{},run);
          if(!valid()) return false;
          const details={...meta,signal:controller.signal};
          const result=await abortable(transcribe(blob,details),controller.signal);
          if(!valid()) return false;
          const text=typeof result==='string' ? result.trim() : '';
          if(!text) return false;
          if(!await abortable(speech.ready,controller.signal) || !valid()) return false;
          if(isReplyBusy()){
            const latest={ready:Promise.resolve(true),interrupted:false};
            if(!await abortable(beginInterruption(run,latest),controller.signal) || !valid()) return false;
          }
          notify(onTranscript,[text,details],run);
          if(!valid()) return false;
          setState('submitting',{},run);
          if(!valid()) return false;
          return !!await abortable(submit(text,{signal:controller.signal}),controller.signal) && valid();
        }catch(error){
          if(valid() && error?.name!=='AbortError') report(error,run);
          return false;
        }finally{
          for(const signal of signals) signal.removeEventListener('abort',cancel);
          if(run.operation===operation){
            run.operation=null;
            if(live(run)) setState('listening',{},run);
          }
        }
      });
      run.seen.set(blob,task);
      return task;
    }

    function start(){
      if(current) return current.startPromise || Promise.resolve(true);
      const run={controller:new AbortController(),capture:null,operation:null,speech:null,
                 seen:new WeakMap(),started:false,startPromise:null};
      current=run;
      setState('starting',{},run);
      if(!live(run)) return Promise.resolve(false);
      try{
        run.capture=captureFactory({
          onUtterance:(blob,meta)=>utterance(run,blob,meta),
          onSpeechStart:meta=>speechStart(run,meta),
          isPlaybackActive:()=>live(run) && !!isPlaybackActive(),
          onState:value=>{
            if(!live(run) || run.operation) return;
            const details=typeof value==='string' ? {status:value} : value || {};
            if(details.status==='idle' && run.started && details.active===false){ stop(); return; }
            if(['starting','listening','speaking'].includes(details.status)) setState(details.status,details,run);
          },
          onError:error=>captureError(error,run),
        });
        if(!live(run)){ closeCapture(run); return Promise.resolve(false); }
        if(!run.capture || typeof run.capture.start!=='function' || typeof run.capture.stop!=='function'){
          throw new TypeError('Talk capture must provide start and stop.');
        }
        // Invoke capture inside the click handler before awaiting microphone access.
        const opening=Promise.resolve(run.capture.start()).then(result=>{
          if(!live(run)) closeCapture(run);
          return result;
        });
        run.startPromise=abortable(opening,run.controller.signal).then(result=>{
          if(!live(run)) return false;
          if(result===false){ captureError(new Error('Microphone did not start.'),run); return false; }
          run.started=true;
          if(!run.operation && state.status!=='speaking') setState('listening',{},run);
          return live(run);
        },error=>{
          if(live(run) && error?.name!=='AbortError') captureError(error,run);
          return false;
        });
        return run.startPromise;
      }catch(error){
        captureError(error,run);
        return Promise.resolve(false);
      }
    }

    return {start,stop,getState:()=>({...state})};
  }

  root.MistTalkSession={create};
  if(typeof module!=='undefined' && module.exports) module.exports=root.MistTalkSession;
})(typeof window!=='undefined'?window:globalThis);
