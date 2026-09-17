import sys,time,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parents[1]/'benchmarks'/'live'));import turbo_trial as m
class T(unittest.TestCase):
 def test_mock_sse_protocol(self):
  class R:
   status=200
   def __init__(s):s.x=iter([b'data: {"choices":[{"delta":{"reasoning_content":"r"}}]}\n',b'data: {"choices":[{"delta":{"content":"v"},"finish_reason":"stop"}]}\n',b'data: {"usage":{"completion_tokens":2}}\n',b'data: [DONE]\n'])
   def getheaders(s):return [('content-type','text/event-stream')]
   def readline(s):return next(s.x,b'')
  class C:
   def __init__(s,*x,**y):pass
   def request(s,*x):pass
   def getresponse(s):return R()
   def close(s):pass
  q=m.Client('http://x/v1',C).request({'stream':True},time.monotonic()+2);self.assertTrue(m.good(q));self.assertIsNotNone(q['first_reasoning_ttft_seconds']);self.assertIsNotNone(q['first_visible_ttft_seconds'])
 def test_stream_tool_call_is_complete_assistant_schema(self):
  class R:
   status=200
   def __init__(s):s.x=iter([b'data: {"choices":[{"delta":{"tool_calls":[{"index":0,"id":"call_1","type":"function","function":{"name":"get_weather","arguments":"{\\"location\\":\\"Paris\\"}"}}]},"finish_reason":"tool_calls"}]}\n',b'data: {"usage":{"completion_tokens":1}}\n',b'data: [DONE]\n'])
   def getheaders(s):return [('content-type','text/event-stream')]
   def readline(s):return next(s.x,b'')
  class C:
   def __init__(s,*x,**y):pass
   def request(s,*x):pass
   def getresponse(s):return R()
   def close(s):pass
  q=m.Client('http://x/v1',C).request({'stream':True},time.monotonic()+2);self.assertTrue(m.good(q));self.assertTrue(m.toolok(q['tool_calls']));self.assertEqual(q['tool_calls'][0]['type'],'function')
 def test_stream_http_error_keeps_raw_body(self):
  class R:
   status=400
   def getheaders(s):return [('content-type','application/json')]
   def read(s):return b'{"error":"bad tool schema"}'
  class C:
   def __init__(s,*x,**y):pass
   def request(s,*x):pass
   def getresponse(s):return R()
   def close(s):pass
  q=m.Client('http://x/v1',C).request({'stream':True},time.monotonic()+2);self.assertEqual(q['status'],400);self.assertIn('bad tool schema',q['raw_response'])
 def test_arm_validator_fails_closed_on_missing_matrix_and_foreign_state(self):
  q=m.validate_arm({'state':'complete','foreign_traffic_detected':True,'records':[]});self.assertFalse(q['valid']);self.assertIn('foreign_or_ambiguous_traffic',q['reasons']);self.assertIn('scenario_counts',q['reasons'])
 def test_validators(self):
  self.assertTrue(m.toolok([{'id':'x','function':{'name':'get_weather','arguments':'{"location":"Paris"}'}}]));self.assertFalse(m.toolok([]));self.assertTrue(m.codeok('even','```python\ndef is_even(n): return n % 2 == 0\n```'));self.assertTrue(m.codeok('clamp','```python\ndef clamp(n,low,high): return min(max(n,low),high)\n```'));self.assertTrue(m.codeok('gcd','```python\ndef gcd(a,b):\n while b: a,b=b,a%b\n return abs(a)\n```'));self.assertFalse(m.codeok('even','```python\ndef is_even(n): return n.__class__\n```'))
if __name__=='__main__':unittest.main()
