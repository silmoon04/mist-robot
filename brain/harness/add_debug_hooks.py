"""Apply the browser timing hooks to the existing conversation surface."""
from pathlib import Path
p=Path(__file__).resolve().parents[1]/'duplex/static/app.js'
s=p.read_text(encoding='utf-8')
s=s.replace("let pendingCaption='',lastSpeechKey=null,backgroundJob=null;", "let pendingCaption='',lastSpeechKey=null,backgroundJob=null,micFrames=0,micPower=0;")
s=s.replace("send({type:'playback_state',playing:true});", "send({type:'playback_state',playing:true});trace({type:'playback_started',epoch:event.epoch,sequence:event.seq,queue_ms:Math.max(0,player.end-context.currentTime)*1000});")
s=s.replace("()=>{send({type:'playback_state',playing:false});if(ready)", "()=>{send({type:'playback_state',playing:false});trace({type:'playback_idle'});if(ready)")
s=s.replace("const {pcm}=event.data;", "const {pcm,rms}=event.data;micFrames++;micPower+=(rms||0)**2;")
s+='''
function trace(event){if(ready)send({type:'debug_client',event:{...event,client_ms:performance.now()}});}
new MutationObserver(()=>trace({type:'expression',name:currentFace,variant:face.expression,pinned:expressionPinned})).observe($('face'),{attributes:true,attributeFilter:['aria-label']});
setInterval(()=>{if(!ready)return;trace({type:'microphone_stats',frames:micFrames,rms:micFrames?Math.sqrt(micPower/micFrames):0,fixture:fixtureMode});micFrames=0;micPower=0;trace({type:'audio_scheduled',queue_ms:Math.max(0,(player?.end||0)-(context?.currentTime||0))*1000,playing:player?.playing||false,viseme:face.snapshot().viseme});},1000);
'''
p.write_text(s,encoding='utf-8')
