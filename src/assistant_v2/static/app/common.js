// Small helpers shared by all pages: top bar, status, chat bubbles, requests.
export const $ = (s, el = document) => el.querySelector(s);
export const esc = x => String(x ?? '').replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
// escape, then **bold**
export const fmt = x => esc(x).replace(/\*\*(.+?)\*\*/g, '<b>$1</b>');
export async function post(url, body) {
  try { const r = await fetch(url, { method: 'POST', body: JSON.stringify(body || {}) }); return await r.json(); }
  catch (e) { return { error: 'The assistant is not running. Start it again with start_assistant.bat.' }; }
}
export async function get(url) { try { return await (await fetch(url)).json(); } catch (e) { return null; } }

export function topbar(active, extraHtml = '') {
  const el = $('#top'); if (!el) return;
  el.className = 'top';
  el.innerHTML = `<a class="brand" href="/"><span class="logo">V</span><span>Voron 0.2 Assistant</span></a>
    <nav class="nav"><a href="/" class="${active === 'home' ? 'on' : ''}">Home</a><a href="/assembly" class="${active === 'assembly' ? 'on' : ''}">Assembly</a><a href="/repair" class="${active === 'repair' ? 'on' : ''}">Repair assistant</a></nav>
    <span class="space"></span>${extraHtml}<span class="status" title="The language model (Ollama) improves the answers. Without it the assistant still works."><span class="dot" id="st-dot"></span><span id="st-text">checking…</span></span>`;
  get('/api/info').then(i => { if (!i) { $('#st-text').textContent = 'server not running'; return; }
    $('#st-dot').className = 'dot ' + (i.ollama ? 'on' : 'off'); $('#st-text').textContent = i.ollama ? 'Full mode (language model on)' : /demo/.test(i.model || '') ? 'Basic mode (symptom graph only)' : 'Basic mode (start Ollama for full mode)'; });
}

// chat log helper
export function Chat(log) {
  const C = {
    say(html, who = 'bot') { const d = document.createElement('div'); d.className = 'msg ' + who; d.innerHTML = html; log.appendChild(d); log.scrollTop = log.scrollHeight; return d; },
    me(text) { return C.say(esc(text), 'me'); },
    typing(label = '') { const d = C.say(`<span class="typing"><i></i><i></i><i></i></span> <span class="mut small">${esc(label)}</span>`); return () => d.remove(); },
    // add a row of buttons to a message; after one click all are disabled
    buttons(msg, list) { const row = document.createElement('div'); row.className = 'btns';
      for (const b of list) { const el = document.createElement('button'); el.className = 'sm ' + (b.cls || ''); el.textContent = b.label;
        el.onclick = () => { if (!b.keep) row.querySelectorAll('button').forEach(x => x.disabled = true); b.on(el); }; row.appendChild(el); }
      msg.appendChild(row); log.scrollTop = log.scrollHeight; return row; },
    clear() { log.innerHTML = ''; },
  };
  return C;
}
// composer: Enter sends, Shift+Enter makes a new line
export function composer(textarea, button, onSend) {
  const go = () => { const t = textarea.value.trim(); if (!t) return; textarea.value = ''; onSend(t); };
  button.onclick = go; textarea.addEventListener('keydown', e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); go(); } });
}
