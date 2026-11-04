/* UNiNUS Nutriculture Card 0.2.0-alpha.1 — P1 shadow / P2 mapped native controls. */
(() => {
  'use strict';
  const TAG = 'uninus-nutriculture-card';
  const finite = value => (typeof value === 'number' || (typeof value === 'string' && value.trim() !== '')) && Number.isFinite(Number(value));
  const text = (node, value) => { const next = String(value ?? ''); if (node.textContent !== next) node.textContent = next; };
  const make = (tag, value, className) => { const el = document.createElement(tag); if (value !== undefined) text(el, value); if (className) el.className = className; return el; };
  const PARAMETERS = [
    ['level_low','液位下限',2.25,'m'],['level_high','液位上限',2.4,'m'],
    ['ph_low','pH 下限',5.4,''],['ph_high','pH 上限',5.8,''],
    ['ec_low','EC 下限',0.8,'mS/cm'],['ec_high','EC 上限',0.9,'mS/cm'],
    ['refill_timeout','補水逾時',190,'min'],['ec_timeout','EC 逾時',90,'min'],
    ['ph_timeout','pH 逾時',190,'min'],['mix_duration','混合時間',10,'min']
  ];
  const FLOW_STATES = ['uncommissioned','disabled','idle','starting','refilling','stopping','completed','aborted','fault'];
  const isShadow = status => status?.attributes?.schema_version === 1 && status.attributes.mode === 'shadow';
  const V3_STATES = [...FLOW_STATES,'waiting_resource','dosing','mixing','waiting_sample','stabilizing'];
  const DOSE = [
    ['safe_min_level_m','最低安全液位',0,10,.01,'m'],['pulse_seconds','單次脈衝',1,86400,1,'s'],
    ['max_total_on_seconds','累積 ON 預算',1,86400,1,'s'],['max_pulses','最大脈衝數',1,1000,1,''],
    ['post_mix_seconds','必要混合',1,86400,1,'s'],['sample_wait_timeout_seconds','新樣本等待',1,86400,1,'s'],
    ['stable_samples','穩定樣本數',1,100,1,''],['stable_interval_seconds','穩定樣本間隔',1,86400,1,'s'],
    ['flow_timeout_seconds','整輪期限',1,86400,1,'s'],['ph_danger_low','危險低 pH',0,14,.1,'pH'],
    ['ec_danger_high','危險高 EC',0,100,.01,'mS/cm'],['ph_high_alarm','高 pH 告警',0,14,.1,'pH'],
    ['ph_high_alarm_seconds','高 pH 告警延遲',1,86400,1,'s']
  ];
  const STAGES = ['refill','nutrient','acid','mix'], DAYS = ['mon','tue','wed','thu','fri','sat','sun'];
  const exact = (obj,keys) => obj && typeof obj === 'object' && !Array.isArray(obj) && Object.keys(obj).length === keys.length && keys.every(k=>Object.hasOwn(obj,k));
  const number = v => typeof v === 'number' && Number.isFinite(v);
  const inRange = (v,min,max,step) => number(v) && v>=min && v<=max && Math.abs((v-min)/step-Math.round((v-min)/step))<1e-6;
  const validGroups = a => exact(a.parameters,PARAMETERS.map(r=>r[0])) && Object.values(a.parameters).every(number) &&
    exact(a.dosing_parameters,DOSE.map(r=>r[0])) && DOSE.every(([k,,min,max,step])=>inRange(a.dosing_parameters[k],min,max,step)) &&
    exact(a.allowed_weekdays,STAGES) && STAGES.every(k=>Array.isArray(a.allowed_weekdays[k]) && new Set(a.allowed_weekdays[k]).size===a.allowed_weekdays[k].length && a.allowed_weekdays[k].every(d=>DAYS.includes(d)));
  const validV3 = a => a.ready_for_irrigation === false && exact(a.capabilities,STAGES) && STAGES.every(k=>typeof a.capabilities[k]==='boolean') && !a.capabilities.acid && !a.capabilities.mix &&
    exact(a.settings_target,['config_entry_id','service']) && typeof a.settings_target.config_entry_id === 'string' && a.settings_target.config_entry_id.trim()!=='' && a.settings_target.service==='apply_control_settings' &&
    Number.isSafeInteger(a.settings_revision) && a.settings_revision>=0 && validGroups(a) &&
    exact(a.parameter_entities,PARAMETERS.map(r=>r[0])) && Object.values(a.parameter_entities).every(id=>typeof id==='string' && /^number\.[a-z0-9_]+$/.test(id)) && new Set(Object.values(a.parameter_entities)).size===10 &&
    a.control_entities && Object.entries(a.control_entities).every(([k,id])=>['automation_enabled','refill_enabled','nutrient_enabled','flow_run','emergency_stop','reset_fault'].includes(k) && typeof id==='string' && new RegExp(`^${['emergency_stop','reset_fault'].includes(k)?'button':'switch'}\\.[a-z0-9_]+$`).test(id) && (k!=='nutrient_enabled'||a.capabilities.nutrient)) && new Set(Object.values(a.control_entities)).size===Object.values(a.control_entities).length &&
    exact(a.stage_states,STAGES) && ['unsupported','idle','starting','waiting_resource','running','stopping','completed','aborted','fault','skipped_disabled','skipped_weekday','blocked_dependency'].includes(a.stage_states.nutrient) && FLOW_STATES.concat(['running','skipped_disabled','skipped_weekday','blocked_dependency','unsupported']).includes(a.stage_states.refill) && a.stage_states.acid==='unsupported' && a.stage_states.mix==='unsupported' &&
    [null,'starting_circulation','pulsing','confirming_off','mixing','waiting_sample','stabilizing'].includes(a.nutrient_phase) &&
    exact(a.dose_progress,['pulse_count','reserved_on_seconds','stable_count']) && ['pulse_count','stable_count'].every(k=>Number.isSafeInteger(a.dose_progress[k]) && a.dose_progress[k]>=0) && number(a.dose_progress.reserved_on_seconds) && a.dose_progress.reserved_on_seconds>=0 &&
    exact(a.output_states,['nutrient','circulation']) && Object.values(a.output_states).every(v=>['on','off','unknown'].includes(v));

  const Q=DOSE.slice(0,9), S=DOSE.slice(9), STAGE_VALUES=['unsupported','idle','starting','waiting_resource','running','stopping','completed','aborted','fault','skipped_disabled','skipped_weekday','blocked_dependency'];
  const groupMap=(m,rows)=>exact(m,rows.map(r=>r[0]))&&rows.every(([k,,lo,hi,step])=>inRange(m[k],lo,hi,step));
  const NORMAL_LIMITS={level_low:[0,10,.01],level_high:[0,10,.01],ph_low:[0,14,.1],ph_high:[0,14,.1],ec_low:[0,20,.01],ec_high:[0,20,.01],refill_timeout:[1,1440,1],ec_timeout:[1,1440,1],ph_timeout:[1,1440,1],mix_duration:[1,1440,1]};
  const V4_KEYS=['schema_version','mode','ready_for_irrigation','source_entities','parameter_entities','parameters','reasons','capabilities','control_entities','allowed_weekdays','stage_states','flow_state','fault','run_id','settings_target','settings_revision','dosing_parameters','acid_parameters','mix_parameters','safety_parameters','nutrient_phase','acid_phase','dose_progress','acid_progress','output_states'];
  // Only these native HA Entity metadata fields may sit outside our contract.
  const HA_METADATA=['friendly_name','icon','device_class','options'];
  const validV4Groups=a=>exact(a.parameters,PARAMETERS.map(r=>r[0]))&&Object.entries(NORMAL_LIMITS).every(([k,limits])=>inRange(a.parameters[k],...limits))&&['level','ph','ec'].every(k=>a.parameters[k+'_low']<a.parameters[k+'_high'])&&groupMap(a.safety_parameters,S)&&
    (a.dosing_parameters===null||groupMap(a.dosing_parameters,DOSE))&&(a.acid_parameters===null||groupMap(a.acid_parameters,Q))&&(a.mix_parameters===null||groupMap(a.mix_parameters,[Q[0],Q[8]]))&&
    (a.dosing_parameters===null||S.every(([k])=>a.dosing_parameters[k]===a.safety_parameters[k]))&&
    exact(a.allowed_weekdays,STAGES)&&STAGES.every(k=>Array.isArray(a.allowed_weekdays[k])&&new Set(a.allowed_weekdays[k]).size===a.allowed_weekdays[k].length&&a.allowed_weekdays[k].every(d=>DAYS.includes(d)));
  const progress=v=>exact(v,['pulse_count','reserved_on_seconds','stable_count'])&&['pulse_count','stable_count'].every(k=>Number.isSafeInteger(v[k])&&v[k]>=0)&&number(v.reserved_on_seconds)&&v.reserved_on_seconds>=0;
  const phase=v=>[null,'starting_circulation','pulsing','confirming_off','mixing','waiting_sample','stabilizing'].includes(v);
  const validV4=a=>V4_KEYS.every(k=>Object.hasOwn(a,k))&&Object.keys(a).every(k=>V4_KEYS.includes(k)||HA_METADATA.includes(k))&&V3_STATES.includes(a.flow_state)&&a.ready_for_irrigation===false&&validV4Groups(a)&&exact(a.capabilities,STAGES)&&STAGES.every(k=>typeof a.capabilities[k]==='boolean')&&
    ['nutrient','acid','mix'].every((k,i)=>(a[['dosing_parameters','acid_parameters','mix_parameters'][i]]!==null)===a.capabilities[k])&&
    exact(a.source_entities,['ph','ec','level'])&&Object.values(a.source_entities).every(id=>typeof id==='string'&&/^sensor\.[a-z0-9_]+$/.test(id))&&
    exact(a.settings_target,['config_entry_id','service'])&&typeof a.settings_target.config_entry_id==='string'&&a.settings_target.config_entry_id.trim()!==''&&a.settings_target.service==='apply_control_settings_v4'&&Number.isSafeInteger(a.settings_revision)&&a.settings_revision>=0&&
    a.parameter_entities&&typeof a.parameter_entities==='object'&&!Array.isArray(a.parameter_entities)&&Object.entries(a.parameter_entities).every(([k,id])=>PARAMETERS.some(r=>r[0]===k)&&typeof id==='string'&&/^number\.[a-z0-9_]+$/.test(id))&&new Set(Object.values(a.parameter_entities)).size===Object.keys(a.parameter_entities).length&&
    a.control_entities&&Object.entries(a.control_entities).every(([k,id])=>['automation_enabled','refill_enabled','nutrient_enabled','acid_enabled','mix_enabled','flow_run','emergency_stop','reset_fault'].includes(k)&&typeof id==='string'&&new RegExp(`^${['emergency_stop','reset_fault'].includes(k)?'button':'switch'}\\.[a-z0-9_]+$`).test(id)&&(!k.endsWith('_enabled')||k==='automation_enabled'||a.capabilities[k.replace('_enabled','')]))&&new Set(Object.values(a.control_entities)).size===Object.keys(a.control_entities).length&&
    exact(a.stage_states,STAGES)&&STAGES.every(k=>STAGE_VALUES.includes(a.stage_states[k]))&&phase(a.nutrient_phase)&&phase(a.acid_phase)&&progress(a.dose_progress)&&progress(a.acid_progress)&&
    exact(a.output_states,['nutrient','acid','circulation'])&&Object.values(a.output_states).every(v=>['on','off','unknown'].includes(v))&&Array.isArray(a.reasons)&&a.reasons.every(v=>typeof v==='string')&&['fault','run_id'].every(k=>a[k]===null||(typeof a[k]==='string'&&a[k].trim()!==''));

  const RULES=['flow_start','after_previous_started','after_previous_finished'];
  const PHASE5=[null,'starting','starting_circulation','refilling','pulsing','confirming_off','mixing','waiting_sample','stabilizing','waiting_delay','waiting_condition','waiting_resource','stopping'];
  const RESULTS5=[null,'completed','aborted','fault','skipped_disabled','skipped_weekday','blocked_dependency'];
  const REASONS5=[null,'delay_pending','condition_not_met','level_unsafe','resource_chemical','resource_circulation','source_unavailable','source_stale','dependency_not_started','output_confirmation_pending'];
  const STATES5=[...V3_STATES,'running','waiting_delay','waiting_condition'];
  const revision=v=>Number.isSafeInteger(v)&&v>=0;
  const sameValue=(a,b)=>Array.isArray(a)?Array.isArray(b)&&a.length===b.length&&a.every((v,i)=>sameValue(v,b[i])):a!==null&&typeof a==='object'?b!==null&&typeof b==='object'&&Object.keys(a).length===Object.keys(b).length&&Object.keys(a).every(k=>Object.hasOwn(b,k)&&sameValue(a[k],b[k])):a===b;
  const weekdays=w=>exact(w,STAGES)&&STAGES.every(k=>Array.isArray(w[k])&&new Set(w[k]).size===w[k].length&&w[k].every(d=>DAYS.includes(d)));
  const validPlan=p=>exact(p,['rows','run_timeout_seconds'])&&inRange(p.run_timeout_seconds,1,86400,1)&&Array.isArray(p.rows)&&p.rows.length===4&&new Set(p.rows.map(r=>r?.stage)).size===4&&p.rows.every((r,i)=>exact(r,['stage','start_rule','delay_seconds','condition','wait_timeout_seconds'])&&STAGES.includes(r.stage)&&RULES.includes(r.start_rule)&&(i!==0||r.start_rule==='flow_start')&&inRange(r.delay_seconds,0,86400,1)&&inRange(r.wait_timeout_seconds,1,86400,1)&&(r.condition===null||(exact(r.condition,['source','operator','value'])&&['level','ph','ec'].includes(r.condition.source)&&['gte','lte'].includes(r.condition.operator)&&number(r.condition.value)&&r.condition.value>=0&&r.condition.value<=({level:10,ph:14,ec:20}[r.condition.source]))));
  const instant=v=>v===null||(typeof v==='string'&&/^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d{1,6})?(?:Z|\+00:00)$/.test(v)&&Number.isFinite(Date.parse(v)));
  const validV5=a=>{
    const extra=['flow_plan','flow_plan_revision','flow_plan_target','run_plan','step_runtime'];
    if(![...V4_KEYS,...extra].every(k=>Object.hasOwn(a,k))||!Object.keys(a).every(k=>[...V4_KEYS,...extra,...HA_METADATA].includes(k)))return false;
    if(!exact(a.output_states,['nutrient','acid','circulation','refill'])||!Object.values(a.output_states).every(v=>['on','off','unknown'].includes(v))||!STATES5.includes(a.flow_state))return false;
    if(!exact(a.flow_plan_target,['config_entry_id','service','preview_service'])||a.flow_plan_target.service!=='apply_flow_plan_v5'||a.flow_plan_target.preview_service!=='preview_flow_plan_v5'||a.settings_target?.service!=='apply_control_settings_v5'||a.flow_plan_target.config_entry_id!==a.settings_target.config_entry_id)return false;
    if(!validPlan(a.flow_plan)||!revision(a.flow_plan_revision)||!exact(a.step_runtime,STAGES))return false;
    for(const k of STAGES){const r=a.step_runtime[k];if(!exact(r,['phase','result','started_at','settled_at','waiting_reason'])||!PHASE5.includes(r.phase)||!RESULTS5.includes(r.result)||!REASONS5.includes(r.waiting_reason)||!instant(r.started_at)||!instant(r.settled_at)||((r.phase?.startsWith('waiting_')??false)!==(r.waiting_reason!==null))||(['skipped_disabled','skipped_weekday','blocked_dependency'].includes(r.result)&&r.started_at!==null))return false;}
    const run=a.run_plan;
    if(run!==null&&(!exact(run,['run_id','settings_revision','flow_plan_revision','flow_plan','allowed_weekdays','enabled_stages'])||typeof run.run_id!=='string'||!run.run_id.trim()||!revision(run.settings_revision)||!revision(run.flow_plan_revision)||!validPlan(run.flow_plan)||!weekdays(run.allowed_weekdays)||!exact(run.enabled_stages,STAGES)||!STAGES.every(k=>typeof run.enabled_stages[k]==='boolean')))return false;
    // Reuse strict v4 groups/mapping checks through an explicit projection, never downgrade the source.
    const base=Object.fromEntries(V4_KEYS.map(k=>[k,a[k]]));base.schema_version=4;base.settings_target={...a.settings_target,service:'apply_control_settings_v4'};base.flow_state=V3_STATES.includes(a.flow_state)?a.flow_state:'idle';base.output_states=Object.fromEntries(['nutrient','acid','circulation'].map(k=>[k,a.output_states[k]]));
    if(!STAGES.every(k=>[...STAGE_VALUES,'waiting_delay','waiting_condition'].includes(a.stage_states[k])))return false;
    base.stage_states=Object.fromEntries(STAGES.map(k=>[k,['waiting_delay','waiting_condition'].includes(a.stage_states[k])?'waiting_resource':a.stage_states[k]]));
    if(!PHASE5.includes(a.nutrient_phase)||!PHASE5.includes(a.acid_phase))return false;
    base.nutrient_phase=phase(a.nutrient_phase)?a.nutrient_phase:null;base.acid_phase=phase(a.acid_phase)?a.acid_phase:null;
    return validV4(base);
  };
  const isControl = status => status?.attributes?.mode === 'control' && (status.attributes.schema_version === 2 ? !['nutrient','acid','mix'].some(k=>status.attributes.capabilities?.[k]===true) && !status.attributes.control_entities?.nutrient_enabled : (status.attributes.schema_version === 3 && validV3(status.attributes)) || (status.attributes.schema_version === 4 && validV4(status.attributes)) || (status.attributes.schema_version === 5 && validV5(status.attributes)));
  const writable = status => (isShadow(status) && ['within_range','out_of_range','invalid'].includes(status.state)) || (isControl(status) && (status.attributes.schema_version===5?STATES5:status.attributes.schema_version>=3?V3_STATES:FLOW_STATES).includes(status.state) && status.attributes.flow_state === status.state);
  const style = `
    :host{display:block;min-width:0;color:var(--primary-text-color,#213b48);font-family:var(--paper-font-body1_-_font-family,system-ui,sans-serif)}
    *{box-sizing:border-box}ha-card{display:block;border:1px solid var(--divider-color,#d9e4e7);border-radius:var(--ha-card-border-radius,16px);background:var(--ha-card-background,var(--card-background-color,#fff));padding:18px;overflow-wrap:anywhere}
    h2{font-size:19px;line-height:1.35;margin:0}header p{color:var(--secondary-text-color,#607782);font-size:13px;margin:4px 0 12px}.badge{display:inline-block;color:var(--primary-color,#277b86);background:var(--secondary-background-color,#edf5f6);border-radius:8px;padding:4px 8px;font-size:12px}
    .safety{border-left:3px solid var(--primary-color,#277b86);padding:8px 10px;margin:12px 0;font-size:13px;background:var(--secondary-background-color,#edf5f6)}
    .tiles{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px}.tile{min-width:0;background:var(--secondary-background-color,#f2f7f8);padding:12px 8px;border-radius:10px}.tile span{display:block;color:var(--secondary-text-color,#607782);font-size:12px}.tile strong{display:block;font-size:22px;font-variant-numeric:tabular-nums;margin:6px 0}.tile small{font-size:11px;overflow-wrap:anywhere}
    .quality{font-size:13px;margin:12px 0 0;white-space:pre-line}.quality.warn{color:var(--error-color,#a44e28)}
    details{margin-top:16px;border-top:1px solid var(--divider-color,#d9e4e7);padding-top:12px}summary{cursor:pointer;font-size:14px;font-weight:600;min-height:32px}details>p{font-size:12px;color:var(--secondary-text-color,#607782)}
    .param{display:grid;grid-template-columns:minmax(0,1fr) minmax(70px,110px) 64px;gap:6px 10px;align-items:center;padding:10px 0;border-top:1px solid var(--divider-color,#d9e4e7)}.param label{font-size:13px;min-width:0}.param small{display:block;font-size:11px;color:var(--secondary-text-color,#607782);margin-top:3px}.param .message{grid-column:1/-1;font-size:12px;white-space:pre-line;color:var(--secondary-text-color,#607782)}
    input,button{font:inherit;min-width:0;max-width:100%;border-radius:7px;padding:9px 7px;border:1px solid var(--divider-color,#cddce1);color:inherit;background:var(--card-background-color,#fff)}input{width:100%;font-size:14px}button{cursor:pointer;font-size:13px;color:var(--primary-color,#277b86)}button:disabled{cursor:not-allowed;opacity:.5}:focus-visible{outline:2px solid var(--primary-color,#277b86);outline-offset:2px}
    .control{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:8px;align-items:center;padding:9px 0;border-top:1px solid var(--divider-color,#d9e4e7)}.control button{min-width:64px;min-height:40px}.control small{grid-column:1/-1;white-space:pre-line;font-size:12px}.control p,[data-control-status]{white-space:pre-line}
    :host{container-type:inline-size}.group-param{grid-template-columns:minmax(0,1fr) minmax(70px,110px)}fieldset{min-width:0;border:1px solid var(--divider-color,#d9e4e7);margin:8px 0}fieldset label{display:inline-flex;align-items:center;gap:4px;margin:4px}fieldset input{width:auto;min-height:24px} [data-group-message]{font-size:12px;white-space:pre-line} [data-group-settings]>button{margin:10px 6px 0 0;min-height:40px}
    @container(max-width:360px){ha-card{padding:12px}.tile strong{font-size:20px}.tile{padding:10px 6px}}
  `;
  class NutricultureCard extends HTMLElement {
    constructor() {
      super(); this.attachShadow({mode:'open'});
      const css = make('style', style); this.root = make('ha-card');
      const header = make('header'); this.heading = make('h2','UNiNUS Nutriculture');
      this.badge = make('span','影子監測','badge');
      header.append(this.heading,make('p','養液控制'),this.badge);
      this.safety = make('div','不控制設備 · 尚未提供灌溉許可','safety');
      const tiles = make('section',undefined,'tiles'); tiles.setAttribute('aria-label','即時來源讀值');
      this.readings = {};
      for (const [key,label] of [['ph','pH 酸鹼值'],['ec','EC 導電度'],['level','液位']]) {
        const tile = make('div',undefined,'tile'); tile.dataset.reading = key;
        const value = make('strong','—'), unit = make('small','');
        tile.append(make('span',label),value,unit); tiles.append(tile); this.readings[key] = {value,unit};
      }
      this.quality = make('div','','quality'); this.quality.setAttribute('role','status');
      this.root.append(header,this.safety,tiles,this.quality); this.shadowRoot.append(css,this.root);
      this.rows = new Map(); this.flights = new Map();
      this.controls = make('section'); this.controls.dataset.controls = '';
      this.controlStatus = make('p'); this.controlStatus.dataset.controlStatus = ''; this.controlStatus.setAttribute('role','status');
      this.unsupported = make('p'); this.unsupported.dataset.unsupported = '';
      this.controls.append(this.controlStatus,this.unsupported);
      this.controlRows = new Map();
      for (const [key,label,domain] of [['automation_enabled','自動化總開關','switch'],['refill_enabled','補水子開關','switch'],['nutrient_enabled','加養子開關','switch'],['acid_enabled','加酸子開關','switch'],['mix_enabled','獨立攪拌子開關','switch'],['flow_run','整輪運行','switch'],['emergency_stop','急停','button'],['reset_fault','復歸','button']]) {
        const el = make('div',undefined,'control'); el.dataset.control = key;
        const caption = make('span'), button = make('button',label), message = make('small');
        button.type = 'button'; button.setAttribute('aria-label',label); message.setAttribute('role','status');
        const row = {key,label,domain,el,caption,button,message,error:''};
        button.addEventListener('click',()=>this.invokeControl(row));
        el.append(caption,button,message); this.controls.append(el); this.controlRows.set(key,row);
      }
      this.details = make('details');
      this.parameterHelp = make('p','每次僅儲存一項，不提供群組原子更新。時間參數僅儲存，不控制設備。');
      this.details.append(make('summary','參數調整 · 單項儲存'),this.parameterHelp);
      for (const [key,label,initial,unit] of PARAMETERS) {
        const el = make('div',undefined,'param'); el.dataset.param = key;
        const caption = make('label',label); caption.htmlFor = key;
        const metadata = make('small'); caption.append(metadata);
        const input = make('input'); input.type = 'number'; input.id = key; input.inputMode = 'decimal';
        const button = make('button','儲存'); button.type = 'button'; button.setAttribute('aria-label',`儲存 ${label}`);
        const message = make('div','','message'); message.setAttribute('role','status');
        const row = {key,el,metadata,input,button,message,initial,unit,dirty:false,pending:false,error:''};
        input.addEventListener('input',()=>{row.dirty = true; row.error = ''; if(this.status()?.attributes?.schema_version>=3){this.beginGroup();this.groupMessageText='';} this.updateRows();this.updateGroup();});
        button.addEventListener('click',()=>this.save(row));
        el.append(caption,input,button,message); this.rows.set(key,row); this.details.append(el);
      }
      this.groupPanel = make('section'); this.groupPanel.dataset.groupSettings='';
      this.midpoint = make('p'); this.midpoint.dataset.midpoint='';
      this.doseDetails=make('details'); this.doseDetails.dataset.doseDetails=''; this.doseDetails.append(make('summary','安全與劑量 · 工程限制，非設備認證'));
      this.doseRows=new Map();
      for(const [key,label,min,max,step,unit] of DOSE){
        const el=make('div',undefined,'param'); el.dataset.dose=key;
        const caption=make('label',`${label} (${unit || '次'})`), input=make('input'); input.type='number'; input.id=`dose_${key}`;caption.htmlFor=input.id;
        for(const [k,v] of Object.entries({min,max,step}))input.setAttribute(k,String(v));
        input.addEventListener('input',()=>{this.beginGroup();this.groupMessageText='';this.updateGroup();});
        el.append(caption,input);this.doseDetails.append(el);this.doseRows.set(key,{input});
      }
      this.acidRows=new Map();this.mixRows=new Map();
      for(const [name,rows,map] of [['acid',Q,this.acidRows],['mix',[Q[0],Q[8]],this.mixRows]])for(const [key,label,min,max,step,unit] of rows){
        const el=make('div',undefined,'param');el.dataset[name]=key;const input=make('input');input.type='number';
        for(const [k,v] of Object.entries({min,max,step}))input.setAttribute(k,String(v));
        input.addEventListener('input',()=>{this.beginGroup();this.groupMessageText='';this.updateGroup();});
        el.append(make('label',`${name==='acid'?'加酸':'獨立攪拌'} · ${label} (${unit||'次'})`),input);this.doseDetails.append(el);map.set(key,{input,el});
      }
      this.weekDetails=make('details');this.weekDetails.dataset.weekDetails='';this.weekDetails.append(make('summary','各階段允許星期'));
      this.weekRows=new Map();
      for(const [i,stage] of STAGES.entries()){
        const block=make('fieldset');block.append(make('legend',['補水','加養','加酸','獨立攪拌'][i]));
        const inputs=new Map();for(const [j,day] of DAYS.entries()){
          const label=make('label',['一','二','三','四','五','六','日'][j]),input=make('input');input.type='checkbox';input.dataset.weekday=stage+'_'+day;
          input.addEventListener('change',()=>{this.beginGroup();this.groupMessageText='';this.updateGroup();});label.prepend(input);block.append(label);inputs.set(day,input);
        }this.weekDetails.append(block);this.weekRows.set(stage,inputs);
      }
      this.groupApply=make('button','Apply · 套用整組');this.groupApply.type='button';this.groupApply.dataset.groupApply='';this.groupApply.addEventListener('click',()=>this.applyGroup());
      this.groupCancel=make('button','Cancel · 重新載入');this.groupCancel.type='button';this.groupCancel.dataset.groupCancel='';this.groupCancel.addEventListener('click',()=>{this.groupDraft=null;this.groupOperation=null;this.groupMessageText='已取消草稿；重新載入後端值';this.update();});
      this.groupMessage=make('p');this.groupMessage.dataset.groupMessage='';this.groupMessage.setAttribute('role','status');
      this.groupPanel.append(this.midpoint,this.doseDetails,this.weekDetails,this.groupApply,this.groupCancel,this.groupMessage);
      this.root.append(this.details); this.updateRows();
    }
    static getConfigElement() { return document.createElement(`${TAG}-editor`); }
    static getStubConfig(hass) {
      const entity = Object.keys(hass?.states ?? {}).find(id => /^sensor\.[a-z0-9_]+$/.test(id) && (isShadow(hass.states[id]) || isControl(hass.states[id])));
      return {entity:entity ?? 'sensor.uninus_nutriculture_status',show_parameters:true};
    }
    getCardSize() { return this.details.isConnected && this.details.open ? 12 : 4; }
    connectedCallback() { this.update(); }
    disconnectedCallback() { this.invalidate(); }
    invalidate() {
      this.epoch = (this.epoch ?? 0) + 1;this.planOperation=null;this.previewOperation=null;this.planEpoch=(this.planEpoch??0)+1;
      this.groupOperation=null;
      for (const row of this.rows.values()) { row.operation = null; row.pending = false; }
      for (const row of this.controlRows.values()) { row.operation = null; row.error = ''; }
    }
    setConfig(config) {
      if (!config || typeof config.entity !== 'string' || !/^sensor\.[a-z0-9_]+$/.test(config.entity)) throw new Error('請選擇狀態 sensor Entity');
      this.invalidate();
      if (this.config?.entity !== config.entity) {
        for (const row of this.rows.values()) { row.dirty = false; row.error = ''; }
        this.details.open = false;
      }
      this.config = {...config};
      if (config.show_parameters === false) this.details.remove();
      else if (this.details.parentNode !== this.root) this.root.append(this.details);
      this.update();
    }
    set hass(hass) { this._hass = hass; this.update(); }
    get hass() { return this._hass; }
    status() { return this._hass?.states?.[this.config?.entity]; }
    target(row) {
      const status = this.status();
      if (!writable(status)) return {error:'狀態缺失或不相容；禁止儲存'};
      const id = status.attributes.parameter_entities?.[row.key];
      if (typeof id !== 'string' || !/^number\.[a-z0-9_]+$/.test(id)) return {error:'Number 對應無效；禁止儲存'};
      const state = this._hass?.states?.[id];
      if (!finite(state?.state)) return {error:'Number 缺失或無法使用；禁止儲存'};
      const {min,max,step,unit_of_measurement:unit} = state.attributes ?? {};
      if (![min,max,step].every(finite) || Number(min)>Number(max) || Number(step)<=0) return {error:'Number metadata 無效；禁止儲存'};
      return {id,state,min:Number(min),max:Number(max),step:Number(step),unit:unit ?? row.unit};
    }
    valid(row,target) {
      if (target.error || !finite(row.input.value)) return false;
      const value = Number(row.input.value), ticks = (value-target.min)/target.step;
      return value>=target.min && value<=target.max && Math.abs(ticks-Math.round(ticks))<1e-6;
    }
    updateRows() {
      if (!this.rows) return;
      const v3=this.status()?.attributes?.schema_version>=3;
      for (const row of this.rows.values()) {
        const target = this.target(row);
        row.button.hidden=v3;row.el.classList.toggle('group-param',v3);
        if (row.boundTarget !== target.id) {
          if (row.dirty) row.error = 'Number 對應已變更；舊草稿已清除，請重新輸入';
          row.boundTarget = target.id; row.dirty = false; row.pending = false; row.operation = null;
        }
        if (!row.dirty && !row.pending && !(v3 && this.groupDraft)) {
          const value = v3 ? this.status()?.attributes?.parameters?.[row.key] : target.state?.state ?? this.status()?.attributes?.parameters?.[row.key];
          const next = finite(value) ? String(value) : '';
          if (row.input.value !== next) row.input.value = next;
        }
        for (const key of ['min','max','step']) {
          if (!target.error) row.input.setAttribute(key,String(target[key])); else row.input.removeAttribute(key);
        }
        text(row.metadata,target.error ? `預設 ${row.initial} ${row.unit}` : `${target.min}–${target.max} ${target.unit} · 間距 ${target.step}`);
        row.input.disabled = row.pending || !!target.error || (v3 && !!this.groupOperation);
        row.button.disabled = row.pending || this.flights.has(target.id) || !row.dirty || !this.valid(row,target);
        text(row.button,row.pending ? '儲存中' : '儲存');
        text(row.message,target.error || row.error || (row.dirty && !this.valid(row,target) ? '請輸入範圍內、符合間距的有限數值' : ''));
      }
    }
    async save(row) {
      if(this.status()?.attributes?.schema_version>=3)return;
      const target = this.target(row);
      if (row.boundTarget !== target.id) { this.updateRows(); return; }
      if (!this.isConnected || this.config?.show_parameters === false || this.flights.has(target.id) || row.pending || !row.dirty || !this.valid(row,target) || !this._hass?.callService) return;
      // Snapshot ownership and payload before the first deferred boundary.
      const op = {epoch:this.epoch,entity:this.config.entity,target:target.id,value:Number(row.input.value)};
      this.flights.set(op.target,op);
      row.operation = op; row.pending = true; row.error = ''; this.updateRows();
      const current = () => this.isConnected && this.epoch === op.epoch && row.operation === op;
      try {
        await this._hass.callService('number','set_value',{entity_id:op.target,value:op.value});
        if (!current()) return;
        row.dirty = false; row.error = '已送出單項儲存；以 Entity 讀回值為準';
      } catch (error) {
        if (!current()) return;
        row.error = `儲存失敗：${error?.message ?? String(error)}`;
      } finally {
        if (this.flights.get(op.target) === op) this.flights.delete(op.target);
        if (current()) { row.operation = null; row.pending = false; this.updateRows(); }
        else if (this.isConnected) {
          // Release only the transport lock; never reconcile new-scope drafts/notices.
          for (const candidate of this.rows.values()) {
            const next = this.target(candidate);
            candidate.button.disabled = candidate.pending || this.flights.has(next.id) || !candidate.dirty || !this.valid(candidate,next);
          }
        }
      }
    }
    groupIdentity() {
      const a=this.status()?.attributes;
      return JSON.stringify([this.config?.entity,a?.settings_target,a?.parameter_entities]);
    }
    beginGroup() {
      if(!this.groupDraft && writable(this.status()) && this.status().attributes.schema_version>=3){
        const a=this.status().attributes;
        this.groupDraft={identity:this.groupIdentity(),revision:a.settings_revision,entry:a.settings_target.config_entry_id};
      }
    }
    groupValues() {
      if([4,5].includes(this.status()?.attributes?.schema_version)){
        const a=this.status().attributes, read=map=>Object.fromEntries([...map].map(([k,r])=>[k,r.input.value===''?null:Number(r.input.value)]));
        const all=read(this.doseRows),safety=Object.fromEntries(S.map(([k])=>[k,all[k]]));
        return {parameters:read(this.rows),dosing_parameters:a.capabilities.nutrient?{...all,...safety}:null,acid_parameters:a.capabilities.acid?read(this.acidRows):null,mix_parameters:a.capabilities.mix?read(this.mixRows):null,safety_parameters:safety,...(a.schema_version===5?{}:{allowed_weekdays:Object.fromEntries([...this.weekRows].map(([k,inputs])=>[k,[...inputs].filter(([,input])=>input.checked).map(([d])=>d)]))})};
      }
      return {parameters:Object.fromEntries([...this.rows].map(([k,r])=>[k,r.input.value===''?null:Number(r.input.value)])),
        dosing_parameters:Object.fromEntries([...this.doseRows].map(([k,r])=>[k,r.input.value===''?null:Number(r.input.value)])),
        allowed_weekdays:Object.fromEntries([...this.weekRows].map(([k,inputs])=>[k,[...inputs].filter(([,input])=>input.checked).map(([d])=>d)]))};
    }
    groupValid(values) {
      if([4,5].includes(this.status()?.attributes?.schema_version)){
        if(!validV4Groups({...values,allowed_weekdays:values.allowed_weekdays??this.status().attributes.allowed_weekdays})||![...this.rows.values()].every(r=>this.valid(r,this.target(r))))return false;
        const p=values.parameters,s=values.safety_parameters;
        return p.level_low<p.level_high&&p.ph_low<p.ph_high&&p.ec_low<p.ec_high&&s.ph_danger_low<p.ph_low&&s.ec_danger_high>p.ec_high&&[values.dosing_parameters,values.acid_parameters].every(d=>d===null||d.pulse_seconds<=d.max_total_on_seconds);
      }
      if(!validGroups(values) || ![...this.rows.values()].every(r=>this.valid(r,this.target(r))))return false;
      const p=values.parameters,d=values.dosing_parameters;
      return p.level_low<p.level_high && p.ph_low<p.ph_high && p.ec_low<p.ec_high && d.ph_danger_low<p.ph_low && d.ec_danger_high>p.ec_high && d.pulse_seconds<=d.max_total_on_seconds;
    }
    updateGroup() {
      if(!this.groupPanel)return;
      const status=this.status(),a=status?.attributes,v3=a?.schema_version>=3;
      text(this.details.firstChild,v3?'參數調整 · 整組 Apply / Cancel':'參數調整 · 單項儲存');
      if(!v3){this.groupPanel.remove();this.groupDraft=null;this.groupOperation=null;return;}
      if(this.groupPanel.parentNode!==this.details)this.details.append(this.groupPanel);
      text(this.parameterHelp,'完整十項參數、安全劑量與四階段星期一次套用；綁定與 commissioning 請使用原生 Options。後端整組驗證；草稿不影響設備。');
      const identity=this.groupIdentity();
      if(this.groupDraft && this.groupDraft.identity!==identity){this.groupDraft=null;this.groupOperation=null;this.groupMessageText='目標或映射已變更；舊草稿已清除';for(const r of this.rows.values())r.dirty=false;this.updateRows();}
      const op=this.groupOperation;
      if(op && op.settled && op.identity===identity && writable(status) && a.settings_revision>=op.revision && this.sameGroups(a,op.values)){
        this.groupOperation=null;this.groupDraft=null;this.groupMessageText=`已套用 · 後端 revision ${a.settings_revision} 讀回一致（非 fsync 保證）`;for(const r of this.rows.values())r.dirty=false;this.updateRows();
      }
      this.weekDetails.hidden=a?.schema_version===5;
      if(a?.schema_version===5)text(this.parameterHelp,'數值設定獨立套用；星期僅在流程編輯器與排序原子保存。Enable 決定納入，flow_run 啟動整輪。');
      const pending=!!this.groupOperation, usable=writable(status);
      if(!this.groupDraft){
        for(const [k,r] of this.rows){const v=a?.parameters?.[k];if(r.input.value!==String(v ?? ''))r.input.value=String(v ?? '');r.dirty=false;}
        for(const [k,r] of this.doseRows){const v=String(([4,5].includes(a?.schema_version)&&S.some(r=>r[0]===k)?a?.safety_parameters?.[k]:a?.dosing_parameters?.[k]) ?? '');if(r.input.value!==v)r.input.value=v;}
        for(const [stage,inputs] of this.weekRows)for(const [day,input] of inputs)input.checked=a?.allowed_weekdays?.[stage]?.includes(day)??false;
      }
      for(const [k,r] of this.doseRows){r.input.disabled=!usable||pending||([4,5].includes(a?.schema_version)&&Q.some(v=>v[0]===k)&&!a.capabilities.nutrient);r.input.parentNode.hidden=[4,5].includes(a?.schema_version)&&Q.some(v=>v[0]===k)&&!a.capabilities.nutrient;}
      for(const [name,map] of [['acid',this.acidRows],['mix',this.mixRows]])for(const [k,r] of map){
        r.el.hidden=![4,5].includes(a?.schema_version)||!a.capabilities?.[name];r.input.disabled=!usable||pending||r.el.hidden;
        if(!this.groupDraft){const v=String(a?.[name+'_parameters']?.[k]??'');if(r.input.value!==v)r.input.value=v;}
      }
      for(const inputs of this.weekRows.values())for(const input of inputs.values())input.disabled=!usable || pending;
      const values=this.groupValues(),valid=this.groupValid(values);
      const conflict=this.groupDraft && a?.settings_revision!==this.groupDraft.revision;
      this.groupApply.disabled=!this.isConnected || !usable || !this.groupDraft || pending || !valid || !!conflict || this.flights.has('settings:'+a?.settings_target?.config_entry_id) || this.config?.show_parameters===false;
      this.groupCancel.disabled=!this.isConnected || (!this.groupDraft && !this.groupOperation);
      text(this.midpoint,`EC 中點（唯讀）：${number(values.parameters.ec_low)&&number(values.parameters.ec_high)?Number(((values.parameters.ec_low+values.parameters.ec_high)/2).toFixed(5)):'—'} mS/cm`);
      text(this.groupMessage,(!usable?'狀態缺失或不相容；禁止儲存':this.groupMessageText) || (conflict?`settings_conflict：保留草稿；最新 revision ${a.settings_revision}，原 revision ${this.groupDraft.revision}。Cancel 重新載入最新值：${JSON.stringify({parameters:a.parameters,dosing_parameters:a.dosing_parameters,allowed_weekdays:a.allowed_weekdays})}`:this.groupDraft&&!valid?'請檢查完整群組的型別、範圍、間距與上下限':'尚未套用；後端設定為準'));
    }
    sameGroups(a,b) {
      if([4,5].includes(a.schema_version))return ['parameters','dosing_parameters','acid_parameters','mix_parameters','safety_parameters'].every(k=>b[k]===null?a[k]===null:a[k]!==null&&Object.keys(b[k]).every(key=>a[k]?.[key]===b[k][key]))&&(a.schema_version===5||STAGES.every(k=>JSON.stringify(a.allowed_weekdays[k])===JSON.stringify(b.allowed_weekdays[k])));
      return ['parameters','dosing_parameters'].every(group=>Object.keys(b[group]).every(k=>a[group]?.[k]===b[group][k])) && STAGES.every(k=>JSON.stringify([...(a.allowed_weekdays?.[k]??[])].sort())===JSON.stringify([...b.allowed_weekdays[k]].sort()));
    }
    async applyGroup() {
      this.updateGroup();
      if(this.groupApply.disabled || !this._hass?.callService)return;
      const a=this.status().attributes,draft=this.groupDraft,values=this.groupValues();
      const op={epoch:this.epoch,identity:this.groupIdentity(),revision:draft.revision,entry:draft.entry,values,settled:false};
      // Never use an unvalidated cached target to route a changed scope.
      if(op.identity!==draft.identity || a.settings_target.config_entry_id!==op.entry || a.settings_revision!==op.revision)return;
      const key='settings:'+op.entry;this.flights.set(key,op);this.groupOperation=op;this.groupMessageText='套用中；等待服務與後端 revision / 值讀回';this.update();
      const current=()=>this.isConnected && this.epoch===op.epoch && this.groupOperation===op && this.groupIdentity()===op.identity;
      try {
        await this._hass.callService('uninus_nutriculture',a.settings_target.service,{config_entry_id:op.entry,expected_revision:op.revision,...values});
        if(current()){op.settled=true;this.groupMessageText='已送出；等待後端 revision / 值讀回一致';}
      } catch(error){if(current()){this.groupOperation=null;this.groupMessageText=`套用失敗（保留草稿）：${error?.message??String(error)}`;}}
      finally {if(this.flights.get(key)===op)this.flights.delete(key);if(current() || this.isConnected)this.update();}
    }
    planIdentity() {const a=this.status()?.attributes;return JSON.stringify([this.config?.entity,a?.flow_plan_target]);}
    beginPlan() {
      const a=this.status()?.attributes;
      if(!writable(this.status())||a.schema_version!==5)return null;
      if(!this.planDraft)this.planDraft={identity:this.planIdentity(),entry:a.flow_plan_target.config_entry_id,revision:a.settings_revision,planRevision:a.flow_plan_revision,flow_plan:structuredClone(a.flow_plan),allowed_weekdays:structuredClone(a.allowed_weekdays)};
      return this.planDraft;
    }
    editPlan(change) {const d=this.beginPlan();if(!d||this.planOperation)return;change(d);this.planEpoch=(this.planEpoch??0)+1;this.previewOperation=null;this.previewResults=null;this.planNotice='';this.updatePlan();}
    createPlanPanel() {
      this.planPanel=make('section');this.planPanel.dataset.flowEditor='';this.planPanel.append(make('h3','四階段流程 · 下輪生效'),make('p','Enable 使用原生子開關；允許重疊不保證同時啟動，實際資源與安全由後端仲裁。跨午夜由真正 admission 當日決定，不保證完成時間。'));
      this.planRows=new Map();this.planBody=make('div');this.planBody.setAttribute('role','table');this.planPanel.append(this.planBody);
      const field=(parent,label,node)=>{const el=make('label',label);el.append(node);parent.append(el);return node;};
      for(const stage of STAGES){
        const el=make('fieldset');el.dataset.flowRow=stage;el.setAttribute('role','row');el.append(make('legend',stage));
        const row={el};
        for(const [dir,delta] of [['up',-1],['down',1]]){const b=make('button',dir==='up'?'↑ 上移':'↓ 下移');b.type='button';b.dataset.move=dir;b.addEventListener('click',()=>this.editPlan(d=>{const i=d.flow_plan.rows.findIndex(r=>r.stage===stage),j=i+delta;if(j>=0&&j<4)[d.flow_plan.rows[i],d.flow_plan.rows[j]]=[d.flow_plan.rows[j],d.flow_plan.rows[i]];}));el.append(b);row[dir]=b;}
        const select=(label,key,options)=>{const s=make('select');s.dataset.flowField=key;for(const v of options){const o=make('option',v||'無條件');o.value=v;s.append(o);}field(el,label,s);return s;};
        row.rule=select('起始規則 ','start_rule',RULES);
        const num=(label,key,min)=>{const n=make('input');n.type='number';n.min=String(min);n.max='86400';n.step='1';n.dataset.flowField=key;field(el,label,n);return n;};
        row.delay=num('延遲秒 ','delay_seconds',0);row.wait=num('等待期限秒 ','wait_timeout_seconds',1);
        row.source=select('條件來源 ','source',['','level','ph','ec']);row.operator=select('比較 ','operator',['gte','lte']);row.value=num('條件有限值 ','value',0);row.value.step='any';row.value.max='20';
        for(const [key,node] of [['start_rule',row.rule],['delay_seconds',row.delay],['wait_timeout_seconds',row.wait],['condition',row.source],['condition',row.operator],['condition',row.value]])node.addEventListener(node.tagName==='SELECT'?'change':'input',()=>this.editPlan(d=>{const r=d.flow_plan.rows.find(r=>r.stage===stage);if(key==='condition')r.condition=row.source.value?{source:row.source.value,operator:row.operator.value,value:row.value.value===''?null:Number(row.value.value)}:null;else r[key]=key==='start_rule'?node.value:node.value===''?null:Number(node.value);}));
        row.days=new Map();for(const day of DAYS){const n=make('input');n.type='checkbox';n.dataset.flowDay=day;field(el,day,n);n.addEventListener('change',()=>this.editPlan(d=>{d.allowed_weekdays[stage]=DAYS.filter(k=>row.days.get(k).checked);}));row.days.set(day,n);}
        row.runtime=make('p');row.runtime.dataset.stepRuntime=stage;el.append(row.runtime);this.planRows.set(stage,row);
      }
      this.runTimeout=make('input');this.runTimeout.type='number';this.runTimeout.min='1';this.runTimeout.max='86400';this.runTimeout.step='1';this.runTimeout.dataset.runTimeout='';field(this.planPanel,'整輪期限秒 ',this.runTimeout);this.runTimeout.addEventListener('input',()=>this.editPlan(d=>{d.flow_plan.run_timeout_seconds=this.runTimeout.value===''?null:Number(this.runTimeout.value);}));
      for(const [key,label,fn] of [['Apply','Apply · 原子保存',()=>this.applyPlan()],['Cancel','Cancel · 捨棄草稿',()=>{this.planEpoch=(this.planEpoch??0)+1;this.planDraft=null;this.planOperation=null;this.previewOperation=null;this.previewResults=null;this.planNotice='已取消草稿';this.updatePlan();}],['Preview','Preview · 七日後端預覽',()=>this.previewPlan()]]){const b=make('button',label);b.type='button';b.dataset['plan'+key]='';b.addEventListener('click',fn);this['plan'+key]=b;this.planPanel.append(b);}
      this.planMessage=make('p');this.planMessage.dataset.planMessage='';this.planMessage.setAttribute('role','status');this.previewView=make('div');this.previewView.dataset.previewResults='';this.planPanel.append(this.planMessage,this.previewView);
    }
    updatePlan() {
      if(!this.planPanel)this.createPlanPanel();
      const a=this.status()?.attributes,usable=a?.schema_version===5&&writable(this.status());
      if(!usable){this.planPanel.remove();this.planOperation=null;this.previewOperation=null;this.planEpoch=(this.planEpoch??0)+1;return;}
      const identity=this.planIdentity();if(this.planDraft&&this.planDraft.identity!==identity){this.planDraft=null;this.planOperation=null;this.previewOperation=null;this.previewResults=null;this.planNotice='目標已改變；舊草稿清除';this.planEpoch=(this.planEpoch??0)+1;}
      if(this.planPanel.parentNode!==this.root)this.root.append(this.planPanel);
      const op=this.planOperation;
      if(op?.settled&&op.epoch===this.epoch&&op.identity===identity&&op.draft===this.planDraft&&a.settings_revision===op.response.settings_revision&&a.flow_plan_revision===op.response.flow_plan_revision&&sameValue(a.flow_plan,op.payload.flow_plan)&&sameValue(a.allowed_weekdays,op.payload.allowed_weekdays)){this.planDraft=null;this.planOperation=null;this.planNotice='已套用；同 entry / revision / 全值後端讀回一致';}
      const d=this.planDraft??a,p=d.flow_plan,w=d.allowed_weekdays,pending=!!this.planOperation,conflict=!!this.planDraft&&(a.settings_revision!==d.revision||a.flow_plan_revision!==d.planRevision);
      for(const [i,r] of p.rows.entries()){
        const row=this.planRows.get(r.stage);if(this.planBody.children[i]!==row.el)this.planBody.insertBefore(row.el,this.planBody.children[i]??null);
        const values=[[row.rule,r.start_rule],[row.delay,r.delay_seconds],[row.wait,r.wait_timeout_seconds],[row.source,r.condition?.source??''],[row.operator,r.condition?.operator??'gte'],[row.value,r.condition?.value??'']];
        for(const [n,v] of values){if(n.value!==String(v??''))n.value=String(v??'');n.disabled=pending;}
        for(const [day,n] of row.days){n.checked=w[r.stage].includes(day);n.disabled=pending;}
        row.up.disabled=pending||i===0;row.down.disabled=pending||i===3;
        const runtime=a.step_runtime[r.stage];text(row.runtime,`own phase: ${runtime.phase??'—'} · result: ${runtime.result??'—'} · wait: ${runtime.waiting_reason??'—'} · started: ${runtime.started_at??'—'} · settled: ${runtime.settled_at??'—'}`);
      }
      if(this.runTimeout.value!==String(p.run_timeout_seconds??''))this.runTimeout.value=String(p.run_timeout_seconds??'');this.runTimeout.disabled=pending;
      const valid=validPlan(p)&&weekdays(w),locked=this.flights.has('plan:'+a.flow_plan_target.config_entry_id);
      this.planApply.disabled=!this.isConnected||!this.planDraft||!valid||conflict||pending||locked;
      this.planPreview.disabled=!this.isConnected||!valid||conflict||pending||!!this.previewOperation;
      text(this.planMessage,!valid?'流程無效：首列必須 flow_start，重排不會暗改規則；請檢查整秒期限與條件量程':conflict?'settings_conflict：保留草稿與原兩 revision；Cancel 才載入新版':this.planNotice??'尚未保存；預覽會送出未保存星期與計畫');
      if(this.previewRendered!==this.previewResults){this.previewRendered=this.previewResults;this.previewView.replaceChildren();for(const result of this.previewResults??[]){const day=make('section');day.dataset.previewDay=result.weekday;day.append(make('h4',result.weekday));for(const r of result.rows)day.append(make('p',`${r.stage} · ${r.eligibility} · 最早下界 ${r.earliest_offset_seconds===null?'未知':r.earliest_offset_seconds+'s'} · ${r.uncertainties.join(' / ')}`));day.append(make('p',result.warnings.join(' / ')));this.previewView.append(day);}}
      text(this.unsupported,`物理輸出（非 Enable）：${Object.entries(a.output_states).map(([k,v])=>k+' '+v).join(' / ')}\nIRR ready: false · 等待期間整輪保持 ON；unknown / fault 不代表完成。`);
    }
    planPayload(d) {return {config_entry_id:d.entry,expected_revision:d.revision,expected_flow_plan_revision:d.planRevision,flow_plan:structuredClone(d.flow_plan),allowed_weekdays:structuredClone(d.allowed_weekdays)};}
    async flowRequest(service,payload) {
      if(!this._hass?.callWS)throw new Error('需要支援 service response 的 HA transport');
      const result=await this._hass.callWS({type:'call_service',domain:'uninus_nutriculture',service,service_data:payload,return_response:true});
      return result?.response;
    }
    async applyPlan() {
      this.updatePlan();if(this.planApply.disabled)return;
      const d=this.planDraft,a=this.status().attributes,key='plan:'+d.entry,op={epoch:this.epoch,identity:this.planIdentity(),draft:d,payload:this.planPayload(d)};
      this.flights.set(key,op);this.planOperation=op;this.planNotice='保存中；等待服務及嚴格讀回';this.updatePlan();
      const current=()=>this.isConnected&&this.epoch===op.epoch&&this.planOperation===op&&this.planDraft===d&&this.planIdentity()===op.identity&&writable(this.status());
      try{const r=await this.flowRequest(a.flow_plan_target.service,op.payload);if(!current())return;
        if(!exact(r,['applied','settings_revision','flow_plan_revision','flow_plan','allowed_weekdays'])||typeof r.applied!=='boolean'||!revision(r.settings_revision)||!revision(r.flow_plan_revision)||r.settings_revision<d.revision||r.flow_plan_revision<d.planRevision||!validPlan(r.flow_plan)||!weekdays(r.allowed_weekdays)||!sameValue(r.flow_plan,d.flow_plan)||!sameValue(r.allowed_weekdays,d.allowed_weekdays))throw new Error('invalid_plan_response');op.response=r;op.settled=true;this.planNotice='已送出；等待同 revision 全值讀回';
      }catch(e){if(current()){this.planOperation=null;this.planNotice='保存失敗／衝突：保留草稿';}}
      finally{if(this.flights.get(key)===op)this.flights.delete(key);if(current()||this.isConnected)this.updatePlan();}
    }
    async previewPlan() {
      this.updatePlan();if(this.planPreview.disabled)return;
      const d=this.beginPlan(),a=this.status().attributes,op={epoch:this.epoch,draft:d,draftEpoch:this.planEpoch,identity:this.planIdentity()};this.previewOperation=op;this.updatePlan();
      const current=()=>this.isConnected&&this.epoch===op.epoch&&this.planEpoch===op.draftEpoch&&this.previewOperation===op&&this.planDraft===d&&this.planIdentity()===op.identity&&writable(this.status())&&this.status().attributes.settings_revision===d.revision&&this.status().attributes.flow_plan_revision===d.planRevision;
      try{const payload=this.planPayload(d),results=await Promise.all(DAYS.map(async weekday=>{const r=await this.flowRequest(a.flow_plan_target.preview_service,{...payload,weekday});
        if(!exact(r,['settings_revision','flow_plan_revision','weekday','rows','warnings'])||r.settings_revision!==d.revision||r.flow_plan_revision!==d.planRevision||r.weekday!==weekday||!Array.isArray(r.rows)||r.rows.length!==4||!Array.isArray(r.warnings)||!r.warnings.every(v=>typeof v==='string'&&v.length<=256)||!r.rows.every((row,i)=>exact(row,['stage','eligibility','earliest_offset_seconds','uncertainties'])&&row.stage===payload.flow_plan.rows[i].stage&&['eligible','skipped_disabled','skipped_weekday','blocked_dependency','blocked_safety'].includes(row.eligibility)&&(row.earliest_offset_seconds===null||(number(row.earliest_offset_seconds)&&row.earliest_offset_seconds>=0))&&Array.isArray(row.uncertainties)&&row.uncertainties.every(v=>typeof v==='string'&&v.length<=256)))throw new Error('invalid_preview_response');return r;}));
        if(current()){this.previewResults=results;this.planNotice='七日後端預覽；僅最早下界，真正 admission 安全與跨日以後端為準';}
      }catch(e){if(current())this.planNotice='預覽失敗／衝突；保留草稿';}
      finally{if(current()){this.previewOperation=null;this.updatePlan();}}
    }
    controlTarget(row) {
      const status = this.status();
      if (!isControl(status) || !writable(status)) return {error:'控制狀態缺失或不相容；禁止操作'};
      const a=status.attributes;
      if (row.key==='nutrient_enabled' && (a.schema_version<3 || !a.capabilities.nutrient)) return {error:'加養尚未支援；禁止操作'};
      if(['acid_enabled','mix_enabled'].includes(row.key)&& (![4,5].includes(a.schema_version)||!a.capabilities[row.key.replace('_enabled','')]))return {error:'階段尚未支援；禁止操作'};
      if (row.key==='refill_enabled' && a.capabilities?.refill!==true) return {error:'補水尚未支援；禁止操作'};
      if (row.key==='flow_run') {
        if (a.schema_version===2 && a.capabilities?.refill!==true) return {error:'補水尚未支援；禁止操作'};
        if (a.schema_version>=3) {
          const run=this._hass?.states?.[a.control_entities.flow_run];
          if (run?.state!=='on') {
            const selected=STAGES.filter(k=>this._hass?.states?.[a.control_entities[`${k}_enabled`]]?.state==='on');
            if (a.schema_version===5 ? (!selected.length||selected.some(k=>!a.capabilities[k])) : (selected.length!==1 || !a.capabilities[selected[0]])) return {error:'組合尚未支援或未選擇合法階段；禁止操作'};
          }
        }
      }
      const id = status.attributes.control_entities?.[row.key];
      if (typeof id !== 'string' || !new RegExp(`^${row.domain}\\.[a-z0-9_]+$`).test(id)) return {error:'控制 Entity 對應無效；禁止操作'};
      const state = this._hass?.states?.[id];
      if (!state || state.state === 'unavailable' || (row.domain === 'switch' && !['on','off'].includes(state.state)) || typeof state.state !== 'string') return {error:'控制 Entity 缺失或無法使用；禁止操作'};
      return {id,state:state.state,service:row.domain === 'button' ? 'press' : state.state === 'on' ? 'turn_off' : 'turn_on'};
    }
    updateControls() {
      this.p3bRows=this.p3bRows||new Map();
      for(const key of ['acid_enabled','mix_enabled']){
        if(this.controlRows.has(key))this.p3bRows.set(key,this.controlRows.get(key));
        if([4,5].includes(this.status()?.attributes?.schema_version)){if(this.p3bRows.has(key))this.controlRows.set(key,this.p3bRows.get(key));}
        else if(this.controlRows.has(key)){this.controlRows.get(key).el.remove();this.controlRows.delete(key);}
      }
      const v3=this.status()?.attributes?.schema_version>=3;
      if(v3 && this.nutrientRow)this.controlRows.set('nutrient_enabled',this.nutrientRow);
      if(!v3 && this.controlRows.has('nutrient_enabled')){this.nutrientRow=this.controlRows.get('nutrient_enabled');this.nutrientRow.el.remove();this.controlRows.delete('nutrient_enabled');}
      for (const row of this.controlRows.values()) {
        row.el.hidden=['acid_enabled','mix_enabled'].includes(row.key)&&![4,5].includes(this.status()?.attributes?.schema_version);
        if(row.key==='nutrient_enabled' && this.status()?.attributes?.schema_version<3){row.el.remove();continue;}
        if(row.el.parentNode!==this.controls)this.controls.insertBefore(row.el,this.controlRows.get('flow_run').el);
        const target = this.controlTarget(row);
        if (row.boundTarget !== target.id) { row.boundTarget = target.id; row.error = ''; row.operation = null; }
        text(row.caption,`${row.label} · ${target.state ?? '不可用'} `);
        row.button.disabled = !this.isConnected || !!target.error || this.flights.has(target.id);
        text(row.button,row.domain === 'button' ? row.label : target.state === 'on' ? '關閉' : '開啟');
        text(row.message,target.error || row.error);
      }
    }
    async invokeControl(row) {
      const target = this.controlTarget(row);
      if (row.boundTarget !== target.id) { this.updateControls(); return; }
      if (!this.isConnected || target.error || this.flights.has(target.id) || !this._hass?.callService) return;
      const op = {epoch:this.epoch,entity:this.config.entity,target:target.id};
      this.flights.set(op.target,op); row.operation = op; row.error = ''; this.updateControls();
      const current = () => this.isConnected && this.epoch === op.epoch && row.operation === op && this.controlTarget(row).id === op.target;
      try {
        await this._hass.callService(row.domain,target.service,{entity_id:op.target});
        if (current()) row.error = '已送出操作；以 Entity 讀回值為準';
      } catch (error) {
        if (current()) row.error = `操作失敗：${error?.message ?? String(error)}`;
      } finally {
        if (this.flights.get(op.target) === op) this.flights.delete(op.target);
        if (current()) row.operation = null;
        if (this.isConnected) this.updateControls();
      }
    }
    update() {
      text(this.heading,this.config?.title ?? 'UNiNUS Nutriculture');
      const status = this.status();
      for (const [key, nodes] of Object.entries(this.readings)) {
        const source = this._hass?.states?.[status?.attributes?.source_entities?.[key]];
        text(nodes.value,finite(source?.state) ? Number(source.state).toLocaleString(undefined,{maximumFractionDigits:3}) : '—');
        text(nodes.unit,source?.attributes?.unit_of_measurement ?? ({ph:'pH',ec:'mS/cm',level:'m'}[key]));
      }
      const control = isControl(status), compatible = isShadow(status) || control;
      text(this.parameterHelp,control ? '每次僅儲存一項，不提供群組原子更新。補水門檻與逾時由後端即時校驗；加養／加酸／獨立混合尚未支援。' : '每次僅儲存一項，不提供群組原子更新。時間參數僅儲存，不控制設備。');
      text(this.badge,control ? status.attributes.schema_version>=3?'控制模式 · P3 加養 / 群組設定':'控制模式 · P2 補水' : '影子監測');
      text(this.safety,control ? status.attributes.schema_version>=3?'原生控制 · 後端安全校驗 · 尚未提供灌溉許可':'僅補水控制 · 後端安全校驗 · 尚未提供灌溉許可' : '不控制設備 · 尚未提供灌溉許可');
      if (control) {
        if (this.controls.parentNode !== this.root) this.root.insertBefore(this.controls,this.details.parentNode === this.root ? this.details : null);
        const a = status.attributes;
        text(this.controlStatus,`流程：${a.flow_state ?? '未知'} · Sensor：${status.state}\n故障：${a.fault ?? '無'} · 本輪：${a.run_id ?? '無'}`);
        text(this.unsupported,a.schema_version===4?`加酸：${a.stage_states.acid} · phase ${a.acid_phase??'無'} · 脈衝 ${a.acid_progress.pulse_count} · ON ${a.acid_progress.reserved_on_seconds}s · 穩定 ${a.acid_progress.stable_count}\n獨立攪拌：${a.stage_states.mix} · 酸輸出 ${a.output_states.acid} / 循環 ${a.output_states.circulation}`:a.schema_version>=3?`加養：${a.capabilities.nutrient?'原生映射已支援':'尚未支援（引擎未接通）'} · 加酸／獨立混合：尚未支援\n養階段：${a.stage_states.nutrient} · phase：${a.nutrient_phase??'無'} · 脈衝 ${a.dose_progress.pulse_count} · ON 預算 ${a.dose_progress.reserved_on_seconds}s · 穩定 ${a.dose_progress.stable_count}\n輸出：養 ${a.output_states.nutrient} / 循環 ${a.output_states.circulation}`:'加養／加酸／獨立混合：尚未支援（P2 不執行）');
      } else this.controls.remove();
      const labels = {within_range:'讀值在範圍內',out_of_range:'讀值超出範圍',invalid:'來源資料無效'};
      const warning = !compatible ? '狀態缺失或不相容：僅支援 schema 1 / shadow 或 schema 2 / 3 / 4 / 5 control；禁止儲存。' : control ? (writable(status) ? '控制狀態以原生 Entity 讀回為準'+(status.attributes.schema_version===4?'；編輯四列流程請先至原生整合 Options 建立 v5 計畫。':'') : '未知或不一致狀態；禁止儲存。') : labels[status.state] ?? '未知狀態；禁止儲存。';
      const reasons = Array.isArray(status?.attributes?.reasons) ? status.attributes.reasons.map(String) : [];
      const blocked = Array.from(this.rows.values()).filter(row=>this.target(row).error).length;
      const parameterWarning = compatible && blocked ? `${blocked} 項參數無法儲存；請展開參數檢查 Number Entity。` : '';
      text(this.quality,[warning,parameterWarning,...reasons].filter(Boolean).join('\n'));
      this.quality.classList.toggle('warn',!compatible || status.state !== 'within_range' || blocked>0);
      this.updateRows(); this.updateControls();this.updateGroup();this.updatePlan();
    }
  }
  class NutricultureEditor extends HTMLElement {
    constructor() {
      super(); this.attachShadow({mode:'open'});
      this.shadowRoot.append(make('style',`${style}label{display:block;margin:12px 0;font-size:14px}select{width:100%;max-width:100%;padding:10px;box-sizing:border-box;color:inherit;background:var(--card-background-color,#fff)}input[type=checkbox]{width:auto;margin-right:8px}`));
      this.entityInput = make('select'); this.entityInput.name = 'entity';
      this.titleInput = make('input'); this.titleInput.name = 'title'; this.titleInput.type = 'text';
      this.showInput = make('input'); this.showInput.name = 'show_parameters'; this.showInput.type = 'checkbox';
      for (const [label,input] of [['狀態 Entity',this.entityInput],['標題',this.titleInput],['顯示參數調整',this.showInput]]) {
        const field = make('label',label); field.append(input); this.shadowRoot.append(field);
      }
      this.shadowRoot.append(make('p','schema 1 / shadow：不控制設備；schema 2 / control：原生補水控制。兩者皆尚未提供灌溉許可。'));
      this.entityInput.addEventListener('change',()=>this.change('entity',this.entityInput.value));
      this.titleInput.addEventListener('input',()=>this.change('title',this.titleInput.value));
      this.showInput.addEventListener('change',()=>this.change('show_parameters',this.showInput.checked));
    }
    setConfig(config) {
      this.config = structuredClone(config ?? {});
      this.titleInput.value = this.config.title ?? '';
      this.showInput.checked = this.config.show_parameters !== false;
      this.options();
    }
    set hass(hass) { this._hass = hass; this.options(); }
    options() {
      const ids = Object.keys(this._hass?.states ?? {}).filter(id=>/^sensor\.[a-z0-9_]+$/.test(id));
      if (this.config?.entity && !ids.includes(this.config.entity)) ids.push(this.config.entity);
      ids.sort(); const signature = JSON.stringify(ids);
      if (this.optionSignature !== signature) {
        this.optionSignature = signature; this.entityInput.replaceChildren(make('option','請選擇狀態 sensor'));
        this.entityInput.firstChild.value = '';
        for (const id of ids) { const option = make('option',id); option.value = id; this.entityInput.append(option); }
      }
      this.entityInput.value = this.config?.entity ?? '';
    }
    change(key,value) {
      this.config = {...this.config,[key]:value};
      this.dispatchEvent(new CustomEvent('config-changed',{detail:{config:structuredClone(this.config)},bubbles:true,composed:true}));
    }
  }
  if (!customElements.get(`${TAG}-editor`)) customElements.define(`${TAG}-editor`,NutricultureEditor);
  if (!customElements.get(TAG)) customElements.define(TAG,NutricultureCard);
  window.customCards = window.customCards || [];
  if (!window.customCards.some(card=>card.type === TAG)) window.customCards.push({type:TAG,name:'UNiNUS Nutriculture / 養液控制',description:'P1 影子監測／P2 原生補水控制與單項參數儲存；尚未提供灌溉許可',preview:true});
})();
