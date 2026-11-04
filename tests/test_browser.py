import json
import os
from pathlib import Path
import unittest
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]

FIXTURE = """() => {
 window.calls = [];
 window.fixture = (entity = 'sensor.status') => {
   const keys = ['level_low','level_high','ph_low','ph_high','ec_low','ec_high','refill_timeout','ec_timeout','ph_timeout','mix_duration'];
   const values = [2.25,2.4,5.4,5.8,.8,.9,190,90,190,10];
   const mapping = Object.fromEntries(keys.map(k => [k, 'number.tank_' + k]));
   const states = Object.fromEntries(keys.map((k,i) => [mapping[k], {state:String(values[i]), attributes:{min:0,max:i<6?14:240,step:i<6?.01:1,unit_of_measurement:i<2?'m':i<4?'':i<6?'mS/cm':'min'}}]));
   states[entity] = {state:'within_range',attributes:{schema_version:1,mode:'shadow',ready_for_irrigation:false,source_entities:{ph:'sensor.ph',ec:'sensor.ec',level:'sensor.level'},parameter_entities:mapping,parameters:Object.fromEntries(keys.map((k,i)=>[k,values[i]])),reasons:[]}};
   states['sensor.ph']={state:'5.6',attributes:{unit_of_measurement:'pH'}};
   states['sensor.ec']={state:'0.85',attributes:{unit_of_measurement:'mS/cm'}};
   states['sensor.level']={state:'2.3',attributes:{unit_of_measurement:'m'}};
   return {states,callService:(...args)=>{calls.push(args);return Promise.resolve();}};
 };
 window.card = document.createElement('uninus-nutriculture-card');
 document.body.append(card);
 card.setConfig({type:'custom:uninus-nutriculture-card',entity:'sensor.status'});
 card.hass = fixture();
} """

class BrowserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pw = sync_playwright().start()
        options = {'headless': True}
        if os.environ.get('CHROMIUM_EXECUTABLE'):
            options['executable_path'] = os.environ['CHROMIUM_EXECUTABLE']
        cls.browser = cls.pw.chromium.launch(**options)
        print('BROWSER_VERSION=' + cls.browser.version, flush=True)

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.pw.stop()

    def setUp(self):
        self.page = self.browser.new_page(viewport={'width':768,'height':1000})
        self.errors = []
        self.page.on('pageerror', lambda error:self.errors.append(str(error)))
        self.page.set_content('<!doctype html><html lang="zh-Hant"><meta charset="utf-8"><body style="margin:0;padding:8px;box-sizing:border-box"></body></html>')
        self.page.add_script_tag(path=str(ROOT/'uninus-nutriculture-card.js'))
        self.page.evaluate(FIXTURE)

    def tearDown(self):
        self.page.close()
        self.assertEqual(self.errors, [])

    def flow_fixture(self):
        import subprocess
        states=json.loads(subprocess.check_output(['node','-e',"console.log(JSON.stringify(require('./tests/p3c_fixture.cjs')()))"],cwd=ROOT))
        self.page.evaluate("states=>{card.hass={states,callService:(...args)=>{calls.push(args);return Promise.resolve()},callWS:m=>{calls.push([m.domain,m.service,m.service_data]);return Promise.resolve({response:{applied:true,settings_revision:m.service_data.expected_revision+1,flow_plan_revision:m.service_data.expected_flow_plan_revision+1,flow_plan:m.service_data.flow_plan,allowed_weekdays:m.service_data.allowed_weekdays}})}}}",states)

    def test_43_v5_visible_editor_atomic_weekdays_order(self):
        self.flow_fixture()
        p=self.page
        self.assertEqual(p.locator('[data-flow-row]').count(),4)
        p.locator('[data-flow-row="mix"] [data-move="up"]').click()
        self.assertEqual(p.locator('[data-flow-row]').evaluate_all('(els)=>els.map(e=>e.dataset.flowRow)'),['refill','nutrient','mix','acid'])
        p.locator('[data-flow-row="mix"] [data-flow-day="sun"]').check()
        p.locator('[data-plan-apply]').click()
        call=p.evaluate('calls.at(-1)')
        self.assertEqual(call[:2],['uninus_nutriculture','apply_flow_plan_v5'])
        self.assertEqual(set(call[2]),{'config_entry_id','expected_revision','expected_flow_plan_revision','flow_plan','allowed_weekdays'})
        self.assertEqual(call[2]['allowed_weekdays']['mix'],['sun'])
        self.assertEqual(call[2]['flow_plan']['rows'][2]['stage'],'mix')
        self.assertNotIn('已套用',p.locator('[data-plan-message]').inner_text())

    def test_44_v5_preview_draft_seven_days_stale_cancel(self):
        self.flow_fixture()
        p=self.page
        p.evaluate("""()=>{window.previewPending=[];card.hass.callWS=m=>{calls.push(m);return new Promise(resolve=>previewPending.push({m,resolve}))};window.finishPreview=()=>{for(const {m,resolve} of previewPending.splice(0)){const d=m.service_data;resolve({response:{settings_revision:d.expected_revision,flow_plan_revision:d.expected_flow_plan_revision,weekday:d.weekday,rows:d.flow_plan.rows.map(r=>({stage:r.stage,eligibility:r.stage==='mix'?'blocked_safety':'eligible',earliest_offset_seconds:r.stage==='refill'?0:null,uncertainties:['sensor_duration_unknown']})),warnings:['admission_day_only']}})}}}""")
        p.locator('[data-flow-row="mix"] [data-flow-day="sun"]').check()
        p.locator('[data-plan-preview]').click()
        self.assertEqual(p.evaluate('calls.length'),7)
        self.assertEqual(p.evaluate('calls[0].service_data.allowed_weekdays.mix'),['sun'])
        self.assertEqual(p.evaluate('Object.keys(calls[0].service_data).length'),6)
        p.locator('[data-plan-cancel]').click()
        p.evaluate('finishPreview()')
        self.assertEqual(p.locator('[data-preview-day]').count(),0)
        p.locator('[data-plan-preview]').click()
        p.evaluate('finishPreview()')
        self.assertEqual(p.locator('[data-preview-day]').count(),7)
        self.assertIn('blocked_safety',p.locator('[data-preview-results]').inner_text())

    def test_45_v5_invalid_reorder_conflict_and_pending_remount(self):
        self.flow_fixture()
        p=self.page
        p.locator('[data-flow-row="refill"] [data-move="down"]').click()
        self.assertTrue(p.locator('[data-plan-apply]').is_disabled())
        self.assertIn('首列',p.locator('[data-plan-message]').inner_text())
        p.locator('[data-plan-cancel]').click()
        p.locator('[data-flow-row="acid"] [data-flow-field="delay_seconds"]').fill('2')
        p.evaluate("()=>{card.hass.callWS=m=>{calls.push(m);return new Promise((resolve,reject)=>{window.planResolve=resolve;window.planReject=reject})}}")
        p.locator('[data-plan-apply]').click()
        p.evaluate("()=>{card.applyPlan();card.remove();document.body.append(card);card.applyPlan()}")
        self.assertEqual(p.evaluate('calls.length'),1)
        p.locator('[data-plan-cancel]').click()
        p.locator('[data-flow-row="acid"] [data-flow-field="delay_seconds"]').fill('4')
        p.evaluate("planReject(new Error('old conflict'))")
        self.assertEqual(p.locator('[data-flow-row="acid"] [data-flow-field="delay_seconds"]').input_value(),'4')
        p.evaluate("()=>{card.hass.states['sensor.status'].attributes.settings_revision++;card.hass=card.hass}")
        self.assertTrue(p.locator('[data-plan-apply]').is_disabled())
        self.assertIn('settings_conflict',p.locator('[data-plan-message]').inner_text())

    def test_46_v5_settings_namespace_and_authoritative_plan_readback(self):
        self.flow_fixture()
        p=self.page
        p.evaluate('card.details.open=true;card.doseDetails.open=true')
        p.locator('[data-acid="pulse_seconds"] input').fill('3')
        p.locator('[data-flow-row="acid"] [data-flow-field="delay_seconds"]').fill('2')
        p.locator('[data-plan-apply]').click()
        p.evaluate("()=>{const a=card.hass.states['sensor.status'].attributes,d=calls.at(-1)[2];a.flow_plan=structuredClone(d.flow_plan);a.allowed_weekdays=structuredClone(d.allowed_weekdays);a.settings_revision++;a.flow_plan_revision++;card.hass=card.hass}")
        self.assertIn('已套用',p.locator('[data-plan-message]').inner_text())
        self.assertEqual(p.locator('[data-acid="pulse_seconds"] input').input_value(),'3')
        self.assertTrue(p.locator('[data-group-apply]').is_disabled())
        p.locator('[data-group-cancel]').click()
        p.locator('[data-acid="pulse_seconds"] input').fill('3')
        p.locator('[data-group-apply]').click()
        self.assertEqual(p.evaluate('Object.keys(calls.at(-1)[2]).length'),7)
        self.assertNotIn('allowed_weekdays',p.evaluate('calls.at(-1)[2]'))

    def test_47_v5_demo_memory_only(self):
        p=self.page
        requests=[]
        p.on('request',lambda r:requests.append(r.url))
        p.goto((ROOT/'demo/index.html').as_uri())
        self.assertEqual(p.locator('#scenario option[value="settings5"]').count(),1)
        p.locator('#scenario').select_option('settings5')
        self.assertEqual(p.locator('[data-flow-row]').count(),4)
        p.locator('[data-plan-preview]').click()
        self.assertEqual(p.locator('[data-preview-day]').count(),7)
        self.assertTrue(all(r.startswith('file:') for r in requests))
        if os.environ.get('BROWSER_EVIDENCE_DIR'):
            out=Path(os.environ['BROWSER_EVIDENCE_DIR']);out.mkdir(parents=True,exist_ok=True)
            p.screenshot(path=str(out/'p3c-v5-memory-only.png'),full_page=True)

    def control_fixture(self):
        self.page.evaluate("""() => {
          const h=fixture(), a=h.states['sensor.status'].attributes;
          Object.assign(a,{schema_version:2,mode:'control',flow_state:'idle',fault:null,run_id:null,
            capabilities:{refill:true,nutrient:false,acid:false,mix:false},
            allowed_weekdays:{refill:['mon','tue'],nutrient:[],acid:[],mix:[]},
            stage_states:{refill:'idle',nutrient:'unsupported',acid:'unsupported',mix:'unsupported'},
            control_entities:{automation_enabled:'switch.controller',refill_enabled:'switch.refill',flow_run:'switch.run',emergency_stop:'button.stop',reset_fault:'button.reset'}});
          h.states['sensor.status'].state='idle';
          for(const id of Object.values(a.control_entities)) h.states[id]={state:id.startsWith('switch.')?'off':'unknown',attributes:{}};
          window.controlFixture=()=>structuredClone(h.states);
          card.hass=h;
        }""")

    def nutrient_fixture(self):
        self.page.evaluate("""states=>{window.p3states=states; card.hass={states,callService:(...args)=>{calls.push(args);return Promise.resolve()}};}""",json.loads((ROOT/'tests/fixtures/p3a.json').read_text()))

    def test_41_v4_demo_memory_only_apply_cancel_reload(self):
        p = self.page
        requests = []
        p.on('request', lambda r: requests.append(r.url))
        p.goto((ROOT/'demo'/'index.html').as_uri())
        self.assertEqual(p.locator('#scenario option[value="settings4"]').count(), 1)
        p.locator('#scenario').select_option('settings4')
        self.assertTrue(p.evaluate('card.controls.isConnected'))
        p.evaluate('card.details.open=true;card.doseDetails.open=true')
        p.locator('[data-acid="pulse_seconds"] input').fill('3')
        p.locator('[data-group-cancel]').click()
        self.assertEqual(p.locator('[data-acid="pulse_seconds"] input').input_value(), '2')
        p.locator('[data-acid="pulse_seconds"] input').fill('3')
        p.locator('[data-group-apply]').click()
        self.assertIn('已套用', p.locator('[data-group-message]').inner_text())
        result = json.loads(p.locator('#log').inner_text())
        self.assertEqual(result['service'], 'apply_control_settings_v4')
        self.assertIsNone(result['data']['dosing_parameters'])
        p.reload()
        p.locator('#scenario').select_option('settings4')
        self.assertEqual(p.evaluate("card.hass.states['sensor.demo_status'].attributes.acid_parameters.pulse_seconds"), 2)
        self.assertEqual([u for u in requests if not u.startswith('file:')], [])

    def test_42_v4_range_null_subset_and_expired_mutation(self):
        import subprocess
        states=json.loads(subprocess.check_output(['node','-e',"console.log(JSON.stringify(require('./tests/p3b_fixture.cjs')()))"],cwd=ROOT))
        p=self.page
        p.evaluate("states=>{card.hass={states,callService:(...args)=>{calls.push(args);return Promise.resolve()}}}",states)
        p.evaluate('card.details.open=true;card.doseDetails.open=true')
        p.locator('[data-param="ph_low"] input').fill('5.3')
        self.assertFalse(p.locator('[data-group-apply]').is_disabled())
        p.evaluate("delete card.hass.states['sensor.status'].attributes.parameter_entities.ec_high;card.hass=card.hass")
        self.assertTrue(p.locator('[data-group-apply]').is_disabled())
        self.assertFalse(p.locator('[data-control="acid_enabled"] button').is_disabled())
        p.evaluate("card.hass.states['sensor.status'].attributes.acid_parameters.pulse_seconds=1.5;card.hass=card.hass;card.applyGroup()")
        self.assertEqual(p.evaluate('calls'), [])
        self.assertTrue(p.evaluate("!!card.controlTarget({key:'acid_enabled',domain:'switch'}).error"))
        self.assertFalse(p.evaluate('card.controls.isConnected'))

    def test_40_v4_acid_groups_native_controls_cancel_apply(self):
        import subprocess
        states=json.loads(subprocess.check_output(['node','-e',"console.log(JSON.stringify(require('./tests/p3b_fixture.cjs')()))"],cwd=ROOT))
        self.page.evaluate("states=>{card.hass={states,callService:(...args)=>{calls.push(args);return Promise.resolve()}}}",states)
        p=self.page
        row=p.locator('[data-control="acid_enabled"] button')
        self.assertFalse(row.is_disabled())
        row.click()
        self.assertEqual(p.evaluate('calls.at(-1)'),['switch','turn_off',{'entity_id':'switch.actual_acid_enabled'}])
        p.locator('summary').first.click()
        p.locator('[data-dose-details] summary').click()
        p.locator('[data-acid="pulse_seconds"] input').fill('3')
        p.locator('[data-group-cancel]').click()
        self.assertEqual(len(p.evaluate('calls')),1)
        p.locator('[data-acid="pulse_seconds"] input').fill('3')
        p.locator('[data-group-apply]').click()
        call=p.evaluate('calls.at(-1)')
        self.assertEqual(call[:2],['uninus_nutriculture','apply_control_settings_v4'])
        self.assertIsNone(call[2]['dosing_parameters'])
        self.assertEqual(call[2]['acid_parameters']['pulse_seconds'],3)
        self.assertIsNone(call[2]['mix_parameters'])
        self.assertEqual(len(call[2]['safety_parameters']),4)
        self.assertNotIn('已套用',p.locator('[data-group-message]').inner_text())
        p.evaluate("()=>{const a=card.hass.states['sensor.status'].attributes,d=calls.at(-1)[2];for(const k of ['parameters','dosing_parameters','acid_parameters','mix_parameters','safety_parameters','allowed_weekdays'])a[k]=d[k];a.settings_revision++;card.hass=card.hass}")
        self.assertIn('已套用',p.locator('[data-group-message]').inner_text())

    def test_24_v3_native_nutrient_enable_run_stop_and_states(self):
        self.nutrient_fixture()
        p=self.page
        row=p.locator('[data-control="nutrient_enabled"]')
        self.assertEqual(row.count(),1)
        row.locator('button').click()
        self.assertEqual(p.evaluate('calls.at(-1)'),['switch','turn_off',{'entity_id':'switch.actual_nutrient_enabled'}])
        p.locator('[data-control="flow_run"] button').click()
        self.assertEqual(p.evaluate('calls.at(-1)'),['switch','turn_on',{'entity_id':'switch.actual_flow_run'}])
        for state in ['waiting_resource','dosing','mixing','waiting_sample','stabilizing']:
            p.evaluate("s=>{const a=card.hass.states['sensor.status'];a.state=a.attributes.flow_state=s;card.hass.states['switch.actual_flow_run'].state='on';card.hass=card.hass}",state)
            self.assertIn(state,p.locator('[data-control-status]').inner_text())
        p.locator('[data-control="flow_run"] button').click()
        self.assertEqual(p.evaluate('calls.at(-1)'),['switch','turn_off',{'entity_id':'switch.actual_flow_run'}])
        p.locator('[data-control="emergency_stop"] button').click()
        self.assertEqual(p.evaluate('calls.at(-1)'),['button','press',{'entity_id':'button.actual_emergency_stop'}])

    def test_25_v3_group_apply_cancel_readback_and_reopen(self):
        self.nutrient_fixture()
        p=self.page
        p.locator('summary').first.click()
        self.assertEqual(p.locator('[data-param] button:visible').count(),0)
        p.locator('[data-param="ec_low"] input').fill('0.82')
        p.locator('[data-param="ec_high"] input').fill('0.92')
        p.locator('[data-dose-details] summary').click()
        p.locator('[data-dose="pulse_seconds"] input').fill('6')
        self.assertIn('0.87',p.locator('[data-midpoint]').inner_text())
        self.assertEqual(p.evaluate('calls'),[])
        p.locator('[data-group-cancel]').click()
        self.assertEqual(p.evaluate('calls'),[])
        self.assertEqual(p.locator('[data-param="ec_low"] input').input_value(),'0.8')
        p.locator('[data-param="ec_low"] input').fill('0.82')
        p.locator('[data-dose="pulse_seconds"] input').fill('6')
        p.locator('[data-group-apply]').click()
        call=p.evaluate('calls.at(-1)')
        self.assertEqual(call[:2],['uninus_nutriculture','apply_control_settings'])
        self.assertEqual(set(call[2]),{'config_entry_id','expected_revision','parameters','dosing_parameters','allowed_weekdays'})
        self.assertEqual(call[2]['expected_revision'],4)
        self.assertEqual(call[2]['config_entry_id'],'entry-a')
        self.assertEqual(len(call[2]['parameters']),10)
        self.assertEqual(len(call[2]['dosing_parameters']),13)
        self.assertEqual(call[2]['dosing_parameters']['pulse_seconds'],6)
        self.assertNotIn('已套用',p.locator('[data-group-message]').inner_text())
        self.assertIn('讀回',p.locator('[data-group-message]').inner_text())
        p.evaluate("() => {const a=card.hass.states['sensor.status'].attributes,d=calls.at(-1)[2];a.parameters=d.parameters;a.dosing_parameters=d.dosing_parameters;a.allowed_weekdays=d.allowed_weekdays;a.settings_revision=5;for(const [k,v] of Object.entries(d.parameters))card.hass.states[a.parameter_entities[k]].state=String(v);card.hass=card.hass}")
        self.assertIn('已套用',p.locator('[data-group-message]').inner_text())
        p.locator('summary').first.click();p.locator('summary').first.click()
        self.assertEqual(p.locator('[data-param="ec_low"] input').input_value(),'0.82')

    def test_26_v3_conflict_preserves_complete_draft_and_cancel_reloads(self):
        self.nutrient_fixture()
        p=self.page
        p.locator('summary').first.click()
        p.locator('[data-param="ec_low"] input').fill('0.82')
        p.evaluate("() => {const a=card.hass.states['sensor.status'].attributes;a.settings_revision=5;a.parameters.ec_low=.81;card.hass=card.hass}")
        self.assertEqual(p.locator('[data-param="ec_low"] input').input_value(),'0.82')
        self.assertIn('settings_conflict',p.locator('[data-group-message]').inner_text())
        self.assertTrue(p.locator('[data-group-apply]').is_disabled())
        p.locator('[data-group-cancel]').click()
        self.assertEqual(p.locator('[data-param="ec_low"] input').input_value(),'0.81')
        self.assertEqual(p.evaluate('calls'),[])
        p.locator('[data-param="ec_low"] input').fill('0.82')
        p.evaluate("() => {card.hass.callService=(...args)=>{calls.push(args);return Promise.reject(new Error('settings_conflict'))}}")
        p.locator('[data-group-apply]').click()
        self.assertIn('settings_conflict',p.locator('[data-group-message]').inner_text())
        self.assertEqual(p.locator('[data-param="ec_low"] input').input_value(),'0.82')
        self.assertEqual(len(p.evaluate('calls')),1)

    def test_27_v3_pending_slot_mapping_and_remount_late_promises(self):
        self.nutrient_fixture()
        p=self.page
        p.locator('summary').first.click()
        p.locator('[data-param="ec_low"] input').fill('0.82')
        p.evaluate("() => {card.hass.callService=(...args)=>{calls.push(args);return new Promise((resolve,reject)=>{window.finish=resolve;window.fail=reject})}}")
        p.locator('[data-group-apply]').click()
        p.evaluate("card.setConfig({entity:'sensor.status'});card.remove();document.body.append(card)")
        p.locator('[data-param="ec_low"] input').fill('0.83')
        p.evaluate('card.groupApply.click()')
        self.assertEqual(len(p.evaluate('calls')),1)
        p.evaluate("() => {const states=structuredClone(p3states);states['sensor.other']=states['sensor.status'];delete states['sensor.status'];states['sensor.other'].attributes.settings_target.config_entry_id='entry-b';states['sensor.other'].attributes.settings_revision=40;card.setConfig({entity:'sensor.other'});card.hass={states,callService:(...args)=>{calls.push(args);return Promise.resolve()}};card.details.open=true}")
        p.locator('[data-param="ec_low"] input').fill('0.84')
        p.evaluate("fail(new Error('old-entry-error'))")
        self.assertEqual(p.locator('[data-param="ec_low"] input').input_value(),'0.84')
        self.assertNotIn('old-entry-error',p.locator('[data-group-message]').inner_text())
        p.locator('[data-group-apply]').click()
        self.assertEqual(p.evaluate('calls.at(-1)[2].config_entry_id'),'entry-b')
        self.assertEqual(p.evaluate('calls.at(-1)[2].expected_revision'),40)
        self.assertEqual(p.evaluate('calls[0][2].config_entry_id'),'entry-a')
        self.assertEqual(p.evaluate('calls[0][2].expected_revision'),4)
        p.locator('[data-group-cancel]').click()
        p.locator('[data-param="ec_low"] input').fill('0.85')
        p.evaluate("() => {const a=card.hass.states['sensor.other'].attributes;card.hass.states['number.new_ec']={state:'.81',attributes:{min:0,max:14,step:.01}};a.parameter_entities.ec_low='number.new_ec';card.groupApply.click()}")
        self.assertEqual(len(p.evaluate('calls')),2)
        self.assertNotEqual(p.locator('[data-param="ec_low"] input').input_value(),'0.85')
        p.evaluate('card.remove();card.groupApply.click();document.body.append(card)')
        self.assertEqual(len(p.evaluate('calls')),2)

    def test_28_v3_container_geometry_themes_and_live_typing(self):
        self.nutrient_fixture()
        p=self.page
        p.locator('summary').first.click()
        p.locator('[data-dose-details] summary').click()
        p.locator('[data-week-details] summary').click()
        field=p.locator('[data-param="ec_low"] input')
        field.fill('0.82');field.press('Home');field.press('ArrowRight')
        p.evaluate("window.original=card.rows.get('ec_low').input;card.hass=card.hass")
        field.press('1')
        self.assertEqual(field.input_value(),'01.82')
        self.assertTrue(p.evaluate("original===card.rows.get('ec_low').input && card.shadowRoot.activeElement===original"))
        output=Path(os.environ['BROWSER_EVIDENCE_DIR']);output.mkdir(parents=True,exist_ok=True)
        rows=[]
        p.set_viewport_size({'width':1280,'height':1000})
        for theme in ['light','dark']:
            p.evaluate("t=>{document.body.style.setProperty('--primary-text-color',t==='dark'?'#eee':'#213b48');document.body.style.setProperty('--card-background-color',t==='dark'?'#161b22':'#fff');document.body.style.setProperty('--secondary-background-color',t==='dark'?'#262d36':'#edf5f6')}",theme)
            for width in [320,768,1200]:
                p.evaluate("w=>{card.style.width=w+'px';card.hass=card.hass}",width)
                g=p.evaluate("""() => {const box=card.getBoundingClientRect(),nodes=[card,card.root,...card.shadowRoot.querySelectorAll('button,input,fieldset,.param,.control')].filter(n=>n.getClientRects().length);return {width:box.width,overflow:Math.max(...nodes.map(n=>n.scrollWidth-n.clientWidth)),outside:nodes.filter(n=>{const r=n.getBoundingClientRect();return r.left<box.left-.5||r.right>box.right+.5}).length}}""")
                self.assertEqual(g['width'],width);self.assertLessEqual(g['overflow'],1);self.assertEqual(g['outside'],0)
                rows.append({'theme':theme,**g});p.screenshot(path=str(output/f'v3-{theme}-{width}.png'),full_page=True)
        (output/'v3-geometry.json').write_text(json.dumps(rows,indent=2))
        self.assertEqual(p.evaluate('calls'),[])

    def test_29_v3_invalid_latest_contract_and_busy_rejection_fail_closed(self):
        self.nutrient_fixture()
        p=self.page
        mutations=["a.schema_version=2","a.flow_state='future'","s.state='fault'","a.capabilities.acid=true","a.settings_target.domain='evil'","a.dosing_parameters.extra=1","a.dosing_parameters.pulse_seconds=true","a.allowed_weekdays.nutrient=['mon','mon']","a.control_entities.nutrient_enabled=a.control_entities.flow_run","delete card.hass.states['number.actual_ph_low'].attributes.step"]
        for mutation in mutations:
            self.nutrient_fixture()
            p.evaluate("() => {calls.length=0;const nutrientButton=card.controlRows.get('nutrient_enabled').button;const s=card.hass.states['sensor.status'],a=s.attributes;"+mutation+";card.hass=card.hass;card.groupApply.click();nutrientButton.click()}")
            # Bad Number metadata blocks settings, not otherwise valid native switches.
            self.assertEqual(len(p.evaluate('calls')),1 if mutation.startswith('delete card.hass.states') else 0)
        self.nutrient_fixture()
        p.evaluate("() => {calls.length=0;card.hass.callService=(...args)=>{calls.push(args);return Promise.reject(new Error('busy'))}}")
        p.locator('[data-control="flow_run"] button').click()
        self.assertIn('busy',p.locator('[data-control="flow_run"]').inner_text())
        p.evaluate("card.hass.states['switch.actual_flow_run'].state='unknown';card.hass=card.hass")
        self.assertTrue(p.locator('[data-control="flow_run"] button').is_disabled())

    def test_30_v3_offline_group_demo_is_memory_only(self):
        p = self.page
        requests = []
        p.on('request', lambda r: requests.append(r.url))
        p.goto((ROOT/'demo'/'index.html').as_uri())
        p.locator('#scenario').select_option('settings')
        self.assertEqual(p.evaluate("card.hass.states['sensor.demo_status'].attributes.schema_version"),3)
        p.evaluate('card.details.open=true')
        low = p.locator('[data-param="ec_low"] input')
        low.fill('0.85')
        p.locator('[data-group-cancel]').click()
        self.assertEqual(p.locator('#log').inner_text(),'尚無呼叫')
        self.assertEqual(low.input_value(),'0.8')
        low.fill('0.85')
        p.locator('[data-group-apply]').click()
        p.wait_for_function("card.groupMessage.textContent.includes('已套用')")
        result = json.loads(p.locator('#log').inner_text())
        self.assertTrue(result['simulation'])
        self.assertEqual(result['service'],'apply_control_settings')
        self.assertEqual(result['data']['parameters']['ec_low'],0.85)
        self.assertFalse(p.evaluate("card.hass.states['sensor.demo_status'].attributes.capabilities.nutrient"))
        self.assertEqual([url for url in requests if not url.startswith('file:')],[])

    def test_17_v2_displays_real_states_and_keeps_ten_number_editors(self):
        self.control_fixture()
        p=self.page
        self.assertIn('控制模式',p.locator('.badge').inner_text())
        self.assertIn('idle',p.locator('[data-control-status]').inner_text())
        self.assertIn('尚未提供灌溉許可',p.locator('.safety').inner_text())
        self.assertNotIn('不控制設備',p.locator('.safety').inner_text())
        for label in ['加養','加酸','獨立混合','尚未支援']:
            self.assertIn(label,p.locator('[data-unsupported]').inner_text())
        p.locator('summary').click()
        row=p.locator('[data-param="ph_low"]')
        row.locator('input').fill('5.55');row.locator('button').click()
        self.assertEqual(p.evaluate('calls'),[['number','set_value',{'entity_id':'number.tank_ph_low','value':5.55}]])
        for state in ['uncommissioned','disabled','idle','starting','refilling','stopping','completed','aborted','fault']:
            p.evaluate("state=>{const s=card.hass.states['sensor.status'];s.state=state;s.attributes.flow_state=state;s.attributes.fault='<img src=x onerror=alert(1)>';s.attributes.run_id='run-1';card.hass=card.hass}",state)
            self.assertIn(state,p.locator('[data-control-status]').inner_text())
            self.assertIn('<img src=x onerror=alert(1)>',p.locator('[data-control-status]').inner_text())
            self.assertEqual(p.locator('uninus-nutriculture-card img').count(),0)
        p.evaluate("card.hass=fixture()")
        self.assertEqual(p.locator('[data-controls]').count(),0)
        self.assertIn('不控制設備',p.locator('.safety').inner_text())

    def test_18_native_mapped_actions_rejection_and_authoritative_readback(self):
        self.control_fixture()
        p=self.page
        self.assertEqual(p.locator('[data-control] button').count(),5)
        self.assertEqual(p.evaluate('calls'),[])
        for key,target in [('automation_enabled','switch.controller'),('refill_enabled','switch.refill'),('flow_run','switch.run')]:
            row=p.locator(f'[data-control="{key}"]')
            self.assertIn('off',row.inner_text())
            row.locator('button').click()
            self.assertEqual(p.evaluate('calls.at(-1)'),['switch','turn_on',{'entity_id':target}])
            self.assertIn('off',row.inner_text())
            self.assertIn('讀回',row.inner_text())
            p.evaluate("id=>{card.hass.states[id].state='on';card.hass=card.hass}",target)
            self.assertIn('on',row.inner_text())
            row.locator('button').click()
            self.assertEqual(p.evaluate('calls.at(-1)'),['switch','turn_off',{'entity_id':target}])
        for key,target in [('emergency_stop','button.stop'),('reset_fault','button.reset')]:
            p.locator(f'[data-control="{key}"] button').click()
            self.assertEqual(p.evaluate('calls.at(-1)'),['button','press',{'entity_id':target}])
        p.evaluate("() => {card.hass.callService=(...args)=>{calls.push(args);return Promise.reject(new Error('<svg onload=alert(1)> not_commissioned'));};const s=card.hass.states['sensor.status'];s.state='uncommissioned';s.attributes.flow_state='uncommissioned';card.hass=card.hass;}")
        p.locator('[data-control="automation_enabled"] button').click()
        self.assertIn('not_commissioned',p.locator('[data-control="automation_enabled"]').inner_text())
        self.assertIn('uncommissioned',p.locator('[data-control-status]').inner_text())
        self.assertEqual(p.locator('uninus-nutriculture-card svg').count(),0)
        self.assertEqual(p.evaluate("card.hass.states['switch.controller'].state"),'on')

    def test_19_v2_latest_event_validation_and_fail_closed_targets(self):
        self.control_fixture()
        p=self.page
        # No render between state mutation and a trusted click: use newest ON state.
        p.evaluate("card.hass.states['switch.run'].state='on'")
        p.locator('[data-control="flow_run"] button').click()
        self.assertEqual(p.evaluate('calls'),[['switch','turn_off',{'entity_id':'switch.run'}]])
        mutations={
            'schema3':"s.attributes.schema_version=3",
            'schema2_shadow':"s.attributes.mode='shadow'",
            'unknown_flow':"s.state=s.attributes.flow_state='future'",
            'mismatch':"s.state='fault'",
            'missing_map':"delete s.attributes.control_entities.flow_run",
            'wrong_domain':"s.attributes.control_entities.flow_run='button.stop'",
            'malformed_domain_separator':"s.attributes.control_entities.flow_run='switchXrun';h.states['switchXrun']={state:'off'}",
            'bad_id':"s.attributes.control_entities.flow_run='switch.BAD'",
            'missing_entity':"delete h.states['switch.run']",
            'unknown':"h.states['switch.run'].state='unknown'",
            'unavailable':"h.states['switch.run'].state='unavailable'",
            'unsupported':"s.attributes.capabilities.refill=false",
            'missing_capability':"delete s.attributes.capabilities.refill",
            'missing_status':"delete h.states['sensor.status']",
        }
        for label,mutation in mutations.items():
            with self.subTest(label=label):
                self.control_fixture()
                p.evaluate("() => {calls.length=0;const h=card.hass,s=h.states['sensor.status'];"+mutation+";card.controlRows.get('flow_run').button.click();}")
                self.assertEqual(p.evaluate('calls'),[])
        self.control_fixture()
        p.evaluate("() => {calls.length=0;const h=card.hass;h.states['switch.replacement']={state:'off'};h.states['sensor.status'].attributes.control_entities.flow_run='switch.replacement';card.controlRows.get('flow_run').button.click();}")
        self.assertEqual(p.evaluate('calls'),[])
        p.locator('[data-control="flow_run"] button').click()
        self.assertEqual(p.evaluate('calls'),[['switch','turn_on',{'entity_id':'switch.replacement'}]])
        for key,mutation in [('emergency_stop',"delete h.states['button.stop']"),('reset_fault',"h.states['button.reset'].state='unavailable'"),('reset_fault',"h.states['sensor.status'].attributes.control_entities.reset_fault='switch.run'")]:
            self.control_fixture()
            p.evaluate("key=>{calls.length=0;window.key=key}",key)
            p.evaluate("() => {const h=card.hass;"+mutation+";card.controlRows.get(key).button.click()}")
            self.assertEqual(p.evaluate('calls'),[])

    def test_20_v2_pending_lifecycle_and_new_scope_notices(self):
        self.control_fixture()
        p=self.page
        row=p.locator('[data-control="flow_run"]')
        p.evaluate("() => {card.hass.callService=(...args)=>{calls.push(args);return Promise.reject(new Error('old-scope-error'))}}")
        row.locator('button').click()
        self.assertIn('old-scope-error',row.inner_text())
        p.evaluate("() => {const h=card.hass;h.states['sensor.other']=structuredClone(h.states['sensor.status']);card.setConfig({entity:'sensor.other'});}")
        self.assertNotIn('old-scope-error',row.inner_text())
        for reject in [False,True]:
            self.control_fixture()
            p.evaluate("() => {card.setConfig({entity:'sensor.status'});calls.length=0;card.hass.callService=(...args)=>{calls.push(args);return new Promise((resolve,reject)=>{window.finish=resolve;window.fail=reject})}}")
            row.locator('button').click()
            p.evaluate("card.controlRows.get('flow_run').button.click();card.setConfig({entity:'sensor.status',title:'same'});card.remove();document.body.append(card);card.controlRows.get('flow_run').button.click()")
            self.assertEqual(len(p.evaluate('calls')),1)
            self.assertTrue(row.locator('button').is_disabled())
            p.evaluate("fail(new Error('stale-rejection'))" if reject else 'finish()')
            self.assertNotIn('stale-rejection',row.inner_text())
            self.assertNotIn('已送出操作',row.inner_text())
            self.assertTrue(row.locator('button').is_enabled())
        # New target can act while old transport settles; late errors cannot overwrite it.
        self.control_fixture()
        p.evaluate("() => {calls.length=0;card.hass.callService=(...args)=>{calls.push(args);return new Promise((resolve,reject)=>{window.fail=reject})}}")
        row.locator('button').click()
        p.evaluate("() => {card.hass.states['switch.new_run']={state:'off'};card.hass.states['sensor.status'].attributes.control_entities.flow_run='switch.new_run';card.hass=card.hass;card.hass.callService=(...args)=>{calls.push(args);return Promise.resolve()}}")
        row.locator('button').click()
        p.evaluate("fail(new Error('old-mapping-error'))")
        self.assertNotIn('old-mapping-error',row.inner_text())
        self.assertIn('讀回',row.inner_text())
        self.assertEqual(p.evaluate('calls.at(-1)'),['switch','turn_on',{'entity_id':'switch.new_run'}])

    def test_21_v2_pending_slot_switch_and_detached_events(self):
        self.control_fixture()
        p=self.page
        p.evaluate("() => {card.hass.callService=(...args)=>{calls.push(args);return new Promise((resolve,reject)=>{window.finish=resolve;window.fail=reject})}}")
        p.locator('[data-control="flow_run"] button').click()
        p.evaluate("() => {const h=fixture('sensor.other');h.states['sensor.other']=structuredClone(card.hass.states['sensor.status']);h.states['sensor.other'].attributes.control_entities.flow_run='switch.other_run';h.states['switch.other_run']={state:'off'};card.setConfig({entity:'sensor.other'});card.hass=h;card.details.open=true}")
        field=p.locator('[data-param="ph_low"] input')
        field.fill('5.75')
        p.evaluate("fail(new Error('old-tank-late-error'))")
        self.assertEqual(field.input_value(),'5.75')
        self.assertNotIn('old-tank-late-error',p.locator('[data-controls]').inner_text())
        p.locator('[data-control="flow_run"] button').click()
        self.assertEqual(p.evaluate('calls.at(-1)'),['switch','turn_on',{'entity_id':'switch.other_run'}])
        count=len(p.evaluate('calls'))
        p.evaluate("card.remove();card.controlRows.get('emergency_stop').button.click();card.rows.get('ph_low').button.click();document.body.append(card)")
        self.assertEqual(len(p.evaluate('calls')),count)
        self.assertEqual(field.input_value(),'5.75')

    def test_22_v2_geometry_dark_light_and_node_continuity(self):
        self.control_fixture()
        p=self.page
        output=Path(os.environ.get('BROWSER_EVIDENCE_DIR',str(ROOT/'test-results'/'browser')))
        output.mkdir(parents=True,exist_ok=True)
        results=[]
        for theme in ['light','dark']:
            p.evaluate("theme=>{document.body.style.cssText+=';--primary-text-color:'+(theme==='dark'?'#eee':'#213b48')+';--card-background-color:'+(theme==='dark'?'#161b22':'#fff')+';--secondary-background-color:'+(theme==='dark'?'#262d36':'#edf5f6')}",theme)
            for width in [320,768,1200]:
                p.set_viewport_size({'width':width,'height':1000})
                p.evaluate("card.details.open=true;card.hass.states['sensor.status'].attributes.fault='X'.repeat(300);card.hass=card.hass")
                g=p.evaluate("""() => {const nodes=[card,card.root,...card.shadowRoot.querySelectorAll('.control,button,input,.param')];return {viewport:innerWidth,card_width:card.getBoundingClientRect().width,maxOverflow:Math.max(...nodes.map(n=>n.scrollWidth-n.clientWidth)),outside:nodes.filter(n=>{const r=n.getBoundingClientRect();return r.left<0||r.right>innerWidth+.5}).length,buttons:[...card.controlRows.values()].map(r=>({width:r.button.getBoundingClientRect().width,height:r.button.getBoundingClientRect().height}))}}""")
                self.assertEqual(g['card_width'],width-16)
                self.assertLessEqual(g['maxOverflow'],1)
                self.assertEqual(g['outside'],0)
                self.assertEqual(p.evaluate('[...card.controlRows.keys()].sort()'),['automation_enabled','emergency_stop','flow_run','refill_enabled','reset_fault'])
                self.assertTrue(all(b['width']>=44 and b['height']>=36 for b in g['buttons']))
                results.append({'theme':theme,**g})
                p.screenshot(path=str(output/f'v2-{theme}-{width}.png'),full_page=True)
        (output/'v2-geometry.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
        button=p.locator('[data-control="flow_run"] button')
        button.focus()
        p.evaluate("window.originalButton=card.controlRows.get('flow_run').button;for(let i=0;i<5;i++){card.hass.states['sensor.status'].attributes.run_id=String(i);card.hass=card.hass}")
        self.assertTrue(p.evaluate("originalButton===card.controlRows.get('flow_run').button && card.shadowRoot.activeElement===originalButton && card.details.open"))
        self.assertEqual(p.evaluate('calls'),[])

    def test_23_v2_demo_memory_only_actions_and_failures(self):
        p=self.page
        requests=[]
        p.on('request',lambda r:requests.append(r.url))
        p.goto((ROOT/'demo'/'index.html').as_uri())
        self.assertIn('v2',p.locator('#scenario').inner_text())
        p.locator('#scenario').select_option('control')
        p.locator('[data-control="flow_run"] button').click()
        log=json.loads(p.locator('#log').inner_text())
        self.assertEqual(log,{'simulation':True,'domain':'switch','service':'turn_on','data':{'entity_id':'switch.demo_flow_run'}})
        self.assertIn('refilling',p.locator('[data-control-status]').inner_text())
        p.locator('[data-control="emergency_stop"] button').click()
        self.assertIn('emergency_stop',p.locator('[data-control-status]').inner_text())
        p.locator('[data-control="reset_fault"] button').click()
        self.assertIn('idle',p.locator('[data-control-status]').inner_text())
        p.locator('#scenario').select_option('control_rejected')
        p.locator('[data-control="flow_run"] button').click()
        self.assertIn('simulated_rejection',p.locator('[data-control="flow_run"]').inner_text())
        self.assertEqual([u for u in requests if not u.startswith('file:')],[])

    def test_01_shadow_readings_and_untrusted_title(self):
        p = self.page
        text = p.locator('uninus-nutriculture-card').evaluate('(el)=>el.shadowRoot.textContent')
        for expected in ['UNiNUS Nutriculture','養液控制','影子監測','不控制設備','尚未提供灌溉許可','5.6','0.85','2.3']:
            self.assertIn(expected,text)
        p.evaluate("card.setConfig({entity:'sensor.status',title:'<img src=x onerror=alert(1)>'})")
        self.assertEqual(p.locator('uninus-nutriculture-card img').count(),0)
        self.assertIn('<img src=x onerror=alert(1)>',p.locator('uninus-nutriculture-card').evaluate('(el)=>el.shadowRoot.textContent'))
        p.evaluate("card.hass.states['sensor.ph'].state='unknown';card.hass=card.hass")
        self.assertIn('—',p.locator('[data-reading="ph"]').inner_text())

    def test_02_explicit_single_item_save_uses_actual_metadata(self):
        p = self.page
        self.assertEqual(p.locator('[data-param]').count(),10)
        p.locator('summary').click()
        row = p.locator('[data-param="ph_low"]')
        field = row.locator('input')
        self.assertEqual(field.get_attribute('min'),'0')
        self.assertEqual(field.get_attribute('max'),'14')
        self.assertEqual(field.get_attribute('step'),'0.01')
        field.fill('5.55')
        self.assertEqual(p.evaluate('calls'),[])
        row.locator('button').click()
        self.assertEqual(p.evaluate('calls'),[['number','set_value',{'entity_id':'number.tank_ph_low','value':5.55}]])
        self.assertIn('單項儲存',p.locator('details').inner_text())
        self.assertIn('僅儲存',p.locator('details').inner_text())

    def test_03_draft_cannot_follow_a_new_tank(self):
        p = self.page
        p.locator('summary').click()
        field = p.locator('[data-param="ph_low"] input')
        field.fill('5.55')
        p.evaluate("""() => {
          const h = fixture('sensor.other');
          h.states['sensor.other'].attributes.parameter_entities.ph_low = 'number.other_ph';
          h.states['number.other_ph'] = {state:'6',attributes:{min:0,max:14,step:.01}};
          card.hass = h; card.setConfig({entity:'sensor.other'});
        }""")
        self.assertEqual(field.input_value(),'6')
        p.evaluate("card.shadowRoot.querySelector('[data-param=ph_low] button').click()")
        self.assertEqual(p.evaluate('calls'),[])

    def test_04_old_completion_cannot_touch_reconfigured_draft(self):
        p = self.page
        p.locator('summary').click()
        row = p.locator('[data-param="ph_low"]')
        row.locator('input').fill('5.55')
        p.evaluate("() => {card.hass.callService=(...args)=>{calls.push(args);return new Promise((resolve,reject)=>{window.finish=resolve;window.fail=reject;});};}")
        row.locator('button').click()
        p.evaluate("card.shadowRoot.querySelector('[data-param=ph_low] button').click()")
        self.assertEqual(len(p.evaluate('calls')),1)
        self.assertTrue(row.locator('input').is_disabled())
        p.evaluate("card.setConfig({entity:'sensor.other'});card.hass=fixture('sensor.other')")
        p.locator('summary').click()
        self.assertTrue(row.locator('input').is_enabled())
        row.locator('input').fill('6.15')
        p.evaluate("fail(new Error('old tank rejection'))")
        self.assertEqual(row.locator('input').input_value(),'6.15')
        self.assertNotIn('old tank rejection',row.inner_text())
        self.assertTrue(row.locator('button').is_enabled())

    def test_05_mapping_drift_cannot_retarget_a_typed_draft(self):
        p = self.page
        p.locator('summary').click()
        row = p.locator('[data-param="ph_low"]')
        row.locator('input').fill('5.55')
        p.evaluate("""() => {
          card.hass.states['number.replacement']={state:'6',attributes:{min:0,max:14,step:.01}};
          card.hass.states['sensor.status'].attributes.parameter_entities.ph_low='number.replacement';
          card.hass=card.hass;
          card.shadowRoot.querySelector('[data-param=ph_low] button').click();
        }""")
        self.assertEqual(p.evaluate('calls'),[])
        self.assertNotEqual(row.locator('input').input_value(),'5.55')
        self.assertFalse(row.locator('button').is_enabled())

    def test_06_picker_editor_preserves_config_and_toggles_parameters(self):
        p = self.page
        result = p.evaluate("""() => {
          const C = customElements.get('uninus-nutriculture-card');
          const picked = (window.customCards || []).find(c => c.type === 'uninus-nutriculture-card');
          return {picked, size:card.getCardSize?.(), stub:C.getStubConfig?.(fixture())};
        }""")
        self.assertIsNotNone(result.get('picked'))
        self.assertGreater(result.get('size',0),0)
        self.assertEqual(result.get('stub',{}).get('entity'),'sensor.status')
        p.evaluate("""() => {
          window.original={type:'custom:uninus-nutriculture-card',entity:'sensor.status',future:{x:7}};
          window.editor=customElements.get('uninus-nutriculture-card').getConfigElement();
          editor.hass=fixture();editor.setConfig(original);document.body.append(editor);
          window.events=[];editor.addEventListener('config-changed',e=>events.push(e.detail.config));
        }""")
        p.locator('uninus-nutriculture-card-editor [name="title"]').fill('新的標題')
        p.locator('uninus-nutriculture-card-editor [name="show_parameters"]').uncheck()
        self.assertEqual(p.evaluate('original'),{'type':'custom:uninus-nutriculture-card','entity':'sensor.status','future':{'x':7}})
        emitted=p.evaluate('events.at(-1)')
        self.assertEqual(emitted['future'],{'x':7})
        self.assertFalse(emitted['show_parameters'])
        self.assertEqual(emitted['title'],'新的標題')
        p.evaluate('card.setConfig(events.at(-1))')
        self.assertEqual(p.locator('uninus-nutriculture-card details').count(),0)
        p.evaluate('editor.setConfig(events.at(-1));editor.hass=fixture()')
        self.assertFalse(p.locator('uninus-nutriculture-card-editor [name="show_parameters"]').is_checked())
        self.assertEqual(p.evaluate('calls'),[])

    def test_07_unresolved_target_stays_locked_across_same_config(self):
        p = self.page
        p.locator('summary').click()
        row = p.locator('[data-param="ph_low"]')
        row.locator('input').fill('5.55')
        p.evaluate("() => {card.hass.callService=(...args)=>{calls.push(args);return new Promise(resolve=>{window.finish=resolve;});};}")
        row.locator('button').click()
        p.evaluate("card.setConfig({entity:'sensor.status',title:'same tank'});card.remove();document.body.append(card)")
        row.locator('input').fill('5.65')
        p.evaluate("card.shadowRoot.querySelector('[data-param=ph_low] button').click()")
        self.assertEqual(len(p.evaluate('calls')),1)
        self.assertTrue(row.locator('button').is_disabled())
        p.evaluate('finish()')
        self.assertEqual(row.locator('input').input_value(),'5.65')
        self.assertTrue(row.locator('button').is_enabled())

    def test_08_missing_incompatible_and_invalid_targets_fail_closed(self):
        scenarios = {
            'missing_status': "delete h.states['sensor.status']",
            'schema': "h.states['sensor.status'].attributes.schema_version=2",
            'active_mode': "h.states['sensor.status'].attributes.mode='active'",
            'unavailable_status': "h.states['sensor.status'].state='unavailable'",
            'missing_mapping': "delete h.states['sensor.status'].attributes.parameter_entities.ph_low",
            'non_number': "h.states['sensor.status'].attributes.parameter_entities.ph_low='switch.pump'",
            'malformed_id': "h.states['sensor.status'].attributes.parameter_entities.ph_low='number.BAD'",
            'missing_number': "delete h.states['number.tank_ph_low']",
            'unavailable_number': "h.states['number.tank_ph_low'].state='unavailable'",
            'unknown_number': "h.states['number.tank_ph_low'].state='unknown'",
            'bad_metadata': "h.states['number.tank_ph_low'].attributes.step=0",
        }
        self.page.locator('summary').click()
        for label,mutation in scenarios.items():
            with self.subTest(label=label):
                self.page.evaluate("() => {const h=fixture();"+mutation+";card.hass=h;const r=card.rows.get('ph_low');r.input.value='5.55';r.input.dispatchEvent(new Event('input'));r.button.click();}")
                self.assertEqual(self.page.evaluate('calls'),[])
                self.assertTrue(self.page.locator('[data-param="ph_low"] button').is_disabled())
                self.assertIn('禁止儲存',self.page.locator('[data-param="ph_low"]').inner_text())

    def test_09_numeric_range_step_finite_and_rejection_preserves_draft(self):
        p = self.page
        p.locator('summary').click()
        row=p.locator('[data-param="ph_low"]')
        for value in ['', 'NaN','Infinity','-1','15','5.555']:
            p.evaluate("value=>{const r=card.rows.get('ph_low');r.input.value=value;r.input.dispatchEvent(new Event('input'));r.button.click();}",value)
            self.assertEqual(p.evaluate('calls'),[])
            self.assertTrue(row.locator('button').is_disabled())
        p.evaluate("() => {card.hass.callService=(...args)=>{calls.push(args);return Promise.reject(new Error('<img src=x> denied'));};}")
        row.locator('input').fill('5.55')
        row.locator('button').click()
        self.assertEqual(row.locator('input').input_value(),'5.55')
        self.assertIn('<img src=x> denied',row.inner_text())
        self.assertEqual(row.locator('img').count(),0)
        self.assertTrue(row.locator('button').is_enabled())
        self.assertEqual(len(p.evaluate('calls')),1)

    def test_10_live_updates_preserve_node_focus_caret_and_disclosure(self):
        p = self.page
        p.locator('summary').click()
        field=p.locator('[data-param="ph_low"] input')
        field.fill('5.55'); field.press('Home'); field.press('ArrowRight')
        p.evaluate("window.originalInput=card.rows.get('ph_low').input")
        for i in range(5):
            p.evaluate("i=>{card.hass.states['sensor.ph'].state=String(5.6+i/100);card.hass=card.hass}",i)
        self.assertTrue(p.evaluate("originalInput===card.rows.get('ph_low').input && card.shadowRoot.activeElement===originalInput && card.details.open"))
        field.press('1')
        self.assertEqual(field.input_value(),'51.55')
        self.assertEqual(p.evaluate('calls'),[])
        self.assertIn('5.64',p.locator('[data-reading="ph"]').inner_text())

    def test_11_disconnected_success_and_failure_cannot_clear_draft(self):
        p=self.page
        p.locator('summary').click()
        row=p.locator('[data-param="ph_low"]')
        for reject in [False,True]:
            row.locator('input').fill('5.55')
            p.evaluate("() => {card.hass.callService=(...args)=>{calls.push(args);return new Promise((resolve,reject)=>{window.finish=resolve;window.fail=reject;});};}")
            row.locator('button').click()
            p.evaluate('card.remove()')
            p.evaluate("fail(new Error('detached error'))" if reject else 'finish()')
            p.evaluate('document.body.append(card)')
            self.assertEqual(row.locator('input').input_value(),'5.55')
            self.assertNotIn('detached error',row.inner_text())
            self.assertTrue(row.locator('button').is_enabled())
        self.assertEqual(len(p.evaluate('calls')),2)

    def test_12_responsive_geometry_and_screenshots(self):
        p=self.page
        output=Path(os.environ.get('BROWSER_EVIDENCE_DIR',str(ROOT/'test-results'/'browser')))
        output.mkdir(parents=True,exist_ok=True)
        rows=[]
        for width in [320,768,1200]:
            p.set_viewport_size({'width':width,'height':1000})
            p.evaluate("card.hass=fixture();card.setConfig({entity:'sensor.status',title:'模擬資料 · UNiNUS Nutriculture / 養液控制'});card.details.open=true")
            geometry=p.evaluate("""() => {
              const nodes=[document.documentElement,document.body,card,card.root,...card.shadowRoot.querySelectorAll('.tiles,.tile,.param,input,button')];
              return {viewport:innerWidth,card:card.getBoundingClientRect().width,maxOverflow:Math.max(...nodes.map(el=>el.scrollWidth-el.clientWidth)),outside:nodes.filter(el=>{const r=el.getBoundingClientRect();return r.right>innerWidth+.5||r.left<-.5}).length};
            }""")
            self.assertEqual(geometry['viewport'],width)
            self.assertEqual(geometry['card'],width-16)
            self.assertLessEqual(geometry['maxOverflow'],1)
            self.assertEqual(geometry['outside'],0)
            p.screenshot(path=str(output/f'card-{width}.png'),full_page=True)
            rows.append(geometry)
            p.evaluate("card.setConfig({entity:'sensor.status',title:'X'.repeat(300)});card.hass.states['sensor.status'].attributes.reasons=['Y'.repeat(300)];card.hass=card.hass")
            self.assertLessEqual(p.evaluate('document.documentElement.scrollWidth-innerWidth'),1)
        (output/'geometry.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
        print('GEOMETRY='+json.dumps(rows),flush=True)

    def test_13_initialization_orders_and_editor_entity_events(self):
        p=self.page
        self.assertTrue(p.evaluate("() => {const C=customElements.get('uninus-nutriculture-card');for(const first of ['config','hass']){const c=new C();if(first==='config'){c.setConfig({entity:'sensor.status'});c.hass=fixture();}else{c.hass=fixture();c.setConfig({entity:'sensor.status'});}document.body.append(c);c.remove();}return true;}"))
        p.evaluate("""() => {
          const C=customElements.get('uninus-nutriculture-card');window.editor=C.getConfigElement();
          window.h=fixture();h.states['sensor.other']={state:'invalid',attributes:{}};
          editor.setConfig({entity:'sensor.status',unknown:'keep'});editor.hass=h;document.body.append(editor);
          window.events=[];document.body.addEventListener('config-changed',e=>events.push(e.detail.config));
        }""")
        p.locator('uninus-nutriculture-card-editor select').select_option('sensor.other')
        self.assertEqual(p.evaluate('events.at(-1).entity'),'sensor.other')
        title=p.locator('uninus-nutriculture-card-editor [name="title"]')
        title.fill('abcd');title.press('Home');title.press('ArrowRight')
        p.evaluate('editor.hass=h')
        title.press('X')
        self.assertEqual(title.input_value(),'aXbcd')
        self.assertEqual(p.evaluate('events.at(-1).unknown'),'keep')
        self.assertEqual(p.evaluate('calls'),[])

    def test_14_collapsed_card_surfaces_unwritable_parameters(self):
        self.page.evaluate("delete card.hass.states['number.tank_ph_low'];card.hass=card.hass")
        self.assertIn('參數無法儲存',self.page.locator('.quality').inner_text())
        self.assertFalse(self.page.locator('details').evaluate('(el)=>el.open'))

    def test_15_offline_demo_writes_only_simulated_memory(self):
        p=self.page
        requests=[]
        p.on('request',lambda request:requests.append(request.url))
        p.goto((ROOT/'demo'/'index.html').as_uri())
        self.assertIn('模擬資料 · 非即時系統',p.locator('h1').inner_text())
        p.locator('summary').click()
        p.locator('[data-param="ph_low"] input').fill('5.55')
        p.locator('[data-param="ph_low"] button').click()
        log=json.loads(p.locator('#log').inner_text())
        self.assertEqual(log,{'simulation':True,'domain':'number','service':'set_value','data':{'entity_id':'number.demo_ph_low','value':5.55}})
        p.locator('#scenario').select_option('active')
        self.assertTrue(p.locator('[data-param="ph_low"] button').is_disabled())
        self.assertEqual([url for url in requests if not url.startswith('file:')],[])

    def test_16_all_ten_parameters_target_their_own_number(self):
        p=self.page
        p.locator('summary').click()
        keys=['level_low','level_high','ph_low','ph_high','ec_low','ec_high','refill_timeout','ec_timeout','ph_timeout','mix_duration']
        values=[2.26,2.41,5.41,5.81,.81,.91,191,91,191,11]
        for key,value in zip(keys,values):
            row=p.locator(f'[data-param="{key}"]')
            row.locator('input').fill(str(value));row.locator('button').click()
        self.assertEqual(p.evaluate('calls'),[['number','set_value',{'entity_id':'number.tank_'+key,'value':value}] for key,value in zip(keys,values)])
        for state in ['within_range','out_of_range','invalid']:
            p.evaluate("state=>{card.hass.states['sensor.status'].state=state;card.hass.states['sensor.status'].attributes.ready_for_irrigation=true;card.hass.states['sensor.status'].attributes.reasons=['<svg onload=alert(1)>'];card.hass=card.hass}",state)
            self.assertIn('尚未提供灌溉許可',p.locator('.safety').inner_text())
            self.assertIn('不控制設備',p.locator('.safety').inner_text())
            self.assertEqual(p.locator('uninus-nutriculture-card svg').count(),0)
            self.assertIn('<svg onload=alert(1)>',p.locator('.quality').inner_text())

if __name__ == '__main__':
    unittest.main(verbosity=2)
