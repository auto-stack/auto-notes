from pathlib import Path
ROOT=Path.cwd()
source=(ROOT/'tests/probe/evidence/r5-work/run_vm_negative.py').read_text(encoding='utf8')
head=source.split('            # ── R5-VM-1:')[0]
tail=source[source.index("            record['negative_results'] = results"):]
cases='''
click('Welcome')
doc=call('GET','/api/v1/notes/n-1')['doc']
call('PUT','/api/v1/notes/n-1',dict(expected_revision=doc['revision'],title='server-A',body='external-A',request_id='ind-ext-A'))
edit('VM precious A'); click('Save'); click('Shopping List')
doc=call('GET','/api/v1/notes/n-3')['doc']
call('PUT','/api/v1/notes/n-3',dict(expected_revision=doc['revision'],title='server-B',body='external-B',request_id='ind-ext-B'))
edit('VM precious B'); click('Save'); click('Quick Ideas')
edit('VM precious C'); before=state(); click('Recover'); after=state()
results['full_slots_recover']=dict(before=before,after=after,b_preserved='VM precious B' in [after.get('draft_title'),after.get('rec_title'),after.get('rec2_title')])
check('IND-VM-1 existing B draft preserved',results['full_slots_recover']['b_preserved'],after)
click('Discard')
while state().get('has_recovery')=='true' or state().get('has_recovery2')=='true': click('Dismiss')
click('Quick Ideas')
call('POST','/api/v1/test/fault',dict(stage='after_manifest'))
edit('VM C1 unconfirmed'); click('Save')
call('POST','/api/v1/test/fault',dict(stage='off'))
committed=call('GET','/api/v1/notes/n-2')
edit('VM C2 new draft'); edited=state(); click('Recipe: Pasta'); stashed=state()
click('Recover'); restored=state(); click('Save'); retry1=state(); click('Save'); retry2=state()
results['changed_intent_recovery']=dict(committed=committed,edited=edited,stashed=stashed,restored=restored,retry1=retry1,retry2=retry2,server=call('GET','/api/v1/notes/n-2'))
check('IND-VM-2 recovered new intent can save',retry2.get('dirty')=='false' and results['changed_intent_recovery']['server']['doc']['title']=='VM C2 new draft',retry2)
'''
source=head+'\n'.join('            '+line if line else '' for line in cases.splitlines())+'\n'+tail
exec(compile(source,'independent-vm-runner','exec'))
