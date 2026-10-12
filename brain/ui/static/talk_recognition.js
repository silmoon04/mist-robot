/* Use a gated live transcript when available, with one complete-WAV fallback. */
(function(root){
  'use strict';
  function create({captureFactory,streamFactory,batchTranscribe,onRecognition=()=>{}}){
    const owners=new WeakMap();
    const report=event=>{try{onRecognition(event);}catch(_){}};
    function capture(callbacks){
      const entry={stream:null,stopped:false,statuses:new Map()};
      if(streamFactory){
        try{entry.stream=streamFactory({
          onStatus:event=>{entry.statuses.set(event.utteranceId,event.status);report(event);},
          onPartial:event=>report({status:'partial',utteranceId:event.utteranceId})
        });}catch(_){entry.stream=null;}
      }
      const stream=entry.stream;
      const instance=captureFactory({...callbacks,
        onStreamStart:meta=>{entry.statuses.clear();stream?.start(meta);},
        onStreamData:(samples,meta)=>stream?.push(samples,meta),
        onStreamEnd:meta=>stream?.end(meta),
        onStreamCancel:meta=>{entry.statuses.set(meta.utteranceId,'cancelled');stream?.cancel(meta);},
        onUtterance:(blob,meta)=>{owners.set(blob,entry);return callbacks.onUtterance(blob,meta);}
      });
      const stop=instance.stop.bind(instance);
      instance.stop=()=>{
        entry.stopped=true;
        try{return stop();}finally{stream?.stop();}
      };
      return instance;
    }
    async function transcribe(blob,meta){
      const entry=owners.get(blob);
      try{
        if(meta.signal?.aborted||entry?.stopped) return '';
        if(entry?.stream){
          let result=null;
          try{result=await entry.stream.result(meta);}catch(_){entry.stream.cancel(meta);}
          if(meta.signal?.aborted||entry.stopped||['cancelled','stopped'].includes(entry.statuses.get(meta.utteranceId))) return '';
          if(result && typeof result.transcript==='string'){
            report({status:'streaming',utteranceId:meta.utteranceId,timings:result.timings});
            return typeof result.confidence==='number'&&result.confidence<.45?'':result.transcript.trim();
          }
        }
        if(meta.signal?.aborted||entry?.stopped) return '';
        report({status:'batch',utteranceId:meta.utteranceId});
        return await batchTranscribe(blob,meta);
      }finally{owners.delete(blob);}
    }
    return {captureFactory:capture,transcribe};
  }
  root.MistTalkRecognition={create};
  if(typeof module!=='undefined'&&module.exports) module.exports=root.MistTalkRecognition;
})(typeof window!=='undefined'?window:globalThis);
