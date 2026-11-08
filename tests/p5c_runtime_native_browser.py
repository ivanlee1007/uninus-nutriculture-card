"""C12 shipping Chromium -> JSONL -> real registered native History acceptance.

Invoked by tools/p5c_runtime_native.py, not unittest discovery. No synthetic API
responses: only native snapshot fixtures and replies from registered Core routes.
"""

import json
import os
import queue
import re
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
            page.on("console", lambda message: print(message.text, file=sys.stderr))
            page.on("pageerror", lambda error: print(str(error), file=sys.stderr))
            page.set_content('<!doctype html><meta charset="utf-8"><body>')
            page.expose_function("nativeRPC", rpc)
            page.add_script_tag(path=os.environ["P5C_CARD_BUNDLE"])
            page.evaluate("""async () => {
                await customElements.whenDefined('uninus-nutriculture-card');
                window.cards={}; window.receipts=[]; window.pending=0;
                window.mutations=[];
                window.mount=async(name,principal='all',optional=true)=>{
                    const s=await nativeRPC('snapshot',{index:0,principal});
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
                    c.setConfig({entity:s.status_id,...(optional?{
                        quality_entity:s.quality_id,result_entity:s.result_id}:{} )});
                    c.hass={states:s.states,user,connection,callWS,
                        callService:async (...args)=>{
                            mutations.push(args);
                            throw Error('unexpected browser mutation '+JSON.stringify(args));
                        },
                        services:s.services,config:{time_zone:'Asia/Taipei',unit_system:{length:'m'}},
                        locale:{language:'zh-Hant',time_format:'24',time_zone:'server'}};
                };
                await mount('A');
            }""")
            a = page.locator("#A")
            native = rpc("snapshot", {"index": 0, "principal": "all"})
            mounted = page.evaluate("() => cards.A.status()")
            assert mounted == native["states"][native["status_id"]], mounted
            assert mounted["attributes"]["schema_version"] == 5
            optional = page.evaluate(
                "() => ({quality:cards.A.qualityNative(),result:cards.A.resultNative()})"
            )
            assert optional["quality"] and optional["result"], optional
            entry = mounted["attributes"]["settings_target"]["config_entry_id"]
            assert (
                optional["quality"]["config_entry_id"]
                == optional["result"]["config_entry_id"]
                == entry
            )
            assert optional["result"]["last_result"]["state"] == "stopped", optional
            rpc(
                "checkpoint",
                {
                    "case": "shipping_native_S5_mount",
                    "browser": browser.version,
                    "optional_quality_result_strict_native_valid": True,
                },
            )
            assert (
                page.evaluate(
                    "receipts.filter(r=>r.message.type==='history/history_during_period').length"
                )
                == 0
            )
            # Baseline must fail on genuine absent shipping behavior AFTER setup proof.
            assert a.locator("[data-runtime-panel]").count() == 1, (
                "desired runtime panel missing from shipping Card (native setup already proven)"
            )
            for stage in ("refill", "nutrient", "acid", "mix"):
                node = a.locator(f'[data-runtime-stage="{stage}"]')
                assert node.count() == 1 and node.is_visible()
                assert mounted["attributes"]["stage_states"][stage] in node.inner_text()
            for output in ("refill", "nutrient", "acid", "circulation"):
                node = a.locator(f'[data-runtime-output="{output}"]')
                assert node.count() == 1 and node.is_visible()
                assert (
                    mounted["attributes"]["output_states"][output] in node.inner_text()
                )
            panel = a.locator("details[data-trace-panel]")
            assert panel.count() == 1 and not panel.evaluate("e=>e.open")
            assert a.locator("details[data-history-panel]").count() == 1
            a.locator("[data-trace-toggle]").focus()
            a.locator("[data-trace-toggle]").press("Enter")

            def settle():
                page.wait_for_function("pending===0")
                page.wait_for_timeout(150)

            def receipt(name):
                return page.evaluate(
                    "n=>receipts.filter(r=>r.name===n&&r.message.type==='history/history_during_period').at(-1)",
                    name,
                )

            def verify_window(hours):
                settle()
                row = receipt("A")
                assert row and row["reply"]["success"], row
                message = row["message"]
                assert (
                    set(message["entity_ids"])
                    == {native["status_id"], native["quality_id"], native["result_id"]}
                    and len(message["entity_ids"]) == 3
                ), message
                # Retain trailing-Z support on Python <3.11.
                start = datetime.fromisoformat(
                    message["start_time"].replace("Z", "+00:00")  # noqa: FURB162
                )
                end = datetime.fromisoformat(message["end_time"].replace("Z", "+00:00"))  # noqa: FURB162 -- retain trailing-Z support on Python <3.11
                assert (end - start).total_seconds() == hours * 3600
                assert (
                    start.utcoffset().total_seconds()
                    == end.utcoffset().total_seconds()
                    == 0
                )
                for key, value in {
                    "include_start_time_state": True,
                    "significant_changes_only": False,
                    "minimal_response": False,
                    "no_attributes": False,
                }.items():
                    assert message[key] is value, (key, message)
                rows = row["reply"]["result"]
                status = [
                    r
                    for r in rows[native["status_id"]]
                    if r["a"].get("schema_version") == 5
                ]
                assert any(r["a"]["output_states"]["nutrient"] == "on" for r in status)
                assert any(r["a"]["output_states"]["nutrient"] == "off" for r in status)
                assert all(r["a"]["schema_version"] == 5 for r in status)
                assert rows[native["quality_id"]] and rows[native["result_id"]]
                text = a.locator("[data-trace-list]").inner_text()
                assert (
                    text.strip()
                    and re.search(r"\bon\b", text)
                    and re.search(r"\boff\b", text)
                ), text
                assert re.search(r"nutrient|加養", text), text
                assert re.search(
                    r"歷史|HISTORICAL",
                    a.locator("[data-trace-panel]").inner_text(),
                    re.IGNORECASE,
                ), text
                # Terminal reason is taken from the actual native DTO, never invented.
                terminal = next(
                    r["a"]["last_result"]
                    for r in reversed(rows[native["result_id"]])
                    if r["a"].get("last_result")
                )
                assert terminal["state"] in text, (terminal, text)
                if terminal.get("reason"):
                    assert terminal["reason"] in text, (terminal, text)
                quality = rows[native["quality_id"]][-1]["a"]
                assert quality["quality"]["state"] in text, (quality, text)
                assert re.search(r"品質|quality", text, re.IGNORECASE), text
                terminal_row = next(
                    r
                    for r in reversed(rows[native["result_id"]])
                    if r["a"].get("last_result")
                )
                expected_time = page.evaluate(
                    "s=>new Intl.DateTimeFormat('zh-TW',{timeZone:'Asia/Taipei',hour:'2-digit',minute:'2-digit',second:'2-digit',hour12:false}).format(new Date(s*1000))",
                    terminal_row["lu"],
                )
                assert expected_time in text and "+08:00" in text, (expected_time, text)
                rpc(
                    "checkpoint",
                    {
                        "case": f"shipping_trace_native_{hours}h",
                        "request_id": row["reply"]["id"],
                        "rendered_trace": text,
                        "native_last_result": terminal,
                    },
                )

            verify_window(1)
            for hours in (6, 24):
                a.locator("[data-trace-window]").select_option(str(hours))
                verify_window(hours)
            count = page.evaluate(
                "receipts.filter(r=>r.message.type==='history/history_during_period').length"
            )
            a.locator("[data-trace-refresh]").click()
            verify_window(24)
            assert (
                page.evaluate(
                    "receipts.filter(r=>r.message.type==='history/history_during_period').length"
                )
                == count + 1
            )
            a.locator("[data-trace-toggle]").click()
            settle()
            count = page.evaluate("receipts.length")
            page.wait_for_timeout(300)
            assert page.evaluate("receipts.length") == count
            for name, principal, expected_count in (
                ("P", "partial", 1),
                ("N", "none", 0),
            ):
                page.evaluate("async([n,p])=>{await mount(n,p);}", [name, principal])
                c = page.locator("#" + name)
                c.locator("[data-trace-toggle]").click()
                settle()
                row = receipt(name)
                assert row and row["reply"]["success"], row
                assert len(row["reply"]["result"]) == expected_count, row
                text = c.locator("[data-trace-list]").inner_text()
                status_text = c.locator("[data-trace-status]").inner_text()
                if principal == "partial":
                    assert set(row["reply"]["result"]) == {native["status_id"]}
                    assert re.search(r"\bon\b", text) and re.search(r"\boff\b", text), (
                        text
                    )
                else:
                    assert not re.search(
                        r"\b(on|off|running|aborted|stopped)\b", text
                    ), text
                    assert optional["result"]["last_result"]["run_id"] not in text, text
                    assert re.search(
                        r"無.*(資料|歷史)|no.*(readable|history)",
                        status_text,
                        re.IGNORECASE,
                    ), status_text
                rpc(
                    "checkpoint",
                    {
                        "case": "native_READ_" + principal,
                        "request_id": row["reply"]["id"],
                        "trace_list": text,
                        "status": status_text,
                    },
                )
            # Optional source absence must not disable valid recorded S5 stage history.
            page.evaluate("async()=>{await mount('M','all',false);}")
            missing = page.locator("#M")
            missing.locator("[data-trace-toggle]").click()
            settle()
            row = receipt("M")
            assert set(row["message"]["entity_ids"]) == {native["status_id"]}, row
            assert row["reply"]["success"] and set(row["reply"]["result"]) == {
                native["status_id"]
            }
            assert re.search(
                r"\bon\b", missing.locator("[data-trace-list]").inner_text()
            )
            assert re.search(
                r"未|缺|無|unavailable|missing",
                missing.locator("[data-trace-panel]").inner_text(),
                re.IGNORECASE,
            )
            assert page.evaluate("mutations") == []
            rpc("inspect")
            rpc(
                "done",
                {
                    "case": "native_runtime_trace_browser_complete",
                    "qualification": "one fakehardware native run; recent Recorder samples; READ filtering, not HTTP bearer handshake",
                },
            )
        finally:
            browser.close()


if __name__ == "__main__":
    try:
        main()
    except BaseException:  # noqa: BLE001 -- report all child exits to parent after main cleanup
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)
