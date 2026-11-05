"""Real shipped DOM/Chromium, frozen API fixture only; NOT native HA."""
import json
import os
from pathlib import Path
import subprocess
import unittest
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = """states=>{
 window.calls=[];window.writes=[];
 const entry=states['sensor.status'].attributes.settings_target.config_entry_id;
 window.dto={schema_version:1,config_entry_id:entry,catalog_revision:0,settings_revision:states['sensor.status'].attributes.settings_revision,recipes:[],last_applied:null,parameters_match:false,parameters:structuredClone(states['sensor.status'].attributes.parameters)};
 window.transport=async m=>{
 calls.push(structuredClone(m)); const d=m.service_data;
 if(m.service!=='get_recipes_v1'){
 if(d.expected_catalog_revision!==dto.catalog_revision) throw {code:'recipe_conflict'};
 if(m.service==='save_recipe_v1'){
 const r={id:d.recipe_id||'1234567890abcdef1234567890abcdef',name:d.name.trim(),parameters:structuredClone(d.parameters)};
 dto.recipes=dto.recipes.filter(x=>x.id!==r.id).concat(r);dto.catalog_revision++;writes.push(m.service);
 }else if(m.service==='delete_recipe_v1'){
 if(d.confirm_delete!==true)throw {code:'confirmation_required'};
 dto.recipes=dto.recipes.filter(r=>r.id!==d.recipe_id);dto.catalog_revision++;writes.push(m.service);
 }else if(m.service==='apply_recipe_v1'){
 if(d.expected_settings_revision!==dto.settings_revision)throw {code:'settings_conflict'};
 const r=dto.recipes.find(r=>r.id===d.recipe_id);dto.parameters=structuredClone(r.parameters);dto.last_applied={recipe_id:r.id,name:r.name,parameters:structuredClone(r.parameters)};dto.parameters_match=true;dto.catalog_revision++;dto.settings_revision++;writes.push(m.service);
 }}
 return {context:{id:'fixture'},response:structuredClone(dto)};
 };
 window.card=document.createElement('uninus-nutriculture-card');document.body.append(card);
 card.setConfig({entity:'sensor.status'});
 card.hass={states,services:{uninus_nutriculture:Object.fromEntries(['get_recipes_v1','save_recipe_v1','delete_recipe_v1','apply_recipe_v1'].map(k=>[k,{}]))},callWS:m=>transport(m),callService:()=>{throw Error('recipe must not use legacy writes')}};
}"""

class RecipeBrowserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pw=sync_playwright().start()
        options={'headless':True}
        if os.environ.get('CHROMIUM_EXECUTABLE'): options['executable_path']=os.environ['CHROMIUM_EXECUTABLE']
        cls.browser=cls.pw.chromium.launch(**options)
        print('BROWSER_VERSION='+cls.browser.version,flush=True)

    @classmethod
    def tearDownClass(cls):
        cls.browser.close();cls.pw.stop()

    def setUp(self):
        self.p=self.browser.new_page(viewport={'width':320,'height':1000})
        self.errors=[];self.p.on('pageerror',lambda e:self.errors.append(str(e)))
        self.p.set_default_timeout(1800)
        self.p.set_content('<!doctype html><meta charset="utf-8"><body style="margin:0;padding:8px">')
        self.p.add_script_tag(path=str(ROOT/'uninus-nutriculture-card.js'))
        states=json.loads(subprocess.check_output(['node','-e',"console.log(JSON.stringify(require('./tests/p3c_fixture.cjs')()))"],cwd=ROOT))
        self.p.evaluate(FIXTURE,states)

    def tearDown(self):
        self.p.close();self.assertEqual(self.errors,[])

    def open(self):
        self.p.locator('[data-recipe-panel] summary').click()
        self.p.wait_for_function("calls.some(m=>m.service==='get_recipes_v1')")

    def test_01_create_save_authoritative_catalog(self):
        self.open();p=self.p
        p.locator('[data-recipe-name]').fill('配方 A')
        p.locator('[data-recipe-save]').click()
        self.assertEqual(p.evaluate('dto.recipes.length'),1,'Save must persist a complete recipe through the versioned service')
        self.assertEqual(p.evaluate('dto.recipes[0].name'),'配方 A')
        self.assertEqual(len(p.evaluate('dto.recipes[0].parameters')),10)
        self.assertEqual(p.evaluate('writes'),['save_recipe_v1'])
        self.assertEqual(p.locator('[data-recipe-select] option').count(),2)
        self.assertEqual(p.evaluate('calls[0]'),{'type':'call_service','domain':'uninus_nutriculture','service':'get_recipes_v1','service_data':{'config_entry_id':p.evaluate('dto.config_entry_id')},'return_response':True})

    def test_02_select_edit_apply_cancel_delete_confirmation(self):
        self.open();p=self.p
        p.locator('[data-recipe-name]').fill('同名')
        p.locator('[data-recipe-parameter="mix_duration"]').fill('11')
        p.locator('[data-recipe-save]').click()
        p.locator('[data-recipe-select]').select_option('')
        self.assertEqual(p.locator('[data-recipe-name]').input_value(),'','Selecting New must discard saved record selection without writing')
        self.assertEqual(p.locator('[data-recipe-parameter="mix_duration"]').input_value(),'10')
        rid=p.evaluate('dto.recipes[0].id')
        p.locator('[data-recipe-select]').select_option(rid)
        self.assertEqual(p.locator('[data-recipe-parameter="mix_duration"]').input_value(),'11')
        p.locator('[data-recipe-name]').fill('取消草稿')
        p.locator('[data-recipe-cancel]').click()
        self.assertEqual(p.locator('[data-recipe-name]').input_value(),'同名')
        self.assertEqual(p.evaluate('writes'),['save_recipe_v1'])
        before=p.evaluate('structuredClone(card.hass.states)')
        p.locator('[data-recipe-apply]').click()
        self.assertEqual(p.evaluate('dto.parameters.mix_duration'),11)
        self.assertEqual(p.evaluate('card.hass.states'),before,'DTO must not fabricate hass state')
        apply=p.evaluate("calls.find(x=>x.service==='apply_recipe_v1').service_data")
        self.assertEqual(set(apply),{'config_entry_id','recipe_id','expected_catalog_revision','expected_settings_revision'})
        self.assertIn('歷史',p.locator('[data-recipe-history]').inner_text())
        p.locator('[data-recipe-delete]').click()
        self.assertEqual(p.evaluate('dto.recipes.length'),1)
        p.locator('[data-recipe-delete-cancel]').click()
        self.assertEqual(p.evaluate('dto.recipes.length'),1)
        p.locator('[data-recipe-delete]').click()
        p.locator('[data-recipe-delete-confirm]').press('Enter')
        self.assertEqual(p.evaluate('dto.recipes.length'),0)
        self.assertEqual(p.evaluate('calls.at(-1).service_data.confirm_delete'),True)

    def test_03_conflict_keeps_draft_and_no_automatic_retry(self):
        self.open();p=self.p
        p.locator('[data-recipe-name]').fill('CAS 草稿')
        p.evaluate('dto.catalog_revision++')
        p.locator('[data-recipe-save]').click()
        self.assertEqual(p.evaluate('writes'),[])
        self.assertEqual(p.locator('[data-recipe-name]').input_value(),'CAS 草稿')
        self.assertIn('衝突',p.locator('[data-recipe-message]').inner_text())
        self.assertEqual(p.evaluate('calls.length'),2)
        p.locator('[data-recipe-refresh]').click()
        self.assertEqual(p.locator('[data-recipe-name]').input_value(),'')

    def test_04_telemetry_keyboard_geometry_and_no_poll(self):
        self.open();p=self.p
        f=p.locator('[data-recipe-name]');f.focus();f.press('A')
        p.evaluate('window.original=card.recipeName;card.hass=card.hass;card.hass=card.hass')
        f.press('B')
        self.assertEqual(f.input_value(),'AB')
        self.assertTrue(p.evaluate('card.shadowRoot.activeElement===original && card.recipeName===original'))
        self.assertEqual(p.evaluate('calls.length'),1)
        bounds=p.locator('[data-recipe-panel] input,[data-recipe-panel] select,[data-recipe-panel] button:visible').evaluate_all('(els)=>els.map(e=>{const r=e.getBoundingClientRect();return [r.left,r.right]})')
        self.assertTrue(all(a>=0 and b<=320 for a,b in bounds),bounds)

    def test_05_closed_dto_rejects_wrong_target_and_fields(self):
        self.open();p=self.p
        p.locator('[data-recipe-name]').fill('保留草稿')
        p.evaluate("window.good=structuredClone(dto);dto.config_entry_id='entry-foreign'")
        p.locator('[data-recipe-refresh]').click()
        self.assertEqual(p.locator('[data-recipe-name]').input_value(),'保留草稿')
        for change in ["dto.schema_version=2","dto.catalog_revision=-1","dto.parameters.mix_duration=true","dto.recipes=[{id:'bad',name:'bad',parameters:dto.parameters}]","dto.last_applied={recipe_id:'1234567890abcdef1234567890abcdef',name:'x',parameters:dto.parameters};dto.parameters_match=false","dto.extra=1"]:
            p.evaluate('dto=structuredClone(good);'+change)
            p.locator('[data-recipe-refresh]').click()
            self.assertEqual(p.locator('[data-recipe-name]').input_value(),'保留草稿')
        self.assertEqual(p.evaluate('writes'),[])

    def test_06_late_success_and_error_do_not_touch_new_slot(self):
        self.open();p=self.p
        p.evaluate("()=>{window.old=structuredClone(dto);window.baseTransport=transport;transport=m=>new Promise((resolve,reject)=>{window.finish=resolve;window.fail=reject})}")
        p.locator('[data-recipe-name]').fill('old')
        p.locator('[data-recipe-save]').click()
        p.evaluate("const a=card.hass.states['sensor.status'].attributes;a.settings_target.config_entry_id='entry-b';a.flow_plan_target.config_entry_id='entry-b';dto.config_entry_id='entry-b';transport=baseTransport;card.hass=card.hass")
        self.open();p.locator('[data-recipe-name]').fill('new slot')
        p.evaluate('finish({response:old})')
        self.assertEqual(p.locator('[data-recipe-name]').input_value(),'new slot')
        p.evaluate("()=>{transport=m=>new Promise((resolve,reject)=>{window.fail=reject})}")
        p.locator('[data-recipe-save]').click()
        p.evaluate("const a=card.hass.states['sensor.status'].attributes;a.settings_target.config_entry_id='entry-c';a.flow_plan_target.config_entry_id='entry-c';dto.config_entry_id='entry-c';transport=baseTransport;card.hass=card.hass")
        self.open();p.locator('[data-recipe-name]').fill('C slot')
        p.evaluate("fail({code:'recipe_conflict',message:'PRIVATE DEBUG'})")
        self.assertEqual(p.locator('[data-recipe-name]').input_value(),'C slot')
        self.assertNotIn('PRIVATE',p.locator('[data-recipe-message]').inner_text())

    def test_07_disconnect_releases_ui_owner_not_old_transport(self):
        self.open();p=self.p
        p.evaluate("()=>{transport=m=>new Promise(resolve=>{window.finish=resolve})}")
        p.locator('[data-recipe-name]').fill('old')
        p.locator('[data-recipe-save]').click()
        p.evaluate('card.remove();document.body.append(card);finish({response:structuredClone(dto)})')
        p.evaluate('card.hass=card.hass')
        self.assertTrue(p.locator('[data-recipe-refresh]').is_enabled(),'Disconnected operation must not permanently own busy UI')
        self.assertEqual(p.locator('[data-recipe-name]').input_value(),'old')

    def test_08_missing_capability_keeps_legacy_controls(self):
        p=self.p
        p.evaluate("delete card.hass.services.uninus_nutriculture.apply_recipe_v1;card.hass=card.hass")
        self.assertTrue(p.locator('[data-recipe-panel]').is_hidden())
        self.assertGreater(p.locator('[data-control] button:visible').count(),0)
        self.assertEqual(p.evaluate('calls'),[])

    def test_09_same_names_stable_ids_safe_text_and_settings_cas(self):
        p=self.p
        p.evaluate("()=>{dto.recipes=['11111111111111111111111111111111','22222222222222222222222222222222'].map((id,i)=>({id,name:'<img src=x onerror=alert(1)>',parameters:{...dto.parameters,mix_duration:11+i}}))}")
        self.open()
        options=p.locator('[data-recipe-select] option').all_text_contents()
        self.assertIn('11111111111111111111111111111111',options[1])
        self.assertIn('22222222222222222222222222222222',options[2])
        self.assertEqual(p.locator('[data-recipe-panel] img').count(),0)
        p.locator('[data-recipe-select]').select_option('22222222222222222222222222222222')
        self.assertEqual(p.locator('[data-recipe-parameter="mix_duration"]').input_value(),'12')
        p.locator('[data-recipe-name]').fill('改名')
        p.locator('[data-recipe-save]').click()
        self.assertEqual(p.evaluate('calls.at(-1).service_data.recipe_id'),'22222222222222222222222222222222')
        p.evaluate('dto.settings_revision++')
        p.locator('[data-recipe-apply]').click()
        self.assertEqual(p.evaluate('writes'),['save_recipe_v1'])
        self.assertEqual(p.locator('[data-recipe-name]').input_value(),'改名')
        self.assertEqual(p.evaluate('calls.length'),3)
        p.evaluate("()=>{const r=dto.recipes[0];dto.last_applied={recipe_id:r.id,name:r.name,parameters:{...r.parameters,mix_duration:13}};dto.parameters_match=false}")
        p.locator('[data-recipe-refresh]').click()
        self.assertIn('與現值不同',p.locator('[data-recipe-history]').inner_text())

    def test_10_two_cards_catalog_cas_preserves_losing_draft(self):
        self.open();p=self.p
        p.evaluate("()=>{window.second=document.createElement('uninus-nutriculture-card');document.body.append(second);second.setConfig({entity:'sensor.status'});second.hass=card.hass;second.recipePanel.open=true}")
        p.wait_for_function('!!second.recipeData')
        first=p.locator('uninus-nutriculture-card').first
        other=p.locator('uninus-nutriculture-card').nth(1)
        first.locator('[data-recipe-name]').fill('winner')
        other.locator('[data-recipe-name]').fill('loser draft')
        first.locator('[data-recipe-save]').click()
        other.locator('[data-recipe-save]').click()
        self.assertEqual(p.evaluate('dto.recipes.length'),1)
        self.assertEqual(other.locator('[data-recipe-name]').input_value(),'loser draft')
        self.assertIn('衝突',other.locator('[data-recipe-message]').inner_text())
        self.assertEqual(p.evaluate('calls.length'),4)

    def test_11_nonnegative_but_regressed_revisions_rejected(self):
        self.open();p=self.p
        p.evaluate('dto.catalog_revision=5;dto.settings_revision=50')
        p.locator('[data-recipe-refresh]').click()
        p.locator('[data-recipe-name]').fill('保留版本草稿')
        p.evaluate('dto.catalog_revision=4')
        p.locator('[data-recipe-refresh]').click()
        self.assertEqual(p.locator('[data-recipe-name]').input_value(),'保留版本草稿')
        p.evaluate('dto.catalog_revision=5;dto.settings_revision=49')
        p.locator('[data-recipe-refresh]').click()
        self.assertEqual(p.locator('[data-recipe-name]').input_value(),'保留版本草稿')

    def test_12_unicode_80_catalog_edit_save_apply_delete(self):
        p=self.p
        names=['A'*80, '🌱'*80, '中'*40+'🌱'*40]
        ids=['1'*32,'2'*32,'3'*32]
        p.evaluate("([names,ids])=>{dto.recipes=names.map((name,i)=>({id:ids[i],name,parameters:structuredClone(dto.parameters)}));dto.last_applied={recipe_id:ids[1],name:names[1],parameters:structuredClone(dto.parameters)};dto.parameters_match=true}",[names,ids])
        self.open()
        p.wait_for_function('!card.recipeOperation')
        self.assertTrue(p.evaluate('!!card.recipeData'),'Every backend-valid 80-codepoint name must load the entire catalog')
        self.assertEqual(p.locator('[data-recipe-select] option').count(),4)
        self.assertIn(names[1],p.locator('[data-recipe-history]').inner_text())
        for name,rid in zip(names,ids):
            with self.subTest(name=name):
                p.locator('[data-recipe-select]').select_option(rid)
                self.assertEqual(p.locator('[data-recipe-name]').input_value(),name)
                p.locator('[data-recipe-name]').fill('temporary')
                p.locator('[data-recipe-name]').fill(name)
                self.assertEqual(p.locator('[data-recipe-name]').input_value(),name,'HTML input must not truncate astral80')
                self.assertTrue(p.locator('[data-recipe-save]').is_enabled())
                p.locator('[data-recipe-save]').click()
                self.assertEqual(p.evaluate('calls.at(-1).service_data.name'),name)
                self.assertTrue(p.evaluate('!!card.recipeData'))
                p.locator('[data-recipe-apply]').click()
                self.assertEqual(p.evaluate('dto.last_applied.name'),name)
                self.assertIn(name,p.locator('[data-recipe-history]').inner_text())
                p.locator('[data-recipe-delete]').click()
                p.locator('[data-recipe-delete-confirm]').click()
                self.assertTrue(p.evaluate('!!card.recipeData'),'Deleted record history must still accept Unicode80')
        self.assertEqual(p.evaluate('dto.recipes'),[])
        self.assertEqual(p.evaluate('writes'),['save_recipe_v1','apply_recipe_v1','delete_recipe_v1']*3)

    def test_13_unicode_80_81_draft_and_closed_dto_boundaries(self):
        self.open();p=self.p
        f=p.locator('[data-recipe-name]')
        for name in ['A'*80, '🌱'*80, '中'*40+'🌱'*40, 'e\u0301'*40]:
            with self.subTest(valid=name):
                f.fill(name)
                self.assertEqual(f.input_value(),name)
                self.assertTrue(p.locator('[data-recipe-save]').is_enabled())
        for name in ['A'*81, '🌱'*81, '中'*40+'🌱'*41]:
            with self.subTest(paste81=name):
                f.fill(name)
                self.assertEqual(f.input_value(),name,'Never silently truncate an invalid paste into a valid different name')
                self.assertTrue(p.locator('[data-recipe-save]').is_disabled())
                count=p.evaluate('calls.length')
                p.evaluate("card.recipeRequest('save_recipe_v1')")
                self.assertEqual(p.evaluate('calls.length'),count)
        for name in ['A'*81, '🌱'*81, '中'*40+'🌱'*41, 'e\u0301'*40+'x', 'bad\x00name', '   ']:
            with self.subTest(invalid=name):
                # DOM assignment exercises the draft guard even beyond HTML's code-unit cap.
                f.evaluate("(e,v)=>{e.value=v;e.dispatchEvent(new Event('input',{bubbles:true}))}",name)
                self.assertTrue(p.locator('[data-recipe-save]').is_disabled())
                count=p.evaluate('calls.length')
                p.evaluate("card.recipeRequest('save_recipe_v1')")
                self.assertEqual(p.evaluate('calls.length'),count,'Invalid draft must not send')
        for field in ['recipe','history']:
            for name in ['A'*81, '🌱'*81, '中'*40+'🌱'*41, 'bad\x00name', ' padded ']:
                with self.subTest(field=field,name=name):
                    p.evaluate("([field,name])=>{const r={id:'4'.repeat(32),name,parameters:structuredClone(dto.parameters)};dto.recipes=field==='recipe'?[r]:[];dto.last_applied=field==='history'?{recipe_id:r.id,name,parameters:r.parameters}:null;dto.parameters_match=field==='history'}",[field,name])
                    p.evaluate('window.before=card.recipeData')
                    p.locator('[data-recipe-refresh]').click()
                    p.wait_for_function('!card.recipeOperation')
                    self.assertTrue(p.evaluate('card.recipeData===before'),'Invalid DTO must stay whole-catalog fail closed')
        self.assertEqual(p.evaluate('writes'),[])

    def transport_settlement(self, settlement):
        self.open();p=self.p
        p.wait_for_function('!card.recipeOperation')
        p.locator('[data-recipe-name]').fill('reconnect draft 🌱')
        p.evaluate("void (transport=m=>{calls.push(structuredClone(m));return new Promise((resolve,reject)=>{window.finish=resolve;window.fail=reject})})")
        p.locator('[data-recipe-save]').click()
        p.evaluate("window.oldOp=card.recipeOperation;window.oldData=card.recipeData;window.newCalls=[];card.hass={...card.hass,callWS:async m=>{newCalls.push(structuredClone(m));return {response:structuredClone(dto)}}}")
        self.assertTrue(p.evaluate('card.recipeOperation===oldOp && card.recipeFlights.get(dto.config_entry_id)===oldOp'))
        for key in ['refresh','save','cancel']:
            self.assertTrue(p.locator('[data-recipe-'+key+']').is_disabled())
        p.evaluate("void card.recipeRequest('get_recipes_v1');void card.recipeRequest('save_recipe_v1')")
        self.assertEqual(p.evaluate('newCalls'),[],'Unsettled old transport retains same-entry lock')
        if settlement=='resolve':
            p.evaluate('finish({response:{...structuredClone(dto),catalog_revision:99}})')
        else:
            p.evaluate("fail({code:'recipe_conflict',message:'PRIVATE_RECONNECT'})")
        p.wait_for_function('card.recipeFlights.size===0')
        self.assertFalse(p.evaluate('!!card.recipeOperation'),'Settled obsolete op must release only its UI ownership')
        self.assertTrue(p.evaluate('card.recipeData===oldData && card.recipeDirty'))
        self.assertEqual(p.locator('[data-recipe-name]').input_value(),'reconnect draft 🌱')
        self.assertEqual(p.evaluate('card.recipeData.catalog_revision'),0)
        self.assertEqual(p.evaluate('newCalls'),[],'No automatic retry/read/mutation')
        self.assertEqual(p.evaluate('writes'),[])
        self.assertNotIn('PRIVATE',p.locator('[data-recipe-message]').inner_text())
        self.assertNotIn('衝突',p.locator('[data-recipe-message]').inner_text(),'Obsolete error must not be adopted')
        self.assertNotIn('已保存',p.locator('[data-recipe-message]').inner_text())
        for key in ['refresh','save','cancel']:
            self.assertTrue(p.locator('[data-recipe-'+key+']').is_enabled())
        p.locator('[data-recipe-refresh]').click()
        p.wait_for_function('newCalls.length===1 && !card.recipeOperation')
        self.assertEqual(p.evaluate('newCalls[0].service'),'get_recipes_v1')
        self.assertEqual(p.locator('[data-recipe-name]').input_value(),'')
        self.assertEqual(p.evaluate('writes'),[])

    def test_14_replaced_transport_resolve_releases_own_settled_ui(self):
        self.transport_settlement('resolve')

    def test_15_replaced_transport_reject_releases_own_settled_ui(self):
        self.transport_settlement('reject')

    def test_16_old_settlement_cannot_clear_new_slot_ui_or_pending_owner(self):
        p=self.p
        for pending in [False,True]:
            for settlement in ['resolve','reject']:
                with self.subTest(pending=pending,settlement=settlement):
                    if not p.evaluate('card.recipePanel.open'): self.open()
                    p.wait_for_function('!card.recipeOperation')
                    p.locator('[data-recipe-name]').fill('A draft')
                    p.evaluate("()=>{window.originalWS=card.hass.callWS;window.oldDTO=structuredClone(dto);transport=m=>{calls.push(structuredClone(m));return new Promise((resolve,reject)=>{window.oldFinish=resolve;window.oldFail=reject})}}")
                    p.locator('[data-recipe-save]').click()
                    p.evaluate("const a=card.hass.states['sensor.status'].attributes;const id='entry-'+Math.random();a.settings_target.config_entry_id=id;a.flow_plan_target.config_entry_id=id;dto.config_entry_id=id;card.hass={...card.hass,callWS:async m=>{calls.push(structuredClone(m));if(m.service==='get_recipes_v1')return {response:structuredClone(dto)};return new Promise(resolve=>{window.newFinish=resolve})}}")
                    self.open();p.wait_for_function('!card.recipeOperation')
                    p.locator('[data-recipe-name]').fill('B draft')
                    if pending:p.locator('[data-recipe-save]').click()
                    p.evaluate('window.bOp=card.recipeOperation;window.bNotice=card.recipeNotice;window.bData=card.recipeData;window.callCount=calls.length')
                    if settlement=='resolve':p.evaluate('oldFinish({response:oldDTO})')
                    else:p.evaluate("oldFail({code:'recipe_conflict',message:'PRIVATE_OLD_SLOT'})")
                    p.wait_for_function('!card.recipeFlights.has(oldDTO.config_entry_id)')
                    self.assertTrue(p.evaluate('card.recipeOperation===bOp && card.recipeNotice===bNotice && card.recipeData===bData'))
                    self.assertEqual(p.locator('[data-recipe-name]').input_value(),'B draft')
                    self.assertTrue(p.evaluate('calls.length===callCount'))
                    self.assertEqual(p.locator('[data-recipe-refresh]').is_disabled(),pending)
                    self.assertEqual(p.evaluate('card.recipeFlights.size'),int(pending))
                    if pending:
                        self.assertTrue(p.evaluate('card.recipeFlights.get(dto.config_entry_id)===bOp'))
                        p.evaluate('newFinish({response:structuredClone(dto)})')
                        p.wait_for_function('!card.recipeOperation')
                    p.evaluate('transport=async m=>{calls.push(structuredClone(m));return {response:structuredClone(dto)}};card.hass={...card.hass,callWS:m=>transport(m)}')
        self.assertEqual(p.evaluate('writes'),[])

if __name__=='__main__': unittest.main(verbosity=2)
