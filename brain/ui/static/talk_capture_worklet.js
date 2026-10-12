/* Batch microphone PCM; the output stays silent. */
class MistTalkCaptureProcessor extends AudioWorkletProcessor {
  constructor(options) {
    super();
    const batchMs = Math.max(10, Math.min(100, Number(options?.processorOptions?.batchMs) || 20));
    this.batchSize = Math.round(sampleRate * batchMs / 1000);
    this.samples = new Float32Array(this.batchSize);
    this.offset = 0;
    this.stopped = false;
    this.port.onmessage = event => { if (event.data?.type === 'stop') this.stopped = true; };
  }
  process(inputs, outputs) {
    for (const output of outputs) for (const channel of output) channel.fill(0);
    if (this.stopped) return false;
    const channels = inputs[0];
    if (!channels?.length) return true;
    for (let index = 0; index < channels[0].length; index++) {
      let value = 0;
      for (const channel of channels) value += channel[index] || 0;
      this.samples[this.offset++] = value / channels.length;
      if (this.offset === this.batchSize) {
        this.port.postMessage({type: 'pcm', samples: this.samples}, [this.samples.buffer]);
        this.samples = new Float32Array(this.batchSize);
        this.offset = 0;
      }
    }
    return true;
  }
}
registerProcessor('mist-talk-capture', MistTalkCaptureProcessor);
