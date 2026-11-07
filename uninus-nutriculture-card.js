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
  // P4c structural vocabulary copied from the frozen schema; separate from legacy DTOs.
  const P4C_DEFS={"Stage":{"type":"object","properties":{"phase":{"anyOf":[{"enum":["confirming_off","mixing","pulsing","refilling","stabilizing","starting","starting_circulation","stopping","waiting_condition","waiting_delay","waiting_resource","waiting_sample"]},{"type":"null"}]},"result":{"anyOf":[{"enum":["completed","aborted","fault","skipped_disabled","skipped_weekday","blocked_dependency"]},{"type":"null"}]},"started_at":{"anyOf":[{"type":"string","format":"date-time","pattern":"^\\d{4}-\\d{2}-\\d{2}T.*\\+00:00$"},{"type":"null"}]},"settled_at":{"anyOf":[{"type":"string","format":"date-time","pattern":"^\\d{4}-\\d{2}-\\d{2}T.*\\+00:00$"},{"type":"null"}]},"waiting_reason":{"anyOf":[{"enum":["circulation_lost","condition_not_met","delay_pending","dependency_not_started","dose_budget_exhausted","ec_danger","ec_high","ec_timeout","emergency_stop","entry_inactive","flow_timeout","level_unsafe","no_actual_start","none","operation_failed","output_already_owned","output_identity_invalid","output_not_off","output_unbound","output_unexpected","ph_danger","ph_high","ph_low","ph_timeout","refill_timeout","resource_chemical","restart_output_not_off","revoked","sample_invalid","sample_timeout","source_invalid","stage_skipped","start_cancelled","start_unconfirmed","stop_unconfirmed","weekday"]},{"type":"null"}]}},"required":["phase","result","started_at","settled_at","waiting_reason"],"additionalProperties":false},"Run":{"type":"object","properties":{"run_id":{"type":"string","pattern":"^[0-9a-f]{32}$"},"epoch":{"type":"string","pattern":"^[0-9a-f]{32}$"},"settings_revision":{"type":"integer","minimum":0,"maximum":9007199254740991},"flow_plan_revision":{"type":"integer","minimum":0,"maximum":9007199254740991},"state":{"enum":["accepted","running","stopping","completed","stopped","incomplete","failed"]},"closure":{"enum":["pending","unconfirmed","confirmed"]},"reason":{"enum":["circulation_lost","condition_not_met","delay_pending","dependency_not_started","dose_budget_exhausted","ec_danger","ec_high","ec_timeout","emergency_stop","entry_inactive","flow_timeout","level_unsafe","no_actual_start","none","operation_failed","output_already_owned","output_identity_invalid","output_not_off","output_unbound","output_unexpected","ph_danger","ph_high","ph_low","ph_timeout","refill_timeout","resource_chemical","restart_output_not_off","revoked","sample_invalid","sample_timeout","source_invalid","stage_skipped","start_cancelled","start_unconfirmed","stop_unconfirmed","weekday"]},"accepted_at":{"type":"string","format":"date-time","pattern":"^\\d{4}-\\d{2}-\\d{2}T.*\\+00:00$"},"started_at":{"anyOf":[{"type":"string","format":"date-time","pattern":"^\\d{4}-\\d{2}-\\d{2}T.*\\+00:00$"},{"type":"null"}]},"finished_at":{"anyOf":[{"type":"string","format":"date-time","pattern":"^\\d{4}-\\d{2}-\\d{2}T.*\\+00:00$"},{"type":"null"}]},"transition_at":{"type":"string","format":"date-time","pattern":"^\\d{4}-\\d{2}-\\d{2}T.*\\+00:00$"},"stages":{"type":"object","properties":{"refill":{"$ref":"#/$defs/Stage"},"nutrient":{"$ref":"#/$defs/Stage"},"acid":{"$ref":"#/$defs/Stage"},"mix":{"$ref":"#/$defs/Stage"}},"required":["refill","nutrient","acid","mix"],"additionalProperties":false}},"required":["run_id","epoch","settings_revision","flow_plan_revision","state","closure","reason","accepted_at","started_at","finished_at","transition_at","stages"],"additionalProperties":false},"Event":{"type":"object","properties":{"schema_version":{"const":1},"config_entry_id":{"type":"string","minLength":1,"maxLength":128},"epoch":{"type":"string","pattern":"^[0-9a-f]{32}$"},"observation_revision":{"type":"integer","minimum":0,"maximum":9007199254740991},"sequence":{"type":"integer","minimum":1,"maximum":9007199254740991},"event_id":{"type":"string","pattern":"^[0-9a-f]{32}:[1-9][0-9]{0,15}$"},"kind":{"enum":["accepted","running","stopping","completed","stopped","incomplete","failed","stop_unconfirmed","ph_low","ec_high","ph_high"]},"reason":{"enum":["circulation_lost","condition_not_met","delay_pending","dependency_not_started","dose_budget_exhausted","ec_danger","ec_high","ec_timeout","emergency_stop","entry_inactive","flow_timeout","level_unsafe","no_actual_start","none","operation_failed","output_already_owned","output_identity_invalid","output_not_off","output_unbound","output_unexpected","ph_danger","ph_high","ph_low","ph_timeout","refill_timeout","resource_chemical","restart_output_not_off","revoked","sample_invalid","sample_timeout","source_invalid","stage_skipped","start_cancelled","start_unconfirmed","stop_unconfirmed","weekday"]},"occurred_at":{"type":"string","format":"date-time","pattern":"^\\d{4}-\\d{2}-\\d{2}T.*\\+00:00$"},"run":{"anyOf":[{"$ref":"#/$defs/Run"},{"type":"null"}]}},"required":["schema_version","config_entry_id","epoch","observation_revision","sequence","event_id","kind","reason","occurred_at","run"],"additionalProperties":false},"ResultDTO":{"type":"object","properties":{"schema_version":{"const":1},"config_entry_id":{"type":"string","minLength":1,"maxLength":128},"epoch":{"type":"string","pattern":"^[0-9a-f]{32}$"},"observation_revision":{"type":"integer","minimum":0,"maximum":9007199254740991},"support":{"enum":["supported","unsupported"]},"current_run":{"anyOf":[{"$ref":"#/$defs/Run"},{"type":"null"}]},"last_result":{"anyOf":[{"$ref":"#/$defs/Run"},{"type":"null"}]},"latest_event":{"anyOf":[{"$ref":"#/$defs/Event"},{"type":"null"}]}},"required":["schema_version","config_entry_id","epoch","observation_revision","support","current_run","last_result","latest_event"],"additionalProperties":false},"TargetBinding":{"type":"object","properties":{"entity_id":{"type":"string","pattern":"^notify\\.[a-z0-9_]+$","maxLength":255},"registry_entry_id":{"type":"string","minLength":1,"maxLength":128},"platform":{"type":"string","minLength":1,"maxLength":128},"unique_id":{"type":"string","minLength":1,"maxLength":512},"config_entry_id":{"anyOf":[{"type":"string","minLength":1,"maxLength":128},{"type":"null"}]}},"required":["entity_id","registry_entry_id","platform","unique_id","config_entry_id"],"additionalProperties":false},"NotificationPolicy":{"type":"object","properties":{"enabled":{"type":"boolean"},"provider":{"enum":[null,"persistent_notification","notify_entity"]},"target_binding":{"anyOf":[{"$ref":"#/$defs/TargetBinding"},{"type":"null"}]},"events":{"type":"array","items":{"enum":["start","stop","completed","incomplete","failed","danger","timeout","stop_unconfirmed"]},"minItems":0,"maxItems":8,"uniqueItems":true},"cooldown_seconds":{"type":"integer","minimum":60,"maximum":86400}},"required":["enabled","provider","target_binding","events","cooldown_seconds"],"additionalProperties":false},"PolicyInput":{"type":"object","properties":{"enabled":{"type":"boolean"},"provider":{"enum":[null,"persistent_notification","notify_entity"]},"events":{"type":"array","items":{"enum":["start","stop","completed","incomplete","failed","danger","timeout","stop_unconfirmed"]},"minItems":0,"maxItems":8,"uniqueItems":true},"cooldown_seconds":{"type":"integer","minimum":60,"maximum":86400},"target_entity_id":{"anyOf":[{"type":"string","pattern":"^notify\\.[a-z0-9_]+$","maxLength":255},{"type":"null"}]}},"required":["enabled","provider","events","cooldown_seconds","target_entity_id"],"additionalProperties":false},"Delivery":{"type":"object","properties":{"event_id":{"type":"string","pattern":"^[0-9a-f]{32}:[1-9][0-9]{0,15}$"},"kind":{"enum":["accepted","running","stopping","completed","stopped","incomplete","failed","stop_unconfirmed","ph_low","ec_high","ph_high"]},"status":{"enum":["queued","handoff_returned","failed","suppressed","cancelled","timed_out"]},"code":{"anyOf":[{"enum":["provider_unavailable","provider_failed","provider_timeout","queue_full","cooldown","expired","cancelled","revoked","storage_failed"]},{"type":"null"}]},"acknowledged":{"type":"boolean"},"updated_at":{"type":"string","format":"date-time","pattern":"^\\d{4}-\\d{2}-\\d{2}T.*\\+00:00$"}},"required":["event_id","kind","status","code","acknowledged","updated_at"],"additionalProperties":false},"CatalogItem":{"type":"object","properties":{"entity_id":{"type":"string","pattern":"^notify\\.[a-z0-9_]+$","maxLength":255},"label":{"type":"string","minLength":1,"maxLength":80},"available":{"type":"boolean"}},"required":["entity_id","label","available"],"additionalProperties":false},"NotificationDTO":{"type":"object","properties":{"schema_version":{"const":1},"config_entry_id":{"type":"string","minLength":1,"maxLength":128},"epoch":{"type":"string","pattern":"^[0-9a-f]{32}$"},"revision":{"type":"integer","minimum":0,"maximum":9007199254740991},"policy":{"$ref":"#/$defs/NotificationPolicy"},"availability":{"enum":["disabled","available","unavailable","indeterminate"]},"error":{"anyOf":[{"enum":["provider_unavailable","storage_failed","indeterminate"]},{"type":"null"}]},"catalog":{"type":"array","items":{"$ref":"#/$defs/CatalogItem"},"minItems":0,"maxItems":256,"uniqueItems":true},"deliveries":{"type":"array","items":{"$ref":"#/$defs/Delivery"},"minItems":0,"maxItems":32,"uniqueItems":true}},"required":["schema_version","config_entry_id","epoch","revision","policy","availability","error","catalog","deliveries"],"additionalProperties":false}};
  const P4C_EVENTS=["start", "stop", "completed", "incomplete", "failed", "danger", "timeout", "stop_unconfirmed"];
  const P4C_ERRORS=["unauthorized", "entry_not_loaded", "settings_schema_mismatch", "invalid_notification_policy", "invalid_provider", "notification_conflict", "notification_not_found", "storage_failed", "indeterminate"];
  const p4cDate = v => {
    const m=typeof v==='string'&&v.match(/^(\d{4})-(\d\d)-(\d\d)T(\d\d):(\d\d):(\d\d)(?:\.\d{1,6})?\+00:00$/);
    return !!(m&&+m[2]>=1&&+m[2]<=12&&+m[3]>=1&&+m[3]<=new Date(Date.UTC(+m[1],+m[2],0)).getUTCDate()&&+m[4]<24&&+m[5]<60&&+m[6]<60&&Number.isFinite(Date.parse(v)));
  };
  const p4cSafe = v => !/[\u0000-\u001f\u007f-\u009f؜‎‏‪-‮⁦-⁩]/u.test(v)&&Array.from(v).every(c=>{const n=c.codePointAt(0);return n<0xd800||n>0xdfff;});
  const p4cCheck=(s,v)=>{
    if(s.$ref)return p4cCheck(P4C_DEFS[s.$ref.split('/').at(-1)],v);
    if(s.anyOf)return s.anyOf.some(x=>p4cCheck(x,v));
    if(Object.hasOwn(s,'const')&&v!==s.const)return false;
    if(s.enum&&!s.enum.includes(v))return false;
    if(s.type==='null')return v===null;
    if(s.type==='boolean')return typeof v==='boolean';
    if(s.type==='integer')return Number.isSafeInteger(v)&&v>=s.minimum&&v<=s.maximum;
    if(s.type==='string')return typeof v==='string'&&p4cSafe(v)&&(s.minLength===undefined||Array.from(v).length>=s.minLength)&&(s.maxLength===undefined||Array.from(v).length<=s.maxLength)&&(!s.pattern||new RegExp(s.pattern).test(v))&&(s.format!=='date-time'||p4cDate(v));
    if(s.type==='array')return Array.isArray(v)&&v.length>=s.minItems&&v.length<=s.maxItems&&(!s.uniqueItems||new Set(v.map(x=>JSON.stringify(x))).size===v.length)&&v.every(x=>p4cCheck(s.items,x));
    if(s.type==='object')return exact(v,s.required)&&s.required.every(k=>p4cCheck(s.properties[k],v[k]));
    return true;
  };
  const p4cValid=(name,v)=>p4cCheck(P4C_DEFS[name],v);
  const p4cPolicy=(p,input=false)=>{
    const target=input?p.target_entity_id:p.target_binding;
    return (!p.enabled||(p.provider!==null&&p.events.length>0))&&(p.provider==='notify_entity'?target!==null:target===null);
  };
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
  // Python len(str) counts Unicode code points, not UTF-16 units or graphemes.
  const recipeNameLength=v=>Array.from(v).length;
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
      this.initRecipes();
    }
    initRecipes() {
      this.recipeFlights=new Map();this.recipeInputs=new Map();
      this.recipePanel=make('details');this.recipePanel.dataset.recipePanel='';
      this.recipePanel.append(make('summary','參數配方'),make('p','參數配方，不含硬體/流程/安全設定'));
      this.recipeSelect=make('select');this.recipeSelect.dataset.recipeSelect='';this.recipeSelect.setAttribute('aria-label','選擇配方');
      // Native maxlength counts UTF-16 and can silently truncate a pasted name; validate code points instead.
      this.recipeName=make('input');this.recipeName.dataset.recipeName='';
      const label=make('label','配方名稱');label.append(this.recipeName);
      this.recipePanel.append(this.recipeSelect,label);
      for(const [key,caption,,unit] of PARAMETERS){
        const row=make('label',`${caption} ${unit}`),input=make('input');input.type='number';input.dataset.recipeParameter=key;
        const [min,max,step]=NORMAL_LIMITS[key];for(const [k,v] of Object.entries({min,max,step}))input.setAttribute(k,String(v));
        input.addEventListener('input',()=>{this.recipeDirty=true;this.renderRecipes();});
        row.append(input);this.recipePanel.append(row);this.recipeInputs.set(key,input);
      }
      this.recipeName.addEventListener('input',()=>{this.recipeDirty=true;this.renderRecipes();});
      this.recipeButtons={};
      for(const [key,caption] of [['refresh','Refresh · 重新整理'],['save','Save · 保存配方'],['apply','Apply · 原子套用'],['cancel','Cancel · 取消草稿'],['delete','Delete · 刪除配方']]){
        const button=make('button',caption);button.type='button';button.dataset['recipe'+key[0].toUpperCase()+key.slice(1)]='';
        button.addEventListener('click',()=>{
          if(key==='cancel'){this.recipeDraft(this.recipeData.recipes.find(r=>r.id===this.recipeSelected));this.recipeConfirm.hidden=true;this.recipeNotice='已取消草稿；未寫入';this.renderRecipes();}
          else if(key==='delete'){this.recipeConfirm.hidden=false;this.recipeConfirmCancel.focus();}
          else this.recipeRequest({refresh:'get_recipes_v1',save:'save_recipe_v1',apply:'apply_recipe_v1'}[key]);
        });
        this.recipeButtons[key]=button;this.recipePanel.append(button);
      }
      this.recipeSelect.addEventListener('change',()=>{this.recipeDraft(this.recipeData.recipes.find(r=>r.id===this.recipeSelect.value));this.recipeConfirm.hidden=true;this.recipeNotice='僅選擇；未保存、未套用';this.renderRecipes();});
      this.recipeConfirm=make('fieldset');this.recipeConfirm.hidden=true;this.recipeConfirm.append(make('legend','再次確認：永久刪除此配方？'));
      this.recipeConfirmCancel=make('button','取消刪除');this.recipeConfirmCancel.type='button';this.recipeConfirmCancel.dataset.recipeDeleteCancel='';
      this.recipeConfirmCancel.addEventListener('click',()=>{this.recipeConfirm.hidden=true;this.recipeButtons.delete.focus();});
      this.recipeConfirmYes=make('button','確認刪除');this.recipeConfirmYes.type='button';this.recipeConfirmYes.dataset.recipeDeleteConfirm='';this.recipeConfirmYes.addEventListener('click',()=>this.recipeRequest('delete_recipe_v1'));
      this.recipeConfirm.addEventListener('keydown',e=>{if(e.key==='Escape'){e.preventDefault();this.recipeConfirmCancel.click();}});
      this.recipeConfirm.append(this.recipeConfirmCancel,this.recipeConfirmYes);this.recipePanel.append(this.recipeConfirm);
      this.recipeHistory=make('p');this.recipeHistory.dataset.recipeHistory='';this.recipePanel.append(this.recipeHistory);
      this.recipeMessage=make('p');this.recipeMessage.dataset.recipeMessage='';this.recipeMessage.setAttribute('role','status');this.recipePanel.append(this.recipeMessage);
      this.recipePanel.addEventListener('toggle',()=>{if(this.recipePanel.open&&!this.recipeData&&!this.recipeOperation)this.recipeRequest('get_recipes_v1');});
      this.shadowRoot.append(make('style','[data-recipe-panel] label{display:block;margin:8px 0}[data-recipe-panel] input,[data-recipe-panel] select{display:block;width:100%;min-width:0;max-width:100%}[data-recipe-panel] button{max-width:100%;margin:4px 4px 4px 0}[data-recipe-panel][hidden]{display:none}'));
      this.root.append(this.recipePanel);
    }
    recipeTarget() {
      const s=this.status(),names=['get_recipes_v1','save_recipe_v1','delete_recipe_v1','apply_recipe_v1'];
      return this.isConnected&&writable(s)&&s.attributes.schema_version===5&&typeof this._hass?.callWS==='function'&&names.every(k=>Object.hasOwn(this._hass.services?.uninus_nutriculture??{},k))?s.attributes.settings_target.config_entry_id:null;
    }
    recipeParameters(p) {
      return exact(p,PARAMETERS.map(r=>r[0]))&&Object.entries(NORMAL_LIMITS).every(([k,limits])=>inRange(p[k],...limits))&&['level','ph','ec'].every(k=>p[k+'_low']<p[k+'_high']);
    }
    recipeDTO(d,entry) {
      const uuid=v=>typeof v==='string'&&/^[a-f0-9]{32}$/.test(v),name=v=>typeof v==='string'&&recipeNameLength(v)>=1&&recipeNameLength(v)<=80&&v===v.trim()&&!/[\x00-\x1f]/.test(v);
      return exact(d,['schema_version','config_entry_id','catalog_revision','settings_revision','recipes','last_applied','parameters_match','parameters'])&&d.schema_version===1&&d.config_entry_id===entry&&revision(d.catalog_revision)&&revision(d.settings_revision)&&this.recipeParameters(d.parameters)&&Array.isArray(d.recipes)&&d.recipes.length<=100&&new Set(d.recipes.map(r=>r?.id)).size===d.recipes.length&&d.recipes.every(r=>exact(r,['id','name','parameters'])&&uuid(r.id)&&name(r.name)&&this.recipeParameters(r.parameters))&&(d.last_applied===null||(exact(d.last_applied,['recipe_id','name','parameters'])&&uuid(d.last_applied.recipe_id)&&name(d.last_applied.name)&&this.recipeParameters(d.last_applied.parameters)))&&typeof d.parameters_match==='boolean'&&d.parameters_match===(d.last_applied!==null&&sameValue(d.parameters,d.last_applied.parameters));
    }
    updateRecipes() {
      if(!this.recipePanel)return;
      const entry=this.recipeTarget(),identity=JSON.stringify([this.config?.entity,entry]);
      if(identity!==this.recipeIdentity){
        this.recipeIdentity=identity;this.recipeGeneration=(this.recipeGeneration??0)+1;this.recipeOperation=null;this.recipeData=null;this.recipeSelected=null;this.recipeDirty=false;this.recipeNotice='';this.recipePanel.open=false;
        this.recipeSelect.replaceChildren();this.recipeName.value='';for(const input of this.recipeInputs.values())input.value='';
      }
      if(entry){if(this.recipePanel.parentNode!==this.root)this.root.append(this.recipePanel);}else this.recipePanel.remove();this.recipePanel.hidden=!entry;this.renderRecipes();
    }
    recipeDraft(record=null) {
      this.recipeSelected=record?.id??null;this.recipeName.value=record?.name??'';
      const p=record?.parameters??this.recipeData.parameters;
      for(const [k,input] of this.recipeInputs)input.value=String(p[k]);
      this.recipeDirty=false;this.recipeSelect.value=this.recipeSelected??'';
    }
    renderRecipes() {
      if(!this.recipePanel)return;
      const busy=!!this.recipeOperation||this.recipeFlights.has(this.recipeTarget());
      for(const [k,b] of Object.entries(this.recipeButtons))b.disabled=busy||(k!=='refresh'&&!this.recipeData);
      const p=Object.fromEntries([...this.recipeInputs].map(([k,i])=>[k,i.value===''?null:Number(i.value)]));
      this.recipeButtons.save.disabled=busy||!this.recipeData||!this.recipeName.value.trim()||recipeNameLength(this.recipeName.value.trim())>80||/[\x00-\x1f]/.test(this.recipeName.value)||!this.recipeParameters(p);
      for(const input of [this.recipeName,this.recipeSelect,...this.recipeInputs.values()])input.disabled=busy||!this.recipeData;
      this.recipeButtons.apply.disabled=busy||!this.recipeSelected||this.recipeDirty;
      this.recipeButtons.delete.disabled=busy||!this.recipeSelected;
      this.recipeConfirmYes.disabled=busy||!this.recipeSelected;
      this.recipeConfirmCancel.disabled=busy;
      const last=this.recipeData?.last_applied;
      text(this.recipeHistory,last?`上次套用歷史：${last.name} · ${last.recipe_id}；${this.recipeData.parameters_match?'與讀回參數相同':'與現值不同（已偏離上次套用）'}。不是品質／灌溉許可。`:'尚無套用歷史；不代表品質／灌溉許可。');
      text(this.recipeMessage,this.recipeNotice??'');
    }
    async recipeRequest(service) {
      const entry=this.recipeTarget();if(!entry||this.recipeFlights.has(entry))return;
      const data=this.recipeData,payload={config_entry_id:entry};
      if(service!=='get_recipes_v1'){
        if(!data)return;
        Object.assign(payload,{expected_catalog_revision:data.catalog_revision,recipe_id:this.recipeSelected??null});
        if(service==='save_recipe_v1'){
          if(this.recipeButtons.save.disabled)return;
          Object.assign(payload,{name:this.recipeName.value.trim(),parameters:Object.fromEntries([...this.recipeInputs].map(([k,i])=>[k,Number(i.value)]))});
        }else if(service==='apply_recipe_v1'){
          if(this.recipeButtons.apply.disabled)return;payload.expected_settings_revision=data.settings_revision;
        }else if(service==='delete_recipe_v1'){
          if(this.recipeConfirm.hidden||!this.recipeSelected)return;payload.confirm_delete=true;
        }else return;
      }
      const op={entry,generation:this.recipeGeneration,epoch:this.epoch,ws:this._hass.callWS,service,payload,catalogRevision:data?.catalog_revision??0,settingsRevision:Math.max(data?.settings_revision??0,this.status().attributes.settings_revision)};
      this.recipeFlights.set(entry,op);this.recipeOperation=op;this.recipeNotice='等待後端讀回…';this.renderRecipes();
      const current=()=>this.isConnected&&this.recipeOperation===op&&this.recipeGeneration===op.generation&&this.epoch===op.epoch&&this.recipeTarget()===entry&&this._hass.callWS===op.ws;
      try{
        const result=await op.ws.call(this._hass,{type:'call_service',domain:'uninus_nutriculture',service,service_data:payload,return_response:true});
        if(!current())return;
        const dto=result?.response;if(!this.recipeDTO(dto,entry)||dto.catalog_revision<op.catalogRevision||dto.settings_revision<op.settingsRevision)throw {code:'invalid_response'};
        this.recipeData=structuredClone(dto);
        this.recipeSelect.replaceChildren();const empty=make('option','新增 · 使用目前參數');empty.value='';this.recipeSelect.append(empty);
        for(const r of dto.recipes){const option=make('option',`${r.name} · ${r.id}`);option.value=r.id;this.recipeSelect.append(option);}
        this.recipeDraft(service==='save_recipe_v1'?dto.recipes.find(r=>r.id===payload.recipe_id)||dto.recipes.at(-1):service==='apply_recipe_v1'?dto.recipes.find(r=>r.id===payload.recipe_id):null);this.recipeConfirm.hidden=true;
        this.recipeNotice=({save_recipe_v1:'配方已保存；未套用參數、未啟動輸出',apply_recipe_v1:'參數已原子套用並讀回；未啟動輸出',delete_recipe_v1:'配方已刪除；保留上次套用歷史'})[service]??'配方已讀回';
      }catch(error){if(current())this.recipeNotice=error?.code==='recipe_conflict'?'配方版本衝突；草稿保留，請明確重新整理':'無法完成配方操作；草稿保留，請重新整理後再試';}
      finally{if(this.recipeFlights.get(entry)===op)this.recipeFlights.delete(entry);if(this.recipeOperation===op){if(!current())this.recipeNotice='連線已變更；草稿保留，請明確重新整理';this.recipeOperation=null;this.renderRecipes();}}
    }
    resultDTO(d) {
      if(!p4cValid('ResultDTO',d))return false;
      const terminal=r=>['completed','stopped','incomplete','failed'].includes(r.state);
      const run=r=>!r||(r.epoch===d.epoch&&terminal(r)===(r.closure==='confirmed'&&r.finished_at!==null)&&(!terminal(r)?r.finished_at===null:true));
      if(!run(d.current_run)||!run(d.last_result)||(d.current_run&&terminal(d.current_run))||(d.last_result&&!terminal(d.last_result)))return false;
      const e=d.latest_event;if(e){if(e.config_entry_id!==d.config_entry_id||e.epoch!==d.epoch||e.event_id!==`${e.epoch}:${e.sequence}`||e.observation_revision>d.observation_revision||!run(e.run))return false;if(!e.run&&!['ph_low','ph_high','ec_high'].includes(e.kind))return false;if(e.run&&['accepted','running','stopping','completed','stopped','incomplete','failed'].includes(e.kind)&&e.run.state!==e.kind)return false;}
      return d.support!=='unsupported'||[d.current_run,d.last_result,e].every(v=>v===null);
    }
    resultNative() {
      const s=this._hass?.states?.[this.config?.result_entity];if(!s?.attributes)return null;
      const d=Object.fromEntries(Object.entries(s.attributes).filter(([k])=>!HA_METADATA.includes(k)));
      if(!this.resultDTO(d)||s.state!==(d.support==='unsupported'?'unsupported':(d.current_run??d.last_result)?.state??'idle'))return null;
      if(this.config.entity&&this.status()?.attributes.settings_target?.config_entry_id!==d.config_entry_id)return null;
      return d;
    }
    notificationDTO(d,entry,epoch) {
      if(!p4cValid('NotificationDTO',d)||d.config_entry_id!==entry||d.epoch!==epoch||!p4cPolicy(d.policy))return false;
      if(new Set(d.catalog.map(x=>x.entity_id)).size!==d.catalog.length||new Set(d.deliveries.map(x=>x.event_id)).size!==d.deliveries.length)return false;
      if(!d.catalog.every(x=>x.label===x.label.normalize('NFC')))return false;
      return d.deliveries.every(x=>{const [e,n]=x.event_id.split(':');return e===epoch&&Number.isSafeInteger(Number(n))&&Number(n)>0;});
    }
    initResult() {
      if(this.resultPanel)return;
      this.notificationFlights=new Map();this.notificationOwner={};
      this.resultPanel=make('details');this.resultPanel.dataset.resultPanel='';this.resultPanel.append(make('summary','本輪結果（唯讀）'));
      this.resultStatus=make('p');this.resultStatus.dataset.resultStatus='';this.resultRows=make('section');this.resultPanel.append(this.resultStatus,this.resultRows,make('p','已受理不代表完成；completed 與品質合格／灌溉許可分離。許可唯一權威仍為 quality_v1。'));
      this.notificationPanel=make('details');this.notificationPanel.dataset.notificationPanel='';this.notificationPanel.append(make('summary','通知管理（admin 私有）'));
      this.notificationForm=make('section');this.notificationPanel.append(this.notificationForm);this.notificationInputs={};
      const add=(k,label,type,options=[])=>{const row=make('label',label),i=make(type==='select'?'select':'input');i.dataset['notification'+k[0].toUpperCase()+k.slice(1)]='';i.setAttribute('aria-label',label);if(type!=='select')i.type=type;else for(const [v,l] of options){const o=make('option',l);o.value=v; i.append(o);}row.append(i);this.notificationForm.append(row);this.notificationInputs[k]=i;i.addEventListener(type==='number'?'input':'change',()=>{this.notificationObserve();this.notificationDirty=true;this.renderResult();});return i;};
      add('enabled','啟用通知（預設關閉）','checkbox');add('provider','通知 Provider','select',[['','未選取'],['persistent_notification','persistent_notification'],['notify_entity','notify_entity']]);add('target','原生 NotifyEntity（僅私有 catalog）','select',[['','未選取']]);
      const cooldown=add('cooldown','冷卻秒數（60–86400；工程預設 300）','number');cooldown.min='60';cooldown.max='86400';cooldown.step='1';
      this.notificationEvents=new Map();for(const k of P4C_EVENTS){const row=make('label',k==='start'?'start（已受理）':k),i=make('input');i.type='checkbox';i.dataset.notificationEvent=k;i.addEventListener('change',()=>{this.notificationObserve();this.notificationDirty=true;this.renderResult();});row.append(i);this.notificationForm.append(row);this.notificationEvents.set(k,i);}
      this.notificationButtons={};for(const [k,label] of [['get','更新通知狀態'],['save','保存通知設定'],['cancel','取消通知草稿'],['reconcile','重新讀取通知設定']]){const b=make('button',label);b.type='button';b.dataset['notification'+k[0].toUpperCase()+k.slice(1)]='';b.addEventListener('click',()=>{this.notificationObserve();if(k==='cancel'){if(this.notificationData)this.notificationDraft(this.notificationData);this.notificationNotice='已取消；未寫入';this.renderResult();}else this.notificationRequest(k);});this.notificationButtons[k]=b;this.notificationForm.append(b);}
      this.notificationLedger=make('section');this.notificationLedger.dataset.notificationLedger='';this.notificationMessage=make('p');this.notificationMessage.dataset.notificationMessage='';this.notificationMessage.setAttribute('role','status');this.notificationPanel.append(this.notificationLedger,this.notificationMessage);
      this.notificationPanel.addEventListener('toggle',()=>{if(this.notificationPanel.open&&!this.notificationData)this.notificationRequest('get');});
      this.shadowRoot.append(make('style','[data-notification-panel] label{display:block;margin:10px 0}[data-notification-panel] select,[data-notification-panel] input[type=number]{display:block;width:100%;box-sizing:border-box}[data-notification-panel] button{max-width:100%;margin:4px}[data-notification-panel] [hidden]{display:none}'));
    }
    notificationPurge() {
      this.notificationOwner={};this.notificationDenied=false;this.notificationUnknown=false;this.notificationData=null;this.notificationBaseline=null;this.notificationDirty=false;this.notificationOperation=null;this.notificationNotice='';
      if(!this.notificationInputs)return;for(const i of Object.values(this.notificationInputs)){i.value='';i.checked=false;}this.notificationInputs.target.replaceChildren(make('option','未選取'));this.notificationInputs.target.firstChild.value='';for(const i of this.notificationEvents.values())i.checked=false;this.notificationLedger.replaceChildren();
    }
    notificationObserve() {
      const u=this._hass?.user,n=this.resultNative(),ws=this._hass?.callWS,c=this.config?.result_entity&&this.isConnected?this._hass?.connection:undefined;
      const key=JSON.stringify([typeof u?.id==='string'?u.id:null,u?.is_admin===true,u?.is_active!==false,u?.system_generated===true||u?.systemGenerated===true,this.config?.entity,this.config?.result_entity,n?.config_entry_id,n?.epoch,n?.support,c?.connected!==false,this.isConnected]);
      if(this.notificationKey!==key||this.notificationWS!==ws||this.notificationConnection!==c){this.notificationPurge();this.notificationKey=key;this.notificationWS=ws;if(this.notificationConnection!==c){if(this.notificationConnection?.removeEventListener){this.notificationConnection.removeEventListener('disconnected',this.notificationDisconnect);this.notificationConnection.removeEventListener('ready',this.notificationReady);}this.notificationConnection=c;this.notificationDisconnect=()=>{this.notificationOffline=true;this.notificationPurge();this.renderResult();};this.notificationReady=()=>{this.notificationOffline=false;this.notificationPurge();this.renderResult();};if(c?.addEventListener){c.addEventListener('disconnected',this.notificationDisconnect);c.addEventListener('ready',this.notificationReady);}}}
    }
    notificationAllowed() {
      const u=this._hass?.user,n=this.resultNative();return !!(!this.notificationDenied&&n?.support==='supported'&&typeof u?.id==='string'&&u.id.trim()&&u.is_admin===true&&u.is_active!==false&&u.system_generated!==true&&u.systemGenerated!==true&&this.isConnected&&!this.notificationOffline&&this._hass?.connection?.connected!==false&&typeof this._hass?.callWS==='function'&&this._hass?.services?.uninus_nutriculture?.get_result_v1);
    }
    notificationDraft(d) {
      this.notificationBaseline=structuredClone(d);this.notificationDirty=false;const p=d.policy,i=this.notificationInputs;i.enabled.checked=p.enabled;i.provider.value=p.provider??'';i.cooldown.value=String(p.cooldown_seconds);i.target.replaceChildren();const empty=make('option','未選取');empty.value='';i.target.append(empty);for(const x of d.catalog){const o=make('option',x.label);o.value=x.entity_id;o.disabled=!x.available;i.target.append(o);}i.target.value=p.target_binding?.entity_id??'';for(const [k,i] of this.notificationEvents)i.checked=p.events.includes(k);
    }
    notificationPolicyInput() {
      const i=this.notificationInputs,p={enabled:i.enabled.checked,provider:i.provider.value||null,target_entity_id:i.provider.value==='notify_entity'?(i.target.value||null):null,events:P4C_EVENTS.filter(k=>this.notificationEvents.get(k).checked),cooldown_seconds:i.cooldown.value===''?null:Number(i.cooldown.value)};
      return p4cValid('PolicyInput',p)&&p4cPolicy(p,true)?p:null;
    }
    updateResult() {
      this.initResult();this.notificationObserve();for(const panel of [this.resultPanel,this.notificationPanel]){if(this.config?.result_entity){if(panel.parentNode!==this.root)this.root.append(panel);}else panel.remove();}this.renderResult();
    }
    renderResult() {
      if(!this.resultPanel)return;this.notificationObserve();const d=this.resultNative(),r=d?.current_run??d?.last_result;
      text(this.resultStatus,'結果：'+(!this.isConnected||this.notificationOffline||this._hass?.connection?.connected===false?'未知／離線':d?(d.support==='unsupported'?'未支援':r?.state??'idle'):'未知／未支援或格式無效（唯讀）'));
      this.resultRows.replaceChildren();if(d&&r&&!this.notificationOffline)for(const [k,s] of Object.entries(r.stages))this.resultRows.append(make('p',`${k} · ${s.phase??'—'} · ${s.result??'—'} · ${s.waiting_reason??'—'} · ${s.started_at??'—'} → ${s.settled_at??'—'}`));
      if(r)this.resultRows.append(make('p',`run ${r.run_id} · ${r.closure} · ${r.reason} · ${r.accepted_at} → ${r.finished_at??'—'}`));
      const allowed=this.notificationAllowed(),base=this.notificationBaseline,data=this.notificationData,busy=this.notificationFlights.has(d?.config_entry_id);this.notificationForm.hidden=!allowed;
      for(const i of [...Object.values(this.notificationInputs),...this.notificationEvents.values()])i.disabled=!allowed||busy||!base||(this.notificationUnknown||data?.availability==='indeterminate');
      this.notificationButtons.get.disabled=!allowed||busy;this.notificationButtons.reconcile.disabled=!allowed||busy||!data;this.notificationButtons.save.disabled=!allowed||busy||!base||(this.notificationUnknown||data?.availability==='indeterminate')||!this.notificationPolicyInput();this.notificationButtons.cancel.disabled=busy||!base;
      this.notificationLedger.replaceChildren();if(allowed&&data)for(const x of data.deliveries){const row=make('p',`${x.kind==='accepted'?'已受理':x.kind} · ${x.status==='handoff_returned'?'handoff_returned（已交接返回，非送達確認）':x.status==='timed_out'?'timed_out（結果未知）':x.status} · ${x.acknowledged?'已讀':'未讀'} · ${x.code??''}`),b=make('button','標為已讀（不復歸）');b.type='button';b.dataset.notificationAck=x.event_id;b.disabled=busy||x.acknowledged;b.addEventListener('click',()=>this.notificationRequest('ack',x.event_id));row.append(b);this.notificationLedger.append(row);}
      text(this.notificationMessage,allowed?(this.notificationNotice||'尚未讀取通知設定；不發測試通知'):'唯讀／通知管理未支援或未授權');
    }
    async notificationRequest(action,eventId) {
      this.notificationObserve();const n=this.resultNative();if(!this.notificationAllowed()||this.notificationFlights.has(n.config_entry_id))return;
      const base=this.notificationBaseline,policy=action==='save'?this.notificationPolicyInput():null;
      if(action==='save'&&(!base||!policy||(this.notificationUnknown||this.notificationData?.availability==='indeterminate')))return;
      if(['ack','reconcile'].includes(action)&&!this.notificationData)return;
      if(action==='ack'&&!this.notificationData.deliveries.some(d=>d.event_id===eventId&&!d.acknowledged))return;
      const payload={type:'uninus_nutriculture/notification_v1/'+action,config_entry_id:n.config_entry_id};if(action==='save')Object.assign(payload,{expected_epoch:base.epoch,expected_revision:base.revision,policy});if(action==='ack')Object.assign(payload,{expected_epoch:this.notificationData.epoch,event_id:eventId});if(action==='reconcile')payload.expected_epoch=this.notificationData.epoch;
      const op={owner:this.notificationOwner,entry:n.config_entry_id,epoch:n.epoch,ws:this._hass.callWS,hass:this._hass,connection:this._hass.connection};this.notificationOperation=op;this.notificationFlights.set(op.entry,op);this.notificationNotice='等待後端回覆…';this.renderResult();
      const current=()=>{this.notificationObserve();return this.notificationAllowed()&&this.notificationOwner===op.owner&&this.notificationOperation===op&&this._hass.callWS===op.ws&&this._hass.connection===op.connection&&this.resultNative()?.config_entry_id===op.entry&&this.resultNative()?.epoch===op.epoch;};
      try{let dto=await op.ws.call(op.hass,payload);if(!current())return;if(!this.notificationDTO(dto,op.entry,op.epoch))throw {code:'invalid_response'};
        if(action==='save'){const input=p=>({enabled:p.enabled,provider:p.provider,events:p.events,cooldown_seconds:p.cooldown_seconds,target_entity_id:p.target_binding?.entity_id??null});if(dto.revision!==base.revision+1||!sameValue(input(dto.policy),policy)||dto.availability==='indeterminate')throw {code:dto.availability==='indeterminate'?'indeterminate':'invalid_response'};
          const saved=dto;dto=await op.ws.call(op.hass,{type:'uninus_nutriculture/notification_v1/get',config_entry_id:op.entry});if(!current())return;if(!this.notificationDTO(dto,op.entry,op.epoch)||dto.revision!==saved.revision||!sameValue(dto.policy,saved.policy)||dto.availability==='indeterminate')throw {code:'indeterminate'};
        }
        if(action==='ack'&&!dto.deliveries.some(d=>d.event_id===eventId&&d.acknowledged))throw {code:'invalid_response'};if(action==='reconcile')this.notificationUnknown=dto.availability==='indeterminate';this.notificationData=structuredClone(dto);if(action==='save'||action==='reconcile'||!this.notificationDirty)this.notificationDraft(dto);this.notificationNotice=dto.availability==='indeterminate'?'indeterminate：保存結果未知；請明確重新讀取通知設定':action==='save'?'通知設定已保存並讀回；未發送通知':action==='ack'?'已標為已讀（不復歸、不重送）':action==='reconcile'?'已明確重新讀取通知設定；未重載控制或補送':'通知狀態已更新（純快取）';
      }catch(e){if(current()){const code=P4C_ERRORS.includes(e?.code)?e.code:'operation_failed';if(action==='save'&&(code==='indeterminate'||code==='operation_failed'))this.notificationUnknown=true;this.notificationNotice=code==='indeterminate'||action==='save'&&code==='operation_failed'?'indeterminate：保存結果未知；請明確重新讀取通知設定':code==='notification_conflict'?'notification_conflict：草稿保留，請取消後更新通知狀態':`通知操作失敗：${code}；草稿保留`;
          if(code==='unauthorized'){this.notificationPurge();this.notificationDenied=true;this.notificationNotice='unauthorized';}
        }}finally{if(this.notificationFlights.get(op.entry)===op)this.notificationFlights.delete(op.entry);if(this.notificationOperation===op)this.notificationOperation=null;this.renderResult();}
    }
    initQuality() {
      if(this.qualityPanel)return;
      this.qualityFlights=new Map();this.qualityGeneration=0;this.qualityOwner={};this.qualityInputs=new Map();
      this.qualityPanel=make('details');this.qualityPanel.dataset.qualityPanel='';this.qualityPanel.append(make('summary','資料品質與灌溉許可（P4b）'));
      for(const [key,label] of [['truth','資料品質'],['completion','本輪必要完成'],['permit','灌溉許可'],['info','窗口／期限（僅資訊）']]){const p=make('p',label);p.dataset['quality'+key[0].toUpperCase()+key.slice(1)]='';this['quality'+key[0].toUpperCase()+key.slice(1)]=p;this.qualityPanel.append(p);}
      this.qualityForm=make('section');this.qualityPanel.append(this.qualityForm);
      const add=(key,label,type='number',choices=null)=>{const row=make('label',label),input=make(choices?'select':'input');input.dataset.qualityField=key;input.setAttribute('aria-label',label);if(!choices)input.type=type;else for(const v of choices){const o=make('option',v);o.value=v;input.append(o);}if(type==='number'){input.min='1';input.max=key==='stable_samples'?'100':'86400';input.step='1';}input.addEventListener(type==='checkbox'||choices?'change':'input',()=>{this.qualityDirty=true;this.renderQuality();});row.append(input);this.qualityForm.append(row);this.qualityInputs.set(key,input);};
      add('enabled','啟用品質策略','checkbox');add('stable_samples','穩定樣本數（1–100 筆）');add('stable_interval_seconds','穩定樣本間隔（秒）');add('stable_duration_seconds','穩定窗口跨度（秒）');add('permit_ttl_seconds','許可最長有效期 TTL（秒）');
      for(const [k,l] of [['refill','補水'],['nutrient','加養'],['acid','加酸'],['mix','混合']])add('required.'+k,'本輪必要階段：'+l+'（至少一項；不改啟用設定）','checkbox');
      for(const [k,l] of [['ph','pH'],['ec','EC'],['level','液位']]){add(k+'.mode',l+' 新實測來源模式','text',['reported','sequence','timestamp']);add(k+'.attribute',l+' 來源屬性（reported 留空；最多128 Unicode字元）','text');add(k+'.confirmed',l+' 已確認上游新實測合約','checkbox');}
      this.qualityButtons={};for(const [key,label] of [['refresh','重新整理品質'],['save','保存品質策略'],['cancel','取消品質草稿']]){const b=make('button',label);b.type='button';b.dataset['quality'+key[0].toUpperCase()+key.slice(1)]='';b.addEventListener('click',()=>{if(key==='cancel'){if(this.qualityData)this.qualityDraft(this.qualityData);this.qualityNotice='已取消草稿；未寫入';this.renderQuality();}else this.qualityRequest(key==='save');});this.qualityButtons[key]=b;this.qualityForm.append(b);}
      this.qualityMessage=make('p');this.qualityMessage.dataset.qualityMessage='';this.qualityMessage.setAttribute('role','status');this.qualityPanel.append(this.qualityMessage);
      this.qualityPanel.addEventListener('toggle',()=>{if(this.qualityPanel.open&&!this.qualityData)this.qualityRequest(false);});
      this.shadowRoot.append(make('style','[data-quality-panel] label{display:block;margin:10px 0}[data-quality-panel] input:not([type=checkbox]),[data-quality-panel] select{display:block;width:100%;min-width:0;max-width:100%}[data-quality-panel] input[type=checkbox]{width:auto}[data-quality-panel] button{margin:4px;max-width:100%}[data-quality-panel] [hidden]{display:none}'));this.root.append(this.qualityPanel);
    }
    qualityPolicy(p) {
      if(!exact(p,['enabled','stable_samples','stable_interval_seconds','stable_duration_seconds','permit_ttl_seconds','required_stages','sources'])||typeof p.enabled!=='boolean'||!['stable_samples','stable_interval_seconds','stable_duration_seconds','permit_ttl_seconds'].every(k=>Number.isInteger(p[k])&&p[k]>=1&&p[k]<=(k==='stable_samples'?100:86400))||!Array.isArray(p.required_stages)||p.required_stages.length<1||p.required_stages.length>4||new Set(p.required_stages).size!==p.required_stages.length||!p.required_stages.every(k=>STAGES.includes(k))||!exact(p.sources,['ph','ec','level']))return false;
      return Object.values(p.sources).every(s=>exact(s,['mode','attribute','report_contract_confirmed'])&&['reported','sequence','timestamp'].includes(s.mode)&&typeof s.report_contract_confirmed==='boolean'&&(s.mode==='reported'?s.attribute===null:typeof s.attribute==='string'&&Array.from(s.attribute).length>=1&&Array.from(s.attribute).length<=128)&&(!p.enabled||s.report_contract_confirmed));
    }
    qualityDTO(d,entry) {
      const nullable=v=>v===null||typeof v==='string';
      const date=v=>{if(v===null)return true;if(typeof v!=='string'||!/^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d{1,6})?(?:Z|[+-]\d\d:\d\d)$/.test(v)||!Number.isFinite(Date.parse(v)))return false;const m=v.match(/^(\d{4})-(\d\d)-(\d\d)T(\d\d):(\d\d):(\d\d)/);return +m[2]>=1&&+m[2]<=12&&+m[3]>=1&&+m[3]<=new Date(Date.UTC(+m[1],+m[2],0)).getUTCDate()&&+m[4]<24&&+m[5]<60&&+m[6]<60;};
      const reasons=v=>Array.isArray(v)&&v.length<=32&&new Set(v).size===v.length&&v.every(k=>['policy_disabled','unsupported_control','source_invalid','source_stale','sample_unconfirmed','sample_regressed','out_of_range','stabilizing','no_current_run','run_incomplete','required_stage_disabled','stage_skipped','no_actual_start','closure_pending','output_not_off','fault','master_off','capability_lost','settings_changed','policy_changed','new_run','single_stage','aborted','entry_inactive','expired','candidate_consumed'].includes(k));
      return !!(exact(d,['schema_version','config_entry_id','epoch','observation_revision','policy_revision','settings_revision','flow_plan_revision','policy','entities','quality','completion','permit'])&&d.schema_version===1&&typeof d.config_entry_id==='string'&&Array.from(d.config_entry_id).length>=1&&Array.from(d.config_entry_id).length<=128&&(!entry||d.config_entry_id===entry)&&typeof d.epoch==='string'&&/^[a-f0-9]{32}$/.test(d.epoch)&&['observation_revision','policy_revision','settings_revision','flow_plan_revision'].every(k=>revision(d[k]))&&this.qualityPolicy(d.policy)&&exact(d.entities,['quality_status','irrigation_permit'])&&Object.values(d.entities).every(nullable)&&exact(d.quality,['state','stable_count','stable_since','reasons'])&&['disabled','unsupported','invalid','out_of_range','stabilizing','qualified'].includes(d.quality.state)&&Number.isInteger(d.quality.stable_count)&&d.quality.stable_count>=0&&d.quality.stable_count<=100&&date(d.quality.stable_since)&&reasons(d.quality.reasons)&&exact(d.completion,['state','run_id','settled_at'])&&['none','running','completed','incomplete','aborted','fault'].includes(d.completion.state)&&nullable(d.completion.run_id)&&date(d.completion.settled_at)&&exact(d.permit,['granted','run_id','expires_at','reasons'])&&typeof d.permit.granted==='boolean'&&nullable(d.permit.run_id)&&date(d.permit.expires_at)&&reasons(d.permit.reasons));
    }
    qualityNative() {
      const s=this._hass?.states?.[this.config?.quality_entity];if(!s||!s.attributes)return null;
      const d=Object.fromEntries(Object.entries(s.attributes).filter(([k])=>!HA_METADATA.includes(k)));
      if(!this.qualityDTO(d)||s.state!==d.quality.state||d.entities.quality_status!==this.config.quality_entity)return null;
      if(this.config.entity){const s=this.status();if(!writable(s)||!isControl(s)||s.attributes.settings_target?.config_entry_id!==d.config_entry_id)return null;}
      return d;
    }
    qualityPrincipalKey() {
      const u=this._hass?.user;
      return JSON.stringify([typeof u?.id==='string'?u.id:null,u?.is_admin===true,!!u&&u.is_active!==false]);
    }
    qualityObservePrincipal() {
      const principal=this.qualityPrincipalKey();
      if(this.qualityPrincipal===principal)return;
      // Capture primitives, never the mutable hass.user object. Transport flights
      // retain their locks until settlement; only their UI/data ownership expires.
      this.qualityPrincipal=principal;this.qualityOwner={};this.qualityGeneration++;
      this.qualityData=null;this.qualityDataOwner=null;this.qualitySyncBase=null;
      this.qualityBaseline=null;this.qualityBaselinePrincipal=null;this.qualityDirty=false;
      this.qualityOperation=null;this.qualityAttemptedNative=null;this.qualityNotice='';
      for(const i of this.qualityInputs.values()){if(i.type==='checkbox')i.checked=false;else i.value='';}
    }
    qualityAdmin() {
      const u=this._hass?.user;
      return typeof u?.id==='string'&&u.id.trim()!==''&&u.is_admin===true&&u.is_active!==false;
    }
    qualityWritable() {this.qualityObservePrincipal();const d=this.qualityNative();return !!(d&&this.qualityAdmin()&&this.config?.entity&&this.status()?.attributes.schema_version===5&&this._hass?.services?.uninus_nutriculture?.get_quality_v1&&this._hass?.services?.uninus_nutriculture?.save_quality_policy_v1&&typeof this._hass.callWS==='function'&&!this.qualityOffline);}
    qualityDraft(d) {
      this.qualityBaseline=structuredClone(d);this.qualityBaselinePrincipal=this.qualityPrincipal;const p=d.policy;for(const [k,i] of this.qualityInputs){let v;if(k.startsWith('required.'))v=p.required_stages.includes(k.split('.')[1]);else if(k.includes('.')){const [s,f]=k.split('.');v=p.sources[s][f==='confirmed'?'report_contract_confirmed':f];}else v=p[k];if(i.type==='checkbox')i.checked=v;else i.value=v??'';}this.qualityDirty=false;
    }
    qualityDraftPolicy() {const get=k=>this.qualityInputs.get(k),p={enabled:get('enabled').checked};for(const k of ['stable_samples','stable_interval_seconds','stable_duration_seconds','permit_ttl_seconds'])p[k]=get(k).value===''?null:Number(get(k).value);p.required_stages=STAGES.filter(k=>get('required.'+k).checked);p.sources=Object.fromEntries(['ph','ec','level'].map(k=>[k,{mode:get(k+'.mode').value,attribute:get(k+'.attribute').value||null,report_contract_confirmed:get(k+'.confirmed').checked}]));return p;}
    updateQuality() {
      this.initQuality();this.qualityObservePrincipal();const ws=this._hass?.callWS,conn=this._hass?.connection;
      if(this.qualityConnection!==conn||this.qualityWS!==ws)this.qualityOwner={};
      if(this.qualityConnection!==conn){if(this.qualityConnection?.removeEventListener){const n=this.qualityNative();this.qualityBlockedNative=n?`${n.config_entry_id}:${n.epoch}:${n.observation_revision}`:null;this.qualityConnection.removeEventListener('disconnected',this.qualityDisconnect);this.qualityConnection.removeEventListener('ready',this.qualityReady);}this.qualityConnection=conn;this.qualityDisconnect=()=>{const n=this.qualityNative();this.qualityBlockedNative=n?`${n.config_entry_id}:${n.epoch}:${n.observation_revision}`:null;this.qualityOffline=true;this.qualityOwner={};this.qualityGeneration++;this.qualityData=null;this.renderQuality();};this.qualityReady=()=>{this.qualityOffline=false;this.qualityOwner={};this.qualityGeneration++;this.qualityData=null;this.renderQuality();};if(conn?.addEventListener){conn.addEventListener('disconnected',this.qualityDisconnect);conn.addEventListener('ready',this.qualityReady);}}
      if(this.qualityWS!==ws){if(this.qualityWS){const n=this.qualityNative();this.qualityBlockedNative=n?`${n.config_entry_id}:${n.epoch}:${n.observation_revision}`:null;}this.qualityWS=ws;this.qualityGeneration++;this.qualityData=null;}if(conn?.connected===false)this.qualityOffline=true;
      const d=this.qualityNative(),identity=JSON.stringify([this.config?.entity,this.config?.quality_entity,d?.config_entry_id??this.qualityBoundEntry]);
      if(!d||this.qualityIdentity!==identity||this.qualityOffline)this.qualityOwner={};
      if(this.qualityIdentity!==identity){this.qualityIdentity=identity;this.qualityGeneration++;this.qualityData=null;this.qualityBaseline=null;this.qualityDirty=false;this.qualityOperation=null;this.qualityNotice='';this.qualityBoundEntry=d?.config_entry_id;}
      if(d&&this.qualityObservedEpoch&&this.qualityObservedEpoch!==d.epoch){this.qualityGeneration++;this.qualityData=null;}this.qualityObservedEpoch=d?.epoch;
      if(this.config?.quality_entity){if(this.qualityPanel.parentNode!==this.root)this.root.append(this.qualityPanel);}else this.qualityPanel.remove();this.qualityPanel.hidden=!this.config?.quality_entity;this.renderQuality();this.qualityConverge();
    }
    qualityConverge() {
      this.qualityObservePrincipal();const n=this.qualityNative(),a=(this.qualityDataOwner===this.qualityOwner?this.qualityData:null)??(this.qualitySyncBase?.owner===this.qualityOwner?this.qualitySyncBase.dto:null);
      if(!this.qualityPanel?.open||!this.qualityWritable()||!this.isConnected||!a||!n||a.epoch!==n.epoch||a.config_entry_id!==n.config_entry_id||n.observation_revision<=a.observation_revision||this.qualityOperation||this.qualityFlights.has(n.config_entry_id))return;
      const token=`${n.config_entry_id}:${n.epoch}:${n.observation_revision}`;
      if(token===this.qualityBlockedNative||token===this.qualityAttemptedNative||this.qualityQueued)return;
      const owner=this.qualityOwner,generation=this.qualityGeneration;this.qualityQueued=true;
      queueMicrotask(()=>{this.qualityQueued=false;if(this.qualityOwner===owner&&this.qualityGeneration===generation)this.qualityRequest(false,true);});
    }
    renderQuality() {
      if(!this.qualityPanel)return;this.qualityObservePrincipal();const n=this.qualityNative(),a=this.qualityDataOwner===this.qualityOwner?this.qualityData:null;const connected=!this.qualityOffline&&this.isConnected&&this._hass?.connection?.connected!==false;
      const joined=connected&&n&&this.qualityBlockedNative!==`${n.config_entry_id}:${n.epoch}:${n.observation_revision}`&&(this.config?.entity?(a&&a.config_entry_id===n.config_entry_id&&a.epoch===n.epoch&&a.observation_revision===n.observation_revision):true);
      text(this.qualityTruth,'資料品質：'+(joined?n.quality.state:'未知／未支援或尚未讀回'));
      text(this.qualityCompletion,'本輪必要完成：'+(joined?n.completion.state:'未知'));
      const usable=joined&&n.policy.enabled&&!['disabled','unsupported','invalid'].includes(n.quality.state);
      text(this.qualityPermit,'灌溉許可（P4b 唯一權威）：'+(usable?(n.permit.granted?'許可 True':'不許可 False'):'未知／不許可'));
      text(this.qualityInfo,joined?`穩定 ${n.quality.stable_count}/${n.policy.stable_samples} 筆；窗口 ${n.policy.stable_duration_seconds} 秒；起點 ${n.quality.stable_since??'無'}；到期 ${n.permit.expires_at??'無'}（僅資訊，不由瀏覽器計時授權）`:'品質資料未確認');
      this.qualityForm.hidden=!this.config?.entity;const busy=!!this.qualityOperation||this.qualityFlights.has(n?.config_entry_id);const writable=this.qualityWritable();for(const i of this.qualityInputs.values())i.disabled=(busy&&!this.qualityOperation?.automatic)||!writable||!this.qualityBaseline;
      this.qualityButtons.save.disabled=busy||!writable||!this.qualityBaseline||!this.qualityPolicy(this.qualityDraftPolicy());this.qualityButtons.refresh.disabled=busy||!writable;this.qualityButtons.cancel.disabled=busy||!this.qualityBaseline;
      text(this.qualityMessage,(this.qualityNotice??'')+(this._hass&&!this._hass.connection?'（無原生連線物件：UI harness／未驗證連線）':''));
    }
    async qualityRequest(save=false,automatic=false) {
      this.qualityObservePrincipal();const n=this.qualityNative();if(!n||!this.qualityWritable()||this.qualityFlights.has(n.config_entry_id))return;const base=this.qualityBaseline,policy=save?this.qualityDraftPolicy():null;if(save&&(!base||this.qualityBaselinePrincipal!==this.qualityPrincipal||!this.qualityPolicy(policy)))return;
      const payload={config_entry_id:n.config_entry_id};if(save)Object.assign(payload,{expected_policy_revision:base.policy_revision,expected_settings_revision:base.settings_revision,expected_flow_plan_revision:base.flow_plan_revision,policy});
      const token=`${n.config_entry_id}:${n.epoch}:${n.observation_revision}`;
      if(automatic&&(token===this.qualityAttemptedNative||token===this.qualityBlockedNative))return;
      this.qualityAttemptedNative=token;
      const op={entry:n.config_entry_id,epoch:n.epoch,readEpoch:n.epoch,owner:this.qualityOwner,principal:this.qualityPrincipal,automatic,generation:this.qualityGeneration,ws:this._hass.callWS,connection:this._hass.connection,hass:this._hass};this.qualityOperation=op;this.qualityFlights.set(op.entry,op);this.qualityNotice='等待後端讀回…';this.renderQuality();
      const owned=()=>{this.qualityObservePrincipal();return this.qualityAdmin()&&this.qualityPrincipal===op.principal&&this.isConnected&&!this.qualityOffline&&this._hass.connection?.connected!==false&&this.qualityOperation===op&&this.qualityOwner===op.owner&&this._hass.callWS===op.ws&&this._hass.connection===op.connection&&this.qualityNative()?.config_entry_id===op.entry;};
      const current=()=>owned()&&this.qualityGeneration===op.generation&&this.qualityNative()?.epoch===op.readEpoch;
      const call=(service,data)=>op.ws.call(op.hass,{type:'call_service',domain:'uninus_nutriculture',service,service_data:data,return_response:true});
      try{let result=await call(save?'save_quality_policy_v1':'get_quality_v1',payload);if(!owned())return;let dto=result?.response;if(!this.qualityDTO(dto,op.entry))throw {code:'invalid_response'};
        // Only this owned source-changing Save may transfer its acceptance fence.
        // Native publication alone never transfers ownership or accepts a reply.
        if(save&&dto.epoch!==op.epoch){const live=this.qualityNative();if(this.qualityGeneration!==op.generation+1||sameValue(base.policy.sources,policy.sources)||dto.policy_revision!==base.policy_revision+1||dto.settings_revision!==base.settings_revision||dto.flow_plan_revision!==base.flow_plan_revision||!sameValue(dto.policy,policy)||dto.observation_revision<=n.observation_revision||!sameValue(dto,live))return;op.readEpoch=dto.epoch;op.generation=this.qualityGeneration;}
        if(!current()||dto.epoch!==op.readEpoch)return;
        if(save){if(dto.policy_revision!==base.policy_revision+1||!sameValue(dto.policy,policy))throw {code:'invalid_response'};result=await call('get_quality_v1',{config_entry_id:op.entry});if(!current())return;const read=result?.response;if(!this.qualityDTO(read,op.entry)||read.epoch!==op.readEpoch||read.policy_revision!==dto.policy_revision||!sameValue(read.policy,policy))throw {code:'invalid_response'};dto=read;}
        const native=this.qualityNative();if(!sameValue(dto,native)||token===this.qualityBlockedNative)throw {code:'invalid_response'};
        this.qualityData=structuredClone(dto);this.qualityDataOwner=op.owner;this.qualitySyncBase={owner:op.owner,dto:this.qualityData};if(save||!this.qualityDirty)this.qualityDraft(dto);this.qualityNotice=save?'品質策略已保存並讀回；未啟動任何輸出':'品質資料已讀回；未寫入';
      }catch(e){if(current()){this.qualityData=null;this.qualityNotice=e?.code==='quality_conflict'?'品質版本衝突；草稿保留，請取消後重新整理':'品質操作失敗；草稿保留，請明確重新整理';}}
      finally{if(this.qualityFlights.get(op.entry)===op)this.qualityFlights.delete(op.entry);if(this.qualityOperation===op){const valid=current();if(!valid)this.qualityNotice='連線或版本已變更；草稿保留，請明確重新整理';this.qualityOperation=null;this.renderQuality();if(automatic&&valid)this.qualityConverge();}else this.renderQuality();}
    }
    static getConfigElement() { return document.createElement(`${TAG}-editor`); }
    static getStubConfig(hass) {
      const entity = Object.keys(hass?.states ?? {}).find(id => /^sensor\.[a-z0-9_]+$/.test(id) && (isShadow(hass.states[id]) || isControl(hass.states[id])));
      return {entity:entity ?? 'sensor.uninus_nutriculture_status',show_parameters:true};
    }
    getCardSize() { return this.details.isConnected && this.details.open ? 12 : 4; }
    connectedCallback() { this.update(); }
    disconnectedCallback() { if(this.resultPanel){this.notificationPurge();if(this.notificationConnection?.removeEventListener){this.notificationConnection.removeEventListener('disconnected',this.notificationDisconnect);this.notificationConnection.removeEventListener('ready',this.notificationReady);}this.notificationConnection=null;this.renderResult();}this.invalidate();if(this.qualityPanel){const n=this.qualityNative();this.qualityBlockedNative=n?`${n.config_entry_id}:${n.epoch}:${n.observation_revision}`:null;this.qualityGeneration++;this.qualityData=null;if(this.qualityConnection?.removeEventListener){this.qualityConnection.removeEventListener('disconnected',this.qualityDisconnect);this.qualityConnection.removeEventListener('ready',this.qualityReady);}this.qualityConnection=null;this.renderQuality();} }
    invalidate() {
      this.epoch = (this.epoch ?? 0) + 1;this.planOperation=null;this.previewOperation=null;this.planEpoch=(this.planEpoch??0)+1;this.recipeOperation=null;this.recipeGeneration=(this.recipeGeneration??0)+1;if(this.recipeConfirm)this.recipeConfirm.hidden=true;
      this.groupOperation=null;
      for (const row of this.rows.values()) { row.operation = null; row.pending = false; }
      for (const row of this.controlRows.values()) { row.operation = null; row.error = ''; }
    }
    setConfig(config) {
      if (!config || (config.entity!==undefined&&(typeof config.entity!=='string'||!/^sensor\.[a-z0-9_]+$/.test(config.entity))) || (config.entity===undefined&&config.quality_entity===undefined&&config.result_entity===undefined) || (config.result_entity!==undefined&&(typeof config.result_entity!=='string'||!/^sensor\.[a-z0-9_]+$/.test(config.result_entity))) || (config.quality_entity!==undefined&&(typeof config.quality_entity!=='string'||!/^sensor\.[a-z0-9_]+$/.test(config.quality_entity)))) throw new Error('請選擇狀態 sensor Entity');
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
      this.updateRows(); this.updateControls();this.updateGroup();this.updatePlan();this.updateRecipes();this.updateQuality();this.updateResult();
    }
  }
  class NutricultureEditor extends HTMLElement {
    constructor() {
      super(); this.attachShadow({mode:'open'});
      this.shadowRoot.append(make('style',`${style}label{display:block;margin:12px 0;font-size:14px}select{width:100%;max-width:100%;padding:10px;box-sizing:border-box;color:inherit;background:var(--card-background-color,#fff)}input[type=checkbox]{width:auto;margin-right:8px}`));
      this.resultInput=make('ha-selector');this.resultInput.selector={entity:{domain:'sensor'}};this.resultInput.dataset.resultEntity='';const rlabel=make('label','結果入口 result_entity（明確選取，不猜 Entity ID）');rlabel.append(this.resultInput);this.shadowRoot.append(rlabel);this.resultInput.addEventListener('value-changed',e=>{if(e.currentTarget!==this.resultInput)return;const value=e.detail?.value;if(value!==''&&value!==null&&value!==undefined&&(typeof value!=='string'||!/^sensor\.[a-z0-9_]+$/.test(value)))return;this.config={...this.config};if(value)this.config.result_entity=value;else delete this.config.result_entity;this.dispatchEvent(new CustomEvent('config-changed',{detail:{config:structuredClone(this.config)},bubbles:true,composed:true}));});
      this.entityInput = make('select'); this.entityInput.name = 'entity';
      this.qualityInput=make('ha-selector');this.qualityInput.selector={entity:{domain:'sensor'}};this.qualityInput.dataset.qualityEntity='';const qlabel=make('label','品質入口 quality_entity（可選；不猜 Entity ID）');qlabel.append(this.qualityInput);this.shadowRoot.append(qlabel);this.qualityInput.addEventListener('value-changed',e=>{if(e.currentTarget!==this.qualityInput)return;const value=e.detail?.value;this.config={...this.config};if(value)this.config.quality_entity=value;else delete this.config.quality_entity;this.dispatchEvent(new CustomEvent('config-changed',{detail:{config:structuredClone(this.config)},bubbles:true,composed:true}));});
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
      this.qualityInput.value=this.config.quality_entity??'';this.resultInput.value=this.config.result_entity??'';
      this.options();
    }
    set hass(hass) { this._hass = hass;this.qualityInput.hass=hass;this.resultInput.hass=hass; this.options(); }
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
