"""Execute emitted packet helpers with a bounded fixed-point scope interpreter.

Only the tested script subset is modeled; this is not native CK3 certification.
"""
from decimal import Decimal, ROUND_DOWN
import operator
import random
import unittest
from generate_aawc_stage5_packets import render
from test_aawc_cohort_bounded_arithmetic import parse
from aawc_stage5_identity_reference import normalize

D = Decimal

def fixed(x):
    return D(x).quantize(D('.00001'), rounding=ROUND_DOWN)

class PacketVM:
    def __init__(self, rows, amount=100, population=1000):
        self.packet = dict(culture_rows=rows, faith_rows=[dict(r) for r in rows],
                           amount=D(amount), source_population=D(population), phase=D(0), invalid=D(0))
        self.scopes = {'aawc_stage5_packet': self.packet}
        self.text = render()
        self.steps = 0
        self.writes = []
        self.globals = {}

    def value(self, x, cur, prev):
        if isinstance(x, list):
            result = D(0)
            for k, _, v in x:
                if k == 'floor': result = result // 1
                elif k == 'value': result = self.value(v, cur, prev)
                elif k in ('add', 'subtract', 'multiply', 'divide', 'min', 'max'):
                    result = fixed({'add':operator.add, 'subtract':operator.sub,
                                    'multiply':operator.mul, 'divide':operator.truediv,
                                    'min':max, 'max':min}[k](result, self.value(v,cur,prev)))
                elif k == 'if':
                    if self.cond(next(a for b,_,a in v if b == 'limit'),cur,prev):
                        result += self.value([n for n in v if n[0] != 'limit'],cur,prev)
                else: raise AssertionError(k)
            return result
        if x == 'this': return cur
        if x == 'prev': return prev
        if x.startswith('global_var:'): return self.globals[x[11:]]
        if x.startswith('this.'):
            result = cur
            tail = x[5:].split('.')
        elif x.startswith('prev.'):
            result = prev
            tail = x[5:].split('.')
        elif x.startswith('scope:'):
            head, *tail = x[6:].split('.')
            result = self.scopes[head]
        elif x.startswith('var:'):
            head, *tail = x[4:].split('.')
            result = cur[head]
        elif x.startswith(('barony.', 'holder.', 'county.')):
            head, *tail = x.split('.')
            result = cur[head]
        else: return D(x)
        for part in tail: result = result[part.removeprefix('var:')]
        return result

    def cond(self, nodes, cur, prev):
        for k, op, v in nodes:
            if k in ('NOT', 'OR', 'AND'):
                results = [self.cond([n], cur, prev) for n in v]
                ok = not all(results) if k == 'NOT' else any(results) if k == 'OR' else all(results)
            elif k == 'has_variable': ok = v in cur
            elif k == 'has_global_variable': ok = v in self.globals
            elif k == 'exists':
                try: ok = self.value(v,cur,prev) is not None
                except KeyError: ok = False
            elif isinstance(v, list): ok = self.cond(v, self.value(k, cur, prev), cur)
            else:
                try:
                    left, right = self.value(k, cur, prev), self.value(v, cur, prev)
                except KeyError:
                    if op == '?=': return False
                    raise
                if isinstance(left, dict): ok = left is not right if op == '!=' else left is right
                else: ok = {'=': operator.eq, '>': operator.gt, '<': operator.lt,
                            '<=': operator.le, '>=': operator.ge, '!=': operator.ne, '?=': operator.eq}[op](left, right)
            if not ok: return False
        return True

    def call(self, name, params=None, cur=None, prev=None):
        text = self.text
        for k,v in (params or {}).items(): text = text.replace('$'+k+'$', v)
        defs = {k:v for k,_,v in parse(text)}
        self.run(defs['aawc_stage5_'+name+'_effect'], self.packet if cur is None else cur, prev)

    def run(self, nodes, cur, prev):
        branch = False
        for k,_,v in nodes:
            self.steps += 1
            if self.steps > 50000: raise AssertionError('unbounded iteration')
            if k in ('if', 'else_if', 'else'):
                if k == 'if': branch = False
                take = not branch and (k == 'else' or self.cond(next(a for b,_,a in v if b=='limit'), cur, prev))
                if take:
                    self.run([n for n in v if n[0]!='limit'], cur, prev)
                    branch = True
            elif k == 'dummy_male': self.run(v, {}, cur)
            elif k == 'create_story':
                args = {a:b for a,_,b in v}
                self.scopes[args['save_scope_as']] = {}
            elif k == 'add_to_variable_list':
                args = {a:b for a,_,b in v}
                cur.setdefault(args['name'], []).append(self.value(args['target'],cur,prev))
            elif k in ('add_to_global_variable_list', 'remove_list_global_variable'):
                args = {a:b for a,_,b in v}
                items = self.globals.setdefault(args['name'], [])
                target = self.value(args['target'],cur,prev)
                if k == 'add_to_global_variable_list':
                    if not any(x is target for x in items): items.append(target)
                else: items[:] = [x for x in items if x is not target]
            elif k == 'clear_global_variable_list': self.globals.pop(v, None)
            elif k == 'save_scope_as': self.scopes[v] = cur
            elif k == 'remove_variable': cur.pop(v, None)
            elif k == 'remove_global_variable': self.globals.pop(v,None)
            elif k in ('set_global_variable', 'change_global_variable'):
                args = {a:b for a,_,b in v}
                name = args.pop('name')
                op, x = next(iter(args.items()))
                val = self.value(x, cur, prev)
                if op == 'value': self.globals[name] = val
                else: self.globals[name] = fixed({'add':operator.add,'subtract':operator.sub}[op](self.globals[name],val))
            elif k in ('set_variable', 'change_variable'):
                args = {a:b for a,_,b in v}
                name = args.pop('name')
                op, x = next(iter(args.items()))
                val = self.value(x, cur, prev)
                if op == 'value': cur[name] = val
                else: cur[name] = fixed({'add':operator.add,'subtract':operator.sub,'multiply':operator.mul,'divide':operator.truediv}[op](cur[name],val))
            elif k in ('every_in_list', 'every_in_global_list'):
                args = {a:b for a,_,b in v}
                container = self.globals if k == 'every_in_global_list' else cur
                for row in list(container.get(args['variable'], [])):
                    if 'limit' not in args or self.cond(args['limit'], row, cur):
                        self.run([n for n in v if n[0] not in ('variable','global_variable','limit')], row, cur)
            elif k == 'while':
                limit = next(a for b,_,a in v if b=='limit')
                while self.cond(limit, cur, prev): self.run([n for n in v if n[0]!='limit'], cur, prev)
            elif k.startswith('aawc_stage5_'):
                if v == []: raise AssertionError('CK3 rejects empty scripted-effect argument lists')
                self.call(k[len('aawc_stage5_'):-len('_effect')], {a:b for a,_,b in v} if isinstance(v,list) else {}, cur, prev)
            elif k == 'E_kCAFG_set_struct_factor':
                args = {a:b for a,_,b in v}
                self.write_factor(cur, args['TYPE'], self.value(args['SCOPE'],cur,prev), self.value(args['FACTOR'],cur,prev))
            elif k.startswith(('scope:', 'var:')): self.run(v,self.value(k,cur,prev),cur)
            elif self.external(k, v, cur, prev): pass
            else: raise AssertionError(k)

    def external(self, k, v, cur, prev):
        return False

    def write_factor(self, cur, axis, identity, factor):
        self.writes.append((cur, identity, factor))


def rows(values):
    return [dict(identity={'key':k}, rank=D(i+1), original_factor=D(v), quantity=D(0))
            for i,(k,v) in enumerate(sorted(values.items()))]

class NativePacketTests(unittest.TestCase):
    def test_independent_fallback_and_stable_tie(self):
        vm=PacketVM(list(reversed(rows({'a':'.5','b':'.5'}))))
        vm.packet['faith_explicit']=D(1)
        vm.packet['faith_rows'][0]['quantity']=D(100)
        vm.call('resolve_missing_axis', {'TYPE':'culture'})
        vm.call('resolve_missing_axis', {'TYPE':'faith'})
        self.assertEqual(vm.packet['culture_fallback']['key'],'a')
        self.assertNotIn('faith_fallback',vm.packet)
        self.assertEqual(vm.packet['faith_rows'][0]['quantity'],100)

    def test_bad_ranks_and_empty_fallback_fail_closed(self):
        for rs in ([], rows({'a':'.5','b':'.5'})):
            if rs: rs[1]['rank']=rs[0]['rank']
            vm=PacketVM(rs)
            vm.call('resolve_missing_axis',{'TYPE':'culture'})
            self.assertEqual(vm.packet['invalid'],1)
            self.assertNotIn('culture_fallback',vm.packet)

    def test_normalization_matches_oracle(self):
        rng=random.Random(5)
        for _ in range(100):
            masses={str(i):rng.randint(0,10000) for i in range(5)}
            vm=PacketVM(rows({k:'0' for k in masses}))
            for row in vm.packet['culture_rows']: row['mass']=D(masses[row['identity']['key']])
            vm.packet['denominator']=D(sum(masses.values()))
            vm.call('normalize_rows',{'TYPE':'culture','DENOMINATOR':'scope:aawc_stage5_packet.var:denominator'})
            actual={r['identity']['key']:int(r['units']) for r in vm.packet['culture_rows']}
            self.assertEqual(actual,normalize(masses))
            self.assertEqual(sum(actual.values()),100000)
            self.assertEqual(vm.packet['invalid'],0)

    def test_prepare_debit_and_retry_receipt(self):
        vm=PacketVM(rows({'a':'.6','b':'.4'}))
        for axis in ('culture','faith'):
            vm.packet[axis+'_rows'][0]['quantity']=D(100)
        vm.packet['phase']=D(1)
        vm.call('prepare_source_debit')
        self.assertEqual(vm.packet['source_prepared'],1)
        self.assertEqual([r['units'] for r in vm.packet['culture_rows']],[D(55556),D(44444)])
        vm.packet['source']={'aawc_population_current':D(900)}
        vm.call('apply_source_debit')
        self.assertEqual(vm.writes,[])
        vm.packet['phase']=D(2)
        vm.call('apply_source_debit')
        self.assertEqual(len(vm.writes),4)
        vm.call('apply_source_debit')
        self.assertEqual(len(vm.writes),4)
        self.assertEqual(vm.packet['source']['aawc_population_current'],900)

    def test_overdraw_and_receipt_mismatch(self):
        vm=PacketVM(rows({'a':'.05','b':'.95'}))
        vm.packet['culture_rows'][0]['quantity']=D(100)
        vm.packet['phase']=D(1)
        vm.call('prepare_source_debit')
        self.assertEqual(vm.packet['invalid'],1)
        self.assertNotIn('source_prepared',vm.packet)
        vm.packet.update(phase=D(2),source_prepared=D(1),invalid=D(0),source={'aawc_population_current':D(901)})
        vm.call('apply_source_debit')
        self.assertEqual(vm.writes,[])

if __name__=='__main__': unittest.main()
