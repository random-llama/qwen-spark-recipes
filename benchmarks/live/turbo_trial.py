#!/usr/bin/env python3
"""Single-arm, bounded evidence collector. Never manages engines or routing."""
from __future__ import annotations
import argparse,ast,base64,concurrent.futures,hashlib,http.client,json,os,re,statistics,threading,time,signal
from pathlib import Path
from urllib.parse import urlsplit
CS=(1,2,4); LIMIT=900.; REQ=180.
IMAGE=Path(__file__).resolve().parents[1]/'data'/'quadrants.png'
TOOL={'type':'function','function':{'name':'get_weather','parameters':{'type':'object','additionalProperties':False,'required':['location'],'properties':{'location':{'type':'string'}}}}}
TASKS=(('even','Return only a Python fenced block defining is_even(n), no imports.'),('clamp','Return only a Python fenced block defining clamp(n,low,high), no imports.'),('gcd','Return only a Python fenced block defining gcd(a,b), no imports.'))
def atomic(p,x):
 t=p.with_suffix(p.suffix+'.partial');t.write_text(json.dumps(x,indent=2),encoding='utf-8');os.replace(t,p)
def corpus(n,k):
 w='harbor signal cedar granite orbit copper ripple meadow'.split();return 'TRIAL '+k+'\n'+' '.join(w[i%8] for i in range(n))
def good(r):
 h={k.lower():v for k,v in r.get('headers',[])};u=r.get('usage') or {};ctype='text/event-stream' if r.get('stream') else 'application/json';return r.get('outcome')=='completed' and r.get('status')==200 and ctype in h.get('content-type','') and r.get('finish_reason') in ('stop','length','tool_calls') and isinstance(u.get('completion_tokens'),int) and u['completion_tokens']>0
def metrics(url):
 p=urlsplit(url.rstrip('/').removesuffix('/v1')+'/metrics');c=(http.client.HTTPSConnection if p.scheme=='https' else http.client.HTTPConnection)(p.hostname,p.port,timeout=5)
 try:
  c.request('GET',p.path);body=c.getresponse().read().decode('utf-8','replace');out={}
  for line in body.splitlines():
   x=line.split();
   if len(x)==2:
    try:
     k=x[0].split('{')[0]
     if k.endswith(('request_success_total','num_requests_running','num_requests_waiting')):out[k]=out.get(k,0)+float(x[1])
    except ValueError:pass
  return {k:v for k,v in out.items() if k.endswith(('request_success_total','num_requests_running','num_requests_waiting'))}
 finally:c.close()
class Client:
 def __init__(s,url,factory=None):
  s.url=url.rstrip('/') if url.rstrip('/').endswith('/chat/completions') else url.rstrip('/')+'/chat/completions';s.p=urlsplit(s.url);s.f=factory
  if s.p.scheme not in ('http','https') or not s.p.hostname or s.p.username:raise ValueError('absolute credential-free endpoint required')
 def request(s,payload,deadline,first=None):
  raw=json.dumps(payload,separators=(',',':')).encode();cls=s.f or (http.client.HTTPSConnection if s.p.scheme=='https' else http.client.HTTPConnection);start=time.monotonic();out={'request':payload,'url':s.url,'started_monotonic':start,'stream':bool(payload.get('stream'))};ct=[];rs=[];calls={};gaps=[];last=None;firstgen=lastgen=None;fr=fv=None;usage=None;finish=None;done=False;c=cls(s.p.hostname,s.p.port,timeout=max(.1,deadline-start))
  try:
   c.request('POST',s.p.path,raw,{'Content-Type':'application/json','Accept':'text/event-stream' if payload.get('stream') else 'application/json','Content-Length':str(len(raw))});r=c.getresponse();out.update(status=r.status,headers=list(r.getheaders()),raw_sse='')
   if r.status != 200:
    out['raw_response']=r.read().decode('utf-8','replace');raise RuntimeError('HTTP %s'%r.status)
   if not payload.get('stream'):
    body=r.read().decode('utf-8','replace');out['raw_response']=body;z=json.loads(body);q=(z.get('choices') or [{}])[0];msg=q.get('message') or {};ct=[msg.get('content') or ''];rs=[msg.get('reasoning_content') or msg.get('reasoning') or ''];calls={i:x for i,x in enumerate(msg.get('tool_calls') or [])};usage=z.get('usage') or {};finish=q.get('finish_reason');done=True
   while payload.get('stream'):
    left=deadline-time.monotonic()
    if left<=0:raise TimeoutError('absolute request deadline elapsed')
    sock=getattr(getattr(getattr(r,'fp',None),'raw',None),'_sock',None)
    if sock:sock.settimeout(left)
    line=r.readline()
    if not line:break
    z=line.decode('utf-8','replace');out['raw_sse']+=z
    if not z.startswith('data:'):continue
    z=z[5:].strip()
    if z=='[DONE]':done=True;break
    e=json.loads(z);now=time.monotonic();usage=e.get('usage') or usage
    if e.get('error'):raise RuntimeError(str(e['error']))
    for q in e.get('choices') or []:
     d=q.get('delta') or {};a=d.get('reasoning_content') or d.get('reasoning') or '';b=d.get('content') or ''
     if a and fr is None:fr=now-start
     if a or b or d.get('tool_calls'):
      if firstgen is None:firstgen=now
      lastgen=now
     if b:
      if fv is None:fv=now-start
      if last is not None:gaps.append(now-last)
      last=now;ct.append(b)
      if first:first(now);first=None
     rs.append(a);finish=q.get('finish_reason') or finish
     for x in d.get('tool_calls') or []:
      y=calls.setdefault(x.get('index',0),{'id':'','type':'function','function':{'name':'','arguments':''}});y['id']+=x.get('id','');y['type']=x.get('type') or y['type'];f=x.get('function') or {};y['function']['name']+=f.get('name','');y['function']['arguments']+=f.get('arguments','')
   if not done:raise RuntimeError('missing DONE')
   out.update(outcome='completed',content=''.join(ct),reasoning=''.join(rs),tool_calls=list(calls.values()),usage=usage or {},finish_reason=finish)
  except Exception as e:out.update(outcome='error',error={'type':type(e).__name__,'message':str(e)},content=''.join(ct),reasoning=''.join(rs),tool_calls=list(calls.values()),usage=usage or {},finish_reason=finish)
  finally:
   out.update(ended_monotonic=time.monotonic(),elapsed_seconds=time.monotonic()-start,first_reasoning_ttft_seconds=fr,first_visible_ttft_seconds=fv,max_content_gap_seconds=max(gaps) if gaps else None);u=out['usage'].get('completion_tokens');span=(lastgen-firstgen) if firstgen is not None and lastgen is not None else 0;out['decode_tokens_per_second']=(u-1)/span if isinstance(u,int) and u>1 and span>0 else None;out['end_to_end_completion_tokens_per_second']=u/out['elapsed_seconds'] if isinstance(u,int) and out['elapsed_seconds'] else None;c.close()
  return out
def toolok(x):
 try:return len(x)==1 and bool(x[0]['id']) and x[0]['function']['name']=='get_weather' and json.loads(x[0]['function']['arguments'])=={'location':'Paris'}
 except Exception:return False
def validate_arm(doc):
 """Fail-closed arm receipt validator; controller may call this after reading summary."""
 rs=doc.get('records') or [];kind=lambda k:[x for x in rs if x.get('scenario',{}).get('kind')==k]
 expected={'context':28,'thinking':2,'tool':8,'tool_followup':8,'vision':1,'code':21,'overlap':2}
 counts={k:len(kind(k)) for k in expected};cells=[(c,z,p) for c in CS for z in ('11k','45k') for p in ('fresh','repeat')];tools=[(x,y,z) for x in ('auto','named') for y in (False,True) for z in (False,True)]
 reasons=[]
 if doc.get('state')!='complete':reasons.append('state')
 if doc.get('foreign_traffic_detected') is not False:reasons.append('foreign_or_ambiguous_traffic')
 if counts!=expected:reasons.append('scenario_counts')
 if len({x.get('label') for x in rs})!=len(rs):reasons.append('duplicate_labels')
 if not all(x.get('protocol_valid') for x in rs):reasons.append('protocol')
 if not all(sum(x.get('scenario',{}).get('c')==c and x.get('scenario',{}).get('size')==z and x.get('scenario',{}).get('phase')==p for x in kind('context'))==c for c,z,p in cells):reasons.append('context_cells')
 if not all(sum(x.get('scenario',{}).get('choice')==a and x.get('scenario',{}).get('thinking')==b and x.get('scenario',{}).get('stream')==c for x in kind('tool'))==1 and sum(x.get('scenario',{}).get('choice')==a and x.get('scenario',{}).get('thinking')==b and x.get('scenario',{}).get('stream')==c for x in kind('tool_followup'))==1 for a,b,c in tools):reasons.append('tool_cells')
 if not all(x.get('tool_valid') for x in kind('tool')) or not all(x.get('followup_valid') for x in kind('tool_followup')):reasons.append('tools')
 if not all(x.get('code_valid') for x in kind('code')):reasons.append('code')
 if not all(x.get('content','').strip()=='323' for x in kind('thinking')):reasons.append('thinking')
 if not any('red,blue,green,yellow' in x.get('content','').replace(' ','').lower() for x in kind('vision')):reasons.append('vision')
 if sum(x.get('scenario',{}).get('role')=='decode' for x in kind('overlap'))!=1 or sum(x.get('scenario',{}).get('role')=='prefill' and x.get('overlap_proven') for x in kind('overlap'))!=1:reasons.append('overlap')
 return {'valid':not reasons,'reasons':reasons,'counts':counts}
def codeok(n,t):
 m=re.search(r'```python\s*(.*?)```',t,re.S|re.I)
 if not m:return False
 try:
  z=ast.parse(m.group(1));f=z.body[0];allow=(ast.Module,ast.FunctionDef,ast.arguments,ast.arg,ast.Return,ast.If,ast.Compare,ast.BinOp,ast.Name,ast.Load,ast.Constant,ast.Eq,ast.Lt,ast.Gt,ast.Mod,ast.FloorDiv,ast.Sub,ast.Add,ast.While,ast.Assign,ast.Store,ast.Tuple,ast.Call)
  expected={'even':'is_even','clamp':'clamp','gcd':'gcd'}[n]
  if len(z.body)!=1 or not isinstance(f,ast.FunctionDef) or f.name!=expected or any(not isinstance(x,allow) for x in ast.walk(z)) or any(not(isinstance(x.func,ast.Name) and x.func.id in ('abs','min','max')) for x in ast.walk(z) if isinstance(x,ast.Call)):return False
  old=signal.getsignal(signal.SIGALRM) if hasattr(signal,'SIGALRM') else None
  try:
   if hasattr(signal,'setitimer'):
    signal.signal(signal.SIGALRM,lambda *_:(_ for _ in ()).throw(TimeoutError('generated code deadline')));signal.setitimer(signal.ITIMER_REAL,2)
   q={'__builtins__':{'abs':abs,'min':min,'max':max}};exec(compile(z,'<model>','exec'),q,q)
   if n=='even':result=all(q[expected](x)==(x%2==0) for x in range(-8,9))
   elif n=='clamp':result=all(q[expected](*x)==y for x,y in [((3,0,2),2),((-1,0,2),0),((1,0,2),1)])
   else:result=all(q[expected](*x)==y for x,y in [((54,24),6),((7,3),1),((0,5),5)])
  finally:
   if hasattr(signal,'setitimer'):signal.setitimer(signal.ITIMER_REAL,0);signal.signal(signal.SIGALRM,old)
  return result
 except Exception:return False
class Run:
 def __init__(s,a):
  s.a=a;s.o=Path(a.out).resolve();s.o.mkdir(parents=True);s.end=time.monotonic()+LIMIT;s.c=Client(a.base_url);s.lock=threading.Lock();s.rows=[];s.doc={'schema':3,'arm':a.arm,'model':a.model,'trial_nonce':a.trial_nonce,'records':s.rows,'state':'running','vision_sha256':hashlib.sha256(IMAGE.read_bytes()).hexdigest(),'metrics_before':metrics(a.base_url)};atomic(s.o/'summary.json',s.doc)
 def pay(s,p,think=False,max=64,tools=None,choice=None):
  x={'model':s.a.model,'messages':[{'role':'user','content':p}],'temperature':0,'max_tokens':max,'stream':True,'stream_options':{'include_usage':True},'chat_template_kwargs':{'enable_thinking':think}}
  if tools:x['tools']=tools
  if choice:x['tool_choice']=choice
  return x
 def one(s,l,p,sc,first=None):
  r=s.c.request(p,min(s.end,time.monotonic()+REQ),first);r.update(label=l,scenario=sc,protocol_valid=good(r))
  with s.lock:s.rows.append(r);atomic(s.o/('%03d-'%len(s.rows)+l+'.json'),r);atomic(s.o/'summary.json',s.doc)
  return r
 def amend(s,r,**changes):
  with s.lock:
   r.update(changes);atomic(s.o/('%03d-'%(s.rows.index(r)+1)+r['label']+'.json'),r);atomic(s.o/'summary.json',s.doc)
 def batch(s,l,ps,sc):
  with concurrent.futures.ThreadPoolExecutor(max_workers=len(ps)) as e:return [x.result() for x in [e.submit(s.one,l+'-r%d'%(i+1),p,sc) for i,p in enumerate(ps)]]
 def run(s):
  try:
   for c in CS:
    for size,n in (('11k',11000),('45k',45000)):
     ps=[corpus(n,'%s-c%d-%s-r%d'%(s.a.trial_nonce,c,size,i))+ '\nReply only CONTEXT_OK' for i in range(c)]
     for phase in ('fresh','repeat'):s.batch('context-c%d-%s-%s'%(c,size,phase),[s.pay(x,False,8) for x in ps],{'kind':'context','c':c,'size':size,'phase':phase})
   ev=threading.Event();ts=[]
   with concurrent.futures.ThreadPoolExecutor(max_workers=1) as e:
    d=e.submit(s.one,'overlap-decode',s.pay('Write Python LRU code then explain it.',False,512),{'kind':'overlap','role':'decode'},lambda x:(ts.append(x),ev.set()))
    if not ev.wait(45):raise RuntimeError('no decode content before prefill')
    p=s.one('overlap-prefill',s.pay(corpus(45000,s.a.trial_nonce+'-overlap')+'\nReply only OK',False,8),{'kind':'overlap','role':'prefill'});z=d.result();s.amend(p,overlap_proven=ts[0]<p['started_monotonic']<z['ended_monotonic'])
   for think in (False,True):s.one('thinking-'+str(think),s.pay('Calculate 17*19 and reply only the integer.',think,512),{'kind':'thinking','enabled':think})
   for choice in ('auto','named'):
    for think in (False,True):
     for stream in (True,False):
      q=s.pay('Use get_weather to look up Paris, then tell me its temperature in Celsius from the tool result. Do not guess before calling the tool.',think,512,[TOOL],'auto' if choice=='auto' else {'type':'function','function':{'name':'get_weather'}});q['stream']=stream
      if not stream:q.pop('stream_options',None)
      r=s.one('tool-%s-%s-%s'%(choice,think,stream),q,{'kind':'tool','choice':choice,'thinking':think,'stream':stream});s.amend(r,tool_valid=toolok(r['tool_calls']))
      if r['tool_valid']:
       q={'model':s.a.model,'messages':[{'role':'user','content':'Use get_weather to look up Paris, then tell me its temperature in Celsius from the tool result. Do not guess before calling the tool.'},{'role':'assistant','content':r['content'] or None,'tool_calls':r['tool_calls']},{'role':'tool','tool_call_id':r['tool_calls'][0]['id'],'content':'{"location":"Paris","temperature_c":22}'}],'temperature':0,'max_tokens':512,'stream':stream,'chat_template_kwargs':{'enable_thinking':think}}
       if stream:q['stream_options']={'include_usage':True}
       f=s.one('tool-%s-%s-%s-followup'%(choice,think,stream),q,{'kind':'tool_followup','choice':choice,'thinking':think,'stream':stream});s.amend(f,followup_valid='22' in f['content'] and not f['tool_calls'])
   image='data:image/png;base64,'+base64.b64encode(IMAGE.read_bytes()).decode();v=s.pay('',False,64);v['messages']=[{'role':'user','content':[{'type':'text','text':'Identify the four quadrant colors in reading order. Reply comma-separated lowercase color names.'},{'type':'image_url','image_url':{'url':image}}]}];s.one('vision',v,{'kind':'vision'})
   for c in (1,2,4):
    for n,p in TASKS:
     rs=s.batch('code-c%d-'%c+n,[s.pay(p,False,512) for _ in range(c)],{'kind':'code','c':c,'task':n})
     for r in rs:s.amend(r,code_valid=codeok(n,r['content']))
   s.doc['state']='complete'
  except Exception as e:s.doc.update(state='incomplete',error={'type':type(e).__name__,'message':str(e)})
  s.doc['elapsed_seconds']=LIMIT-(s.end-time.monotonic());s.doc['metrics_after']=metrics(s.a.base_url);s.doc['accepted_http_200_requests']=sum(x.get('status')==200 for x in s.rows);s.doc['completed_inferences']=sum(x.get('status')==200 and x.get('outcome')=='completed' for x in s.rows);s.doc['grading_or_protocol_failures']=sum(not x.get('protocol_valid',False) for x in s.rows);before=s.doc['metrics_before'];after=s.doc['metrics_after'];key=next((x for x in before if x.endswith('request_success_total')),None);s.doc['foreign_traffic_detected']=key is None or key not in after or after[key]-before[key]!=s.doc['accepted_http_200_requests'];s.doc['arm_quality']=validate_arm(s.doc);atomic(s.o/'summary.json',s.doc);return 0 if s.doc['arm_quality']['valid'] else 1
def main(v=None):
 p=argparse.ArgumentParser();p.add_argument('--arm',required=True,choices=('baseline','turbo'));p.add_argument('--base-url',required=True);p.add_argument('--model',required=True);p.add_argument('--trial-nonce',required=True);p.add_argument('--out',required=True);a=p.parse_args(v)
 if os.name!='posix':raise RuntimeError('live execution requires Linux/POSIX because generated-code validation uses SIGALRM; see benchmarks/README.md')
 if Path(a.out).exists():raise ValueError('--out must not exist')
 return Run(a).run()
if __name__=='__main__':raise SystemExit(main())
