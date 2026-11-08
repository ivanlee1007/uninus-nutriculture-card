"""Real shipped Chromium; synthetic authenticated transport, NOT native Core proof.
Fixture eval executes only constant test-owned expressions below, never input/network data.
"""

import json
import os
import unittest
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = r"""() => {
window.calls=[];window.errors=[];addEventListener('unhandledrejection',e=>errors.push(String(e.reason)));
window.mapping={ph:'sensor.ph_a',ec:'sensor.ec_a',level:'sensor.level_a'};
window.user={id:'reader',is_admin:true,is_active:true};window.connection=new EventTarget();connection.connected=true;
window.response=m=>Object.fromEntries(m.entity_ids.map((id,i)=>[id,[{s:String([6.25,1.75,0.45][i]),a:{unit_of_measurement:['pH','mS/cm','m'][i]},lu:Date.parse(m.start_time)/1000+60},{s:String([6.5,1.8,0.5][i]),a:{unit_of_measurement:['pH','mS/cm','m'][i]},lu:Date.parse(m.end_time)/1000-60}]]));
window.transport=async m=>{calls.push(structuredClone(m));return response(m)};window.ws=m=>transport(m);
window.card=document.createElement('uninus-nutriculture-card');
window.publish=()=>{card.hass={user,connection,callWS:ws,callService:()=>{throw Error('MUTATION FORBIDDEN')},config:{time_zone:'Asia/Taipei'},states:{'sensor.tank':{state:'within_range',attributes:{schema_version:1,mode:'shadow',source_entities:structuredClone(mapping),settings_target:{config_entry_id:'entry-a'},epoch:'a'}}}}};
card.setConfig({entity:'sensor.tank',show_parameters:false});publish();document.body.append(card);
}"""


class HistoryBrowser(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pw = sync_playwright().start()
        cls.browser = cls.pw.chromium.launch(
            headless=True, executable_path=os.environ["CHROMIUM_EXECUTABLE"]
        )
        print("BROWSER_VERSION=" + cls.browser.version, flush=True)

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.pw.stop()

    def setUp(self):
        self.p = self.browser.new_page(viewport={"width": 390, "height": 950}, has_touch=True)
        self.errors = []
        self.p.on("pageerror", lambda e: self.errors.append(str(e)))
        self.p.set_default_timeout(1400)
        self.p.set_content('<meta charset="utf-8"><body style="margin:0">')
        self.p.add_script_tag(path=str(ROOT / "uninus-nutriculture-card.js"))
        self.p.evaluate(FIXTURE)

    def tearDown(self):
        try:
            self.assertEqual(self.errors, [])
            self.assertEqual(self.p.evaluate("errors"), [])
            self.assertTrue(
                self.p.evaluate('calls.every(m=>m.type==="history/history_during_period")'),
                "history path must never issue control/config writes",
            )
            if os.environ.get("BROWSER_EVIDENCE_DIR"):
                out = Path(os.environ["BROWSER_EVIDENCE_DIR"])
                out.mkdir(parents=True, exist_ok=True)
                (out / (self._testMethodName + ".json")).write_text(
                    json.dumps(
                        self.p.evaluate(
                            "({calls,errors,html:card.shadowRoot.innerHTML,metrics:Object.fromEntries(Object.entries(card.historyMetrics).map(([k,n])=>[k,n.points]))})"
                        ),
                        ensure_ascii=False,
                        indent=2,
                    ),
                    encoding="utf-8",
                )
        finally:
            self.p.close()

    def open(self):
        self.p.locator("[data-history-toggle]").click()
        self.p.wait_for_function("calls.length>0")
        self.p.wait_for_function("!card.historyOperation")

    def test_01_closed_then_native_read(self):
        p = self.p
        self.assertEqual(p.evaluate("calls"), [])
        self.assertEqual(
            p.locator("details[data-history-panel]").count(),
            1,
            "selected tank must expose closed history disclosure",
        )
        self.assertFalse(p.locator("[data-history-panel]").evaluate("e=>e.open"))
        self.open()
        m = p.evaluate("calls[0]")
        self.assertEqual(m["type"], "history/history_during_period")
        self.assertEqual(m["entity_ids"], ["sensor.ph_a", "sensor.ec_a", "sensor.level_a"])
        self.assertEqual(
            {
                k: m[k]
                for k in [
                    "include_start_time_state",
                    "significant_changes_only",
                    "minimal_response",
                    "no_attributes",
                ]
            },
            {
                "include_start_time_state": True,
                "significant_changes_only": False,
                "minimal_response": False,
                "no_attributes": False,
            },
        )
        self.assertEqual(
            p.evaluate("(Date.parse(calls[0].end_time)-Date.parse(calls[0].start_time))/3600000"), 1
        )
        self.assertIn("6.25", p.locator('[data-history-table="ph"]').inner_text())
        self.assertIn("mS/cm", p.locator('[data-history-table="ec"]').inner_text())
        self.assertIn("0.45", p.locator('[data-history-table="level"]').inner_text())
        self.assertEqual(len(p.evaluate("calls")), 1)

    def test_02_chart_keyboard_touch_window_continuity(self):
        self.open()
        p = self.p
        chart = p.locator('[data-history-plot="ph"]')
        self.assertEqual(chart.count(), 1, "real history plot must be present")
        chart.focus()
        p.keyboard.press("End")
        self.assertIn("6.5", p.locator('[data-history-active-point="ph"]').inner_text())
        p.keyboard.press("Home")
        self.assertIn("6.25", p.locator('[data-history-active-point="ph"]').inner_text())
        p.keyboard.press("ArrowRight")
        self.assertIn("6.5", p.locator('[data-history-active-point="ph"]').inner_text())
        chart.tap(position={"x": 25, "y": 50})
        self.assertIn("6.25", p.locator('[data-history-active-point="ph"]').inner_text())
        p.evaluate(
            'window.retained=card.shadowRoot.querySelector("[data-history-plot=ph]");publish()'
        )
        self.assertTrue(
            p.evaluate('retained===card.shadowRoot.querySelector("[data-history-plot=ph]")')
        )
        self.assertTrue(p.locator("[data-history-panel]").evaluate("e=>e.open"))
        self.assertEqual(p.evaluate("calls.length"), 1)
        for hours in ["6", "24"]:
            p.locator("[data-history-window]").select_option(hours)
            p.wait_for_function("!card.historyOperation")
            self.assertEqual(
                p.evaluate(
                    "(Date.parse(calls.at(-1).end_time)-Date.parse(calls.at(-1).start_time))/3600000"
                ),
                int(hours),
            )
        self.assertIn("Asia/Taipei", p.locator('[data-history-table="ph"]').inner_text())
        self.assertIn("GMT+08:00", p.locator('[data-history-table="ph"]').inner_text())
        for dark in [False, True]:
            p.set_viewport_size({"width": 320, "height": 950})
            p.evaluate(
                'dark=>document.body.style.cssText=dark?"margin:0;--primary-text-color:#eee;--card-background-color:#182329;--ha-card-background:#182329;background:#182329":"margin:0"',
                dark,
            )
            self.assertLessEqual(p.evaluate("document.documentElement.scrollWidth"), 320)
            if os.environ.get("BROWSER_EVIDENCE_DIR"):
                p.screenshot(
                    path=str(
                        Path(os.environ["BROWSER_EVIDENCE_DIR"])
                        / ("dark.png" if dark else "light.png")
                    ),
                    full_page=True,
                )

    def test_03_truthful_gaps_units_partial_boundary_and_duplicates(self):
        p = self.p
        p.evaluate(
            """response=m=>{const t=Date.parse(m.start_time)/1000;return {[mapping.ph]:[{s:'6',a:{unit_of_measurement:'pH'},lu:t-30},{s:'9',a:{unit_of_measurement:'pH'},lu:t+120},{s:'unknown',a:{unit_of_measurement:'pH'},lu:t+60},{s:'6.7',a:{unit_of_measurement:'pH'},lu:t+120},{s:'8',a:{unit_of_measurement:'wrong'},lu:t+180},{s:'Infinity',a:{},lu:t+240},{s:'99',a:{unit_of_measurement:'pH'},lu:Date.parse(m.end_time)/1000+1}], [mapping.level]:[]}};void 0"""
        )
        self.open()
        table = p.locator('[data-history-table="ph"]').inner_text()
        self.assertIn("缺值", table)
        self.assertNotIn("NaN", table)
        self.assertNotIn("Infinity", table)
        self.assertIn("6.7", table)
        self.assertNotIn("\t9\t", table)
        self.assertNotIn("\t99\t", table)
        self.assertIn("單位不相容", table)
        self.assertIn("窗口起始承接", table)
        self.assertIn("無可讀歷史資料", p.locator('[data-history-active-point="ec"]').inner_text())
        self.assertIn("部分", p.locator("[data-history-status]").inner_text())
        self.assertEqual(p.locator('[data-history-plot="ph"] circle').count(), 2)
        self.assertEqual(
            p.locator('[data-history-plot="ph"] path').get_attribute("d").count("M"), 2
        )
        self.assertIn("原始 7", p.locator("[data-history-status]").inner_text())
        self.assertIn("顯示 5", p.locator("[data-history-status]").inner_text())

    def test_04_scope_purge_and_late_reply_races(self):
        self.open()
        p = self.p
        changes = [
            'mapping.ph="sensor.ph_b";publish()',
            'user.id="other";publish()',
            "user.is_admin=false;publish()",
            "user.is_active=false;publish()",
            'connection.connected=false;connection.dispatchEvent(new Event("disconnected"))',
            "ws=m=>transport(m);publish()",
            "connection=new EventTarget();connection.connected=true;publish()",
            'card.setConfig({entity:"sensor.other"})',
            "card.remove();document.body.append(card)",
        ]
        for change in changes:
            with self.subTest(change=change):
                p.evaluate(
                    'user={id:"reader",is_admin:true,is_active:true};mapping={ph:"sensor.ph_a",ec:"sensor.ec_a",level:"sensor.level_a"};connection=new EventTarget();connection.connected=true;ws=m=>transport(m);card.setConfig({entity:"sensor.tank",show_parameters:false});publish();transport=async m=>{calls.push(m);return response(m)};void card.historyRequest()'
                )
                p.wait_for_function("!card.historyOperation")
                self.assertIn("6.25", p.locator('[data-history-table="ph"]').text_content())
                p.evaluate(
                    "transport=m=>{calls.push(m);window.oldMessage=m;return new Promise((resolve,reject)=>{window.finish=resolve;window.fail=reject})};void card.historyRequest()"
                )
                p.wait_for_function("!!window.finish")
                p.evaluate(change)
                self.assertNotIn(
                    "6.25",
                    p.locator('[data-history-table="ph"]').text_content(),
                    "must synchronously purge loaded truth",
                )
                p.evaluate("finish(response(oldMessage));delete window.finish;void 0")
                p.wait_for_timeout(20)
                self.assertNotIn(
                    "6.25",
                    p.locator('[data-history-table="ph"]').text_content(),
                    "old success must not restore scoped data",
                )
        p.evaluate(
            'user={id:"reader",is_admin:true,is_active:true};card.setConfig({entity:"sensor.tank",show_parameters:false});publish();transport=m=>{calls.push(m);(window.flights??=[]).push({m});return new Promise((resolve,reject)=>Object.assign(flights.at(-1),{resolve,reject}))};void card.historyRequest()'
        )
        p.wait_for_function("flights?.length===1")
        p.locator("[data-history-window]").select_option("6")
        p.wait_for_function("flights.length===2")
        p.evaluate("flights[1].resolve(response(flights[1].m));void 0")
        p.wait_for_function("!card.historyOperation")
        p.evaluate('flights[0].reject({code:"unauthorized"});void 0')
        p.wait_for_timeout(20)
        self.assertIn("6.25", p.locator('[data-history-table="ph"]').text_content())
        self.assertEqual(p.locator("[data-history-error]").text_content(), "")

    def test_05_timeout_and_feature_local_errors(self):
        self.open()
        p = self.p
        p.clock.install()
        p.evaluate(
            "transport=m=>{calls.push(m);return new Promise(resolve=>window.late=()=>resolve(response(m)))};void card.historyRequest()"
        )
        p.wait_for_function("!!window.late")
        p.clock.fast_forward(20001)
        self.assertIn("逾時", p.locator("[data-history-error]").text_content())
        self.assertFalse(p.evaluate("!!card.historyOperation"))
        p.evaluate("late();void 0")
        p.wait_for_timeout(10)
        self.assertNotIn("6.25", p.locator('[data-history-table="ph"]').text_content())
        for code, label in [
            ("unknown_command", "不支援"),
            ("cannot_connect", "連線"),
            ("invalid_history", "格式"),
            ("unauthorized", "權限"),
        ]:
            p.evaluate(
                'code=>{ws=m=>transport(m);publish();transport=async m=>{calls.push(m);throw {code,message:"SECRET"}};void card.historyRequest()}',
                code,
            )
            p.wait_for_function("!card.historyOperation")
            self.assertIn(label, p.locator("[data-history-error]").text_content())
            self.assertNotIn("SECRET", p.locator("[data-history-panel]").text_content())
        before = p.evaluate("calls.length")
        p.evaluate("void card.historyRequest()")
        self.assertEqual(p.evaluate("calls.length"), before, "denied scope cannot retry")
        self.assertIn("不控制設備", p.locator(".safety").text_content())

    def test_06_boundary_sample_and_numeric_geometry_are_truthful(self):
        p = self.p
        p.evaluate(
            'response=m=>({[mapping.ph]:[{s:"1e308",a:{unit_of_measurement:"pH"},lu:Date.parse(m.start_time)/1000},{s:"-1e308",a:{unit_of_measurement:"pH"},lu:Date.parse(m.end_time)/1000}]});void 0'
        )
        self.open()
        self.assertIn(
            "窗口起始",
            p.locator('[data-history-table="ph"]').inner_text(),
            "exact boundary row is not evidence of fresh sampling",
        )
        self.assertNotIn("NaN", p.locator('[data-history-plot="ph"]').inner_html())
        self.assertNotIn("Infinity", p.locator('[data-history-plot="ph"]').inner_html())
        self.assertIn("pH", p.locator('[data-history-plot="ph"]').text_content())

    def test_07_initialization_open_intent_and_closed_cancellation(self):
        p = self.p
        p.evaluate(
            'card.remove();card=document.createElement("uninus-nutriculture-card");document.body.append(card);window.toggleSeen=false;card.historyPanel.addEventListener("toggle",()=>window.toggleSeen=true,{once:true})'
        )
        p.locator("[data-history-toggle]").click()
        p.wait_for_function("toggleSeen")
        self.assertEqual(p.evaluate("calls"), [])
        p.evaluate('publish();card.setConfig({entity:"sensor.tank",show_parameters:false});void 0')
        p.wait_for_timeout(30)
        self.assertEqual(
            p.evaluate("calls.length"), 1, "one open intent must drain after hass/config readiness"
        )
        p.wait_for_function("!card.historyOperation")
        self.assertIn("6.25", p.locator('[data-history-table="ph"]').text_content())
        p.evaluate(
            "transport=m=>{calls.push(m);return new Promise(resolve=>window.closeLate=()=>resolve(response(m)))};void card.historyRequest()"
        )
        p.wait_for_function("!!window.closeLate")
        p.locator("[data-history-toggle]").click()
        p.evaluate("closeLate();void 0")
        p.wait_for_timeout(20)
        self.assertNotIn("6.25", p.locator('[data-history-table="ph"]').text_content())
        self.assertFalse(p.evaluate("!!card.historyOperation"))
        p.clock.install()
        p.clock.fast_forward(60000)
        self.assertEqual(p.evaluate("calls.length"), 2, "no polling or late timeout requery")

    def test_08_malformed_relevant_shape_is_not_empty(self):
        p = self.p
        p.evaluate("response=m=>({[mapping.ph]:null});void 0")
        self.open()
        self.assertIn(
            "格式",
            p.locator("[data-history-error]").text_content(),
            "null relevant array must be rejected, not labeled empty",
        )
        cases = [
            "({evil:[]})",
            "[]",
            "null",
            "({[mapping.ph]:[{s:6,a:{},lu:1}]})",
            '({[mapping.ph]:[{s:"6",a:{},lu:"1"}]})',
            '({[mapping.ph]:[{s:"6",a:[],lu:1}]})',
            '({[mapping.ph]:[{s:"6",a:{unit_of_measurement:{}},lu:1}]})',
        ]
        for expr in cases:
            p.evaluate("expr=>{response=m=>eval(expr);void card.historyRequest()}", expr)
            p.wait_for_function("!card.historyOperation")
            self.assertIn("格式", p.locator("[data-history-error]").text_content(), expr)
            self.assertEqual(p.locator('[data-history-plot="ph"] circle').count(), 0)

    def test_09_supplementary_bounds_empty_flat_and_timezone(self):
        # Supplementary probes of already implemented contracts; not claimed as RED.
        self.open()
        p = self.p
        p.evaluate("response=m=>({});void card.historyRequest()")
        p.wait_for_function("!card.historyOperation")
        self.assertIn("無可讀歷史資料", p.locator("[data-history-status]").text_content())
        for count, label in [(240, None), (241, None), (10001, "格式")]:
            p.evaluate(
                'count=>{response=m=>({[mapping.ph]:Array.from({length:count},(_,i)=>({s:"6",a:{unit_of_measurement:"pH"},lu:Date.parse(m.start_time)/1000+i}))});void card.historyRequest()}',
                count,
            )
            p.wait_for_function("!card.historyOperation")
            if label:
                self.assertIn(label, p.locator("[data-history-error]").text_content())
                self.assertEqual(p.locator('[data-history-plot="ph"] circle').count(), 0)
            else:
                if count == 240:
                    self.assertEqual(p.locator('[data-history-plot="ph"] circle').count(), 240)
                else:
                    self.assertGreater(p.locator('[data-history-plot="ph"] circle').count(), 0)
                    self.assertLessEqual(p.locator('[data-history-plot="ph"] circle').count(), 240)
                    self.assertIn("代表抽樣", p.locator("[data-history-status]").text_content())
                    self.assertIn(
                        "ph 原始 241 / 正規化 241",
                        p.locator("[data-history-status]").text_content(),
                    )
                self.assertNotIn("NaN", p.locator('[data-history-plot="ph"]').inner_html())
                self.assertEqual(p.locator('[data-history-panel] [tabindex="0"]').count(), 3)
        p.evaluate(
            'response=m=>({[mapping.ph]:[{s:"6",a:{},lu:Date.parse(m.end_time)/1000-10}]});void card.historyRequest()'
        )
        p.wait_for_function("!card.historyOperation")
        self.assertEqual(p.locator('[data-history-plot="ph"] circle').count(), 1)
        stamps = p.evaluate(
            """() => {card.hass.config.time_zone='America/New_York';return [card.historyTime(Date.parse('2026-11-01T05:30:00Z')),card.historyTime(Date.parse('2026-11-01T06:30:00Z'))]}"""
        )
        self.assertIn("GMT-04:00", stamps[0])
        self.assertIn("GMT-05:00", stamps[1])
        self.assertIn(
            "回退 UTC",
            p.evaluate(
                """() => {card.hass.config.time_zone='INVALID';return card.historyTime(Date.now())}"""
            ),
        )

    def test_10_supplementary_loaded_purge_and_equivalent_continuity(self):
        self.open()
        p = self.p
        chart = p.locator('[data-history-plot="ph"]')
        chart.focus()
        p.keyboard.press("End")
        p.evaluate(
            'window.node=card.shadowRoot.querySelector("[data-history-plot=ph]");window.panel=card.historyPanel;window.point=card.historyMetrics.ph.points[1];publish();card.setConfig({...card.config})'
        )
        self.assertTrue(
            p.evaluate(
                "node===card.shadowRoot.activeElement&&panel===card.historyPanel&&point===card.historyMetrics.ph.points[1]"
            )
        )
        self.assertEqual(p.evaluate("calls.length"), 1)
        changes = [
            "user.is_admin=false;publish()",
            "delete user.id;publish()",
            'mapping.level="sensor.level_new";publish()',
            'card.hass.states["sensor.tank"].attributes.epoch="new";card.hass=card.hass',
            'card.hass.states["sensor.tank"].attributes.settings_target.config_entry_id="entry-b";card.hass=card.hass',
            'card.hass.states["sensor.ph_a"]={attributes:{unit_of_measurement:"other"}};card.hass=card.hass',
        ]
        for change in changes:
            p.evaluate(
                'user={id:"reader",is_admin:true,is_active:true};mapping={ph:"sensor.ph_a",ec:"sensor.ec_a",level:"sensor.level_a"};publish();void card.historyRequest()'
            )
            p.wait_for_function("!card.historyOperation")
            self.assertIn("6.25", p.locator('[data-history-table="ph"]').text_content())
            before = p.evaluate("calls.length")
            p.evaluate(change)
            self.assertEqual(p.evaluate("calls.length"), before)
            self.assertNotIn("6.25", p.locator('[data-history-table="ph"]').text_content())

    def test_11_supplementary_initialization_permutations(self):
        p = self.p
        for sequence in [
            'publish();card.setConfig({entity:"sensor.tank"});document.body.append(card)',
            'card.setConfig({entity:"sensor.tank"});publish();document.body.append(card)',
            'document.body.append(card);publish();card.setConfig({entity:"sensor.tank"})',
            'document.body.append(card);card.setConfig({entity:"sensor.tank"});publish()',
        ]:
            p.evaluate(
                'sequence=>{card.remove();calls=[];card=document.createElement("uninus-nutriculture-card");eval(sequence)}',
                sequence,
            )
            p.wait_for_timeout(25)
            self.assertEqual(p.evaluate("calls"), [])
            self.assertFalse(p.evaluate("card.historyPanel.open"))
            self.open()
            self.assertEqual(p.evaluate("calls.length"), 1)

    def test_12_deduplicated_mapping_counts_and_refusal_counts(self):
        p = self.p
        p.evaluate(
            'mapping={ph:"sensor.shared",ec:"sensor.shared",level:"sensor.shared"};publish();void 0'
        )
        self.open()
        self.assertEqual(p.evaluate("calls[0].entity_ids"), ["sensor.shared"])
        self.assertIn(
            "原始 2",
            p.locator("[data-history-status]").text_content(),
            "raw counts must count native source rows once",
        )
        p.evaluate(
            'response=m=>({[mapping.ph]:Array.from({length:241},(_,i)=>({s:"6",a:{unit_of_measurement:"pH"},lu:Date.parse(m.start_time)/1000+i}))});void card.historyRequest()'
        )
        p.wait_for_function("!card.historyOperation")
        self.assertIn("原始 241", p.locator("[data-history-status]").text_content())
        displayed = p.evaluate(
            "Object.values(card.historyMetrics).reduce((n,s)=>n+s.points.length,0)"
        )
        self.assertGreater(displayed, 0)
        self.assertIn(f"顯示 {displayed}", p.locator("[data-history-status]").text_content())
        self.assertIn("代表抽樣", p.locator("[data-history-status]").text_content())
        for key in ["ph", "ec", "level"]:
            count = p.evaluate("key=>card.historyMetrics[key].points.length", key)
            self.assertLessEqual(count, 240)
            self.assertIn(
                f"{key} 原始 241 / 正規化 241 / 顯示 {count}",
                p.locator("[data-history-status]").text_content(),
            )
        self.assertEqual(p.locator("[data-history-error]").text_content(), "")

    def test_16_supplementary_dense_fidelity_and_full_input_capacity(self):
        # Already-green boundary/oracle coverage, not additional behavioral RED.
        self.open()
        p = self.p
        facts = p.evaluate("""() => {
          const start=Date.parse('2026-11-01T05:00:00Z'),end=start+86400000;
          const ids=Object.values(mapping),units=['pH','mS/cm','m'];
          const rows=(n,j)=>Array.from({length:n},(_,i)=>({s:String(i===71?-1e308:i===357?1e308:6+Math.sin(i)),a:{unit_of_measurement:units[j]},lu:(start+1000+i*8000)/1000}));
          const input=Object.fromEntries(ids.map((id,j)=>[id,rows(10000,j)]));
          const full=card.historyDecode(input,ids,mapping,start,end);
          const f={raw:full.raw,shown:full.shown,counts:full.counts,finite:true,deterministic:true,fidelity:true,sparse:true};
          for(const key of ['ph','ec','level']){const pts=full.series[key];f.finite&&=pts.length>0&&pts.length<=240&&pts.some(p=>p.value===-1e308)&&pts.some(p=>p.value===1e308);}
          for(const n of [0,1,2,240]){const a=rows(n,0);const d=card.historyDecode({[mapping.ph]:a},ids,mapping,start,end);f.sparse&&=d.series.ph.length===n&&d.series.ph.every((p,i)=>p.value===Number(a[i].s)&&p.t===a[i].lu*1000);}
          for(const variant of ['mixed','flat','allgap']){
            const a=rows(900,0);
            for(let i=0;i<a.length;i++){
              if(variant==='flat')a[i].s='6';
              if(variant==='allgap'||(i>=200&&i<=260)||(i>=600&&i<=630))a[i].s='unknown';
              if(variant==='mixed'&&i>=240&&i<=260){a[i].s='99';a[i].a.unit_of_measurement='wrong';}
            }
            const d=card.historyDecode({[mapping.ph]:a},ids,mapping,start,end),pts=d.series.ph;
            const again=card.historyDecode({[mapping.ph]:a},ids,mapping,start,end).series.ph;
            f.deterministic&&=JSON.stringify(pts)===JSON.stringify(again);
            const raw=a.map(r=>({t:r.lu*1000,value:r.s==='unknown'||r.a.unit_of_measurement==='wrong'?null:Number(r.s),unit:r.a.unit_of_measurement}));
            const retained=i=>pts.some(p=>p.t===raw[i].t&&p.value===raw[i].value&&p.unit===raw[i].unit);
            f.fidelity&&=pts.length<=240&&retained(0)&&retained(raw.length-1)&&pts.every(p=>raw.some(r=>r.t===p.t&&r.value===p.value&&r.unit===p.unit));
            let begin=0;
            while(begin<raw.length){let stop=begin;const gap=raw[begin].value===null;while(stop+1<raw.length&&(raw[stop+1].value===null)===gap)stop++;
              f.fidelity&&=retained(begin)&&retained(stop);
              if(!gap){const seg=raw.slice(begin,stop+1).map(p=>p.value);f.fidelity&&=pts.some(p=>p.t>=raw[begin].t&&p.t<=raw[stop].t&&p.value===Math.min(...seg))&&pts.some(p=>p.t>=raw[begin].t&&p.t<=raw[stop].t&&p.value===Math.max(...seg));}
              begin=stop+1;
            }
            for(let i=1;i<raw.length;i++)if(raw[i].unit!==raw[i-1].unit)f.fidelity&&=retained(i-1)&&retained(i);
          }
          // Render a dense mixed response through the real request/DOM path below.
          response=m=>{const t=Date.parse(m.start_time)/1000;return {[mapping.ph]:Array.from({length:900},(_,i)=>({s:i>=200&&i<=260?'unknown':String(i===71?-1e308:i===357?1e308:6),a:{unit_of_measurement:i>=240&&i<=260?'wrong':'pH'},lu:t+i})),[mapping.ec]:[],[mapping.level]:[]};};
          return f;
        }""")
        self.assertTrue(
            p.evaluate("""() => {
            const start=0,end=86400000,ids=Object.values(mapping);
            const a=Array.from({length:481},(_,i)=>({s:'unknown',a:{unit_of_measurement:i%2?'wrong':'pH'},lu:i+1}));
            const d=card.historyDecode({[mapping.ph]:a},ids,mapping,start,end);
            return d.refused.includes('ph')&&d.series.ph.length===0&&d.counts.ph.raw===481;
        }""")
        )
        self.assertEqual(facts["raw"], 30000)
        self.assertLessEqual(facts["shown"], 720)
        for key in ["ph", "ec", "level"]:
            self.assertEqual(facts["counts"][key]["raw"], 10000)
            self.assertLessEqual(facts["counts"][key]["shown"], 240)
        for key in ["finite", "deterministic", "fidelity", "sparse"]:
            self.assertTrue(facts[key], key)
        p.evaluate("void card.historyRequest()")
        p.wait_for_function("!card.historyOperation")
        self.assertEqual(p.locator("[data-history-plot=ph] path").get_attribute("d").count("M"), 2)
        self.assertIn("單位不相容", p.locator("[data-history-table=ph]").text_content())
        self.assertTrue(
            p.evaluate(
                """() => {const pts=card.historyMetrics.ph.points;return pts.every((p,i)=>!i||p.t>pts[i-1].t)&&card.historyMetrics.ph.table.querySelectorAll('td').length===pts.length*4;}"""
            )
        )
        self.assertNotIn("NaN", p.locator("[data-history-plot=ph]").inner_html())
        self.assertNotIn("Infinity", p.locator("[data-history-plot=ph]").inner_html())
        self.assertEqual(p.locator("[data-history-error]").text_content(), "")

    def test_15_unrepresentable_gaps_refuse_only_affected_metric(self):
        p = self.p
        p.evaluate(
            """response=m=>Object.fromEntries(m.entity_ids.map((id,j)=>[id,Array.from({length:j===0?481:3},(_,i)=>({s:j===0&&i%2?'unknown':String(j===0?6:j===1?1.5:0.4),a:{unit_of_measurement:['pH','mS/cm','m'][j]},lu:Date.parse(m.start_time)/1000+i}))]));void 0"""
        )
        self.open()
        self.assertEqual(p.evaluate("card.historyMetrics.ec.points.length"), 3)
        self.assertEqual(p.evaluate("card.historyMetrics.level.points.length"), 3)
        self.assertEqual(p.evaluate("card.historyMetrics.ph.points.length"), 0)
        self.assertIn("ph", p.locator("[data-history-error]").text_content())
        self.assertIn("拒絕", p.locator("[data-history-active-point=ph]").text_content())
        self.assertIn(
            "ph 原始 481 / 正規化 481 / 顯示 0", p.locator("[data-history-status]").text_content()
        )
        self.assertIn("原始 487 / 顯示 6", p.locator("[data-history-status]").text_content())
        self.assertIn("1.5", p.locator("[data-history-table=ec]").text_content())
        p.evaluate(
            """transport=m=>{calls.push(m);return new Promise(resolve=>window.lateDense=()=>resolve(response(m)))};void card.historyRequest()"""
        )
        p.wait_for_function("!!window.lateDense")
        p.evaluate("mapping.ph='sensor.rebound';publish();lateDense();void 0")
        p.wait_for_timeout(20)
        self.assertTrue(
            p.evaluate("Object.values(card.historyMetrics).every(n=>n.points.length===0)")
        )
        self.assertEqual(p.locator("[data-history-error]").text_content(), "")

    def test_14_dense_normal_windows_and_maximum_safe_counts(self):
        p = self.p
        self.open()
        for hours, count in [("6", 361), ("24", 1441), ("24", 10000)]:
            with self.subTest(hours=hours, count=count):
                p.evaluate(
                    """count=>{response=m=>Object.fromEntries(m.entity_ids.map((id,j)=>[id,Array.from({length:j===0?count:3},(_,i)=>({s:String(j===0?6+Math.sin(i/20):j===1?1.2+i/10:0.4+i/100),a:{unit_of_measurement:['pH','mS/cm','m'][j]},lu:Date.parse(m.start_time)/1000+i*(Date.parse(m.end_time)-Date.parse(m.start_time))/1000/((j===0?count:3)-1)}))]));}""",
                    count,
                )
                p.locator("[data-history-window]").select_option(hours)
                p.evaluate("void card.historyRequest()")
                p.wait_for_function("!card.historyOperation")
                points = p.evaluate(
                    "Object.fromEntries(Object.entries(card.historyMetrics).map(([k,n])=>[k,n.points]))"
                )
                self.assertGreater(len(points["ph"]), 0)
                self.assertLessEqual(len(points["ph"]), 240)
                self.assertEqual(len(points["ec"]), 3)
                self.assertEqual(len(points["level"]), 3)
                self.assertIn(
                    f"原始 {count + 6}", p.locator("[data-history-status]").text_content()
                )
                self.assertIn("代表抽樣", p.locator("[data-history-status]").text_content())
                self.assertEqual(p.locator("[data-history-error]").text_content(), "")
                self.assertTrue(
                    p.evaluate(
                        """count=>{const m=calls.at(-1),all=response(m)[mapping.ph],pts=card.historyMetrics.ph.points;return pts.every(p=>all.some(r=>r.lu*1000===p.t&&Number(r.s)===p.value))&&pts[0].t===all[0].lu*1000&&pts.at(-1).t===all.at(-1).lu*1000&&Math.min(...pts.map(p=>p.value))===Math.min(...all.map(r=>Number(r.s)))&&Math.max(...pts.map(p=>p.value))===Math.max(...all.map(r=>Number(r.s)));}""",
                        count,
                    )
                )

    def test_13_supplementary_two_same_name_tanks_new_flight_survives_old(self):
        self.open()
        p = self.p
        p.evaluate(
            """window.publishBoth=()=>{publish();const h=card.hass;h.states['sensor.tank'].attributes.friendly_name='同名槽';h.states['sensor.tank_b']={state:'within_range',attributes:{...h.states['sensor.tank'].attributes,friendly_name:'同名槽',settings_target:{config_entry_id:'entry-b'},source_entities:{ph:'sensor.ph_b',ec:'sensor.ec_b',level:'sensor.level_b'}}};card.hass=h};transport=m=>{calls.push(m);(window.held??=[]).push({m});return new Promise((resolve,reject)=>Object.assign(held.at(-1),{resolve,reject}))};void card.historyRequest()"""
        )
        p.wait_for_function("held.length===1")
        p.evaluate(
            'publishBoth();card.setConfig({entity:"sensor.tank_b",show_parameters:false});void card.historyRequest()'
        )
        p.wait_for_function("held.length===2")
        self.assertEqual(
            p.evaluate("held[1].m.entity_ids"), ["sensor.ph_b", "sensor.ec_b", "sensor.level_b"]
        )
        p.evaluate("window.newOp=card.historyOperation;held[0].resolve(response(held[0].m));void 0")
        p.wait_for_timeout(20)
        self.assertTrue(p.evaluate("card.historyOperation===newOp"))
        self.assertNotIn("6.25", p.locator('[data-history-table="ph"]').text_content())
        p.evaluate(
            'const b=response(held[1].m);b["sensor.ph_b"][0].s="7.75";held[1].resolve(b);void 0'
        )
        p.wait_for_function("!card.historyOperation")
        self.assertIn("7.75", p.locator('[data-history-table="ph"]').text_content())
        self.assertNotIn("6.25", p.locator('[data-history-table="ph"]').text_content())
        before = p.evaluate("calls.length")
        p.clock.install()
        p.clock.fast_forward(60000)
        self.assertEqual(p.evaluate("calls.length"), before)
        self.assertEqual(p.locator("[data-history-error]").text_content(), "")


if __name__ == "__main__":
    unittest.main(verbosity=2)
