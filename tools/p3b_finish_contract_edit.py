"""One-time historical v4 strict parser edit."""
from pathlib import Path
p=Path(__file__).resolve().parents[1]/'uninus-nutriculture-card.js'
s=p.read_text();s=s.replace('  const validV4Groups=a=>exact(a.parameters,PARAMETERS.map(r=>r[0]))&&Object.values(a.parameters).every(number)', '''  const NORMAL_LIMITS={level_low:[0,10,.01],level_high:[0,10,.01],ph_low:[0,14,.1],ph_high:[0,14,.1],ec_low:[0,20,.01],ec_high:[0,20,.01],refill_timeout:[1,1440,1],ec_timeout:[1,1440,1],ph_timeout:[1,1440,1],mix_duration:[1,1440,1]};
  const V4_KEYS=['schema_version','mode','ready_for_irrigation','source_entities','parameter_entities','parameters','reasons','capabilities','control_entities','allowed_weekdays','stage_states','flow_state','fault','run_id','settings_target','settings_revision','dosing_parameters','acid_parameters','mix_parameters','safety_parameters','nutrient_phase','acid_phase','dose_progress','acid_progress','output_states'];
  // Only these native HA Entity metadata fields may sit outside our contract.
  const HA_METADATA=['friendly_name','icon','device_class','options'];
  const validV4Groups=a=>exact(a.parameters,PARAMETERS.map(r=>r[0]))&&Object.entries(NORMAL_LIMITS).every(([k,limits])=>inRange(a.parameters[k],...limits))&&['level','ph','ec'].every(k=>a.parameters[k+'_low']<a.parameters[k+'_high'])''')
s=s.replace('const validV4=a=>a.ready_for_irrigation===false', "const validV4=a=>V4_KEYS.every(k=>Object.hasOwn(a,k))&&Object.keys(a).every(k=>V4_KEYS.includes(k)||HA_METADATA.includes(k))&&V3_STATES.includes(a.flow_state)&&a.ready_for_irrigation===false")
p.write_text(s)
