import fs from 'node:fs/promises';

// QA document only. The application module, stylesheet, media and artwork remain original.
const html=await fs.readFile(new URL('../preview/index.html',import.meta.url),'utf8');
const probe=`<script>
const probe=window.__qaLifecycle={contexts:[],nodes:[],intervals:new Set()};
const NativeAudio=window.AudioContext;
window.AudioContext=class extends NativeAudio {
  constructor(...args){super(...args);probe.contexts.push(this);}
  createBufferSource(){
    const node=super.createBufferSource(),record={starts:0,stops:0,disconnects:0};probe.nodes.push(record);
    for(const [method,key] of [['start','starts'],['stop','stops'],['disconnect','disconnects']]){
      const original=node[method].bind(node);node[method]=(...args)=>{record[key]++;return original(...args);};
    }
    return node;
  }
};
const originalInterval=window.setInterval.bind(window),originalClear=window.clearInterval.bind(window);
window.setInterval=(...args)=>{const id=originalInterval(...args);probe.intervals.add(id);return id;};
window.clearInterval=id=>{probe.intervals.delete(id);return originalClear(id);};
probe.installTeardownObserver=()=>window.addEventListener('pagehide',()=>{
  sessionStorage.setItem('geraldine-qa-teardown',JSON.stringify({contexts:probe.contexts.map(c=>c.state),nodes:probe.nodes,intervals:probe.intervals.size,snapshot:window.characterPreview?.snapshot()}));
});
if(new URLSearchParams(location.search).get('failure')==='missing-wav'){
  const originalFetch=window.fetch.bind(window);
  window.fetch=(input,...args)=>/\\.wav(?:$|\\?)/i.test(String(input))?Promise.resolve(new Response('Intentional QA missing WAV',{status:404,statusText:'QA missing asset'})):originalFetch(input,...args);
}
</script>`;
const fixture=html.replace('href="style.css"','href="../preview/style.css"').replace('<script type="module" src="app.mjs"></script>',`${probe}<script type="module" src="../preview/app.mjs"></script>`);
await fs.writeFile(new URL('./browser-fixture.html',import.meta.url),fixture);
console.log('Wrote QA-only fixture using the current original index DOM and application imports.');
