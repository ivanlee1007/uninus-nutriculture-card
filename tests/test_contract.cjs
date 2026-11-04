'use strict';
// Supplementary unit probes: real shipped prototype, no DOM renderer replacement.
const {test} = require('node:test');
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
const path = require('node:path');
const elements = new Map();
const context = {HTMLElement:class {},window:{},customElements:{get:k=>elements.get(k),define:(k,v)=>elements.set(k,v)},console};
vm.runInNewContext(fs.readFileSync(path.join(__dirname,'../uninus-nutriculture-card.js'),'utf8'),context);
const C = elements.get('uninus-nutriculture-card');
const row = {key:'ph_low',unit:'',input:{value:'5.55'}};
function owner() {
  const status = {state:'within_range',attributes:{schema_version:1,mode:'shadow',parameter_entities:{ph_low:'number.actual_ph'}}};
  return {status:()=>status,_hass:{states:{'number.actual_ph':{state:'5.4',attributes:{min:0,max:14,step:.01,unit_of_measurement:'pH'}}}}};
}
test('target uses exact mapped Number and native metadata',()=>{
  const got = C.prototype.target.call(owner(),row);
  assert.equal(got.id,'number.actual_ph'); assert.equal(got.min,0); assert.equal(got.max,14); assert.equal(got.step,.01); assert.equal(got.unit,'pH');
});
test('schema/mode unavailable never yield a writable target',()=>{
  for (const mutate of [o=>o.status().attributes.schema_version=2,o=>o.status().attributes.mode='active',o=>o.status().state='unavailable']) {
    const o=owner();mutate(o);assert.ok(C.prototype.target.call(o,row).error);
  }
});
test('invalid mappings and unavailable Number fail closed',()=>{
  for (const id of ['switch.pump','number.BAD','number.a extra',null,'']) {
    const o=owner();o.status().attributes.parameter_entities.ph_low=id;assert.ok(C.prototype.target.call(o,row).error);
  }
  const o=owner();o._hass.states['number.actual_ph'].state='unavailable';assert.ok(C.prototype.target.call(o,row).error);
});
test('finite range and step validation includes exact boundary',()=>{
  const target={min:.8,max:.9,step:.01};
  for (const value of ['.8','.85','.9']) assert.equal(C.prototype.valid.call({}, {input:{value}},target),true,value);
  for (const value of ['',null,'NaN','Infinity','.79','.91','.855']) assert.equal(C.prototype.valid.call({}, {input:{value}},target),false,String(value));
});
test('v2 stub selects actual control sensor, never an arbitrary or unknown contract',()=>{
  const valid={state:'idle',attributes:{schema_version:2,mode:'control',flow_state:'idle'}};
  assert.equal(C.getStubConfig({states:{'sensor.other':{attributes:{}},'sensor.control_actual':valid}}).entity,'sensor.control_actual');
  assert.equal(C.getStubConfig({states:{'sensor.future':{attributes:{schema_version:3,mode:'control'}}}}).entity,'sensor.uninus_nutriculture_status');
});
test('v2 Number target accepts control only, preserving v1 shadow validation',()=>{
  const o=owner();Object.assign(o.status().attributes,{schema_version:2,mode:'control',flow_state:'idle'});o.status().state='idle';
  assert.equal(C.prototype.target.call(o,row).id,'number.actual_ph');
  o.status().attributes.mode='shadow';assert.ok(C.prototype.target.call(o,row).error);
});
test('native control resolves exact domains, fresh service and capability',()=>{
  const o=owner(), r={key:'flow_run',domain:'switch'};
  Object.assign(o.status().attributes,{schema_version:2,mode:'control',flow_state:'idle',capabilities:{refill:true},control_entities:{flow_run:'switch.native_run'}});o.status().state='idle';
  o._hass.states['switch.native_run']={state:'off'};
  assert.equal(C.prototype.controlTarget.call(o,r).service,'turn_on');
  o._hass.states['switch.native_run'].state='on';assert.equal(C.prototype.controlTarget.call(o,r).service,'turn_off');
  for(const id of ['button.native_run','switchXnative_run','switch.BAD',null]){o.status().attributes.control_entities.flow_run=id;assert.ok(C.prototype.controlTarget.call(o,r).error)}
  o.status().attributes.control_entities.flow_run='switch.native_run';o.status().attributes.capabilities.refill=false;assert.ok(C.prototype.controlTarget.call(o,r).error);
});
test('native Button unknown is usable but unavailable and wrong domain are not',()=>{
  const o=owner(), r={key:'emergency_stop',domain:'button'};
  Object.assign(o.status().attributes,{schema_version:2,mode:'control',flow_state:'fault',control_entities:{emergency_stop:'button.native_stop'}});o.status().state='fault';
  o._hass.states['button.native_stop']={state:'unknown'};
  assert.equal(C.prototype.controlTarget.call(o,r).service,'press');
  o._hass.states['button.native_stop'].state='unavailable';assert.ok(C.prototype.controlTarget.call(o,r).error);
});
test('schema3 supports nutrient-only native run and rejects inconsistent contracts',()=>{
  const states=structuredClone(require('./fixtures/p3a.json'));
  const o={status:()=>states['sensor.status'],_hass:{states}}, r={key:'flow_run',domain:'switch'};
  assert.equal(C.prototype.controlTarget.call(o,r).id,'switch.actual_flow_run');
  assert.equal(C.prototype.controlTarget.call(o,{key:'nutrient_enabled',domain:'switch'}).id,'switch.actual_nutrient_enabled');
  for(const state of ['waiting_resource','dosing','mixing','waiting_sample','stabilizing']){
    o.status().state=o.status().attributes.flow_state=state;
    assert.equal(C.prototype.controlTarget.call(o,r).id,'switch.actual_flow_run');
  }
  for(const mutate of [a=>a.schema_version=2,a=>a.flow_state='future',a=>a.capabilities.acid=true,a=>a.settings_target.service='evil',a=>a.dosing_parameters.pulse_seconds=true,a=>a.control_entities.nutrient_enabled='switch.actual_flow_run']){
    const fresh=structuredClone(require('./fixtures/p3a.json'));const x={status:()=>fresh['sensor.status'],_hass:{states:fresh}};mutate(x.status().attributes);
    assert.ok(C.prototype.controlTarget.call(x,r).error);
  }
});
test('schema4 acid-only strict native controls and Number subset',()=>{
 const states=require('./p3b_fixture.cjs')(),a=states['sensor.status'].attributes;
 const o={status:()=>states['sensor.status'],_hass:{states}};
 assert.equal(C.prototype.controlTarget.call(o,{key:'acid_enabled',domain:'switch'}).id,'switch.actual_acid_enabled');
 delete a.parameter_entities.ec_high;
 assert.equal(C.prototype.controlTarget.call(o,{key:'acid_enabled',domain:'switch'}).id,'switch.actual_acid_enabled');
 for(const mutate of [a=>a.acid_parameters.pulse_seconds=true,a=>a.safety_parameters.extra=1,a=>a.acid_progress.pulse_count=-1,a=>a.stage_states.acid='disabled',a=>a.parameters.extra=1,a=>a.settings_target.service='apply_control_settings']){
  const fresh=require('./p3b_fixture.cjs')(),x={status:()=>fresh['sensor.status'],_hass:{states:fresh}};mutate(x.status().attributes);
  assert.ok(C.prototype.controlTarget.call(x,{key:'acid_enabled',domain:'switch'}).error);
 }
});

test('v4 rejects outer unknown fields, missing fields and normal parameter range/step violations',()=>{
 const mutations=[a=>a.untrusted_extra=1,a=>delete a.reasons,a=>a.parameters.ph_low=-.1,a=>a.parameters.mix_duration=.5,a=>a.parameters.level_low=.001,a=>a.flow_state='future',a=>a.acid_phase='future'];
 for(const mutate of mutations){
  const states=require('./p3b_fixture.cjs')(),o={status:()=>states['sensor.status'],_hass:{states}};mutate(o.status().attributes);
  assert.ok(C.prototype.controlTarget.call(o,{key:'acid_enabled',domain:'switch'}).error, String(mutate));
 }
 const states=require('./p3b_fixture.cjs')(),o={status:()=>states['sensor.status'],_hass:{states}};
 Object.assign(o.status().attributes,{friendly_name:'Native status',icon:'mdi:flask',device_class:'enum',options:['idle']});
 assert.equal(C.prototype.controlTarget.call(o,{key:'acid_enabled',domain:'switch'}).id,'switch.actual_acid_enabled');
});

test('schema5 strict wire consumer never grants controls to malformed snapshots',()=>{
 const base=require('./p3c_fixture.cjs');
 const check=states=>C.prototype.controlTarget.call({status:()=>states['sensor.status'],_hass:{states}},{key:'acid_enabled',domain:'switch'});
 assert.equal(check(base()).id,'switch.actual_acid_enabled');
 for(const mutate of [a=>a.extra=1,a=>delete a.run_plan,a=>a.output_states.extra='off',a=>delete a.output_states.refill,a=>a.output_states.refill=true,a=>a.flow_plan_target.config_entry_id='other',a=>a.flow_plan_target.preview_service='evil',a=>a.settings_target.service='apply_control_settings_v4',a=>a.flow_plan.rows.reverse(),a=>a.flow_plan.rows[1].stage='refill',a=>a.flow_plan.rows[0].delay_seconds=.5,a=>a.flow_plan.rows[1].condition={source:'ph',operator:'gte',value:15},a=>a.step_runtime.mix.phase='done',a=>a.step_runtime.mix.waiting_reason='raw exception',a=>a.ready_for_irrigation=true,a=>a.acid_parameters=null,a=>a.safety_parameters.extra=1,a=>a.control_entities.acid_enabled='switch.BAD',a=>a.schema_version=6]){const s=base();mutate(s['sensor.status'].attributes);assert.ok(check(s).error,String(mutate));}
 for(const state of ['running','waiting_delay','waiting_condition','waiting_resource']){const s=base();s['sensor.status'].state=s['sensor.status'].attributes.flow_state=state;s['switch.actual_flow_run'].state='on';assert.equal(check(s).id,'switch.actual_acid_enabled');}
});

test('registration is idempotent with a second resource evaluation',()=>{
  vm.runInNewContext(fs.readFileSync(path.join(__dirname,'../uninus-nutriculture-card.js'),'utf8'),context);
  assert.equal(elements.size,2);assert.equal(context.window.customCards.length,1);
  assert.equal(elements.get('uninus-nutriculture-card'),C);
});
