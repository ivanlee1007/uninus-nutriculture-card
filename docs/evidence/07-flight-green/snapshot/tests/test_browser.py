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

if __name__ == '__main__':
    unittest.main(verbosity=2)
