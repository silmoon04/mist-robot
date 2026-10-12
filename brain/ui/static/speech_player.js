/* Speech request ownership and audio-clock face timing. */
(function(root){
  'use strict';
  function create({face, audio = new root.Audio(), fetch = root.fetch.bind(root),
                   onState = ()=>{}, onError = ()=>{}, onTiming=()=>{}, rate = ()=>1}={}){
    let generation=0, request=null, objectUrl=null, speech=null, speechText=null, requestId=null;
    const timing=(stage,details={})=>onTiming({stage,request_id:requestId,epoch_ms:Date.now(),...details});
    function stop(){
      generation++;
      if(request) request.abort();
      request=null;
      audio.onplaying=audio.onended=audio.onerror=audio.onpause=null;
      audio.pause();
      audio.removeAttribute('src');
      audio.load();
      if(objectUrl) root.URL.revokeObjectURL(objectUrl);
      objectUrl=null; speech=null; speechText=null;
      face.stopSpeech();
      onState('idle');
    }
    function applyRate(){
      const value=Math.max(.75,Math.min(1.5,Number(rate())||1));
      audio.defaultPlaybackRate=value; audio.playbackRate=value;
      audio.preservesPitch=true;
    }
    async function tryPlayback(mine){
      try{
        timing('audio_play_attempt');
        await audio.play();
        return mine===generation;
      }catch(error){
        if(mine!==generation || error.name==='AbortError') return false;
        if(error.name==='NotAllowedError'){
          timing('audio_blocked');
          face.stopSpeech();
          onState('blocked',speech);
          return false;
        }
        stop();
        onError('This reply could not be played. Try another voice.');
        return false;
      }
    }
    function resume(){
      if(!speech || !objectUrl) return Promise.resolve(false);
      applyRate();
      return tryPlayback(generation);
    }
    async function play(text,{provider='elevenlabs',voice=null,model=null,request_id=null,purpose='manual'}={}){
      stop();
      if(!text) return;
      requestId=request_id??('speech-'+Date.now().toString(36)+'-'+Math.random().toString(36).slice(2,10));
      const mine=generation;
      request=new AbortController();
      onState('loading');
      timing('tts_request',{characters:text.length,provider,model,purpose});
      try{
        const response=await fetch('/api/speech',{method:'POST',
          headers:{'Content-Type':'application/json'},
          body:JSON.stringify({text,provider,voice,model,request_id:requestId,client_protocol:2,purpose}),signal:request.signal});
        if(mine!==generation) return;
        timing('tts_response_headers');
        const payload=await response.json();
        if(mine!==generation) return;
        timing('tts_response_body',{usage:payload.usage,server_timing:payload.server_timing});
        if(!response.ok) throw new Error(payload.error||'Speech generation failed.');
        request=null;
        const bytes=Uint8Array.from(root.atob(payload.audio_base64),c=>c.charCodeAt(0));
        objectUrl=root.URL.createObjectURL(new Blob([bytes],{type:payload.mime_type}));
        speech=payload;
        speechText=text;
        audio.src=objectUrl;
        applyRate();
        audio.onplaying=()=>{
          if(mine!==generation) return;
          timing('audio_playing',{audio_time_s:audio.currentTime,duration_s:payload.duration_s});
          face.startSpeech({events:payload.events,duration:payload.duration_s,
                            clock:()=>audio.currentTime});
          onState('playing',payload);
        };
        audio.onpause=()=>{if(mine===generation){face.stopSpeech();onState('paused');}};
        audio.onended=()=>{if(mine===generation) stop();};
        audio.onerror=()=>{if(mine===generation){stop();onError('Audio playback failed.');}};
        await tryPlayback(mine);
      }catch(error){
        if(mine!==generation || error.name==='AbortError') return;
        stop();
        onError(error.message||'Speech is unavailable.');
      }
    }
    return {play,resume,stop,applyRate,audio,get speech(){return speech;},get text(){return speechText;}};
  }
  root.MistSpeechPlayer={create};
  if(typeof module!=='undefined' && module.exports) module.exports=root.MistSpeechPlayer;
})(typeof window!=='undefined'?window:globalThis);
