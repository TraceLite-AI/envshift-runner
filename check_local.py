"""Regression checks: final-state oracle, collateral changes, and input executor cleanup."""
import ast, copy, pathlib, unittest
from task_world import fixture,expected,grade,apply,csv_bytes,PROMPTS
class Grading(unittest.TestCase):
 def test_initial_and_final(self):
  for task in PROMPTS:
   self.assertEqual(grade(task,fixture(task))['reward'],0,task)
   data=csv_bytes([r for r in fixture(task).get('expenses',[]) if r['id'] in ['E-101','E-107','E-109','E-112']]) if task=='G07' else None
   self.assertEqual(grade(task,expected(task),data)['reward'],1,task)
 def test_wrong_artifacts(self):
  s=expected('G05');s['invoices'][0]['total']='0.00';self.assertEqual(grade('G05',s)['reward'],0)
  s=expected('G06');s['tickets'][0]['owner']='Mina';self.assertEqual(grade('G06',s)['reward'],0)
  s=fixture('G07');rows=[r for r in s['expenses'] if r['id'] in ['E-101','E-107','E-109']];self.assertEqual(grade('G07',s,csv_bytes(rows))['reward'],0)
  rows.append(rows[0]);self.assertEqual(grade('G07',s,csv_bytes(rows))['reward'],0)
  s=fixture('G08');apply('G08',s,{'op':'draft','id':'C-71',**expected('G08')['customers'][0]['live']});self.assertEqual(grade('G08',s)['reward'],0)
  apply('G08',s,{'op':'publish','id':'C-71'});self.assertEqual(grade('G08',s)['reward'],1)
  s=expected('G09');s['cards'][1]['column']='Review';self.assertEqual(grade('G09',s)['reward'],0)
  s=expected('G10');s['approval']={'route':'Standard','reason':'STD-1'};self.assertEqual(grade('G10',s)['reward'],0)
class Input(unittest.TestCase):
 def test_native_keys_and_drag_release(self):
  module=ast.parse(pathlib.Path('gui_agent_loop.py').read_text());code=ast.Module(body=[n for n in module.body if isinstance(n,ast.FunctionDef) and n.name in ['normalized_point','do']],type_ignores=[])
  class Mouse:
   def __init__(self):self.calls=[];self.fail=False
   def __getattr__(self,name):
    def call(*args,**kw):
     self.calls.append((name,args))
     if self.fail and name=='moveTo' and len(self.calls)>2:raise RuntimeError('motion failed')
    return call
  mouse=Mouse();ns={'pyautogui':mouse,'SCREEN_W':1024,'SCREEN_H':768,'SYS':'Darwin','time':type('Time',(),{'sleep':lambda _:None})}
  exec(compile(code,'input-contract','exec'),ns)
  ns['do']({'action':'key','keys':['ctrl','tab']},None);self.assertEqual(mouse.calls[-1],('hotkey',('ctrl','tab')))
  ns['do']({'action':'scroll','dy':-3},None);self.assertEqual(mouse.calls[-1],('scroll',(-3,)))
  mouse.calls=[];mouse.fail=True
  with self.assertRaises(RuntimeError):ns['do']({'action':'drag','x':200,'y':200,'to_x':800,'to_y':500},None)
  self.assertEqual(mouse.calls[-1],('mouseUp',()))
if __name__=='__main__':unittest.main()
