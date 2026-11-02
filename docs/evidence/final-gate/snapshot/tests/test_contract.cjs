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
test('registration is idempotent with a second resource evaluation',()=>{
  vm.runInNewContext(fs.readFileSync(path.join(__dirname,'../uninus-nutriculture-card.js'),'utf8'),context);
  assert.equal(elements.size,2);assert.equal(context.window.customCards.length,1);
  assert.equal(elements.get('uninus-nutriculture-card'),C);
});
