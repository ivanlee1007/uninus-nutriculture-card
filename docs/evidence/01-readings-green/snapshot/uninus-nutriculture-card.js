/* UNiNUS Nutriculture Card 0.1.0-alpha.1 — self-contained shadow monitor. */
(() => {
  'use strict';
  const TAG = 'uninus-nutriculture-card';
  const finite = value => (typeof value === 'number' || (typeof value === 'string' && value.trim() !== '')) && Number.isFinite(Number(value));
  const text = (node, value) => { const next = String(value ?? ''); if (node.textContent !== next) node.textContent = next; };
  const make = (tag, value, className) => { const el = document.createElement(tag); if (value !== undefined) text(el, value); if (className) el.className = className; return el; };
  const style = `
    :host{display:block;min-width:0;color:var(--primary-text-color,#213b48);font-family:var(--paper-font-body1_-_font-family,system-ui,sans-serif)}
    *{box-sizing:border-box}ha-card{display:block;border:1px solid var(--divider-color,#d9e4e7);border-radius:var(--ha-card-border-radius,16px);background:var(--ha-card-background,var(--card-background-color,#fff));padding:18px;overflow-wrap:anywhere}
    h2{font-size:19px;line-height:1.35;margin:0}header p{color:var(--secondary-text-color,#607782);font-size:13px;margin:4px 0 12px}.badge{display:inline-block;color:var(--primary-color,#277b86);background:var(--secondary-background-color,#edf5f6);border-radius:8px;padding:4px 8px;font-size:12px}
    .safety{border-left:3px solid var(--primary-color,#277b86);padding:8px 10px;margin:12px 0;font-size:13px;background:var(--secondary-background-color,#edf5f6)}
    .tiles{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px}.tile{min-width:0;background:var(--secondary-background-color,#f2f7f8);padding:12px 8px;border-radius:10px}.tile span{display:block;color:var(--secondary-text-color,#607782);font-size:12px}.tile strong{display:block;font-size:22px;font-variant-numeric:tabular-nums;margin:6px 0}.tile small{font-size:11px;overflow-wrap:anywhere}
    .quality{font-size:13px;margin:12px 0 0;white-space:pre-line}.quality.warn{color:var(--error-color,#a44e28)}
    @media(max-width:360px){ha-card{padding:12px}.tile strong{font-size:20px}.tile{padding:10px 6px}}
  `;
  class NutricultureCard extends HTMLElement {
    constructor() {
      super(); this.attachShadow({mode:'open'});
      const css = make('style', style); this.root = make('ha-card');
      const header = make('header'); this.heading = make('h2','UNiNUS Nutriculture');
      header.append(this.heading,make('p','養液控制'),make('span','影子監測','badge'));
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
    }
    setConfig(config) {
      if (!config || typeof config.entity !== 'string' || !/^sensor\.[a-z0-9_]+$/.test(config.entity)) throw new Error('請選擇狀態 sensor Entity');
      this.config = {...config}; this.update();
    }
    set hass(hass) { this._hass = hass; this.update(); }
    get hass() { return this._hass; }
    status() { return this._hass?.states?.[this.config?.entity]; }
    update() {
      text(this.heading,this.config?.title ?? 'UNiNUS Nutriculture');
      const status = this.status();
      for (const [key, nodes] of Object.entries(this.readings)) {
        const source = this._hass?.states?.[status?.attributes?.source_entities?.[key]];
        text(nodes.value,finite(source?.state) ? Number(source.state).toLocaleString(undefined,{maximumFractionDigits:3}) : '—');
        text(nodes.unit,source?.attributes?.unit_of_measurement ?? ({ph:'pH',ec:'mS/cm',level:'m'}[key]));
      }
      const compatible = status?.attributes?.schema_version === 1 && status?.attributes?.mode === 'shadow';
      const labels = {within_range:'讀值在範圍內',out_of_range:'讀值超出範圍',invalid:'來源資料無效'};
      const warning = !compatible ? '狀態缺失或不相容：僅支援 schema 1 / shadow；禁止儲存。' : labels[status.state] ?? '未知狀態；禁止儲存。';
      const reasons = Array.isArray(status?.attributes?.reasons) ? status.attributes.reasons.map(String) : [];
      text(this.quality,[warning,...reasons].join('\n')); this.quality.classList.toggle('warn',!compatible || status.state !== 'within_range');
    }
  }
  customElements.define(TAG,NutricultureCard);
})();
