from pathlib import Path
p=Path(__file__).resolve().parents[1]/'uninus-nutriculture-card.js'
s=p.read_text()
def edit(a,b):
 global s
 assert a in s,a[:70]
 s=s.replace(a,b)
insert=r'''
  const Q=DOSE.slice(0,9), S=DOSE.slice(9), STAGE_VALUES=['unsupported','idle','starting','waiting_resource','running','stopping','completed','aborted','fault','skipped_disabled','skipped_weekday','blocked_dependency'];
  const groupMap=(m,rows)=>exact(m,rows.map(r=>r[0]))&&rows.every(([k,,lo,hi,step])=>inRange(m[k],lo,hi,step));
  const validV4Groups=a=>exact(a.parameters,PARAMETERS.map(r=>r[0]))&&Object.values(a.parameters).every(number)&&groupMap(a.safety_parameters,S)&&
    (a.dosing_parameters===null||groupMap(a.dosing_parameters,DOSE))&&(a.acid_parameters===null||groupMap(a.acid_parameters,Q))&&(a.mix_parameters===null||groupMap(a.mix_parameters,[Q[0],Q[8]]))&&
    (a.dosing_parameters===null||S.every(([k])=>a.dosing_parameters[k]===a.safety_parameters[k]))&&
    exact(a.allowed_weekdays,STAGES)&&STAGES.every(k=>Array.isArray(a.allowed_weekdays[k])&&new Set(a.allowed_weekdays[k]).size===a.allowed_weekdays[k].length&&a.allowed_weekdays[k].every(d=>DAYS.includes(d)));
  const progress=v=>exact(v,['pulse_count','reserved_on_seconds','stable_count'])&&['pulse_count','stable_count'].every(k=>Number.isSafeInteger(v[k])&&v[k]>=0)&&number(v.reserved_on_seconds)&&v.reserved_on_seconds>=0;
  const phase=v=>[null,'starting_circulation','pulsing','confirming_off','mixing','waiting_sample','stabilizing'].includes(v);
  const validV4=a=>a.ready_for_irrigation===false&&validV4Groups(a)&&exact(a.capabilities,STAGES)&&STAGES.every(k=>typeof a.capabilities[k]==='boolean')&&
    ['nutrient','acid','mix'].every((k,i)=>(a[['dosing_parameters','acid_parameters','mix_parameters'][i]]!==null)===a.capabilities[k])&&
    exact(a.source_entities,['ph','ec','level'])&&Object.values(a.source_entities).every(id=>typeof id==='string'&&/^sensor\.[a-z0-9_]+$/.test(id))&&
    exact(a.settings_target,['config_entry_id','service'])&&typeof a.settings_target.config_entry_id==='string'&&a.settings_target.config_entry_id.trim()!==''&&a.settings_target.service==='apply_control_settings_v4'&&Number.isSafeInteger(a.settings_revision)&&a.settings_revision>=0&&
    a.parameter_entities&&typeof a.parameter_entities==='object'&&!Array.isArray(a.parameter_entities)&&Object.entries(a.parameter_entities).every(([k,id])=>PARAMETERS.some(r=>r[0]===k)&&typeof id==='string'&&/^number\.[a-z0-9_]+$/.test(id))&&new Set(Object.values(a.parameter_entities)).size===Object.keys(a.parameter_entities).length&&
    a.control_entities&&Object.entries(a.control_entities).every(([k,id])=>['automation_enabled','refill_enabled','nutrient_enabled','acid_enabled','mix_enabled','flow_run','emergency_stop','reset_fault'].includes(k)&&typeof id==='string'&&new RegExp(`^${['emergency_stop','reset_fault'].includes(k)?'button':'switch'}\\.[a-z0-9_]+$`).test(id)&&(!k.endsWith('_enabled')||k==='automation_enabled'||a.capabilities[k.replace('_enabled','')]))&&new Set(Object.values(a.control_entities)).size===Object.keys(a.control_entities).length&&
    exact(a.stage_states,STAGES)&&STAGES.every(k=>STAGE_VALUES.includes(a.stage_states[k]))&&phase(a.nutrient_phase)&&phase(a.acid_phase)&&progress(a.dose_progress)&&progress(a.acid_progress)&&
    exact(a.output_states,['nutrient','acid','circulation'])&&Object.values(a.output_states).every(v=>['on','off','unknown'].includes(v))&&Array.isArray(a.reasons)&&a.reasons.every(v=>typeof v==='string')&&['fault','run_id'].every(k=>a[k]===null||(typeof a[k]==='string'&&a[k].trim()!==''));
'''
edit('  const isControl =',insert+'\n  const isControl =')
edit('status.attributes.schema_version === 3 && validV3(status.attributes)','(status.attributes.schema_version === 3 && validV3(status.attributes)) || (status.attributes.schema_version === 4 && validV4(status.attributes))')
# Parentheses around the ternary branch remain owned by original isControl.
# Extend grouped editing only; strict validV3 is left unchanged.
s=s.replace('schema_version===3','schema_version>=3').replace('schema_version!==3','schema_version<3')
edit("['nutrient_enabled','加養子開關','switch'],","['nutrient_enabled','加養子開關','switch'],['acid_enabled','加酸子開關','switch'],['mix_enabled','獨立攪拌子開關','switch'],")
edit('      this.weekDetails=make',r'''      this.acidRows=new Map();this.mixRows=new Map();
      for(const [name,rows,map] of [['acid',Q,this.acidRows],['mix',[Q[0],Q[8]],this.mixRows]])for(const [key,label,min,max,step,unit] of rows){
        const el=make('div',undefined,'param');el.dataset[name]=key;const input=make('input');input.type='number';
        for(const [k,v] of Object.entries({min,max,step}))input.setAttribute(k,String(v));
        input.addEventListener('input',()=>{this.beginGroup();this.groupMessageText='';this.updateGroup();});
        el.append(make('label',`${name==='acid'?'加酸':'獨立攪拌'} · ${label} (${unit||'次'})`),input);this.doseDetails.append(el);map.set(key,{input,el});
      }
      this.weekDetails=make''')
edit('    groupValues() {','    groupValues() {\n      if(this.status()?.attributes?.schema_version===4){\n        const a=this.status().attributes, read=map=>Object.fromEntries([...map].map(([k,r])=>[k,r.input.value===\'\'?null:Number(r.input.value)]));\n        const all=read(this.doseRows),safety=Object.fromEntries(S.map(([k])=>[k,all[k]]));\n        return {parameters:read(this.rows),dosing_parameters:a.capabilities.nutrient?{...all,...safety}:null,acid_parameters:a.capabilities.acid?read(this.acidRows):null,mix_parameters:a.capabilities.mix?read(this.mixRows):null,safety_parameters:safety,allowed_weekdays:Object.fromEntries([...this.weekRows].map(([k,inputs])=>[k,[...inputs].filter(([,input])=>input.checked).map(([d])=>d)]))};\n      }')
edit('    groupValid(values) {','    groupValid(values) {\n      if(this.status()?.attributes?.schema_version===4){\n        if(!validV4Groups(values)||![...this.rows.values()].every(r=>this.valid(r,this.target(r))))return false;\n        const p=values.parameters,s=values.safety_parameters;\n        return p.level_low<p.level_high&&p.ph_low<p.ph_high&&p.ec_low<p.ec_high&&s.ph_danger_low<p.ph_low&&s.ec_danger_high>p.ec_high&&[values.dosing_parameters,values.acid_parameters].every(d=>d===null||d.pulse_seconds<=d.max_total_on_seconds);\n      }')
edit('const v=String(a?.dosing_parameters?.[k] ?? \'\');','const v=String((a?.schema_version===4&&S.some(r=>r[0]===k)?a?.safety_parameters?.[k]:a?.dosing_parameters?.[k]) ?? \'\');')
edit('      for(const r of this.doseRows.values())r.input.disabled=!usable || pending;',r'''      for(const [k,r] of this.doseRows){r.input.disabled=!usable||pending||(a?.schema_version===4&&Q.some(v=>v[0]===k)&&!a.capabilities.nutrient);r.input.parentNode.hidden=a?.schema_version===4&&Q.some(v=>v[0]===k)&&!a.capabilities.nutrient;}
      for(const [name,map] of [['acid',this.acidRows],['mix',this.mixRows]])for(const [k,r] of map){
        r.el.hidden=a?.schema_version!==4||!a.capabilities?.[name];r.input.disabled=!usable||pending||r.el.hidden;
        if(!this.groupDraft){const v=String(a?.[name+'_parameters']?.[k]??'');if(r.input.value!==v)r.input.value=v;}
      }''')
edit("      return ['parameters','dosing_parameters'].every", "      if(a.schema_version===4)return ['parameters','dosing_parameters','acid_parameters','mix_parameters','safety_parameters'].every(k=>JSON.stringify(a[k])===JSON.stringify(b[k]))&&STAGES.every(k=>JSON.stringify(a.allowed_weekdays[k])===JSON.stringify(b.allowed_weekdays[k]));\n      return ['parameters','dosing_parameters'].every")
edit("await this._hass.callService('uninus_nutriculture','apply_control_settings',", "await this._hass.callService('uninus_nutriculture',a.settings_target.service,")
edit("      if (row.key==='refill_enabled'", "      if(['acid_enabled','mix_enabled'].includes(row.key)&& (a.schema_version!==4||!a.capabilities[row.key.replace('_enabled','')]))return {error:'階段尚未支援；禁止操作'};\n      if (row.key==='refill_enabled'")
edit('      for (const row of this.controlRows.values()) {\n        if(row.key=', '      for (const row of this.controlRows.values()) {\n        row.el.hidden=[\'acid_enabled\',\'mix_enabled\'].includes(row.key)&&this.status()?.attributes?.schema_version!==4;\n        if(row.key=')
edit("text(this.unsupported,a.schema_version>=3?", "text(this.unsupported,a.schema_version===4?`加酸：${a.stage_states.acid} · phase ${a.acid_phase??'無'} · 脈衝 ${a.acid_progress.pulse_count} · ON ${a.acid_progress.reserved_on_seconds}s · 穩定 ${a.acid_progress.stable_count}\\n獨立攪拌：${a.stage_states.mix} · 酸輸出 ${a.output_states.acid} / 循環 ${a.output_states.circulation}`:a.schema_version>=3?")
edit("['補水','加養','加酸（未支援）','獨立混合（未支援）']", "['補水','加養','加酸','獨立攪拌']")
edit("schema 2 / 3 control", "schema 2 / 3 / 4 control")
p.write_text(s,newline='\n')
