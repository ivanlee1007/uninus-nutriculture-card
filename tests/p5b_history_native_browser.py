"""Shipping Card + live registered native History bridge; stdout JSONL only."""

import json
import os
import queue
import sys
import threading
import traceback
from datetime import datetime

from playwright.sync_api import sync_playwright

INBOX = queue.Queue()


def read_stdin():
    for line in sys.stdin:
        INBOX.put(line)
    INBOX.put(None)


def rpc(kind, payload=None):
    print(json.dumps({"kind": kind, "payload": payload}), flush=True)
    line = INBOX.get(timeout=30)
    if line is None:
        raise RuntimeError("native parent EOF")
    result = json.loads(line)
    if "harness_error" in result:
        raise RuntimeError(result["harness_error"])
    return result


def main():
    threading.Thread(target=read_stdin, daemon=True).start()
    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            headless=True, executable_path=os.environ["CHROMIUM_EXECUTABLE"]
        )
        try:
            page = browser.new_page(viewport={"width": 768, "height": 1200})
            page.set_default_timeout(12000)
            page.on("console", lambda m: print(m.text, file=sys.stderr))
            page.on("pageerror", lambda e: print(str(e), file=sys.stderr))
            page.set_content('<!doctype html><meta charset="utf-8"><body>')
            page.expose_function("nativeRPC", rpc)
            page.add_script_tag(path=os.environ["P5B_CARD_BUNDLE"])
            page.evaluate("""async () => {
                await customElements.whenDefined('uninus-nutriculture-card');
                window.cards={}; window.receipts=[]; window.pending=0;
                window.mount=async(name,index=0,principal='all')=>{
                    const s=await nativeRPC('snapshot',{index,principal});
                    const c=document.createElement('uninus-nutriculture-card');
                    c.id=name; cards[name]=c; document.body.append(c);
                    const connection={connected:true};
                    const user={id:s.user_id,is_admin:s.is_admin,is_owner:false,is_active:true};
                    const callWS=async message=>{
                        pending++;
                        try {
                            const r=await nativeRPC('ws',{message,principal_id:user.id});
                            receipts.push({name,message,reply:r.reply});
                            if(!r.reply.success) throw r.reply.error;
                            return r.reply.result;
                        } finally {pending--;}
                    };
                    c.setConfig({entity:s.status_id});
                    c.hass={states:s.states,user,connection,callWS,
                        callService:async (...args)=>{throw Error('unexpected callService '+JSON.stringify(args));},
                        services:s.services,config:{time_zone:'Asia/Taipei',unit_system:{length:'m'}},
                        locale:{language:'zh-Hant',time_format:'24',time_zone:'server'}};
                };
                await mount('A');
            }""")
            a = page.locator("#A")
            mounted = page.evaluate(
                """()=>({entity:cards.A.config.entity,status:cards.A.status(),readings:Object.fromEntries(Object.entries(cards.A.readings).map(([k,n])=>[k,{value:n.value.textContent,unit:n.unit.textContent}]))})"""
            )
            native = rpc("snapshot", {"index": 0, "principal": "all"})
            assert (
                mounted["entity"] == native["status_id"]
                and mounted["status"] == native["states"][native["status_id"]]
            )
            for metric, source in mounted["status"]["attributes"]["source_entities"].items():
                assert float(mounted["readings"][metric]["value"]) == float(
                    native["states"][source]["state"]
                )
                assert (
                    mounted["readings"][metric]["unit"]
                    == native["states"][source]["attributes"]["unit_of_measurement"]
                )
            rpc("checkpoint", {"case": "shipping_native_mount", "browser": browser.version})
            assert (
                page.evaluate(
                    "receipts.filter(r=>r.message.type==='history/history_during_period').length"
                )
                == 0
            )
            # Genuine desired-feature assertion: baseline fails HERE after bootstrap/wire proof.
            assert a.locator("details[data-history-panel]").count() == 1, (
                "desired history panel missing from shipping Card"
            )
            panel = a.locator("details[data-history-panel]")
            assert not panel.evaluate("(e)=>e.open")
            a.locator("[data-history-toggle]").click()

            def settle():
                page.wait_for_function("pending===0")
                page.wait_for_timeout(100)

            def verify_window(hours):
                settle()
                row = page.evaluate(
                    "receipts.filter(r=>r.name==='A'&&r.message.type==='history/history_during_period').at(-1)"
                )
                assert row and row["reply"]["success"], row
                message = row["message"]
                snapshot = rpc("snapshot", {"index": 0, "principal": "all"})
                expected = snapshot["states"][snapshot["status_id"]]["attributes"][
                    "source_entities"
                ]
                assert (
                    set(message["entity_ids"]) == set(expected.values())
                    and len(message["entity_ids"]) == 3
                )
                start = datetime.fromisoformat(message["start_time"].replace("Z", "+00:00"))
                end = datetime.fromisoformat(message["end_time"].replace("Z", "+00:00"))
                assert (
                    start.utcoffset().total_seconds() == 0 and end.utcoffset().total_seconds() == 0
                )
                assert (end - start).total_seconds() == hours * 3600
                for key, value in {
                    "include_start_time_state": True,
                    "significant_changes_only": False,
                    "minimal_response": False,
                    "no_attributes": False,
                }.items():
                    assert message[key] is value, (key, message)
                for metric, entity in expected.items():
                    rows = row["reply"]["result"][entity]
                    table = a.locator(f'[data-history-table="{metric}"]')
                    assert table.count() == 1
                    for sample in rows:
                        if sample["s"] in ("unknown", "unavailable"):
                            continue
                        text = table.inner_text()
                        assert sample["s"] in text, (metric, sample, text)
                        assert sample["a"].get("unit_of_measurement", "") in text, (
                            metric,
                            sample,
                            text,
                        )
                    chart = a.locator(f'[data-history-plot="{metric}"]')
                    assert chart.count() == 1
                    chart.focus()
                    chart.press("End")
                    active = a.locator(f'[data-history-active-point="{metric}"]')
                    assert active.count() == 1
                    last = next(
                        s for s in reversed(rows) if s["s"] not in ("unknown", "unavailable")
                    )
                    assert last["s"] in active.inner_text()
                    assert last["a"].get("unit_of_measurement", "") in active.inner_text()
                    # Compare rendered time against actual wire seconds in HA configured TZ.
                    expected_time = page.evaluate(
                        "s=>new Intl.DateTimeFormat('zh-TW',{timeZone:'Asia/Taipei',hour:'2-digit',minute:'2-digit',second:'2-digit',hour12:false}).format(new Date(s*1000))",
                        last["lu"],
                    )
                    assert expected_time in active.inner_text(), (
                        last,
                        expected_time,
                        active.inner_text(),
                    )
                rpc("checkpoint", {"case": f"live_render_exact_{hours}h"})

            verify_window(1)
            for hours in (6, 24):
                a.locator("[data-history-window]").select_option(str(hours))
                verify_window(hours)
            # Two identical names are selected by real distinct native status identity.
            page.evaluate("async()=>{await mount('B',1,'all');}")
            b = page.locator("#B")
            b.locator("[data-history-toggle]").click()
            settle()
            latest = page.evaluate(
                "receipts.filter(r=>r.name==='B'&&r.message.type==='history/history_during_period').at(-1)"
            )
            other = rpc("snapshot", {"index": 1, "principal": "all"})
            assert set(latest["message"]["entity_ids"]) == set(
                other["states"][other["status_id"]]["attributes"]["source_entities"].values()
            )
            for name, principal in [("P", "partial"), ("N", "none")]:
                page.evaluate("async ([n,p])=>{await mount(n,0,p);}", [name, principal])
                c = page.locator("#" + name)
                c.locator("[data-history-toggle]").click()
                settle()
                r = page.evaluate(
                    "n=>receipts.filter(r=>r.name===n&&r.message.type==='history/history_during_period').at(-1)",
                    name,
                )
                assert r["reply"]["success"]
                assert len(r["reply"]["result"]) == (1 if principal == "partial" else 0), r
                if principal == "none":
                    assert "無可讀歷史資料" in c.locator("[data-history-status]").inner_text()
                    empty_dom = c.evaluate("""el => ({
                        status:el.shadowRoot.querySelector('[data-history-status]').textContent,
                        metrics:Object.fromEntries(Object.entries(el.historyMetrics).map(([metric,n])=>[metric,{
                            plot:n.plot.outerHTML,
                            paths:[...el.shadowRoot.querySelectorAll(`[data-history-plot="${metric}"] path`)].map(p=>p.getAttribute('d')),
                            circles:el.shadowRoot.querySelectorAll(`[data-history-plot="${metric}"] circle`).length,
                            table:el.shadowRoot.querySelector(`[data-history-table="${metric}"]`).outerHTML,
                            table_data_cells:el.shadowRoot.querySelectorAll(`[data-history-table="${metric}"] td`).length,
                            active:el.shadowRoot.querySelector(`[data-history-active-point="${metric}"]`).textContent,
                            points:n.points
                        }]))
                    })""")
                    rpc("checkpoint", {"case": "no_READ_exact_per_metric_DOM", "dom": empty_dom})
                    assert set(empty_dom["metrics"]) == {"ph", "ec", "level"}, empty_dom
                    for metric, shape in empty_dom["metrics"].items():
                        assert all(not (d or "").strip() for d in shape["paths"]), (metric, shape)
                        assert shape["circles"] == 0 and shape["table_data_cells"] == 0, (
                            metric,
                            shape,
                        )
                        assert shape["points"] == [], (metric, shape)
                        assert "無可讀歷史資料" in shape["active"], (metric, shape)
            rpc("checkpoint", {"case": "live_partial_full_READ_filter_and_same_name_isolation"})
            rpc("inspect")
            rpc("done", {"case": "native_history_browser_complete"})
        finally:
            browser.close()


if __name__ == "__main__":
    try:
        main()
    except BaseException:
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)
