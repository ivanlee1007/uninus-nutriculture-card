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

if __name__ == '__main__':
    unittest.main(verbosity=2)
