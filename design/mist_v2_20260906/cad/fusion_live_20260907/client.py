"""Small local MCP client for the installed Fusion adapter.

Mutations are never retried automatically. A timeout has an uncertain outcome;
inspect Fusion or the script's progress file before issuing another mutation.
"""
import argparse
import hashlib
import json
from pathlib import Path
import urllib.request

ENDPOINT='http://127.0.0.1:27182/mcp'


class FusionClient:
    def __init__(self,timeout=60):
        self.session=None
        self.timeout=timeout
        self.counter=0
        self.rpc('initialize',{'protocolVersion':'2025-03-26','capabilities':{},
            'clientInfo':{'name':'mist-local-cad-client','version':'1.0'}})
        self.rpc('notifications/initialized',notification=True)

    def rpc(self,method,params=None,notification=False):
        payload={'jsonrpc':'2.0','method':method}
        if not notification:
            self.counter+=1
            payload['id']=self.counter
        if params is not None:
            payload['params']=params
        headers={'Content-Type':'application/json','Accept':'application/json, text/event-stream',
                 'MCP-Protocol-Version':'2025-03-26'}
        if self.session:
            headers['Mcp-Session-Id']=self.session
        request=urllib.request.Request(ENDPOINT,data=json.dumps(payload).encode(),headers=headers)
        with urllib.request.urlopen(request,timeout=self.timeout) as response:
            self.session=response.headers.get('Mcp-Session-Id') or self.session
            raw=response.read().decode()
        if not raw:
            return {}
        result=json.loads(raw)
        if 'error' in result:
            raise RuntimeError(json.dumps(result['error']))
        return result

    def call(self,name,arguments):
        return self.rpc('tools/call',{'name':name,'arguments':arguments})


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--tool',default='fusion_mcp_read')
    parser.add_argument('--arguments',type=Path)
    parser.add_argument('--script',type=Path)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--timeout',type=float,default=90)
    args=parser.parse_args()
    if bool(args.arguments)==bool(args.script):
        parser.error('Provide exactly one argument JSON file or Python script file')
    if args.script:
        name='fusion_mcp_execute'
        source=args.script.read_text(encoding='utf-8')
        filename=str(args.script.resolve())
        # Fusion's inline-script scope has no __file__. A real module namespace
        # supports the same relative resources and dataclasses as a Scripts run.
        source_hash=hashlib.sha256(args.script.read_bytes()).hexdigest()
        bootstrap=("import sys, importlib.util, hashlib\nfrom pathlib import Path\n"
                   "def run(_context: str):\n"
                   "    path=Path("+repr(filename)+")\n"
                   "    if hashlib.sha256(path.read_bytes()).hexdigest()!="+repr(source_hash)+":\n"
                   "        raise RuntimeError('Script changed before native execution')\n"
                   "    spec=importlib.util.spec_from_file_location('mist_mcp_file_entry',path)\n"
                   "    module=importlib.util.module_from_spec(spec)\n"
                   "    sys.modules[spec.name]=module\n"
                   "    spec.loader.exec_module(module)\n"
                   "    result=module.run(_context)\n"
                   "    if isinstance(result,dict):\n"
                   "        print({k:result[k] for k in ('status','native_revolute_count','created_rigid_groups','fixture_joint_checks_verified','errors','reactivated_body','preserved_body_unchanged','body_unchanged') if k in result})\n"
                   "        if 'failed' in str(result.get('status','')).lower():\n"
                   "            raise RuntimeError(str(result.get('errors',result.get('error','Native operation failed'))))\n")
        arguments={'featureType':'script','object':{'script':bootstrap}}
    else:
        name=args.tool
        arguments=json.loads(args.arguments.read_text(encoding='utf-8'))
    response=FusionClient(args.timeout).call(name,arguments)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(response,indent=2),encoding='utf-8')
    failed=bool(response.get('result',{}).get('isError'))
    for content in response.get('result',{}).get('content',[]):
        if content.get('type')=='text':
            print(content['text'])
            try:
                inner=json.loads(content['text'])
            except (ValueError,TypeError):
                continue
            if isinstance(inner,dict) and inner.get('success') is False:
                failed=True
    if failed:
        raise SystemExit(1)


if __name__=='__main__':
    main()
