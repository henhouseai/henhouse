// Site.js - Basic JavaScript functionality
console.log('site.js loaded successfully!');


// Ensure global namespace and organize methods under window.hh
window.hh = window.hh || {};
window.hh.page = window.hh.page || {};
// One-time bootstrap import into window.hh
(function initBootstrapIntoHH() {
  const boot = (typeof window.__HH_BOOTSTRAP__ !== 'undefined' && window.__HH_BOOTSTRAP__) || {};
  if (boot.page && boot.page.id && !window.hh.page.id) {
    window.hh.page.id = String(boot.page.id);
  }
})();

// Generic JSON-RPC helper
window.hh.rpc = window.hh.rpc || {};
window.hh.rpc.call = async function rpcCall(method, params) {
  const payload = { jsonrpc: '2.0', id: Date.now(), method, params: params || {} };
  const res = await fetch('/mcp', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });
  return res.json();
};
window.hh.rpc.showError = function showError(label, err) {
  const box = document.createElement('div');
  box.className = 'hh-error';
  box.style.cssText = 'position: fixed; top: 10px; right: 10px; background: #331; color: #f66; padding: 10px; border: 1px solid #f66; z-index: 9999; font-family: monospace; max-width: 420px; white-space: pre-wrap;';
  box.textContent = `[site.js] ${label} failed\n` + String(err);
  (document.body || document.documentElement).appendChild(box);
};
window.hh.rpc.execute = async function execute({ label, method, params, render }) {
  try {
    const data = await window.hh.rpc.call(method, params);
    render && render(data);
  } catch (e) {
    console.error(label + ' error', e);
    window.hh.rpc.showError(label, e);
  }
};

// Requests
window.hh.page.get_page = function get_page(pageId) {
  return window.hh.rpc.call('get_page', { id: String(pageId ?? '') });
};

window.hh.command_list = function command_list() {
  return window.hh.rpc.call('command_list', {});
};

// Link helpers
window.hh.get_link = function get_link(pageId) {
  /**Create a page link URL for the given page ID, matching Python create_page_link format.*/
  return `show-page?id=${String(pageId || '')}`;
};

// Renderers
window.hh.page.render_get_page = function render_get_page(data, seedId) {
  const result = data && data.result ? data.result : null;
  const dat = result && (result.dat || result.data || null);
  const page = dat && dat.page ? dat.page : null;
  const images = dat && Array.isArray(dat.images) ? dat.images : [];
  const childrenByClass = dat && dat.children_by_class ? dat.children_by_class : {};
  const childGroups = childrenByClass && typeof childrenByClass === 'object' ? Object.values(childrenByClass) : [];
  const childrenCount = childGroups.reduce((acc, grp) => {
    const arr = grp && Array.isArray(grp.children) ? grp.children : [];
    return acc + arr.length;
  }, 0);
  const name = page && (page.name || page.title) ? (page.name || page.title) : 'unknown';
  const idStr = page && (page.id !== undefined && page.id !== null) ? String(page.id) : String(seedId || '');

  // Populate global window.hh with normalized structures
  window.hh.page = Object.assign({}, page || {}, { id: idStr });
  const flatChildren = childGroups.flatMap(grp => (grp && Array.isArray(grp.children) ? grp.children : []));
  window.hh.page.children = flatChildren;
  window.hh.images = images;

  console.log('get_page summary:', { name, id: idStr, images: images.length, children: childrenCount, raw: data });
};

window.hh.render_command_list = function render_command_list(data) {
  const result = data && data.result ? data.result : null;
  const dat = result && (result.dat || result.data || null);
  const commands = dat && Array.isArray(dat.commands) ? dat.commands : [];
  const names = commands.map(c => c && (c.name || c.module_path || '?'));
  window.hh.commands = names;
  const box = document.createElement('div');
  box.id = 'hh-command-list';
  box.style.cssText = 'position: fixed; bottom: 10px; left: 10px; background: #222; color: #0ff; padding: 10px; border: 1px solid #0ff; z-index: 9999; font-family: monospace; max-width: 360px; max-height: 40vh; overflow:auto;';
  const title = `Commands (${names.length})`;
  const origin = window.location.origin || '';
  const listHtml = names.length
    ? names.map(n => {
        const cmd = String(n || '').trim();
        const href = origin + '/' + encodeURIComponent(cmd);
        const label = cmd || '?';
        return `- <a href="${href}" target="_blank" rel="noopener noreferrer" style="color:#0ff;text-decoration:underline;">${label}</a>`;
      }).join('<br>')
    : '&lt;none&gt;';
  box.innerHTML = `[site.js] ${title}<br>${listHtml}`;
  (document.body || document.documentElement).appendChild(box);
  console.log('command_list summary:', names);
};

// On load: use seeded page id to call JSON-RPC and display server response
document.addEventListener('DOMContentLoaded', async function() {
  const pageId = window.hh.page && window.hh.page.id ? window.hh.page.id : '';
  window.hh.rpc.execute({
    label: 'Load Page',
    method: 'get_page',
    params: { id: String(pageId || '') },
    render: (data) => window.hh.page.render_get_page(data, pageId)
  });
});

// Also run command_list on load and render available commands
// document.addEventListener('DOMContentLoaded', async function() {
//   window.hh.rpc.execute({
//     label: 'List Commands',
//     method: 'command_list',
//     params: {},
//     render: (data) => window.hh.render_command_list(data)
//   });
// });
