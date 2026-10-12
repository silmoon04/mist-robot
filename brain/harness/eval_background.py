import asyncio,json,sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
sys.path.insert(0,str(Path(__file__).resolve().parent))
from duplex.background import BackgroundBrain
from duplex.runtime import RobotRuntime

async def main():
    out=Path('brain/results/layered_brain_20260914');out.mkdir(parents=True,exist_ok=True)
    runtime=RobotRuntime(out/'runtime');events=[];ticks=[]
    async def emit(e):events.append(e)
    b=BackgroundBrain(runtime,out/'worker',emit,lambda:0)
    began=time.perf_counter()
    receipt=await b.handle('start_background_task',{'question':'Read the actual sensor snapshot with your tool, then propose a concise three-step check before the first quadruped motion test. Distinguish missing measurements from what can be concluded.'})
    ack=time.perf_counter()-began
    while b.tasks:
        before=time.perf_counter();await asyncio.sleep(.02);ticks.append(time.perf_counter()-before)
    result=await b.handle('background_task_status',{})
    report={'submit_ack_ms':ack*1000,'result':result,'event_loop_ticks':len(ticks),'max_tick_ms':max(ticks)*1000,'elapsed_s':time.perf_counter()-began,
            'passed':result['status']=='complete' and result['tool_calls']>0 and len(ticks)>10}
    (out/'worker_result.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report));await b.close();assert report['passed']

asyncio.run(main())
