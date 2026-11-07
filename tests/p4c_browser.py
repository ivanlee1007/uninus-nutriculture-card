"""Shipped Chromium UI / fake private WS; NOT native Core/Store integration."""
import json, os, unittest
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
FIXTURE="""() => {
window.calls=[];window.r={schema_version:1,config_entry_id:'entry-a',epoch:'a'.repeat(32),observation_revision:0,support:'supported',current_run:null,last_result:null,latest_event:null};
window.n={schema_version:1,config_entry_id:'entry-a',epoch:'a'.repeat(32),revision:0,policy:{enabled:false,provider:null,target_binding:null,events:[],cooldown_seconds:300},availability:'disabled',error:null,catalog:[{entity_id:'notify.test_sink',label:'Isolated sink <safe>',available:true}],deliveries:[]};
window.transport=async m=>{calls.push(structuredClone(m));if(m.type.endsWith('/save')){n.revision++;const p=m.policy;n.policy={enabled:p.enabled,provider:p.provider,target_binding:p.target_entity_id?{entity_id:p.target_entity_id,registry_entry_id:'registry',platform:'fixture',unique_id:'sink',config_entry_id:null}:null,events:p.events,cooldown_seconds:p.cooldown_seconds};n.availability=p.enabled?'available':'disabled';}if(m.type.endsWith('/ack'))n.deliveries.find(d=>d.event_id===m.event_id).acknowledged=true;return structuredClone(n)};
window.connection=new EventTarget();connection.connected=true;
window.card=document.createElement('uninus-nutriculture-card');document.body.append(card);
window.publish=()=>{card.hass={user:window.user||(window.user={id:'human-admin',is_admin:true}),states:{'sensor.result_selected':{state:r.support==='unsupported'?'unsupported':(r.current_run||r.last_result)?.state||'idle',attributes:structuredClone(r)}},services:{uninus_nutriculture:{get_result_v1:{}}},connection,callWS:window.ws||(window.ws=m=>transport(m)),callService:()=>{throw Error('NO SERVICE IO')}}};
window.editor=document.createElement('uninus-nutriculture-card-editor');document.body.append(editor);editor.setConfig({});editor.addEventListener('config-changed',e=>window.changed=e.detail.config);publish();editor.hass=card.hass;
}"""
class P4cBrowserTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.pw=sync_playwright().start();cls.browser=cls.pw.chromium.launch(headless=True,executable_path=os.environ['CHROMIUM_EXECUTABLE']);print('BROWSER_VERSION='+cls.browser.version)
 @classmethod
 def tearDownClass(cls):cls.browser.close();cls.pw.stop()
 def setUp(self):
  self.p=self.browser.new_page(viewport={'width':390,'height':1000});self.errors=[];self.p.on('pageerror',lambda e:self.errors.append(str(e)));self.p.set_default_timeout(1500);self.p.set_content('<meta charset="utf-8"><body>');self.p.add_script_tag(path=str(ROOT/'uninus-nutriculture-card.js'));self.p.evaluate(FIXTURE)
 def tearDown(self):self.p.close();self.assertEqual(self.errors,[])
 def select(self):
  self.assertEqual(self.p.locator('[data-result-entity]').count(),1,'Editor must expose explicit result entity selection')
  self.p.locator('[data-result-entity]').evaluate("e=>e.dispatchEvent(new CustomEvent('value-changed',{detail:{value:'sensor.result_selected'}}))")
  self.p.evaluate('card.setConfig(changed)')
 def open(self):
  self.select();self.p.locator('[data-notification-panel] summary').click();self.p.wait_for_function('!!card.notificationData')
 def test_01_editor_private_save_readback_result(self):
  self.open();p=self.p;p.locator('[data-result-panel] summary').click()
  self.assertEqual(p.evaluate('changed.result_entity'),'sensor.result_selected')
  p.locator('[data-notification-provider]').select_option('notify_entity');p.locator('[data-notification-target]').select_option('notify.test_sink');p.locator('[data-notification-enabled]').check();p.locator('[data-notification-event="start"]').check();p.locator('[data-notification-event="completed"]').check();p.locator('[data-notification-cooldown]').fill('600');p.locator('[data-notification-save]').click();p.wait_for_function('!card.notificationOperation')
  expected={'type':'uninus_nutriculture/notification_v1/save','config_entry_id':'entry-a','expected_epoch':'a'*32,'expected_revision':0,'policy':{'enabled':True,'provider':'notify_entity','target_entity_id':'notify.test_sink','events':['start','completed'],'cooldown_seconds':600}}
  self.assertEqual(p.evaluate('calls[1]'),expected);self.assertEqual(p.evaluate('calls.map(m=>m.type.split("/").at(-1))'),['get','save','get']);self.assertIn('已保存並讀回',p.locator('[data-notification-message]').inner_text());self.assertIn('idle',p.locator('[data-result-status]').inner_text())
  out=os.environ.get('BROWSER_EVIDENCE_DIR')
  if out:
   d=Path(out);d.mkdir(parents=True,exist_ok=True);p.screenshot(path=str(d/'primary.png'),full_page=True);(d/'primary.json').write_text(json.dumps(p.evaluate('({calls,dom:card.shadowRoot.innerHTML})'),ensure_ascii=False,indent=2),encoding='utf-8')
 def test_02_ack_cache_get_explicit_reconcile_cancel(self):
  self.open();p=self.p;p.evaluate("n.deliveries=[{event_id:n.epoch+':1',kind:'accepted',status:'handoff_returned',code:null,acknowledged:false,updated_at:'2026-11-06T01:02:03.123456+00:00'}]")
  p.locator('[data-notification-get]').click();p.wait_for_function('!card.notificationOperation');self.assertIn('非送達確認',p.locator('[data-notification-ledger]').inner_text());p.locator('[data-notification-ack]').click();p.wait_for_function('!card.notificationOperation');self.assertTrue(p.evaluate('n.deliveries[0].acknowledged'));self.assertEqual(p.evaluate('calls.at(-1)'),{'type':'uninus_nutriculture/notification_v1/ack','config_entry_id':'entry-a','expected_epoch':'a'*32,'event_id':'a'*32+':1'})
  p.locator('[data-notification-cooldown]').fill('800');p.locator('[data-notification-cancel]').click();self.assertEqual(p.locator('[data-notification-cooldown]').input_value(),'300');self.assertEqual(p.evaluate('calls.length'),3)
  p.locator('[data-notification-reconcile]').click();p.wait_for_function('!card.notificationOperation');self.assertEqual(p.evaluate('calls.at(-1)'),{'type':'uninus_nutriculture/notification_v1/reconcile','config_entry_id':'entry-a','expected_epoch':'a'*32});self.assertTrue(p.evaluate('calls.every(m=>m.type.startsWith("uninus_nutriculture/notification_v1/"))'))
 def test_03_save_unknown_requires_explicit_reconcile(self):
  self.open();p=self.p;p.evaluate("window.originalTransport=transport;transport=async m=>{if(m.type.endsWith('/save')){calls.push(m);throw {code:'indeterminate',message:'SECRET'}}return originalTransport(m)};void 0")
  p.locator('[data-notification-cooldown]').fill('601');p.locator('[data-notification-save]').click();p.wait_for_function('!card.notificationOperation');self.assertIn('結果未知',p.locator('[data-notification-message]').inner_text());self.assertNotIn('SECRET',p.locator('[data-notification-message]').inner_text());self.assertTrue(p.locator('[data-notification-save]').is_disabled(),'Unknown write outcome must block further saves until explicit recovery');self.assertEqual(p.evaluate('calls.length'),2)
  p.locator('[data-notification-get]').click();p.wait_for_function('!card.notificationOperation');self.assertTrue(p.locator('[data-notification-save]').is_disabled(),'Cached GET cannot resolve a transport-indeterminate write')
  p.locator('[data-notification-reconcile]').click();p.wait_for_function('!card.notificationOperation');self.assertTrue(p.locator('[data-notification-save]').is_enabled())
 def test_04_no_authority_no_management_and_readonly_result(self):
  self.select();p=self.p
  for change in ['user.is_admin=false','user.is_admin=1','user.is_active=false','user.system_generated=true','user.id={bad:1}','user.id=""','delete card.hass.services.uninus_nutriculture.get_result_v1']:
   p.evaluate('user={id:"human-admin",is_admin:true};publish();'+change+';card.hass=card.hass');p.evaluate('card.notificationPanel.open=true;void card.notificationRequest("get")');self.assertEqual(p.evaluate('calls'),[],change);self.assertIn('idle',p.locator('[data-result-status]').text_content())
 def test_05_owner_transition_loaded_cache_and_late_all_routes(self):
  self.open();p=self.p
  for action in ['get','save','ack','reconcile']:
   for change in ['user.is_admin=false','user.id="other-human"','user.is_active=false','user.id={bad:1}','r.config_entry_id="entry-b";publish()','r.epoch="b".repeat(32);publish()','window.ws=m=>transport(m);publish()','connection.connected=false;connection.dispatchEvent(new Event("disconnected"))','card.remove();document.body.append(card)']:
    p.evaluate("user={id:'human-admin',is_admin:true};r.config_entry_id='entry-a';r.epoch='a'.repeat(32);connection.connected=true;window.ws=undefined;transport=originalTransportForRace||transport;publish()" if False else "user={id:'human-admin',is_admin:true};r.config_entry_id='entry-a';r.epoch='a'.repeat(32);connection.connected=true;connection.dispatchEvent(new Event('ready'));publish()")
    p.evaluate("n.deliveries=[{event_id:n.epoch+':1',kind:'completed',status:'queued',code:null,acknowledged:false,updated_at:'2026-11-06T01:02:03+00:00'}];void card.notificationRequest('get')");p.wait_for_function('!card.notificationOperation')
    p.evaluate("window.beforeTransport=transport;transport=m=>new Promise(resolve=>window.finish=resolve);void 0");p.evaluate('(action)=>{void card.notificationRequest(action,n.epoch+\":1\")}',action)
    p.wait_for_function('!!window.finish');p.evaluate(change);p.evaluate('finish(structuredClone(n));transport=beforeTransport;delete window.finish;void 0');p.wait_for_timeout(20)
    self.assertIsNone(p.evaluate('card.notificationData'),action+' '+change);self.assertNotIn('notify.test_sink',p.evaluate('card.notificationPanel.textContent'),action+' '+change);self.assertIsNone(p.evaluate('card.notificationBaseline'))
 def test_06_result_terminal_and_strict_structural_matrix(self):
  self.select();p=self.p;p.locator('[data-result-panel] summary').click()
  p.evaluate("window.run={run_id:'c'.repeat(32),epoch:r.epoch,settings_revision:0,flow_plan_revision:0,state:'completed',closure:'confirmed',reason:'none',accepted_at:'2026-11-06T01:00:00+00:00',started_at:null,finished_at:'2026-11-06T01:02:03.123456+00:00',transition_at:'2026-11-06T01:02:03.123456+00:00',stages:Object.fromEntries(['refill','nutrient','acid','mix'].map(k=>[k,{phase:null,result:'completed',started_at:null,settled_at:null,waiting_reason:null}]))};r.last_result=run;publish()")
  self.assertIn('completed',p.locator('[data-result-status]').inner_text());self.assertEqual(p.evaluate('Object.keys(card.resultNative().last_result.stages).length'),4)
  changes=['d.extra=1','d.epoch="BAD"','d.observation_revision=true','d.observation_revision=1.5','d.last_result.run_id="bad"','d.last_result.epoch="b".repeat(32)','d.last_result.reason="SECRET"','d.last_result.state="future"','d.last_result.closure="pending"','d.last_result.finished_at=null','d.last_result.accepted_at="2026-02-30T00:00:00+00:00"','d.last_result.transition_at="2026-11-06T24:00:00+00:00"','d.last_result.settings_revision=true','d.last_result.stages.refill.extra=1','d.last_result.stages.acid.phase="future"','d.current_run=d.last_result','d.support="unsupported"']
  for change in changes:self.assertFalse(p.evaluate('change=>{const d=structuredClone(r);eval(change);return card.resultDTO(d)}',change),change)
  self.assertEqual(p.evaluate('calls'),[])
 def test_07_private_strict_matrix_safe_text_and_input(self):
  self.open();p=self.p
  changes=['d.extra=1','d.revision=true','d.epoch="x"','d.policy.enabled=1','d.policy.extra=1','d.policy.events=["start","start"]','d.policy.events=["unknown"]','d.policy.cooldown_seconds=59','d.policy.cooldown_seconds=86401','d.policy.cooldown_seconds=true','d.policy.provider="script"','d.policy.provider="notify_entity"','d.policy.enabled=true','d.catalog[0].entity_id="switch.fake"','d.catalog[0].available=1','d.catalog[0].label="x".repeat(81)','d.catalog[0].label="a\\u202e"','d.catalog[0].label="\\ud800"','d.catalog.push(d.catalog[0])','d.availability="future"','d.error="SECRET"']
  for change in changes:self.assertFalse(p.evaluate('change=>{const d=structuredClone(n);eval(change);return card.notificationDTO(d,n.config_entry_id,n.epoch)}',change),change)
  self.assertIn('<safe>',p.locator('[data-notification-target]').text_content());self.assertEqual(p.locator('[data-notification-panel] safe').count(),0)
  for value in ['59','86401','60.5','']:
   p.locator('[data-notification-cooldown]').fill(value);self.assertTrue(p.locator('[data-notification-save]').is_disabled(),value)
 def test_08_dirty_focus_get_conflict_and_timeout_wording(self):
  self.open();p=self.p;f=p.locator('[data-notification-cooldown]');f.fill('');f.focus();p.keyboard.type('60');p.evaluate('window.focused=card.notificationInputs.cooldown;publish()');p.keyboard.type('0');self.assertEqual(f.input_value(),'600');self.assertTrue(p.evaluate('card.shadowRoot.activeElement===focused'))
  p.evaluate("n.revision=4;n.policy.cooldown_seconds=900;void card.notificationRequest('get')");p.wait_for_function('!card.notificationOperation');self.assertEqual(f.input_value(),'600');self.assertEqual(p.evaluate('card.notificationBaseline.revision'),0)
  p.evaluate("n.deliveries=[{event_id:n.epoch+':2',kind:'stopping',status:'timed_out',code:'provider_timeout',acknowledged:false,updated_at:'2026-11-06T01:02:03+00:00'}];void card.notificationRequest('get')");p.wait_for_function('!card.notificationOperation');self.assertIn('結果未知',p.locator('[data-notification-ledger]').inner_text())
 def test_09_denial_latch_and_transport_lock(self):
  self.open();p=self.p;p.evaluate("transport=async m=>{calls.push(m);throw {code:'unauthorized',message:'SECRET'}};void card.notificationRequest('get')");p.wait_for_function('!card.notificationOperation');before=p.evaluate('calls.length');p.evaluate("void card.notificationRequest('get')");self.assertEqual(p.evaluate('calls.length'),before,'Denied owner must not retry private reads')
 def test_10_unresolved_flight_scope_lock_and_new_owner(self):
  self.open();p=self.p;p.evaluate("window.original=transport;transport=m=>{calls.push(m);return new Promise(resolve=>window.finishOld=resolve)};void card.notificationRequest('save')");p.wait_for_function('!!window.finishOld');p.evaluate('window.ws=m=>transport(m);publish()');self.assertTrue(p.locator('[data-notification-get]').is_disabled());before=p.evaluate('calls.length');p.evaluate("void card.notificationRequest('get')");self.assertEqual(p.evaluate('calls.length'),before)
  p.evaluate("r.config_entry_id='entry-b';n.config_entry_id='entry-b';publish();transport=m=>new Promise(resolve=>window.finishNew=resolve);void card.notificationRequest('get')");p.wait_for_function('!!window.finishNew');p.evaluate('window.newOp=card.notificationOperation;const old=structuredClone(n);old.config_entry_id="entry-a";finishOld(old)');self.assertTrue(p.evaluate('card.notificationOperation===newOp'));p.evaluate('finishNew(structuredClone(n));transport=original;void 0');p.wait_for_function('!card.notificationOperation');self.assertEqual(p.evaluate('card.notificationData.config_entry_id'),'entry-b')
 def test_11_readback_mismatch_not_saved_or_retried(self):
  self.open();p=self.p;p.evaluate("window.original=transport;transport=async m=>{const d=await original(m);if(m.type.endsWith('/get'))d.policy.cooldown_seconds=777;return d};void 0");p.locator('[data-notification-cooldown]').fill('601');p.locator('[data-notification-save]').click();p.wait_for_function('!card.notificationOperation');self.assertNotIn('已保存',p.locator('[data-notification-message]').inner_text());self.assertTrue(p.locator('[data-notification-save]').is_disabled());self.assertEqual(p.locator('[data-notification-cooldown]').input_value(),'601');self.assertEqual(p.evaluate('calls.length'),3)
 def test_12_event_crossfields_and_private_ledger_rejection(self):
  self.select();p=self.p;p.evaluate("r.latest_event={schema_version:1,config_entry_id:r.config_entry_id,epoch:r.epoch,observation_revision:0,sequence:1,event_id:r.epoch+':1',kind:'ph_low',reason:'ph_low',occurred_at:'2026-11-06T00:00:00+00:00',run:null};publish()")
  self.assertTrue(p.evaluate('card.resultDTO(r)'))
  for change in ['d.latest_event.config_entry_id="other"','d.latest_event.epoch="b".repeat(32)','d.latest_event.event_id=d.epoch+":2"','d.latest_event.sequence=true','d.latest_event.kind="accepted"','d.latest_event.observation_revision=1','d.latest_event.occurred_at="2026-11-06T00:00:00Z"']:
   self.assertFalse(p.evaluate('change=>{const d=structuredClone(r);eval(change);return card.resultDTO(d)}',change),change)
  p.evaluate("n.deliveries=[{event_id:n.epoch+':1',kind:'accepted',status:'queued',code:null,acknowledged:false,updated_at:'2026-11-06T00:00:00+00:00'}]")
  for change in ['d.deliveries[0].event_id="b".repeat(32)+":1"','d.deliveries[0].event_id=d.epoch+":9999999999999999"','d.deliveries[0].acknowledged=1','d.deliveries[0].code="SECRET"','d.deliveries[0].updated_at="2026-02-30T00:00:00+00:00"','d.deliveries[0].extra=1']:
   self.assertFalse(p.evaluate('change=>{const d=structuredClone(n);eval(change);return card.notificationDTO(d,n.config_entry_id,n.epoch)}',change),change)
 def test_13_unsupported_invalid_public_epoch_and_reconnect_purge(self):
  self.open();p=self.p
  for change in ['r.support="unsupported"','r.extra=1']:
   p.evaluate('window.savedResult=structuredClone(r);'+change+';publish()');self.assertIsNone(p.evaluate('card.notificationData'));self.assertTrue(p.locator('[data-notification-save]').is_hidden());before=p.evaluate('calls.length');p.evaluate("void card.notificationRequest('get')");self.assertEqual(p.evaluate('calls.length'),before);p.evaluate("r=savedResult;publish();void card.notificationRequest('get')");p.wait_for_function('!card.notificationOperation')
  p.locator('[data-notification-cooldown]').fill('501');p.evaluate("connection.connected=false;connection.dispatchEvent(new Event('disconnected'));connection.connected=true;connection.dispatchEvent(new Event('ready'))");self.assertIsNone(p.evaluate('card.notificationData'));self.assertEqual(p.locator('[data-notification-cooldown]').input_value(),'');p.wait_for_timeout(40);self.assertFalse(p.evaluate('card.notificationDirty'))
 def test_14_persistent_provider_exact_policy_no_binding(self):
  self.open();p=self.p;p.locator('[data-notification-provider]').select_option('persistent_notification');p.locator('[data-notification-enabled]').check();p.locator('[data-notification-event="failed"]').check();p.locator('[data-notification-save]').click();p.wait_for_function('!card.notificationOperation');self.assertEqual(p.evaluate('calls[1].policy'),{'enabled':True,'provider':'persistent_notification','target_entity_id':None,'events':['failed'],'cooldown_seconds':300});self.assertEqual(p.evaluate('calls.length'),3)
 def test_15_ack_requires_confirmed_private_ledger(self):
  self.open();p=self.p;p.evaluate("n.deliveries=[{event_id:n.epoch+':1',kind:'completed',status:'queued',code:null,acknowledged:false,updated_at:'2026-11-06T00:00:00+00:00'}];void card.notificationRequest('get')");p.wait_for_function('!card.notificationOperation');p.evaluate("window.original=transport;transport=async m=>{if(m.type.endsWith('/ack')){calls.push(m);return structuredClone(n)}return original(m)};void 0");p.locator('[data-notification-ack]').click();p.wait_for_function('!card.notificationOperation');self.assertNotIn('已標為已讀',p.locator('[data-notification-message]').inner_text(),'ACK success requires the requested ledger record acknowledged in readback')
 def test_16_mobile_controls_geometry_and_default_no_io(self):
  self.open();p=self.p
  for width in [320,768,1200]:
   p.set_viewport_size({'width':width,'height':1000});rects=p.locator('[data-notification-panel] input:visible,[data-notification-panel] select:visible,[data-notification-panel] button:visible').evaluate_all('els=>els.map(e=>{const r=e.getBoundingClientRect();return [r.left,r.right]})');self.assertTrue(all(a>=0 and b<=width for a,b in rects),str(width)+str(rects))
  p.wait_for_timeout(80);self.assertEqual(p.evaluate('calls.length'),1)
if __name__=='__main__':unittest.main(verbosity=2)
