"""Shipping Chromium UI contracts; synthetic transport, not native/physical proof."""

import json
import os
import subprocess
import unittest
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
NODE = os.environ.get("NODE", "C:/Program Files/nodejs/node.exe")
FIXTURE = """states => {
window.states=states;window.calls=[];window.errors=[];
addEventListener('unhandledrejection',e=>errors.push(String(e.reason)));
window.user={id:'reader',is_admin:true,is_active:true};
window.connection=new EventTarget();connection.connected=true;
window.response=m=>{const t=Date.parse(m.start_time)/1000,a=structuredClone(states['sensor.status'].attributes);const b=structuredClone(a);b.stage_states.refill='running';b.step_runtime.refill.phase='refilling';b.output_states.refill='on';return {'sensor.status':[{s:'idle',a,lu:t-10},{s:'idle',a:b,lu:t+60}]}};
window.transport=async m=>{calls.push(structuredClone(m));if(m.type!=='history/history_during_period')throw {code:'unknown_command'};return response(m)};
window.ws=m=>transport(m);window.card=document.createElement('uninus-nutriculture-card');
card.setConfig({entity:'sensor.status',show_parameters:false});
window.publish=()=>{card.hass={states,user,connection,callWS:ws,callService:()=>{throw Error('FORBIDDEN MUTATION')},config:{time_zone:'Asia/Taipei'}}};
publish();document.body.append(card);
}"""


class RuntimeBrowser(unittest.TestCase):
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
        self.p = self.browser.new_page(viewport={"width": 360, "height": 800})
        self.errors = []
        self.p.on("pageerror", lambda e: self.errors.append(str(e)))
        self.p.set_default_timeout(1800)
        self.p.set_content(
            '<!doctype html><meta charset="utf-8"><body style="margin:0">'
        )
        self.p.add_script_tag(path=str(ROOT / "uninus-nutriculture-card.js"))
        states = json.loads(
            subprocess.check_output(
                [
                    NODE,
                    "-e",
                    "console.log(JSON.stringify(require('./tests/p3c_fixture.cjs')()))",
                ],
                cwd=ROOT,
            )
        )
        self.p.evaluate(FIXTURE, states)

    def tearDown(self):
        try:
            self.assertEqual(self.errors, [])
            self.assertEqual(self.p.evaluate("errors"), [])
            if os.environ.get("BROWSER_EVIDENCE_DIR"):
                out = Path(os.environ["BROWSER_EVIDENCE_DIR"])
                out.mkdir(parents=True, exist_ok=True)
                (out / (self._testMethodName + ".json")).write_text(
                    json.dumps(
                        self.p.evaluate("({calls,html:card.shadowRoot.innerHTML})"),
                        ensure_ascii=False,
                        indent=2,
                    ),
                    encoding="utf-8",
                )
        finally:
            self.p.close()

    def open_trace(self):
        self.p.locator("[data-trace-toggle]").click()
        self.p.wait_for_function(
            "calls.some(m=>m.type==='history/history_during_period')"
        )
        self.p.wait_for_function("!card.traceOperation")

    def test_03_trace_closed_read_baseline_observed_transition(self):
        p = self.p
        self.assertEqual(
            p.locator("[data-trace-panel]").count(),
            1,
            "recorded trace must have separate disclosure",
        )
        self.assertFalse(p.locator("[data-trace-panel]").evaluate("e=>e.open"))
        self.assertEqual(p.evaluate("calls"), [])
        self.open_trace()
        m = p.evaluate("calls[0]")
        self.assertEqual(m["entity_ids"], ["sensor.status"])
        for key, value in {
            "include_start_time_state": True,
            "significant_changes_only": False,
            "minimal_response": False,
            "no_attributes": False,
        }.items():
            self.assertEqual(m[key], value)
        trace = p.locator("[data-trace-list]").inner_text()
        for value in [
            "baseline",
            "running",
            "refilling",
            "on",
            "Asia/Taipei",
            "GMT+08:00",
        ]:
            self.assertIn(value, trace)
        self.assertIn("品質", p.locator("[data-trace-status]").inner_text())
        self.assertIn("結果", p.locator("[data-trace-status]").inner_text())
        p.evaluate("publish();publish()")
        self.assertEqual(p.evaluate("calls.length"), 1)
        self.assertEqual(p.locator("[data-history-panel]").count(), 1)

    def test_04_optional_same_entry_strict_historical_only(self):
        p = self.p
        p.evaluate("""() => {
const entry=states['sensor.status'].attributes.settings_target.config_entry_id;
window.q={schema_version:1,config_entry_id:entry,epoch:'a'.repeat(32),observation_revision:1,policy_revision:0,settings_revision:0,flow_plan_revision:0,policy:{enabled:false,stable_samples:8,stable_interval_seconds:300,stable_duration_seconds:2100,permit_ttl_seconds:300,required_stages:['refill','nutrient','acid','mix'],sources:Object.fromEntries(['ph','ec','level'].map(k=>[k,{mode:'reported',attribute:null,report_contract_confirmed:false}]))},entities:{quality_status:'sensor.quality_selected',irrigation_permit:'binary_sensor.permit_selected'},quality:{state:'qualified',stable_count:8,stable_since:'2026-11-05T00:00:00Z',reasons:[]},completion:{state:'completed',run_id:'run',settled_at:'2026-11-05T00:00:00Z'},permit:{granted:false,run_id:null,expires_at:null,reasons:['no_current_run']}};
window.r={schema_version:1,config_entry_id:entry,epoch:'a'.repeat(32),observation_revision:0,support:'supported',current_run:null,last_result:null,latest_event:null};
states['sensor.quality_selected']={state:'qualified',attributes:q};states['sensor.result_selected']={state:'idle',attributes:r};
card.setConfig({entity:'sensor.status',quality_entity:'sensor.quality_selected',result_entity:'sensor.result_selected',show_parameters:false});publish();
const original=response;response=m=>{const result=original(m),t=Date.parse(m.start_time)/1000;const past=structuredClone(q);past.permit.granted=true;result['sensor.quality_selected']=[{s:'qualified',a:past,lu:t+10}];result['sensor.result_selected']=[{s:'idle',a:r,lu:t+20}];return Object.fromEntries(Object.entries(result).filter(([id])=>m.entity_ids.includes(id)));};
}""")
        self.open_trace()
        self.assertEqual(
            p.evaluate("calls[0].entity_ids"),
            ["sensor.status", "sensor.quality_selected", "sensor.result_selected"],
        )
        content = p.locator("[data-trace-list]").inner_text()
        self.assertIn("HISTORICAL ONLY", content)
        self.assertIn('"granted":true', content)
        self.assertIn('"epoch"', content)
        self.assertFalse(p.evaluate("q.permit.granted"))
        p.evaluate("q.config_entry_id='foreign';publish()")
        p.locator("[data-trace-refresh]").click()
        p.wait_for_function("!card.traceOperation")
        self.assertEqual(
            p.evaluate("calls.at(-1).entity_ids"),
            ["sensor.status", "sensor.result_selected"],
        )
        self.assertIn("品質", p.locator("[data-trace-status]").inner_text())

    def test_05_dense_pagination_filter_keyboard_geometry(self):
        p = self.p
        p.evaluate(
            """() => {response=m=>{const t=Date.parse(m.start_time)/1000;return {'sensor.status':Array.from({length:123},(_,i)=>{const a=structuredClone(states['sensor.status'].attributes);a.output_states.refill=i%2?'on':'off';return {s:'idle',a,lu:t+i};})}};}"""
        )
        self.open_trace()
        self.assertEqual(
            p.locator("[data-trace-list] li").count(),
            50,
            "every recorded event needs bounded accessible pagination",
        )
        self.assertIn("123", p.locator("[data-trace-status]").inner_text())
        p.locator("[data-trace-next]").focus()
        p.keyboard.press("Enter")
        self.assertIn("2 / 3", p.locator("[data-trace-status]").inner_text())
        p.keyboard.press("Enter")
        self.assertEqual(p.locator("[data-trace-list] li").count(), 23)
        p.locator("[data-trace-filter]").select_option("status")
        self.assertEqual(p.locator("[data-trace-list] li").count(), 50)
        for width, height in [
            (320, 568),
            (320, 1000),
            (360, 800),
            (768, 1024),
            (1280, 800),
        ]:
            for dark in [False, True]:
                p.set_viewport_size({"width": width, "height": height})
                p.evaluate(
                    "dark=>document.body.style.cssText=dark?'margin:0;--primary-text-color:#eee;--card-background-color:#182329;--ha-card-background:#182329;background:#182329':'margin:0'",
                    dark,
                )
                self.assertLessEqual(
                    p.evaluate("document.documentElement.scrollWidth"), width
                )
                self.assertTrue(
                    p.locator(
                        "[data-trace-panel] button,[data-trace-panel] select,[data-trace-toggle]"
                    ).evaluate_all(
                        "rs=>rs.every(r=>r.getBoundingClientRect().height>=44)"
                    )
                )
                if os.environ.get("BROWSER_EVIDENCE_DIR"):
                    p.evaluate("window.scrollTo(0,0)")
                    p.screenshot(
                        path=str(
                            Path(os.environ["BROWSER_EVIDENCE_DIR"])
                            / f"geometry-{width}-{height}-{dark}.png"
                        )
                    )
        p.locator("[data-trace-window]").select_option("6")
        p.wait_for_function("!card.traceOperation")
        self.assertEqual(
            p.evaluate(
                "(Date.parse(calls.at(-1).end_time)-Date.parse(calls.at(-1).start_time))/3600000"
            ),
            6,
        )

    def test_06_disconnect_purges_runtime_trace_and_rejects_late(self):
        p = self.p
        self.open_trace()
        self.assertGreater(p.locator("[data-trace-list] li").count(), 0)
        p.evaluate(
            "connection.connected=false;connection.dispatchEvent(new Event('disconnected'))"
        )
        self.assertEqual(
            p.locator("[data-trace-list] li").count(),
            0,
            "disconnect must immediately purge recorded truth without hass setter",
        )
        self.assertIn("unknown", p.locator("[data-runtime-output=refill]").inner_text())
        p.evaluate(
            "connection.connected=true;connection.dispatchEvent(new Event('ready'));publish();window.pending=[];transport=m=>{calls.push(m);return new Promise((resolve,reject)=>pending.push({resolve,reject,m}))};void 0"
        )
        p.locator("[data-trace-refresh]").click()
        p.wait_for_function("pending.length===1")
        p.evaluate(
            "card.tracePanel.open=false;pending[0].resolve(response(pending[0].m))"
        )
        p.wait_for_function("!card.traceOperation")
        self.assertEqual(p.locator("[data-trace-list] li").count(), 0)
        p.locator("[data-trace-toggle]").click()
        p.wait_for_function("pending.length===2")
        p.evaluate(
            "user.is_admin=false;publish();pending[1].resolve(response(pending[1].m))"
        )
        p.wait_for_function("!card.traceOperation")
        self.assertEqual(p.locator("[data-trace-list] li").count(), 0)
        p.locator("[data-trace-refresh]").click()
        p.wait_for_function("pending.length===3")
        p.evaluate("pending[2].reject({code:'unauthorized'})")
        p.wait_for_function("!card.traceOperation")
        self.assertIn("權限不足", p.locator("[data-trace-error]").inner_text())
        self.assertTrue(p.locator("[data-trace-refresh]").is_disabled())
        p.evaluate("publish();card.traceRequest()")
        self.assertEqual(p.evaluate("pending.length"), 3)

    def test_07_boundary_duplicate_gap_strict_safety(self):
        p = self.p
        p.evaluate(
            """() => {response=m=>{const t=Date.parse(m.start_time)/1000,a=structuredClone(states['sensor.status'].attributes),b=structuredClone(a);b.output_states.refill='on';return {'sensor.status':[{s:'idle',a,lu:t-5},{s:'idle',a:b,lu:t},{s:'unavailable',a:{},lu:t+30},{s:'idle',a,lu:t+60},{s:'idle',a:b,lu:t+60},{s:'idle',a:{...a,secret:'REJECT_ME'},lu:t+90},{s:'idle',a,lu:Date.parse(m.end_time)/1000+1}]}};}"""
        )
        self.open_trace()
        items = p.locator("[data-trace-list] li")
        self.assertEqual(
            items.count(),
            4,
            "exact window row supersedes baseline; equal-time last row wins",
        )
        self.assertNotIn("baseline", items.first.inner_text())
        self.assertIn("資料缺口", items.nth(1).inner_text())
        self.assertIn('"refill":"on"', items.nth(2).inner_text())
        self.assertNotIn("REJECT_ME", p.locator("[data-trace-list]").inner_text())
        for mode in ["foreign", "oversized", "badtime", "nullrows"]:
            p.evaluate(
                "mode=>{response=()=>mode==='foreign'?{'sensor.foreign':[]}:mode==='oversized'?{'sensor.status':Array(10001).fill({s:'idle',a:{},lu:1})}:mode==='nullrows'?{'sensor.status':null}:{'sensor.status':[{s:'idle',a:{},lu:'bad'}]}}",
                mode,
            )
            p.locator("[data-trace-refresh]").click()
            p.wait_for_function("!card.traceOperation")
            self.assertEqual(items.count(), 0)
            self.assertIn("無效", p.locator("[data-trace-error]").inner_text())

    def test_08_unmount_and_authority_require_fresh_runtime(self):
        p = self.p
        self.open_trace()
        p.evaluate(
            "window.oldStatus=states['sensor.status'];user.id='new-reader';publish()"
        )
        self.assertIn(
            "unknown",
            p.locator("[data-runtime-output=refill]").inner_text(),
            "old owner cached runtime must not revive for a new principal",
        )
        self.assertEqual(p.locator("[data-trace-list] li").count(), 0)
        p.evaluate("states['sensor.status']=structuredClone(oldStatus);publish()")
        self.assertIn("off", p.locator("[data-runtime-output=refill]").inner_text())
        p.locator("[data-trace-refresh]").click()
        p.wait_for_function("!card.traceOperation")
        p.evaluate("card.remove()")
        self.assertEqual(p.evaluate("card.traceEvents.length"), 0)
        self.assertIn(
            "unknown",
            p.evaluate(
                "card.shadowRoot.querySelector('[data-runtime-output=refill]').textContent"
            ),
        )
        self.assertIsNone(p.evaluate("card.traceConnection"))

    def test_09_same_name_slots_delayed_scope_isolation(self):
        p = self.p
        p.evaluate(
            """() => {states['sensor.status'].attributes.friendly_name='Same tank';const b=structuredClone(states['sensor.status']);b.attributes.settings_target.config_entry_id='entry-b';b.attributes.flow_plan_target.config_entry_id='entry-b';states['sensor.status_b']=b;window.pending=[];transport=m=>{calls.push(m);return new Promise(resolve=>pending.push({m,resolve}))};}"""
        )
        p.locator("[data-trace-toggle]").click()
        p.wait_for_function("pending.length===1")
        p.evaluate(
            "card.setConfig({entity:'sensor.status_b',title:'Same tank',show_parameters:false});publish()"
        )
        self.assertTrue(
            p.locator("[data-trace-refresh]").is_enabled(),
            "former scope flight must not disable a distinct selected slot",
        )
        p.locator("[data-trace-refresh]").click()
        self.assertEqual(
            p.evaluate("pending.length"),
            2,
            "new semantic scope must remain usable while former scope settles",
        )
        p.evaluate(
            "pending[1].resolve({'sensor.status_b':[{s:'idle',a:states['sensor.status_b'].attributes,lu:Date.parse(pending[1].m.start_time)/1000+5}]})"
        )
        p.wait_for_function("card.traceEvents.length>0")
        self.assertIn("sensor.status_b", p.locator("[data-trace-list]").inner_text())
        p.evaluate("pending[0].resolve(response(pending[0].m))")
        p.wait_for_function("card.traceFlights.size===0")
        self.assertNotIn("sensor.status ·", p.locator("[data-trace-list]").inner_text())
        self.assertEqual(p.evaluate("calls.length"), 2)
        p.evaluate(
            "transport=m=>new Promise(resolve=>{window.finish=()=>resolve({'sensor.status_b':[]})});void 0"
        )
        p.locator("[data-trace-refresh]").click()
        p.evaluate("card.remove();finish()")
        p.wait_for_function("!card.traceOperation")
        self.assertIsNone(
            p.evaluate("card.traceConnection"),
            "late finalizer must not recreate connection listeners after unmount",
        )
        self.assertEqual(p.evaluate("card.traceEvents.length"), 0)

    def test_10_open_before_prerequisites_drains_once(self):
        p = self.p
        p.evaluate(
            "window.h=card.hass;card.remove();card=document.createElement('uninus-nutriculture-card');document.body.append(card)"
        )
        p.locator("[data-trace-toggle]").focus()
        p.keyboard.press("Enter")
        p.wait_for_function("card.tracePanel.open")
        p.wait_for_timeout(40)
        self.assertEqual(p.evaluate("calls.length"), 0)
        p.evaluate(
            "card.hass=h;card.setConfig({entity:'sensor.status',show_parameters:false})"
        )
        p.wait_for_timeout(80)
        self.assertEqual(
            p.evaluate("calls.length"),
            1,
            "an opened disclosure must drain one read intent once config and authority arrive",
        )
        p.wait_for_function("!card.traceOperation")
        self.assertGreater(p.locator("[data-trace-list] li").count(), 0)
        p.evaluate("publish();publish()")
        self.assertEqual(p.evaluate("calls.length"), 1)

    def test_11_window_change_inflight_uses_latest_explicit_window(self):
        p = self.p
        p.evaluate(
            "window.pending=[];transport=m=>{calls.push(m);return new Promise(resolve=>pending.push({m,resolve}))};void 0"
        )
        p.locator("[data-trace-toggle]").click()
        p.wait_for_function("pending.length===1")
        p.locator("[data-trace-window]").select_option("6")
        p.evaluate("pending[0].resolve(response(pending[0].m))")
        p.wait_for_timeout(60)
        self.assertEqual(
            p.locator("[data-trace-list] li").count(),
            0,
            "old window must not render under newer selected window",
        )
        self.assertEqual(
            p.evaluate("pending.length"),
            2,
            "one explicit latest window read must drain after old transport settles",
        )
        self.assertEqual(
            p.evaluate(
                "(Date.parse(pending[1].m.end_time)-Date.parse(pending[1].m.start_time))/3600000"
            ),
            6,
        )
        p.evaluate("pending[1].resolve(response(pending[1].m))")
        p.wait_for_function("!card.traceOperation")
        self.assertGreater(p.locator("[data-trace-list] li").count(), 0)
        self.assertEqual(p.evaluate("calls.length"), 2)

    def test_12_same_owner_denial_latches_even_obsolete_window(self):
        p = self.p
        p.evaluate(
            "window.pending=[];transport=m=>{calls.push(m);return new Promise((resolve,reject)=>pending.push({m,resolve,reject}))};void 0"
        )
        p.locator("[data-trace-toggle]").click()
        p.wait_for_function("pending.length===1")
        p.locator("[data-trace-window]").select_option("24")
        p.evaluate("pending[0].reject({code:'unauthorized'})")
        p.wait_for_timeout(60)
        self.assertIn(
            "權限不足",
            p.locator("[data-trace-error]").inner_text(),
            "same owner denial is not invalidated by a newer window intent",
        )
        self.assertEqual(p.evaluate("calls.length"), 1)
        self.assertTrue(p.locator("[data-trace-refresh]").is_disabled())

    def test_13_runtime_states_waits_times_and_independent_permit(self):
        p = self.p
        self.assertNotIn(
            "尚未提供灌溉許可",
            p.locator(".safety").inner_text(),
            "v5 must defer to independent quality_v1, not claim permit feature is absent",
        )
        for code, label in [
            ("idle", "待命"),
            ("skipped_disabled", "停用略過"),
            ("skipped_weekday", "星期略過"),
            ("blocked_dependency", "前置阻擋"),
            ("waiting_delay", "等待延遲"),
            ("waiting_condition", "等待條件"),
            ("waiting_resource", "等待資源"),
            ("running", "運行中"),
            ("completed", "完成"),
            ("aborted", "中止"),
            ("fault", "故障"),
            ("stopping", "正在停止"),
        ]:
            p.evaluate(
                "code=>{const a=states['sensor.status'].attributes;a.stage_states.refill=code;a.step_runtime.refill={phase:code.startsWith('waiting_')?code:null,result:['completed','aborted','fault','skipped_disabled','skipped_weekday','blocked_dependency'].includes(code)?code:null,waiting_reason:code.startsWith('waiting_')?'delay_pending':null,started_at:null,settled_at:null};publish()}",
                code,
            )
            content = p.locator("[data-runtime-stage=refill]").inner_text()
            self.assertIn(code, content)
            self.assertIn(label, content)
        p.evaluate(
            "const a=states['sensor.status'].attributes;a.stage_states.refill='completed';a.step_runtime.refill={phase:null,result:'completed',waiting_reason:null,started_at:'2026-11-08T00:00:00Z',settled_at:'2026-11-08T00:02:00Z'};publish()"
        )
        self.assertIn(
            "2026-11-08T00:02:00Z",
            p.locator("[data-runtime-stage=refill]").inner_text(),
        )
        self.assertEqual(p.evaluate("calls.length"), 0)

    def test_14_timeout_retains_transport_lock_without_stale_truth(self):
        p = self.p
        p.clock.install()
        p.evaluate(
            "window.pending=[];transport=m=>{calls.push(m);return new Promise(resolve=>pending.push({m,resolve}))};void 0"
        )
        p.locator("[data-trace-toggle]").click()
        p.wait_for_function("pending.length===1")
        p.clock.fast_forward(20001)
        self.assertIn("逾時", p.locator("[data-trace-error]").inner_text())
        self.assertTrue(p.locator("[data-trace-refresh]").is_disabled())
        p.evaluate("void card.traceRequest()")
        self.assertEqual(p.evaluate("calls.length"), 1)
        p.evaluate("pending[0].resolve(response(pending[0].m))")
        p.wait_for_function("!card.traceOperation")
        self.assertEqual(p.locator("[data-trace-list] li").count(), 0)
        self.assertTrue(p.locator("[data-trace-refresh]").is_enabled())
        self.assertEqual(p.evaluate("calls.length"), 1)

    def test_15_terminal_result_reason_and_invalid_history_gap(self):
        p = self.p
        p.evaluate(
            """() => {const entry=states['sensor.status'].attributes.settings_target.config_entry_id;window.r={schema_version:1,config_entry_id:entry,epoch:'a'.repeat(32),observation_revision:0,support:'supported',current_run:null,last_result:null,latest_event:null};states['sensor.result_selected']={state:'idle',attributes:r};card.setConfig({entity:'sensor.status',result_entity:'sensor.result_selected',show_parameters:false});publish();const original=response;response=m=>{const data=original(m),t=Date.parse(m.start_time)/1000,past=structuredClone(r),stamp='2026-11-08T00:00:00+00:00';past.last_result={run_id:'b'.repeat(32),epoch:past.epoch,settings_revision:0,flow_plan_revision:0,state:'stopped',closure:'confirmed',reason:'emergency_stop',accepted_at:stamp,started_at:stamp,finished_at:stamp,transition_at:stamp,stages:structuredClone(states['sensor.status'].attributes.step_runtime)};data['sensor.result_selected']=[{s:'stopped',a:past,lu:t+10},{s:'stopped',a:{...past,config_entry_id:'foreign'},lu:t+20}];return data;};}"""
        )
        self.open_trace()
        content = p.locator("[data-trace-list]").inner_text()
        self.assertIn("emergency_stop", content)
        self.assertIn('"closure":"confirmed"', content)
        self.assertIn("資料缺口", content)
        self.assertNotIn("foreign", content)
        self.assertIsNone(p.evaluate("r.last_result"))

    def test_16_invalid_current_status_purges_recorded_scope(self):
        p = self.p
        self.open_trace()
        self.assertGreater(p.locator("[data-trace-list] li").count(), 0)
        p.evaluate(
            "states['sensor.status'].attributes.output_states.refill='fabricated';publish()"
        )
        self.assertEqual(
            p.locator("[data-trace-list] li").count(),
            0,
            "invalid status cannot retain authoritative selected scope trace",
        )
        self.assertTrue(p.locator("[data-trace-refresh]").is_disabled())
        self.assertIn("unknown", p.locator("[data-runtime-output=refill]").inner_text())

    def test_17_terminal_run_uses_saved_plan_not_retained_run_plan(self):
        p = self.p
        p.evaluate(
            """() => {const a=states['sensor.status'].attributes;a.run_plan={run_id:'closed-run',settings_revision:1,flow_plan_revision:2,flow_plan:structuredClone(a.flow_plan),allowed_weekdays:structuredClone(a.allowed_weekdays),enabled_stages:Object.fromEntries(['refill','nutrient','acid','mix'].map(k=>[k,true]))};a.run_plan.flow_plan.rows=[a.run_plan.flow_plan.rows[0],a.run_plan.flow_plan.rows[2],a.run_plan.flow_plan.rows[1],a.run_plan.flow_plan.rows[3]];a.flow_plan_revision=9;a.flow_state='completed';states['sensor.status'].state='completed';publish();}"""
        )
        self.assertIn("非執行中", p.locator("[data-runtime-panel]").inner_text())
        self.assertIn("計畫修訂 9", p.locator("[data-runtime-panel]").inner_text())
        self.assertEqual(
            p.locator("[data-runtime-stage]").evaluate_all(
                "rs=>rs.map(r=>r.dataset.runtimeStage)"
            ),
            ["refill", "nutrient", "acid", "mix"],
        )

    def test_18_old_window_intent_cannot_revive_under_new_authority(self):
        p = self.p
        p.evaluate(
            "window.pending=[];transport=m=>{calls.push(m);return new Promise(resolve=>pending.push({m,resolve}))};void 0"
        )
        p.locator("[data-trace-toggle]").click()
        p.wait_for_function("pending.length===1")
        p.locator("[data-trace-window]").select_option("6")
        p.evaluate(
            "user.id='replacement';publish();pending[0].resolve(response(pending[0].m))"
        )
        p.wait_for_timeout(60)
        self.assertEqual(
            p.evaluate("calls.length"),
            1,
            "a previous principal user intent must not trigger replacement authority reads",
        )
        self.assertEqual(p.locator("[data-trace-list] li").count(), 0)

    def test_19_denial_not_cleared_by_status_validity_churn(self):
        p = self.p
        p.evaluate(
            "transport=async m=>{calls.push(m);throw {code:'unauthorized'}};void 0"
        )
        self.open_trace()
        self.assertTrue(p.locator("[data-trace-refresh]").is_disabled())
        p.evaluate(
            "states['sensor.status'].attributes.output_states.refill='invalid';publish();states['sensor.status'].attributes.output_states.refill='off';publish()"
        )
        self.assertTrue(
            p.locator("[data-trace-refresh]").is_disabled(),
            "data validity is not a new authority owner and must not clear a denial",
        )
        p.evaluate("void card.traceRequest()")
        self.assertEqual(p.evaluate("calls.length"), 1)

    def test_02_accepted_run_not_draft_overlap_stop_unknown(self):
        p = self.p
        p.evaluate(
            """() => {const a=states['sensor.status'].attributes;a.run_plan={run_id:'accepted-a',settings_revision:3,flow_plan_revision:7,flow_plan:structuredClone(a.flow_plan),allowed_weekdays:structuredClone(a.allowed_weekdays),enabled_stages:Object.fromEntries(['refill','nutrient','acid','mix'].map(k=>[k,true]))};a.run_plan.flow_plan.rows=[a.run_plan.flow_plan.rows[0],a.run_plan.flow_plan.rows[2],a.run_plan.flow_plan.rows[1],a.run_plan.flow_plan.rows[3]];a.stage_states.refill='running';a.stage_states.acid='running';a.step_runtime.refill.phase='refilling';a.step_runtime.acid.phase='confirming_off';a.output_states.acid='unknown';publish();}"""
        )
        panel = p.locator("[data-runtime-panel]")
        self.assertIn("accepted-a", panel.inner_text())
        self.assertIn("7", panel.inner_text())
        self.assertEqual(
            p.locator("[data-runtime-stage]").evaluate_all(
                "rs=>rs.map(r=>r.dataset.runtimeStage)"
            ),
            ["refill", "acid", "nutrient", "mix"],
        )
        self.assertIn("運行中", p.locator("[data-runtime-stage=refill]").inner_text())
        self.assertIn(
            "confirming_off", p.locator("[data-runtime-stage=acid]").inner_text()
        )
        self.assertIn("尚未開始", p.locator("[data-runtime-stage=acid]").inner_text())
        self.assertIn("unknown", p.locator("[data-runtime-output=acid]").inner_text())
        self.assertEqual(
            p.locator("[data-runtime-output=acid]").get_attribute("role"), "alert"
        )
        p.evaluate("card.planDraft={flow_plan:{rows:[]}};publish()")
        self.assertIn("accepted-a", panel.inner_text())

    def test_01_runtime_visible_stable_four_stages(self):
        p = self.p
        self.assertEqual(
            p.locator("[data-runtime-panel]").count(),
            1,
            "actual runtime must be visible before settings",
        )
        self.assertEqual(p.locator("[data-runtime-stage]").count(), 4)
        self.assertIn("非執行中", p.locator("[data-runtime-panel]").inner_text())
        self.assertEqual(p.locator("[data-runtime-output]").count(), 4)
        p.evaluate(
            "window.rows=[...card.shadowRoot.querySelectorAll('[data-runtime-stage]')];publish()"
        )
        self.assertTrue(
            p.evaluate(
                "rows.every((r,i)=>r===card.shadowRoot.querySelectorAll('[data-runtime-stage]')[i])"
            )
        )
        self.assertIn("HA 觀測", p.locator("[data-runtime-panel]").inner_text())
        self.assertEqual(p.evaluate("calls"), [])

    def test_20_operator_stage_cards_requested_vs_actual(self):
        p = self.p
        p.evaluate(
            """() => {const a=states['sensor.status'].attributes;a.run_plan={run_id:'operator-run',settings_revision:3,flow_plan_revision:7,flow_plan:structuredClone(a.flow_plan),allowed_weekdays:structuredClone(a.allowed_weekdays),enabled_stages:Object.fromEntries(['refill','nutrient','acid','mix'].map(k=>[k,true]))};a.run_plan.flow_plan.rows[1].start_rule='after_previous_started';a.run_plan.flow_plan.rows[1].delay_seconds=12;a.stage_states.refill='running';a.stage_states.nutrient='waiting_delay';a.step_runtime.refill.phase='refilling';a.step_runtime.refill.started_at='2026-11-08T00:00:00Z';a.step_runtime.nutrient.phase='waiting_delay';a.step_runtime.nutrient.waiting_reason='delay_pending';publish();}"""
        )
        stages = p.locator("[data-runtime-stage]")
        self.assertEqual(
            stages.locator("h4").count(),
            4,
            "operator needs four headed cards, not long paragraphs",
        )
        self.assertEqual(stages.locator("[data-runtime-badge]").count(), 4)
        nutrient = p.locator("[data-runtime-stage=nutrient]")
        requested = nutrient.locator("[data-runtime-requested]").inner_text()
        for token in [
            "已受理計畫",
            "補水",
            "after_previous_started",
            "12",
            "非實際開始",
        ]:
            self.assertIn(token, requested)
        actual = nutrient.locator("[data-runtime-actual]").inner_text()
        self.assertIn("尚未開始", actual)
        self.assertNotIn("12", actual)
        self.assertIn("延遲尚未到期", nutrient.inner_text())
        self.assertIn("正在補水", p.locator("[data-runtime-stage=refill]").inner_text())
        self.assertIn(
            "2026-11-08T00:00:00Z",
            p.locator("[data-runtime-stage=refill] [data-runtime-actual]").inner_text(),
        )
        self.assertIn("operator-run", p.locator("[data-runtime-panel]").inner_text())
        p.evaluate(
            "window.stageNodes=[...card.shadowRoot.querySelectorAll('[data-runtime-stage], [data-runtime-stage] *')];publish();publish()"
        )
        self.assertTrue(
            p.evaluate(
                "stageNodes.every((n,i)=>n===card.shadowRoot.querySelectorAll('[data-runtime-stage], [data-runtime-stage] *')[i])"
            )
        )
        self.assertEqual(p.evaluate("calls"), [])

    def test_21_readable_timeline_fields_not_primary_json(self):
        p = self.p
        self.open_trace()
        items = p.locator("[data-trace-list] li")
        self.assertEqual(
            items.locator("time[data-trace-time]").count(),
            2,
            "each event needs readable semantic time",
        )
        event = items.nth(1)
        self.assertIn("階段", event.locator("[data-trace-category]").inner_text())
        summary = event.locator("[data-trace-summary]").inner_text()
        for token in ["補水", "running", "refilling", "輸出", "on"]:
            self.assertIn(token, summary)
        for token in ["{", "step_runtime", "output_states", "settings_revision"]:
            self.assertNotIn(token, summary)
        self.assertNotIn(
            "加酸", summary, "unchanged stages are not a repeated DTO dump"
        )
        self.assertIn("baseline", items.first.inner_text())
        self.assertIn("Asia/Taipei", event.locator("time").inner_text())
        self.assertIn("GMT+08:00", event.locator("time").inner_text())
        self.assertTrue(event.locator("time").get_attribute("datetime").endswith("Z"))
        self.assertEqual(p.evaluate("calls.length"), 1)

    def test_22_readable_quality_and_terminal_reason(self):
        p = self.p
        p.evaluate("""() => {
const entry=states['sensor.status'].attributes.settings_target.config_entry_id;
window.q={schema_version:1,config_entry_id:entry,epoch:'a'.repeat(32),observation_revision:1,policy_revision:0,settings_revision:0,flow_plan_revision:0,policy:{enabled:false,stable_samples:8,stable_interval_seconds:300,stable_duration_seconds:2100,permit_ttl_seconds:300,required_stages:['refill','nutrient','acid','mix'],sources:Object.fromEntries(['ph','ec','level'].map(k=>[k,{mode:'reported',attribute:null,report_contract_confirmed:false}]))},entities:{quality_status:'sensor.quality_selected',irrigation_permit:'binary_sensor.permit_selected'},quality:{state:'qualified',stable_count:8,stable_since:'2026-11-05T00:00:00Z',reasons:[]},completion:{state:'completed',run_id:'run',settled_at:'2026-11-05T00:00:00Z'},permit:{granted:false,run_id:null,expires_at:null,reasons:['no_current_run']}};
window.r={schema_version:1,config_entry_id:entry,epoch:'a'.repeat(32),observation_revision:0,support:'supported',current_run:null,last_result:null,latest_event:null};
states['sensor.quality_selected']={state:'qualified',attributes:q};states['sensor.result_selected']={state:'idle',attributes:r};
card.setConfig({entity:'sensor.status',quality_entity:'sensor.quality_selected',result_entity:'sensor.result_selected',show_parameters:false});publish();
const original=response;response=m=>{const result=original(m),t=Date.parse(m.start_time)/1000;const past=structuredClone(q);past.permit.granted=true;result['sensor.quality_selected']=[{s:'qualified',a:past,lu:t+10}];result['sensor.result_selected']=[{s:'idle',a:r,lu:t+20}];return Object.fromEntries(Object.entries(result).filter(([id])=>m.entity_ids.includes(id)));};
}""")
        p.evaluate(
            """() => {const original=response;response=m=>{const data=original(m),t=Date.parse(m.start_time)/1000,past=structuredClone(r),stamp='2026-11-08T00:00:00+00:00';past.last_result={run_id:'b'.repeat(32),epoch:past.epoch,settings_revision:0,flow_plan_revision:0,state:'stopped',closure:'confirmed',reason:'emergency_stop',accepted_at:stamp,started_at:stamp,finished_at:stamp,transition_at:stamp,stages:structuredClone(states['sensor.status'].attributes.step_runtime)};data['sensor.result_selected']=[{s:'stopped',a:past,lu:t+20}];return data;};}"""
        )
        self.open_trace()
        q = p.locator("[data-trace-list]>li").filter(
            has=p.locator("[data-trace-category]", has_text="品質")
        )
        result = p.locator("[data-trace-list]>li").filter(
            has=p.locator("[data-trace-category]", has_text="結果")
        )
        for token in ["qualified", "歷史許可", "HISTORICAL ONLY", "true", "aaaa"]:
            self.assertIn(token, q.locator("[data-trace-summary]").inner_text())
        for token in ["stopped", "emergency_stop", "confirmed", "bbbb", "實際結束"]:
            self.assertIn(token, result.locator("[data-trace-summary]").inner_text())
        self.assertNotIn("{", result.locator("[data-trace-summary]").inner_text())
        self.assertNotIn(
            "last_result", result.locator("[data-trace-summary]").inner_text()
        )
        self.assertFalse(p.evaluate("q.permit.granted"))
        self.assertIsNone(p.evaluate("r.last_result"))

    def test_23_empty_read_is_not_three_actual_events(self):
        p = self.p
        p.evaluate("response=()=>({});void 0")
        self.open_trace()
        status = p.locator("[data-trace-status]").inner_text()
        self.assertIn(
            "無可讀歷史資料",
            status,
            "permission-filtered empty history needs explicit panel summary",
        )
        self.assertIn("觀測事件 0", status)
        self.assertIn("資料缺口 1", status)
        self.assertEqual(p.locator("[data-trace-list]>li").count(), 1)
        self.assertIn("資料缺口", p.locator("[data-trace-list]").inner_text())
        self.assertNotIn("refilling", p.locator("[data-trace-list]").inner_text())
        p.locator("[data-trace-refresh]").click()
        p.wait_for_function("!card.traceOperation")
        self.assertIn("無可讀歷史資料", p.locator("[data-trace-status]").inner_text())
        self.assertEqual(p.evaluate("calls.length"), 2)

    def test_24_card_width_layout_themes_focus_and_geometry(self):
        p = self.p
        self.open_trace()
        evidence = []
        for width, height in [
            (320, 568),
            (320, 1000),
            (360, 800),
            (768, 1024),
            (1280, 800),
        ]:
            for dark in [False, True]:
                p.set_viewport_size({"width": 1600, "height": height})
                p.evaluate(
                    """({width,dark})=>{card.style.cssText=`display:block;width:${width}px`;document.body.style.cssText=dark?'margin:0;--primary-text-color:#eee;--secondary-text-color:#b7c9d0;--secondary-background-color:#25373e;--divider-color:#536770;--card-background-color:#182329;--ha-card-background:#182329;background:#182329':'margin:0';}""",
                    {"width": width, "dark": dark},
                )
                geometry = p.evaluate(
                    """() => {const rect=e=>{const r=e.getBoundingClientRect();return {x:r.x,y:r.y,width:r.width,height:r.height,right:r.right}};const root=card.shadowRoot;return {card:rect(card),grid:rect(root.querySelector('[data-runtime-grid]')),stages:[...root.querySelectorAll('[data-runtime-stage]')].map(rect),overflow:[...root.querySelectorAll('[data-runtime-panel], [data-trace-panel], [data-runtime-stage], [data-trace-list]>li')].filter(e=>e.scrollWidth>e.clientWidth+1).map(e=>e.outerHTML.slice(0,160)),controls:[...root.querySelectorAll('[data-trace-panel] button,[data-trace-panel] select,[data-trace-toggle]')].map(rect)}}"""
                )
                evidence.append(
                    {"width": width, "height": height, "dark": dark, **geometry}
                )
                self.assertEqual(geometry["overflow"], [])
                self.assertTrue(all(r["height"] >= 44 for r in geometry["controls"]))
                columns = len({round(r["x"]) for r in geometry["stages"]})
                self.assertEqual(
                    columns, 1 if width <= 360 else 2 if width == 768 else 4
                )
                self.assertTrue(
                    all(
                        r["right"] <= geometry["card"]["right"] + 1
                        for r in geometry["stages"]
                    )
                )
                if os.environ.get("BROWSER_EVIDENCE_DIR"):
                    p.locator("[data-runtime-panel]").screenshot(
                        path=str(
                            Path(os.environ["BROWSER_EVIDENCE_DIR"])
                            / f"operator-runtime-{width}-{height}-{dark}.png"
                        )
                    )
                    p.locator("[data-trace-panel]").screenshot(
                        path=str(
                            Path(os.environ["BROWSER_EVIDENCE_DIR"])
                            / f"operator-trace-{width}-{height}-{dark}.png"
                        )
                    )
        p.locator("[data-trace-window]").focus()
        p.keyboard.press("ArrowDown")
        p.keyboard.press("Tab")
        p.wait_for_function("!card.traceOperation")
        p.locator("[data-trace-refresh]").focus()
        p.evaluate(
            "window.nodes=[...card.shadowRoot.querySelectorAll('[data-runtime-stage], [data-runtime-stage] *,[data-trace-refresh]')];window.readCount=calls.length;publish();publish();publish()"
        )
        self.assertTrue(
            p.locator("[data-trace-refresh]").evaluate(
                "e=>e===e.getRootNode().activeElement"
            )
        )
        self.assertTrue(
            p.evaluate(
                "nodes.every(n=>n.isConnected)&&nodes.every(n=>[...card.shadowRoot.querySelectorAll('[data-runtime-stage], [data-runtime-stage] *,[data-trace-refresh]')].includes(n))"
            )
        )
        self.assertEqual(p.evaluate("calls.length"), p.evaluate("readCount"))
        if os.environ.get("BROWSER_EVIDENCE_DIR"):
            (
                Path(os.environ["BROWSER_EVIDENCE_DIR"]) / "operator-geometry.json"
            ).write_text(json.dumps(evidence, indent=2), encoding="utf-8")

    def test_25_requested_condition_is_readable_not_object_dump(self):
        p = self.p
        p.evaluate(
            "states['sensor.status'].attributes.flow_plan.rows[1].condition={source:'level',operator:'gte',value:0.5};publish()"
        )
        requested = p.locator(
            "[data-runtime-stage=nutrient] [data-runtime-requested]"
        ).inner_text()
        for token in ["液位", "≥", "0.5", "非實際開始", "after_previous_finished"]:
            self.assertIn(token, requested)
        self.assertNotIn("[object Object]", requested)
        self.assertIn(
            "尚未開始",
            p.locator(
                "[data-runtime-stage=nutrient] [data-runtime-actual]"
            ).inner_text(),
        )
        self.assertEqual(p.evaluate("calls"), [])

    def test_26_three_unreadable_sources_and_partial_retention(self):
        p = self.p
        p.evaluate("""() => {
const entry=states['sensor.status'].attributes.settings_target.config_entry_id;
window.q={schema_version:1,config_entry_id:entry,epoch:'a'.repeat(32),observation_revision:1,policy_revision:0,settings_revision:0,flow_plan_revision:0,policy:{enabled:false,stable_samples:8,stable_interval_seconds:300,stable_duration_seconds:2100,permit_ttl_seconds:300,required_stages:['refill','nutrient','acid','mix'],sources:Object.fromEntries(['ph','ec','level'].map(k=>[k,{mode:'reported',attribute:null,report_contract_confirmed:false}]))},entities:{quality_status:'sensor.quality_selected',irrigation_permit:'binary_sensor.permit_selected'},quality:{state:'qualified',stable_count:8,stable_since:'2026-11-05T00:00:00Z',reasons:[]},completion:{state:'completed',run_id:'run',settled_at:'2026-11-05T00:00:00Z'},permit:{granted:false,run_id:null,expires_at:null,reasons:['no_current_run']}};
window.r={schema_version:1,config_entry_id:entry,epoch:'a'.repeat(32),observation_revision:0,support:'supported',current_run:null,last_result:null,latest_event:null};
states['sensor.quality_selected']={state:'qualified',attributes:q};states['sensor.result_selected']={state:'idle',attributes:r};
card.setConfig({entity:'sensor.status',quality_entity:'sensor.quality_selected',result_entity:'sensor.result_selected',show_parameters:false});publish();
const original=response;response=m=>{const result=original(m),t=Date.parse(m.start_time)/1000;const past=structuredClone(q);past.permit.granted=true;result['sensor.quality_selected']=[{s:'qualified',a:past,lu:t+10}];result['sensor.result_selected']=[{s:'idle',a:r,lu:t+20}];return Object.fromEntries(Object.entries(result).filter(([id])=>m.entity_ids.includes(id)));};
}""")
        p.evaluate("response=()=>({});void 0")
        self.open_trace()
        status = p.locator("[data-trace-status]").inner_text()
        for token in ["無可讀歷史資料", "記錄總數 3", "觀測事件 0", "資料缺口 3"]:
            self.assertIn(token, status)
        self.assertEqual(p.locator("[data-trace-list]>li").count(), 3)
        self.assertEqual(p.evaluate("calls[0].entity_ids.length"), 3)
        p.evaluate(
            "response=m=>({'sensor.status':[{s:'idle',a:states['sensor.status'].attributes,lu:Date.parse(m.start_time)/1000+5}]});void 0"
        )
        p.locator("[data-trace-refresh]").click()
        p.wait_for_function("!card.traceOperation")
        status = p.locator("[data-trace-status]").inner_text()
        self.assertNotIn("無可讀歷史資料", status)
        self.assertIn("觀測事件 1", status)
        self.assertIn("資料缺口 2", status)
        self.assertNotIn("qualified", p.locator("[data-trace-list]").inner_text())
        self.assertFalse(p.evaluate("q.permit.granted"))

    def test_28_settled_denial_survives_timezone_only_change(self):
        p = self.p
        p.evaluate("""() => {
transport=async m=>{calls.push(structuredClone(m));throw {code:'unauthorized'}};
}""")
        self.open_trace()
        self.assertTrue(p.locator("[data-trace-refresh]").is_disabled())
        p.evaluate("""() => {
window.owner=card.hass;
card.hass={...owner,config:{...owner.config,time_zone:'UTC'}};
}""")
        self.assertTrue(
            p.evaluate("""() => {
const h=card.hass;
return h.user===owner.user&&h.user.id===owner.user.id&&
h.user.is_admin===owner.user.is_admin&&h.user.is_active===owner.user.is_active&&
h.connection===owner.connection&&h.callWS===owner.callWS&&
h.states['sensor.status']===owner.states['sensor.status'];
}""")
        )
        self.assertTrue(
            p.locator("[data-trace-refresh]").is_disabled(),
            "C09: presentation timezone must not clear the settled same-owner denial",
        )
        self.assertIn("權限不足", p.locator("[data-trace-error]").inner_text())
        self.assertEqual(p.evaluate("calls.length"), 1)

    def test_29_pending_denial_survives_timezone_only_change(self):
        p = self.p
        p.evaluate("""() => {
transport=m=>{calls.push(structuredClone(m));return new Promise((resolve,reject)=>{
window.deny=()=>reject({code:'unauthorized'});
})};
}""")
        p.locator("[data-trace-toggle]").click()
        p.wait_for_function("!!window.deny")
        p.evaluate("""() => {
const h=card.hass;card.hass={...h,config:{...h.config,time_zone:'UTC'}};deny();
}""")
        p.wait_for_function("!card.traceOperation")
        self.assertTrue(
            p.locator("[data-trace-refresh]").is_disabled(),
            "C09: pending same-owner denial must latch across display-only timezone change",
        )
        self.assertIn("權限不足", p.locator("[data-trace-error]").inner_text())
        self.assertEqual(p.evaluate("calls.length"), 1)

    def test_30_timezone_same_authority_blocks_actual_second_refresh(self):
        p = self.p
        p.evaluate("""() => {
transport=async m=>{calls.push(structuredClone(m));throw {code:'unauthorized'}};
}""")
        self.open_trace()
        self.assertTrue(p.locator("[data-trace-refresh]").is_disabled())
        p.evaluate("""() => {
window.owner=card.hass;window.entity=card.config.entity;
window.entry=card.status().attributes.settings_target.config_entry_id;
card.hass={...owner,config:{...owner.config,time_zone:'UTC'}};
}""")
        unchanged = p.evaluate("""() => {
const h=card.hass;
return {user:h.user===owner.user,principal:h.user.id===owner.user.id,
role:h.user.is_admin===owner.user.is_admin,active:h.user.is_active===owner.user.is_active,
connection:h.connection===owner.connection,ws:h.callWS===owner.callWS,
status:h.states['sensor.status']===owner.states['sensor.status'],
entity:card.config.entity===entity,
entry:card.status().attributes.settings_target.config_entry_id===entry};
}""")
        self.assertTrue(all(unchanged.values()), unchanged)
        # Trusted pointer input reaches the actual button, even when disabled.
        box = p.locator("[data-trace-refresh]").bounding_box()
        p.mouse.click(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
        p.wait_for_function("!card.traceOperation")
        p.wait_for_timeout(60)
        self.assertEqual(
            p.evaluate("calls.length"),
            1,
            "C09: a real second Refresh must not emit a same-authority denied read",
        )
        self.assertTrue(p.locator("[data-trace-refresh]").is_disabled())
        p.evaluate("void card.traceRequest()")
        self.assertEqual(p.evaluate("calls.length"), 1)

    def test_31_cached_timezone_reformats_without_read_or_navigation_loss(self):
        p = self.p
        p.evaluate("""() => {
response=m=>{const t=Date.parse(m.start_time)/1000;return {'sensor.status':
Array.from({length:123},(_,i)=>{const a=structuredClone(states['sensor.status'].attributes);
a.output_states.refill=i%2?'on':'off';return {s:'idle',a,lu:t+i};})}};
}""")
        self.open_trace()
        p.locator("[data-trace-filter]").select_option("status")
        p.locator("[data-trace-next]").click()
        p.locator("[data-trace-filter]").focus()
        p.evaluate("""() => {
window.cached=card.traceEvents;window.times=[...card.traceList.querySelectorAll('time')].map(e=>e.dateTime);
window.focused=card.shadowRoot.activeElement;
const h=card.hass;card.hass={...h,config:{...h.config,time_zone:'UTC'}};
}""")
        self.assertEqual(
            p.locator("[data-trace-list] li").count(),
            50,
            "display timezone must retain the cached selected page",
        )
        self.assertTrue(p.evaluate("card.traceEvents===cached"))
        self.assertEqual(p.evaluate("card.tracePage"), 1)
        self.assertEqual(p.locator("[data-trace-filter]").input_value(), "status")
        self.assertTrue(
            p.evaluate("card.shadowRoot.activeElement===focused&&focused.isConnected")
        )
        self.assertEqual(
            p.locator("[data-trace-time]").evaluate_all("es=>es.map(e=>e.dateTime)"),
            p.evaluate("times"),
        )
        rendered = p.locator("[data-trace-time]").all_text_contents()
        self.assertTrue(
            all("UTC" in text and "Asia/Taipei" not in text for text in rendered)
        )
        self.assertEqual(
            rendered,
            p.evaluate("card.traceEvents.slice(50,100).map(e=>card.historyTime(e.t))"),
        )
        self.assertEqual(p.evaluate("calls.length"), 1)

    def test_27_only_visible_page_gets_presentation(self):
        p = self.p
        p.evaluate(
            """() => {window.rendered=0;const original=card.tracePresentation.bind(card);card.tracePresentation=(...args)=>{rendered++;return original(...args)};response=m=>{const t=Date.parse(m.start_time)/1000;return {'sensor.status':Array.from({length:123},(_,i)=>{const a=structuredClone(states['sensor.status'].attributes);a.output_states.refill=i%2?'on':'off';return {s:'idle',a,lu:t+i};})}};}"""
        )
        self.open_trace()
        self.assertEqual(
            p.evaluate("rendered"),
            50,
            "bounded page must not format every retained snapshot",
        )
        self.assertEqual(p.evaluate("card.traceEvents.length"), 123)
        p.evaluate("rendered=0")
        p.locator("[data-trace-next]").click()
        self.assertEqual(p.evaluate("rendered"), 50)
        self.assertNotIn(
            "加酸",
            p.locator("[data-trace-list]>li")
            .first.locator("[data-trace-summary]")
            .inner_text(),
            "previous-page context still suppresses unchanged stages",
        )
