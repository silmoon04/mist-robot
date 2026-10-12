// Native audio segments share one clock with the authored scene.
export function segmentsFor(audio, duration) {
  const segments = []; let clip = 0, scene = audio.startMs / 1000;
  for (const gap of [...(audio.packetGaps || [])].sort((a,b)=>a.atClipMs-b.atClipMs)) {
    const end = Math.min(duration, gap.atClipMs / 1000);
    if (end > clip) segments.push({scene, clip, duration:end-clip});
    scene += Math.max(0,end-clip) + gap.durationMs/1000; clip=end;
  }
  if (clip < duration) segments.push({scene,clip,duration:duration-clip});
  return segments;
}
export function locate(segments, sceneTime, duration) {
  let position=0;
  for (const segment of segments) {
    if (sceneTime < segment.scene) return {position,active:false,reason:position ? 'packet-gap':'waiting'};
    if (sceneTime < segment.scene+segment.duration) return {position:segment.clip+sceneTime-segment.scene,active:true,reason:'speech'};
    position=segment.clip+segment.duration;
  }
  return {position:Math.min(duration,position),active:false,reason:'ended'};
}
export class SceneTransport {
  constructor(context) { this.context=context; this.nodes=new Set(); this.epoch=0; this.offset=0; this.lastTime=0; this.running=false; this.pending=false; this.interrupted=false; this.destroyed=false; }
  configure(scene,buffer) { this.reset(); this.scene=scene; this.buffer=buffer; this.segments=segmentsFor(scene.audio,buffer.duration); }
  outputTime() { let stamp; try { stamp=this.context.getOutputTimestamp?.(); } catch {} return Number.isFinite(stamp?.contextTime)&&stamp.contextTime>0 ? Math.min(this.context.currentTime,stamp.contextTime) : this.context.currentTime; }
  time() { if(this.running)this.lastTime=Math.max(this.lastTime,this.offset+this.outputTime()-this.anchor); return this.running ? this.lastTime : this.offset; }
  sample() { const result=this.interrupted ? {position:this.interruptPosition,active:false,reason:'interrupted'} : locate(this.segments||[],this.time(),this.buffer?.duration||0); if (!this.running||this.interrupted||this.context.state!=='running') return {...result,active:false,reason:this.interrupted?'interrupted':'suspended-clock'}; return result; }
  async play() {
    if(this.destroyed||this.pending) return false;
    if (this.running) return true;
    const epoch=++this.epoch; this.pending=true;
    try { await this.context.resume(); } catch(error) { if(epoch!==this.epoch)return false; this.pending=false; throw error; }
    if(epoch!==this.epoch) return false;
    this.pending=false;
    if(this.destroyed||this.context.state!=='running')return false;
    this.anchor=this.context.currentTime; this.lastTime=this.offset; this.running=true;
    if(this.interrupted) return true;
    try {
    for(const segment of this.segments) {
      const skip=Math.max(0,this.offset-segment.scene);
      if(skip>=segment.duration) continue;
      const node=this.context.createBufferSource(); node.buffer=this.buffer; node.connect(this.context.destination); this.nodes.add(node);
      node.onended=()=>{this.nodes.delete(node); node.disconnect();};
      node.start(this.anchor+Math.max(0,segment.scene-this.offset),segment.clip+skip,segment.duration-skip);
    }
    } catch(error) { this.pause(); throw error; }
    return true;
  }
  stopNodes() { for(const node of this.nodes) { node.onended=null; try{node.stop();}catch{} node.disconnect(); } this.nodes.clear(); }
  pause() { this.offset=this.time(); this.running=false; this.pending=false; ++this.epoch; this.stopNodes(); }
  interrupt() { this.interruptPosition=this.sample().position; this.interrupted=true; this.pending=false; ++this.epoch; this.stopNodes(); }
  reset() { this.pause(); this.offset=0; this.lastTime=0; this.interrupted=false; }
  destroy() { if(this.destroyed)return; this.reset(); this.destroyed=true; this.context.close()?.catch?.(()=>{}); }
}
