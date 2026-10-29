// 盤面別勝率：data/pos5.json を読み、一覧と、選んだ盤面の勝率・最善進行・導出（答案ふう）を出す
(function () {
  const $ = (s) => document.querySelector(s);
  const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  const val = (s) => { const [a, b] = String(s).split('/'); return b ? a / b : +a; };
  const fr = (s) => { const [a, b] = String(s).split('/'); return b ? `<span class="fr"><span>${a}</span><span>${b}</span></span>` : `<span class="num">${a}</span>`; };
  const pct = (s) => (val(s) * 100).toFixed(1) + '%';
  const sym = (s) => /^P\d*$/.test(s) ? `<span class="sym">P<sub>${s.slice(1)}</sub></span>` : fr(s);
  let D = [], grp = 'すべて';

  function list() {
    const gs = ['すべて', ...new Set(D.map((b) => b.group))];
    $('#groups').innerHTML = gs.map((g) => `<button type="button" class="${g === grp ? 'on' : ''}" data-g="${esc(g)}">${esc(g)}</button>`).join('');
    const rows = D.filter((b) => grp === 'すべて' || b.group === grp).map((b) =>
      `<tr class="c${location.hash === '#' + b.id ? ' sel' : ''}" data-id="${b.id}"><td><span class="bd-name">${esc(b.labels.join(','))}</span><div class="cond">${esc(b.cond.join('、'))}</div></td>
        <td class="n">${pct(b.value)}</td></tr>`).join('');
    $('#list-t').innerHTML = `<table class="bl"><thead><tr><th>盤面（条件）</th><th>村勝率</th></tr></thead><tbody>${rows}</tbody></table>`;
  }

  function eqline(r) {
    const rhs = r.terms.map((t) => `${fr(t.q)}·${sym(t.v)}`).join(' + ');
    return `<div class="eq">${sym(r.sym)} = ${rhs}${r.terms.length > 1 || r.terms[0].v !== r.value ? ` = ${fr(r.value)}` : ''}</div>`;
  }

  function answer(f) {
    return f.map((r) => {
      const alts = r.alts.length > 1 ? `<div class="alt">人外の選択：${r.alts.map((a) => `<span class="${a.chosen ? 'ch' : ''}">${esc(a.label)} → ${fr(a.value)}${a.chosen ? '（採用）' : ''}</span>`).join('、')}</div>` : '';
      const terms = `<ul>${r.terms.map((t) => `<li>${fr(t.q)}：${esc(t.ev)} → ${t.val ? `${sym(t.v)} = ${fr(t.val)}` : (val(t.v) === 1 ? '村勝ち' : val(t.v) === 0 ? '狼勝ち' : fr(t.v))}</li>`).join('')}</ul>`;
      const path = r.path.length ? `<div class="path">${esc(r.path.join(' → '))}</div>` : '';
      return `<div class="ans">${path}${alts}${eqline(r)}${terms}</div>`;
    }).join('');
  }

  function detail(id) {
    const b = D.find((x) => x.id === id);
    if (!b) { $('#detail').innerHTML = ''; return; }
    const cases = `<table><thead><tr><th>内訳</th><th>最善進行での勝率</th><th>内訳が分かっていた場合</th></tr></thead><tbody>${b.cases.map((c) => `<tr><td>${esc(c.name)}</td><td class="n">${fr(c.value)} <span class="pc">${pct(c.value)}</span></td><td class="n">${fr(c.known)} <span class="pc">${pct(c.known)}</span></td></tr>`).join('')}
      ${b.cases.length > 1 ? `<tr><td><b>平均</b></td><td class="n"><b>${fr(b.value)}</b> <span class="pc">${pct(b.value)}</span></td><td></td></tr>` : ''}</tbody></table>`;
    const best = Math.max(...b.root.map((r) => Math.max(...r.values.map(val))));
    const root = `<table><thead><tr><th>1日目の吊り先</th><th>村勝率（平均）</th>${b.cases.length > 1 ? b.cases.map((c) => `<th>${esc(c.name)}</th>`).join('') : ''}</tr></thead><tbody>${b.root.map((r) => {
      const v = r.value || r.values.join('〜');
      const isb = r.values.some((x) => Math.abs(val(x) - best) < 1e-12);
      return `<tr class="${isb ? 'best' : ''}"><td>${esc(r.label)}<span class="muted sm">（${r.pos.map((p) => p + '番').join('・')}）</span>${isb ? '<span class="lbl acc">最善</span>' : ''}</td><td class="n">${r.value ? fr(r.value) + ` <span class="pc">${pct(r.value)}</span>` : esc(v)}</td>${b.cases.length > 1 ? r.cases.map((c) => `<td class="n">${fr(c)}</td>`).join('') : ''}</tr>`;
    }).join('')}</tbody></table>`;
    const pol = `<table class="pol"><thead><tr><th>いつ</th><th>それまでに起きたこと</th><th>村の手</th><th>この局面になる確率</th></tr></thead><tbody>${b.policy.map((p) => `<tr><td class="nw">${esc(p.when)}</td><td>${esc(p.seen)}</td><td><b>${esc(p.act)}</b></td><td class="n">${fr(p.p)}</td></tr>`).join('')}</tbody></table>`;
    const der = b.deriv.map((d, i) => `<details${i === 0 ? ' open' : ''}><summary>${esc(d.name)}（${fr(b.cases[i].value)}）</summary>${answer(d.f)}</details>`).join('');
    $('#detail').innerHTML = `<div class="res" id="d-${b.id}">
      <h3>${esc(b.labels.join(','))}<span class="cond">（${esc(b.cond.join('、'))}）</span></h3>
      <div><span class="big">${pct(b.value)}</span> <span class="big">${fr(b.value)}</span></div>
      <h3>内訳ごとの勝率</h3><div class="tbl">${cases}</div>
      <h3>1日目の吊り先ごとの勝率</h3><p class="sm muted">その吊り先に決めたうえで、あとは最善に進めたときの値です。同じ見え方の人はまとめています。</p><div class="tbl">${root}</div>
      <h3>最善進行</h3><p class="sm muted">公開情報ごとの村の手です。灰A・灰B…は、名前が出てきた順に付けた呼び名です（同じ見え方の人を入れ替えた局面はまとめています）。</p><div class="tbl">${pol}</div>
      <h3>導出</h3><p class="sm muted">最善進行と人外の最善の手に沿って、内訳ごとに勝率を分解した式です。（ ）は本当の役。P は村勝率、P<sub>k</sub> はその先の局面での村勝率です。</p>${der}
    </div>`;
  }

  function route() {
    const id = location.hash.slice(1);
    list();
    if (/^p5-/.test(id)) { detail(id); const el = $('#detail'); if (el.firstChild) el.scrollIntoView({ block: 'start' }); }
  }
  $('#groups').addEventListener('click', (e) => { const g = e.target.closest('button'); if (g) { grp = g.dataset.g; list(); } });
  $('#list-t').addEventListener('click', (e) => { const tr = e.target.closest('tr.c'); if (tr) location.hash = tr.dataset.id; });
  window.addEventListener('hashchange', route);
  fetch('data/pos5.json').then((r) => r.json()).then((d) => { D = d; route(); });
})();
