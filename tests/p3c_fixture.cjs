// Frontend wire fixture only. NOT registered native/backend evidence.
module.exports=()=>{
 const states=require('./p3b_fixture.cjs')(),a=states['sensor.status'].attributes;
 a.schema_version=5;a.settings_target.service='apply_control_settings_v5';
 a.flow_plan_revision=0;a.flow_plan_target={config_entry_id:a.settings_target.config_entry_id,service:'apply_flow_plan_v5',preview_service:'preview_flow_plan_v5'};
 a.flow_plan={rows:['refill','nutrient','acid','mix'].map((stage,i)=>({stage,start_rule:i?'after_previous_finished':'flow_start',delay_seconds:0,condition:null,wait_timeout_seconds:300})),run_timeout_seconds:86400};
 a.run_plan=null;a.step_runtime=Object.fromEntries(['refill','nutrient','acid','mix'].map(k=>[k,{phase:null,result:null,started_at:null,settled_at:null,waiting_reason:null}]));
 a.output_states.refill='off';a.allowed_weekdays.mix=[];return states;
};
