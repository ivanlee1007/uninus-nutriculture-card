(() => {
  class NutricultureCard extends HTMLElement {
    constructor() { super(); this.attachShadow({mode: 'open'}); }
    setConfig(config) { this.config = {...config}; }
    set hass(hass) { this._hass = hass; }
  }
  customElements.define('uninus-nutriculture-card', NutricultureCard);
})();
