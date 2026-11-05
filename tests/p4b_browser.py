"""Shipped browser UI with explicit quality service mocks; NOT native HA join."""
import json, os, subprocess, unittest
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
FIXTURE="""states=>{
window.calls=[];window.writes=[];
window.q={schema_version:1,config_entry_id:states['sensor.status'].attributes.settings_target.config_entry_id,epoch:'a'.repeat(32),observation_revision:1,policy_revision:0,settings_revision:states['sensor.status'].attributes.settings_revision,flow_plan_revision:states['sensor.status'].attributes.flow_plan_revision,policy:{enabled:false,stable_samples:8,stable_interval_seconds:300,stable_duration_seconds:2100,permit_ttl_seconds:300,required_stages:['refill','nutrient','acid','mix'],sources:Object.fromEntries(['ph','ec','level'].map(k=>[k,{mode:'reported',attribute:null,report_contract_confirmed:false}]))},entities:{quality_status:'sensor.quality_selected',irrigation_permit:'binary_sensor.permit_selected'},quality:{state:'qualified',stable_count:8,stable_since:'2026-11-05T00:00:00Z',reasons:[]},completion:{state:'completed',run_id:'run',settled_at:'2026-11-05T00:00:00Z'},permit:{granted:false,run_id:null,expires_at:null,reasons:['no_current_run']}};
window.publish=()=>{states['sensor.quality_selected']={state:q.quality.state,attributes:structuredClone(q)};if(window.card)card.hass={...card.hass,states};};publish();
window.transport=async m=>{calls.push(structuredClone(m));if(m.service==='save_quality_policy_v1'){const d=m.service_data;if(d.expected_policy_revision!==q.policy_revision||d.expected_settings_revision!==q.settings_revision||d.expected_flow_plan_revision!==q.flow_plan_revision)throw {code:'quality_conflict'};q.policy=structuredClone(d.policy);q.policy_revision++;q.permit.granted=false;writes.push(m.service);publish();}return {response:structuredClone(q)};};
window.card=document.createElement('uninus-nutriculture-card');document.body.append(card);card.setConfig({entity:'sensor.status',quality_entity:'sensor.quality_selected'});card.hass={user:{id:'quality-test-admin',is_admin:true,is_active:true},states,services:{uninus_nutriculture:{get_quality_v1:{},save_quality_policy_v1:{}}},callWS:m=>transport(m),callService:()=>{throw Error('NO LOWER IO')}};
}"""
class QualityBrowserTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.pw=sync_playwright().start();cls.browser=cls.pw.chromium.launch(headless=True,executable_path=os.environ.get('CHROMIUM_EXECUTABLE'));print('BROWSER_VERSION='+cls.browser.version)
 @classmethod
 def tearDownClass(cls): cls.browser.close();cls.pw.stop()
 def setUp(self):
  self.p=self.browser.new_page(viewport={'width':320,'height':1000});self.errors=[];self.p.on('pageerror',lambda e:self.errors.append(str(e)));self.p.set_default_timeout(1800);self.p.set_content('<meta charset="utf-8"><body style="margin:0;padding:8px">');self.p.add_script_tag(path=str(ROOT/'uninus-nutriculture-card.js'))
  states=json.loads(subprocess.check_output([os.environ.get('NODE','node'),'-e',"console.log(JSON.stringify(require('./tests/p3c_fixture.cjs')()))"],cwd=ROOT));self.p.evaluate(FIXTURE,states)
 def tearDown(self): self.p.close();self.assertEqual(self.errors,[])
 def open(self):
  self.assertEqual(self.p.locator('[data-quality-panel]').count(),1,'Shipped Card must expose independent quality panel')
  self.p.locator('[data-quality-panel] summary').click();self.p.wait_for_function('!!card.qualityData')
 def test_01_policy_save_cancel_three_cas(self):
  self.open();p=self.p
  self.assertIn('qualified',p.locator('[data-quality-truth]').inner_text());self.assertIn('不許可',p.locator('[data-quality-permit]').inner_text())
  p.locator('[data-quality-field="stable_samples"]').fill('9');p.locator('[data-quality-save]').click();p.wait_for_function('!card.qualityOperation')
  self.assertEqual(p.evaluate('q.policy.stable_samples'),9);self.assertEqual(p.evaluate('writes'),['save_quality_policy_v1'])
  payload=p.evaluate("calls.find(m=>m.service==='save_quality_policy_v1').service_data")
  self.assertEqual(set(payload),{'config_entry_id','expected_policy_revision','expected_settings_revision','expected_flow_plan_revision','policy'})
  self.assertEqual(p.evaluate('calls[0]'),{'type':'call_service','domain':'uninus_nutriculture','service':'get_quality_v1','service_data':{'config_entry_id':p.evaluate('q.config_entry_id')},'return_response':True})
  self.assertIn('讀回',p.locator('[data-quality-message]').inner_text())
  p.locator('[data-quality-field="stable_samples"]').fill('10');p.locator('[data-quality-cancel]').click();self.assertEqual(p.locator('[data-quality-field="stable_samples"]').input_value(),'9');self.assertEqual(p.evaluate('writes.length'),1)
 def test_02_strict_dto_and_unicode_policy(self):
  self.open();p=self.p
  changes=['d.extra=1','d.quality.extra=1','d.policy.sources.ph.extra=1','d.permit.granted=1','d.policy.stable_samples=true','d.policy.stable_samples=null','d.quality.state="future"','d.permit.reasons=["PRIVATE"]','d.permit.reasons=["expired","expired"]','d.policy_revision=-1','d.policy_revision=9007199254740992','d.epoch="bad"','d.quality.stable_since="2026-02-30T00:00:00Z"','d.completion.settled_at="2026-11-05T24:00:00Z"','d.policy.sources.ph.attribute="not-null"','d.policy.required_stages=[]']
  # eval consumes only the fixed mutation strings above, never external input.
  for change in changes:
   self.assertFalse(p.evaluate('(change)=>{const d=structuredClone(q);eval(change);return card.qualityDTO(d,q.config_entry_id)}',change),change)
  p.locator('[data-quality-field="ph.mode"]').select_option('sequence');f=p.locator('[data-quality-field="ph.attribute"]');f.fill('🌱'*128);self.assertEqual(f.input_value(),'🌱'*128);self.assertTrue(p.locator('[data-quality-save]').is_enabled());f.fill('🌱'*129);self.assertTrue(p.locator('[data-quality-save]').is_disabled())
 def test_03_conflict_error_readback_keeps_draft(self):
  self.open();p=self.p;f=p.locator('[data-quality-field="stable_samples"]');f.fill('11');p.evaluate('q.settings_revision++');p.locator('[data-quality-save]').click();p.wait_for_function('!card.qualityOperation');self.assertEqual(f.input_value(),'11');self.assertIn('衝突',p.locator('[data-quality-message]').inner_text());self.assertEqual(p.evaluate('writes'),[])
  p.evaluate("q.settings_revision--;window.base=transport;transport=async m=>{if(m.service==='get_quality_v1')throw {message:'PRIVATE'};return base(m)};void 0")
  p.locator('[data-quality-save]').click();p.wait_for_function('!card.qualityOperation');self.assertEqual(f.input_value(),'11');self.assertNotIn('已保存',p.locator('[data-quality-message]').inner_text());self.assertNotIn('PRIVATE',p.locator('[data-quality-message]').inner_text())
 def test_04_dirty_keyboard_320_and_no_poll_io(self):
  self.open();p=self.p;f=p.locator('[data-quality-field="ph.attribute"]');p.locator('[data-quality-field="ph.mode"]').select_option('sequence');f.focus();p.keyboard.type('sample');p.evaluate('window.original=card.qualityInputs.get("ph.attribute");q.observation_revision++;publish()');p.keyboard.type('_seq');self.assertEqual(f.input_value(),'sample_seq');self.assertTrue(p.evaluate('card.shadowRoot.activeElement===original'));p.wait_for_function('!card.qualityOperation');self.assertEqual(p.evaluate('calls.length'),2);p.wait_for_timeout(150);self.assertEqual(p.evaluate('calls.length'),2);self.assertTrue(p.evaluate('calls.every(m=>m.service==="get_quality_v1")'));self.assertEqual(p.evaluate('writes'),[])
  rects=p.locator('[data-quality-panel] input:visible,[data-quality-panel] select:visible,[data-quality-panel] button:visible').evaluate_all('els=>els.map(e=>{const r=e.getBoundingClientRect();return [r.left,r.right]})');self.assertTrue(all(a>=0 and b<=320 for a,b in rects),rects)
  self.assertEqual(p.locator('[data-quality-grant]').count(),0)
 def test_05_three_truths_revoke_wrongslot_and_state(self):
  self.open();p=self.p
  p.evaluate('q.policy.enabled=true;for(const s of Object.values(q.policy.sources))s.report_contract_confirmed=true;publish()');p.locator('[data-quality-refresh]').click();self.assertIn('不許可 False',p.locator('[data-quality-permit]').inner_text())
  p.evaluate('q.permit.granted=true;publish()');self.assertIn('許可 True',p.locator('[data-quality-permit]').inner_text())
  p.evaluate('q.permit.granted=false;publish()');self.assertNotIn('許可 True',p.locator('[data-quality-permit]').inner_text())
  for change in ['q.config_entry_id="foreign"','card.hass.states["sensor.quality_selected"].state="unavailable"','q.epoch="b".repeat(32)','q.observation_revision++','q.quality.state="invalid"']:
   p.evaluate('window.good=structuredClone(q)');p.evaluate('q.permit.granted=true;'+change+';'+('' if change.startswith('card.') else 'publish()'));self.assertNotIn('許可 True',p.locator('[data-quality-permit]').inner_text(),change);p.evaluate('q=good;publish()')
 def test_06_transport_both_settlements_preserve_lock_cleanup(self):
  self.open();p=self.p
  for reject in [False,True]:
   p.evaluate('card.hass={...card.hass,callWS:m=>transport(m)}')
   p.locator('[data-quality-field="stable_samples"]').fill('12');p.evaluate('window.saved=structuredClone(q);window.base=transport;transport=m=>new Promise((resolve,reject)=>{window.finish=resolve;window.fail=reject});void 0');p.locator('[data-quality-save]').click();p.evaluate('card.hass={...card.hass,callWS:m=>base(m)}');self.assertTrue(p.locator('[data-quality-refresh]').is_disabled());self.assertTrue(p.evaluate('card.qualityFlights.has(q.config_entry_id)'))
   p.evaluate('fail({code:"quality_conflict",message:"PRIVATE"})' if reject else 'finish({response:saved})');p.wait_for_function('!card.qualityOperation');self.assertTrue(p.locator('[data-quality-refresh]').is_enabled());self.assertEqual(p.locator('[data-quality-field="stable_samples"]').input_value(),'12');self.assertNotIn('PRIVATE',p.locator('[data-quality-message]').inner_text());p.evaluate('transport=base;void 0');p.locator('[data-quality-refresh]').click()
 def test_07_new_slot_operation_isolation_and_disconnect(self):
  self.open();p=self.p
  p.evaluate('window.old=structuredClone(q);transport=m=>new Promise(resolve=>{window.finishA=resolve});void 0');p.locator('[data-quality-save]').click()
  p.evaluate('q.config_entry_id="entry-b";const a=card.hass.states["sensor.status"].attributes;a.settings_target.config_entry_id="entry-b";a.flow_plan_target.config_entry_id="entry-b";publish();transport=m=>new Promise((resolve,reject)=>{window.finishB=resolve;window.failB=reject});void card.qualityRequest(false)');p.wait_for_function('card.qualityOperation?.entry==="entry-b"');p.evaluate('window.opB=card.qualityOperation;finishA({response:old})');self.assertTrue(p.evaluate('card.qualityOperation===opB'));self.assertTrue(p.locator('[data-quality-refresh]').is_disabled());p.evaluate('card.remove();document.body.append(card);failB({code:"quality_conflict"})');p.wait_for_function('!card.qualityOperation');self.assertTrue(p.locator('[data-quality-refresh]').is_enabled())
 def test_08_editor_and_standalone_invalid_entity(self):
  p=self.p;p.evaluate('window.editor=document.createElement("uninus-nutriculture-card-editor");document.body.append(editor);editor.setConfig(card.config);editor.hass=card.hass;editor.addEventListener("config-changed",e=>window.changed=e.detail.config);editor.qualityInput.dispatchEvent(new CustomEvent("value-changed",{detail:{value:"sensor.other_quality"}}))');self.assertEqual(p.evaluate('changed.quality_entity'),'sensor.other_quality');self.assertEqual(p.evaluate('editor.qualityInput.selector'),{'entity':{'domain':'sensor'}})
  p.evaluate('card.setConfig({quality_entity:"sensor.quality_selected"});card.qualityPanel.open=true');self.assertTrue(p.locator('[data-quality-save]').is_hidden());self.assertIn('qualified',p.locator('[data-quality-truth]').inner_text());self.assertTrue(p.evaluate('(()=>{try{card.setConfig({entity:"bad",quality_entity:"sensor.quality_selected"});return false}catch{return true}})()'));self.assertEqual(p.evaluate('writes'),[])
 def test_09_native_connection_event_clears_true_and_draft(self):
  self.open();p=self.p
  p.evaluate('window.listeners={};window.connection={connected:true,addEventListener:(k,f)=>listeners[k]=f,removeEventListener:k=>delete listeners[k]};card.hass={...card.hass,connection};q.policy.enabled=true;for(const s of Object.values(q.policy.sources))s.report_contract_confirmed=true;q.permit.granted=true;publish()');p.locator('[data-quality-refresh]').click();self.assertIn('許可 True',p.locator('[data-quality-permit]').inner_text());p.locator('[data-quality-field="stable_samples"]').fill('13');p.evaluate('connection.connected=false;listeners.disconnected()');self.assertNotIn('許可 True',p.locator('[data-quality-permit]').inner_text());p.evaluate('connection.connected=true;listeners.ready()');self.assertNotIn('許可 True',p.locator('[data-quality-permit]').inner_text());self.assertEqual(p.locator('[data-quality-field="stable_samples"]').input_value(),'13');self.assertEqual(p.evaluate('writes'),[])
 def test_10_readonly_connection_reconnect_never_revives_cache(self):
  p=self.p;p.evaluate('window.listeners={};window.connection={connected:true,addEventListener:(k,f)=>listeners[k]=f,removeEventListener:k=>delete listeners[k]};card.setConfig({quality_entity:"sensor.quality_selected"});card.hass={...card.hass,connection};card.qualityPanel.open=true;q.policy.enabled=true;for(const s of Object.values(q.policy.sources))s.report_contract_confirmed=true;q.permit.granted=true;publish()');self.assertIn('許可 True',p.locator('[data-quality-permit]').inner_text());p.evaluate('connection.connected=false;listeners.disconnected();connection.connected=true;listeners.ready()');self.assertNotIn('許可 True',p.locator('[data-quality-permit]').inner_text(),'Connection ready must not restore cached readonly True');p.evaluate('card.remove()');self.assertEqual(p.evaluate('Object.keys(listeners)'),[],'Detached card must release connection listeners')
 # Captured-native replay, NOT a new native Core/live HA join. Historical
 # timestamps are DTO validation/display inputs, not current authorization.
 def record_captured(self, label):
  if not os.environ.get('BROWSER_EVIDENCE_DIR'):return
  out=Path(os.environ['BROWSER_EVIDENCE_DIR']);out.mkdir(parents=True,exist_ok=True)
  state=self.p.evaluate('()=>({cache:card.qualityData,native:card.qualityNative(),baseline:card.qualityBaseline,dirty:card.qualityDirty,requests:calls,truth:card.qualityTruth.textContent,completion:card.qualityCompletion.textContent,permit:card.qualityPermit.textContent,notice:card.qualityMessage.textContent,markup:card.qualityPanel.innerHTML})')
  state.update(page_errors=self.errors,evidence_type='CAPTURED_NATIVE_REPLAY_NOT_LIVE_JOIN')
  (out/(label+'.json')).write_text(json.dumps(state,ensure_ascii=False,indent=2),encoding='utf-8')
 def captured(self, saved=False):
  p=self.p; p.evaluate('card.remove()')
  folder=ROOT/'tests/p4b_r2_capture'
  events=json.loads((folder/'events.json').read_text(encoding='utf-8'))
  wire=json.loads((folder/'wire.json').read_text(encoding='utf-8'))
  receipts=next(e['receipts'] for e in events if e.get('case','').startswith('WIRE_FAIL'))
  grant=json.loads((folder/'grant.json').read_text(encoding='utf-8'))
  p.evaluate('''({receipts,wire,grant,saved})=>{
   window.receipts=receipts;window.wire=wire;window.grant=grant;window.calls=[];
   window.card=document.createElement('uninus-nutriculture-card');document.body.append(card);
   window.connection={connected:true};window.latest=saved?receipts[1]:receipts[0];
   window.push=s=>{card.hass={states:s.states,services:s.services,user:{id:s.user_id,is_admin:true},connection,callWS:transport};};
   window.transport=async m=>{calls.push(structuredClone(m));const i=calls.length-1;
    const expected=structuredClone(wire[m.service==='save_quality_policy_v1'?1:0].request);delete expected.id;
    if(JSON.stringify(m)!==JSON.stringify(expected))throw Error('exact captured request mismatch');
    if(m.service==='save_quality_policy_v1')latest=receipts[1];push(latest.snapshot);
    if(!latest.reply.success)throw latest.reply.error;return latest.reply.result;};
   card.setConfig({entity:latest.snapshot.status_id,quality_entity:latest.snapshot.quality_id});push(latest.snapshot);
  }''',dict(receipts=receipts,wire=wire,grant=grant,saved=saved))
  self.open();return p
 def test_11_captured_first_save_epoch_auto_readback(self):
  p=self.captured();policy=p.evaluate('wire[1].request.service_data.policy')
  for k in ['stable_samples','stable_interval_seconds','stable_duration_seconds','permit_ttl_seconds']:
   p.locator('[data-quality-field="'+k+'"]').fill(str(policy[k]))
  p.locator('[data-quality-field="enabled"]').set_checked(True)
  for k in ['ph','ec','level']:p.locator('[data-quality-field="'+k+'.confirmed"]').set_checked(True)
  p.locator('[data-quality-save]').click();p.wait_for_function('!card.qualityOperation')
  self.assertEqual(p.evaluate('calls.map(m=>m.service)'),['get_quality_v1','save_quality_policy_v1','get_quality_v1'])
  self.record_captured('C-after-first-save')
  self.assertEqual(p.evaluate('card.qualityData.policy_revision'),1)
  self.assertFalse(p.evaluate('card.qualityDirty'));self.assertIn('已保存並讀回',p.locator('[data-quality-message]').inner_text())
  self.assertTrue(p.evaluate('Object.values(card.qualityData.policy.sources).every(s=>s.report_contract_confirmed)'))
 def test_12_captured_telemetry_dirty_convergence(self):
  p=self.captured(saved=True);f=p.locator('[data-quality-field="stable_samples"]');f.fill('3');f.focus()
  p.evaluate('window.original=card.qualityInputs.get("stable_samples");latest={snapshot:grant.snapshot,reply:{success:true,result:{response:grant.dto}}};push(grant.snapshot)')
  try:p.wait_for_function('card.qualityData?.observation_revision===65')
  except Exception:self.assertEqual(p.evaluate('card.qualityData?.observation_revision'),65,'Native obs65 must converge without manual refresh')
  finally:self.record_captured('D-after-native65')
  self.assertIn('qualified',p.locator('[data-quality-truth]').inner_text());self.assertIn('completed',p.locator('[data-quality-completion]').inner_text());self.assertIn('許可 True',p.locator('[data-quality-permit]').inner_text())
  self.assertEqual(f.input_value(),'3');self.assertTrue(p.evaluate('card.shadowRoot.activeElement===original&&card.qualityDirty'))
  self.assertEqual(p.evaluate('calls.length'),2);self.assertTrue(p.evaluate('calls.every(m=>m.service==="get_quality_v1")'))
 def test_13_captured_handover_rejects_foreign_owners_and_epochs(self):
  for transition in ['card.remove();document.body.append(card)', 'card.hass={...card.hass,connection:{connected:true}}', 'card.hass={...card.hass,callWS:m=>transport(m)}', 'latest.snapshot.states[latest.snapshot.quality_id].attributes.epoch="c".repeat(32);push(latest.snapshot)', 'latest.snapshot.states[latest.snapshot.quality_id].attributes.policy_revision++;push(latest.snapshot)']:
   p=self.captured();policy=p.evaluate('wire[1].request.service_data.policy')
   for k in ['stable_samples','stable_interval_seconds','stable_duration_seconds','permit_ttl_seconds']:p.locator('[data-quality-field="'+k+'"]').fill(str(policy[k]))
   p.locator('[data-quality-field="enabled"]').set_checked(True)
   for k in ['ph','ec','level']:p.locator('[data-quality-field="'+k+'.confirmed"]').set_checked(True)
   p.evaluate('window.release=null;window.baseTransport=transport;transport=async m=>{const r=await baseTransport(m);if(m.service!=="save_quality_policy_v1")return r;return await new Promise(resolve=>{window.release=()=>resolve(r)})};push(latest.snapshot);void 0')
   p.locator('[data-quality-save]').click();p.wait_for_function('!!window.release');self.assertTrue(p.evaluate('card.qualityFlights.size===1'));p.evaluate(transition)
   self.assertTrue(p.evaluate('card.qualityFlights.size===1'));p.evaluate('release()');p.wait_for_function('card.qualityFlights.size===0')
   self.assertNotIn('已保存並讀回',p.locator('[data-quality-message]').inner_text(),transition);self.assertEqual(p.evaluate('calls.length'),2,transition)
 def test_14_delayed_event_get_coalesces_latest_without_unlock(self):
  self.open();p=self.p;p.locator('[data-quality-field="stable_samples"]').fill('17')
  p.evaluate('window.base=transport;window.once=true;transport=async m=>{if(once&&m.service==="get_quality_v1"){once=false;calls.push(m);const d=structuredClone(q);return await new Promise(resolve=>window.finish=()=>resolve({response:d}))}return base(m)};q.observation_revision++;publish();void 0')
  p.wait_for_function('!!window.finish');self.assertTrue(p.evaluate('card.qualityFlights.size===1'));p.evaluate('for(let i=0;i<5;i++){q.observation_revision++;publish()}');self.assertEqual(p.evaluate('calls.length'),2);self.assertTrue(p.locator('[data-quality-save]').is_disabled())
  p.evaluate('finish()');p.wait_for_function('card.qualityData?.observation_revision===q.observation_revision&&!card.qualityOperation');self.assertEqual(p.evaluate('calls.length'),3);self.assertEqual(p.locator('[data-quality-field="stable_samples"]').input_value(),'17');self.assertEqual(p.evaluate('writes'),[])
 def test_15_event_error_no_retry_private_or_cached_true(self):
  self.open();p=self.p;p.evaluate('transport=async m=>{calls.push(m);throw {message:"PRIVATE"}};q.observation_revision++;publish();void 0');p.wait_for_function('!card.qualityOperation');p.evaluate('for(let i=0;i<10;i++)publish()');p.wait_for_timeout(150)
  self.assertEqual(p.evaluate('calls.length'),2);self.assertNotIn('PRIVATE',p.locator('[data-quality-panel]').inner_text());self.assertNotIn('許可 True',p.locator('[data-quality-permit]').inner_text());self.assertEqual(p.evaluate('writes'),[])
 def test_16_dirty_native_policy_update_preserves_three_cas_conflict(self):
  self.open();p=self.p;p.locator('[data-quality-field="stable_samples"]').fill('19');p.evaluate('q.policy.stable_samples=23;q.policy_revision++;q.observation_revision++;publish()');p.wait_for_function('card.qualityData?.policy_revision===1&&!card.qualityOperation')
  self.assertEqual(p.evaluate('card.qualityBaseline.policy_revision'),0);self.assertEqual(p.locator('[data-quality-field="stable_samples"]').input_value(),'19');p.locator('[data-quality-save]').click();p.wait_for_function('!card.qualityOperation');self.assertIn('衝突',p.locator('[data-quality-message]').inner_text());self.assertEqual(p.evaluate('writes'),[])
 def test_17_captured_revoke_event_converges_false(self):
  p=self.captured(saved=True);p.evaluate('latest={snapshot:grant.snapshot,reply:{success:true,result:{response:grant.dto}}};push(grant.snapshot)');p.wait_for_function('card.qualityData?.observation_revision===65')
  self.assertIn('許可 True',p.locator('[data-quality-permit]').inner_text())
  p.evaluate('const d=structuredClone(grant.dto);d.observation_revision++;d.permit.granted=false;d.permit.reasons=["expired"];const s=structuredClone(grant.snapshot);s.states[s.quality_id].attributes={...s.states[s.quality_id].attributes,...d};latest={snapshot:s,reply:{success:true,result:{response:d}}};push(s)');p.wait_for_function('card.qualityData?.observation_revision===66');self.assertIn('不許可 False',p.locator('[data-quality-permit]').inner_text());self.assertTrue(p.evaluate('calls.every(m=>m.service==="get_quality_v1")'))
 def q1_granted(self):
  p=self.captured(saved=True)
  p.evaluate("latest={snapshot:grant.snapshot,reply:{success:true,result:{response:grant.dto}}};push(grant.snapshot);q=structuredClone(grant.dto)")
  p.wait_for_function('!card.qualityOperation&&card.qualityData?.permit.granted&&card.qualityData?.observation_revision===65')
  self.assertIn('許可 True',p.locator('[data-quality-permit]').inner_text());return p
 def q1_hold(self):
  # Stable callWS and connection; hold the exact already-produced captured reply.
  p=self.captured(saved=True)
  p.evaluate("window.baseQ1=transport;window.holdQ1=false;window.heldQ1=null;transport=async m=>{const r=await baseQ1(m);if(!holdQ1)return r;heldQ1=structuredClone(r);return await new Promise(resolve=>window.releaseQ1=()=>resolve(r))};push(latest.snapshot);latest={snapshot:grant.snapshot,reply:{success:true,result:{response:grant.dto}}};push(grant.snapshot);void 0")
  p.locator('[data-quality-refresh]').click();p.wait_for_function('!card.qualityOperation&&card.qualityData?.permit.granted');self.assertIn('許可 True',p.locator('[data-quality-permit]').inner_text())
  p.evaluate('holdQ1=true;window.wsQ1=card.hass.callWS;window.connQ1=card.hass.connection;window.userQ1=card.hass.user')
  p.locator('[data-quality-refresh]').click();p.wait_for_function('!!window.releaseQ1');p.evaluate('userQ1=card.hass.user')
  self.assertTrue(p.evaluate('card.hass.callWS===wsQ1&&card.hass.connection===connQ1&&heldQ1.response.permit.granted'))
  return p
 def q1_purged(self):
  p=self.p
  self.assertIsNone(p.evaluate('card.qualityData'))
  self.assertIsNone(p.evaluate('card.qualityBaseline'))
  self.assertFalse(p.evaluate('!!card.qualitySyncBase'))
  self.assertFalse(p.evaluate('card.qualityDirty'))
  self.assertTrue(p.locator('[data-quality-save]').is_disabled())
  self.assertTrue(p.evaluate('[...card.qualityInputs.values()].every(i=>i.type==="checkbox"?!i.checked:i.value==="")'))
 def test_18_q1_same_object_role_demotion_purges_loaded_grant(self):
  p=self.q1_granted();p.locator('[data-quality-field="stable_samples"]').fill('21')
  p.evaluate('window.userQ1=card.hass.user;window.wsQ1=card.hass.callWS;window.connQ1=card.hass.connection;card.hass.user.is_admin=false;card.hass={...card.hass}')
  self.record_captured('Q1-loaded-role-demotion')
  self.assertNotIn('許可 True',p.locator('[data-quality-permit]').inner_text(),'Observed same-principal admin demotion must not retain an authorized joined True cache')
  self.assertTrue(p.evaluate('card.hass.user===userQ1&&card.hass.callWS===wsQ1&&card.hass.connection===connQ1'))
  self.q1_purged();p.evaluate('void card.qualityRequest(true)');self.assertTrue(p.evaluate('calls.every(m=>m.service==="get_quality_v1")'))
 def test_19_q1_same_transport_exact_late_reply_demotion(self):
  p=self.q1_hold();before=p.evaluate('calls.length')
  p.evaluate('card.hass.user.is_admin=false;card.hass={...card.hass}')
  self.q1_purged();self.assertTrue(p.evaluate('card.qualityFlights.size===1&&card.hass.callWS===wsQ1&&card.hass.connection===connQ1&&card.hass.user===userQ1'))
  p.evaluate('void card.qualityRequest(false);void card.qualityRequest(true)');self.assertEqual(p.evaluate('calls.length'),before)
  p.evaluate('releaseQ1()');p.wait_for_function('card.qualityFlights.size===0')
  self.record_captured('Q1-exact-late-reply-role-demotion');self.q1_purged()
  self.assertNotIn('許可 True',p.locator('[data-quality-permit]').inner_text());p.wait_for_timeout(80);self.assertEqual(p.evaluate('calls.length'),before)
 def test_20_q1_same_object_admin_principal_switch_late_reply(self):
  p=self.q1_hold();before=p.evaluate('calls.length');p.locator('[data-quality-panel]').evaluate('e=>e.open=true')
  p.evaluate('window.oldIdQ1=card.hass.user.id;card.hass.user.id="q1-other-admin";card.hass={...card.hass}')
  self.q1_purged();self.assertTrue(p.evaluate('card.hass.user===userQ1&&card.hass.user.is_admin&&card.hass.user.id!==oldIdQ1&&card.hass.callWS===wsQ1&&card.hass.connection===connQ1'))
  p.evaluate('void card.qualityRequest(false)');self.assertEqual(p.evaluate('calls.length'),before);self.assertTrue(p.evaluate('card.qualityFlights.size===1'))
  p.evaluate('releaseQ1()');p.wait_for_function('card.qualityFlights.size===0')
  self.record_captured('Q1-exact-late-reply-principal-switch');self.q1_purged();self.assertEqual(p.evaluate('calls.length'),before)
  self.assertNotIn('許可 True',p.locator('[data-quality-permit]').inner_text())
 def test_21_q1_regrant_requires_fresh_get_save_and_readonly(self):
  p=self.q1_hold();before=p.evaluate('calls.length')
  p.evaluate('card.hass.user.is_admin=false;card.hass={...card.hass};card.hass.user.is_admin=true;card.hass={...card.hass}')
  self.q1_purged();self.assertTrue(p.evaluate('card.qualityFlights.size===1'));p.evaluate('void card.qualityRequest(false)');self.assertEqual(p.evaluate('calls.length'),before)
  p.evaluate('holdQ1=false;releaseQ1()');p.wait_for_function('card.qualityFlights.size===0');self.q1_purged()
  self.assertNotIn('許可 True',p.locator('[data-quality-permit]').inner_text());self.assertEqual(p.evaluate('calls.length'),before)
  self.assertTrue(p.locator('[data-quality-refresh]').is_enabled(),'Settled obsolete owner must release only its own transport wait');p.locator('[data-quality-refresh]').click();p.wait_for_function('!!card.qualityData&&!card.qualityOperation');self.assertIn('許可 True',p.locator('[data-quality-permit]').inner_text())
  self.assertEqual(p.evaluate('calls.length'),before+1)
  # Ordinary standalone native readonly remains legitimate even without admin.
  p.evaluate('card.hass.user.is_admin=false;card.hass={...card.hass};card.setConfig({quality_entity:grant.snapshot.quality_id})')
  self.assertIn('許可 True',p.locator('[data-quality-permit]').inner_text());self.assertTrue(p.locator('[data-quality-save]').is_hidden())
  # Fresh synthetic service boundary permits normal read/Save after regrant.
  p.evaluate('card.remove()');states=json.loads(subprocess.check_output([os.environ.get('NODE','node'),'-e',"console.log(JSON.stringify(require('./tests/p3c_fixture.cjs')()))"],cwd=ROOT));p.evaluate(FIXTURE,states);self.open()
  for change in ['card.hass.user.is_active=false','card.hass.user=null']:
   p.evaluate(change+';card.hass={...card.hass}');self.q1_purged();n=p.evaluate('calls.length');p.evaluate('void card.qualityRequest(true);void card.qualityRequest(false)');self.assertEqual(p.evaluate('calls.length'),n)
   p.evaluate('card.hass.user={id:"quality-test-admin",is_admin:true,is_active:true};card.hass={...card.hass}')
   self.q1_purged();p.locator('[data-quality-refresh]').click();p.wait_for_function('!!card.qualityData&&!card.qualityOperation')
  p.locator('[data-quality-field="stable_samples"]').fill('24');p.locator('[data-quality-save]').click();p.wait_for_function('!card.qualityOperation')
  self.assertEqual(p.evaluate('q.policy.stable_samples'),24);self.assertEqual(p.evaluate('writes'),['save_quality_policy_v1']);self.assertEqual(p.evaluate('card.qualityFlights.size'),0)
  self.assertIn('已保存並讀回',p.locator('[data-quality-message]').inner_text());self.record_captured('Q1-regrant-fresh-get-save')
if __name__=='__main__': unittest.main(verbosity=2)
