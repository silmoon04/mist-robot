import {createSpeechSampler} from '../speech-review/sampler.mjs';

export const RECOVERY_MS = 400;

// Listening is a conversational state. The persistent expression still carries emotion.
export class PreviewPlayback {
  constructor({face,transport,wallClock=()=>performance.now()}) {
    this.face=face; this.transport=transport; this.wallClock=wallClock;
    this.epoch=0; this.sampler=null; this.faceOffsetMs=0; this.recovery=null; this.destroyed=false;
  }
  faceTime() {
    const sceneMs=this.transport.time()*1000, paused=this.recovery?.paused;
    if(paused) {
      const time=paused.faceMs+Math.max(0,this.wallClock()-paused.wallMs);
      if(this.transport.running) { this.faceOffsetMs=time-sceneMs; this.recovery.paused=null; }
      return time;
    }
    return sceneMs+this.faceOffsetMs;
  }
  bindSampler(reason) {
    const transport=this.transport;
    this.sampler=createSpeechSampler({clip:this.clip,clock:()=>transport.sample().position,isRunning:()=>transport.sample().active,getInactiveReason:()=>transport.sample().reason,epoch:this.epoch,sequence:this.epoch,turnId:this.scene.id});
    if(reason)this.sampler.cancel(reason);
    else this.face.startSpeech({...this.sampler,epoch:this.epoch});
  }
  reset(scene,clip,buffer,reason='reset') {
    if(this.destroyed)return false;
    this.sampler?.cancel(reason);
    // The adapter reads this clock while resetting its deterministic blink epoch.
    this.transport.configure(scene,buffer);
    this.faceOffsetMs=0; this.recovery=null; this.scene=scene; this.clip=clip; ++this.epoch;
    this.face.setExpression('attentive',{epoch:this.epoch});
    this.face.reset({epoch:this.epoch});
    this.bindSampler();
    return true;
  }
  beginRecovery(at) {
    this.recovery={startMs:at,untilMs:at+RECOVERY_MS,paused:this.transport.running?null:{faceMs:at,wallMs:this.wallClock()}};
  }
  pause(reason='paused') {
    if(this.destroyed)return;
    const at=this.faceTime(), state=this.face.snapshot().state;
    this.transport.pause(); this.faceOffsetMs=at-this.transport.time()*1000; this.recovery=null;
    this.sampler?.cancel(reason); ++this.epoch;
    // Reset first in the current epoch; advancing it first would erase the native return transition.
    this.face.reset({epoch:this.epoch-1}); this.face.handleEvent({type:'state',state,epoch:this.epoch});
    this.bindSampler(this.transport.interrupted?'interrupted':undefined);
    this.beginRecovery(at);
  }
  interrupt() {
    if(this.destroyed||this.transport.interrupted)return false;
    const at=this.faceTime();
    this.transport.interrupt(); this.sampler?.cancel('interrupted'); ++this.epoch;
    this.face.reset({epoch:this.epoch-1}); this.face.handleEvent({type:'state',state:'listening',epoch:this.epoch});
    this.bindSampler('interrupted'); this.beginRecovery(at);
    return true;
  }
  async play() {
    if(this.destroyed)return false;
    const epoch=this.epoch, started=await this.transport.play();
    if(!started||epoch!==this.epoch||this.destroyed)return false;
    this.faceTime();
    if(!this.transport.interrupted)this.face.startSpeech({...this.sampler,epoch:this.epoch});
    return true;
  }
  update() {
    const time=this.faceTime(), due=this.recovery&&time>=this.recovery.untilMs;
    // Invalidate the frame cache at the recovery boundary, even inside the same 15 fps bucket.
    if(due) {
      if(this.transport.running&&!this.transport.interrupted)this.face.startSpeech({...this.sampler,epoch:this.epoch});
      else this.face.stopSpeech();
    }
    const frame=this.face.update(time);
    let recovered=null;
    if(this.recovery&&(due||frame.pose?.phase!=='transition')) {
      recovered={durationMs:Math.max(0,time-this.recovery.startMs),intent:frame.intent};
      if(this.recovery.paused)this.faceOffsetMs=time-this.transport.time()*1000;
      this.recovery=null;
    }
    return {frame,recovered,time};
  }
  suspendAudio() {
    if(this.transport.context.state==='running'||(!this.transport.running&&!this.transport.pending))return false;
    this.pause('audio-suspended'); return true;
  }
  stop(reason='ended') {
    this.pause(reason); this.sampler?.cancel(reason); this.face.stopSpeech();
    if(reason!=='ended') {
      const at=this.faceTime();this.faceOffsetMs=at-this.transport.time()*1000;this.recovery=null;this.face.reset({epoch:this.epoch});
    }
  }
  destroy() {
    if(this.destroyed)return;
    this.destroyed=true; ++this.epoch; this.sampler?.cancel('teardown'); this.recovery=null; this.face.destroy(); this.transport.destroy();
  }
}
