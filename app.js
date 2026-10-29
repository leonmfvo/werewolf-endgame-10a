// 終盤表：局面（役と見え方の人数）を選ぶと、data/states.json から村勝率と、吊り先・噛み先ごとの値を出す
(function () {
  const $ = (s) => document.querySelector(s);
  const ST = { b: '確定黒', c: '狩人CO者2人', g: 'グレー', w: '確定白', H: '狩人CO者', S: '確定占い', M: '確定霊能' };
  const RN = { V: '村人', H: '狩人', X: '狂人', W: '狼', S: '占い', M: '霊能' };
  let D = null, ph = 'D';
  // 入力：村人 g/w の人数、狩人と狂人の見え方、狼 g/b/c の人数、占い・霊能の生死
  const st = { Vg: 2, Vw: 0, H: 'g', X: '', Wg: 1, Wb: 0, Wc: 0, S: 0, M: 0 };
  const PRE = [
    ['村村狩＋狼1（全員グレー）・昼', { Vg: 2, Vw: 0, H: 'g', X: '', Wg: 1, Wb: 0, Wc: 0, S: 0, M: 0 }, 'D'],
    ['村村狩狂＋狼1（全員グレー）・昼', { Vg: 2, Vw: 0, H: 'g', X: 'g', Wg: 1, Wb: 0, Wc: 0, S: 0, M: 0 }, 'D'],
    ['確定占い＋村3狩＋狼2・夜', { Vg: 3, Vw: 0, H: 'g', X: '', Wg: 2, Wb: 0, Wc: 0, S: 1, M: 0 }, 'N'],
    ['狩人CO済み＋村3＋狼1・昼', { Vg: 3, Vw: 0, H: 'H', X: '', Wg: 1, Wb: 0, Wc: 0, S: 0, M: 0 }, 'D'],
  ];
  function counts() {
    const c = D.pairs.map(() => 0);
    const set = (r, s, v) => { const i = D.pairs.findIndex(([a, b]) => a === r && b === s); c[i] += v; };
    set('V', 'g', st.Vg); set('V', 'w', st.Vw);
    if (st.H) set('H', st.H, 1);
    if (st.X) set('X', st.X, 1);
    set('W', 'g', st.Wg); set('W', 'b', st.Wb); set('W', 'c', st.Wc);
    if (st.S) set('S', 'S', 1); if (st.M) set('M', 'M', 1);
    return c;
  }
  const pct = (f) => (f[0] / f[1] * 100).toFixed(1) + '%';
  const frs = (f) => `${f[0]}/${f[1]}`;
  // 分数は短いときだけ表示し、長いときは押すと出る（title）にする
  const frh = (f) => (String(f[1]).length <= 8 ? ` <span class="muted">(${frs(f)})</span>` : ` <span class="muted" title="${frs(f)}">(分数)</span>`);
  function stepper(key, lo, hi) {
    const w = document.createElement('span'); w.className = 'step';
    const m = document.createElement('button'); m.type = 'button'; m.textContent = '−'; m.setAttribute('aria-label', '減らす');
    const v = document.createElement('b'); v.textContent = st[key];
    const p = document.createElement('button'); p.type = 'button'; p.textContent = '+'; p.setAttribute('aria-label', '増やす');
    m.onclick = () => { if (st[key] > lo) { st[key]--; draw(); } };
    p.onclick = () => { if (st[key] < hi) { st[key]++; draw(); } };
    w.append(m, v, p); return w;
  }
  function radio(key, opts) {
    const w = document.createElement('span'); w.className = 'rad';
    for (const [val, lab] of opts) {
      const b = document.createElement('button'); b.type = 'button'; b.textContent = lab;
      if (st[key] === val) b.className = 'on';
      b.onclick = () => { st[key] = val; draw(); };
      w.append(b);
    }
    return w;
  }
  function row(f, label, ...ctl) {
    const l = document.createElement('div'); l.className = 'rl'; l.textContent = label;
    const c = document.createElement('div'); c.className = 'ctl';
    for (const x of ctl) c.append(x);
    f.append(l, c);
  }
  function lab(t, el) { const s = document.createElement('span'); s.className = 'sm'; s.append(t + ' ', el); return s; }
  function form() {
    const f = $('#form'); f.textContent = '';
    row(f, '村人', lab('グレー', stepper('Vg', 0, 4)), lab('確定白', stepper('Vw', 0, 4)));
    row(f, '狩人', radio('H', [['', 'いない'], ['g', 'グレー'], ['w', '確定白'], ['H', 'CO済み'], ['c', '対抗あり']]));
    row(f, '狂人', radio('X', [['', 'いない'], ['g', 'グレー'], ['w', '確定白']]));
    row(f, '狼', lab('グレー', stepper('Wg', 0, 2)), lab('確定黒', stepper('Wb', 0, 2)), lab('対抗の狩人CO', stepper('Wc', 0, 1)));
    row(f, '占い', radio('S', [[0, 'いない'], [1, '確定して生存']]));
    row(f, '霊能', radio('M', [[0, 'いない'], [1, '確定して生存']]));
    document.querySelectorAll('.sg').forEach((b) => b.classList.toggle('on', b.dataset.ph === ph));
  }
  function who(c) {
    const n = (r, s) => c[D.pairs.findIndex(([a, b]) => a === r && b === s)];
    if (n('S', 'S')) return '指定役：確定占い';
    if (n('M', 'M')) return '指定役：確定霊能';
    if (n('H', 'H')) return '指定役：狩人CO者';
    const w = n('V', 'w') + n('H', 'w') + n('X', 'w');
    if (w) return `指定役：確定白（${w}人からランダム` + (n('X', 'w') ? '。狂人が指定役になると村に一番悪い吊り先を選ぶ' : '') + '）';
    return '指定役なし：自由投票（狼は身内に投票しない）';
  }
  function result() {
    const r = $('#result'); r.textContent = '';
    const box = document.createElement('div'); box.className = 'res'; r.append(box);
    const c = counts();
    const n = c.reduce((a, b) => a + b, 0);
    const w = st.Wg + st.Wb + st.Wc;
    const desc = `生存 ${n} 人（狼 ${w}${st.X ? '・狂人1' : ''}）・${ph === 'D' ? '昼' : '夜'}`;
    const say = (html, cls) => { box.innerHTML = `<div class="who">${desc}</div><p class="${cls || ''}">${html}</p>`; };
    if (w === 0) return say('狼が全員いないので、<b>村の勝ち</b>です。');
    if (2 * w >= n) return say('狼が生存者の半分以上なので、<b>狼の勝ち</b>です。');
    if (n < 3 || n > 9) return say('生存3〜9人の局面だけを計算しています。', 'err');
    const k = c.join('');
    const e = D.states[k];
    if (!e) return say('この組み合わせは計算していません（ありえない組み合わせの可能性があります）。', 'err');
    const [v, opts] = e[ph];
    let html = `<div class="who">${desc}</div><div><span class="big">${pct(v)}</span>${String(v[1]).length <= 12 ? `<span class="fr">(${frs(v)})</span>` : `<details class="frd"><summary>厳密な値（分数）</summary><code>${frs(v)}</code></details>`}</div><div class="who">村勝率（村・人外とも最善を尽くしたとき）</div>`;
    const keys = Object.keys(opts);
    if (ph === 'D') {
      html += `<p class="sm">${who(c)}</p>`;
      const free = who(c).startsWith('指定役なし');
      if (free) html += '<p class="muted sm">指定役がいないので、確定黒・狩人CO者2人がいればその人を全員一致で吊り、いなければグレーから多数決（狼は身内に投票せず、ほかの人はランダムに投票）で吊ります。上の村勝率はその結果です。</p>';
      if (keys.length && !free) {
        const best = Math.max(...keys.map((s) => opts[s][0] / opts[s][1]));
        html += '<div class="tbl"><table class="gt"><thead><tr><th>吊る区分（区分の中ではランダム）</th><th>吊ったあとの村勝率</th><th></th></tr></thead><tbody>' +
          keys.map((s) => `<tr><td>${ST[s]}</td><td class="n">${pct(opts[s])}${frh(opts[s])}</td><td>${Math.abs(opts[s][0] / opts[s][1] - best) < 1e-12 ? '<span class="lbl good">村の最善</span>' : ''}</td></tr>`).join('') +
          '</tbody></table></div><p class="muted sm">指定役は「村の最善」の区分を吊ります。</p>';
      }
    } else if (keys.length) {
      const worst = Math.min(...keys.map((s) => opts[s][0] / opts[s][1]));
      html += '<div class="tbl"><table class="gt"><thead><tr><th>噛む区分（人間の中からランダム）</th><th>そのときの村勝率</th><th></th></tr></thead><tbody>' +
        keys.map((s) => `<tr><td>${ST[s]}</td><td class="n">${pct(opts[s])}${frh(opts[s])}</td><td>${Math.abs(opts[s][0] / opts[s][1] - worst) < 1e-12 ? '<span class="lbl bad">狼の最善</span>' : ''}</td></tr>`).join('') +
        '</tbody></table></div>';
    }
    box.innerHTML = html;
  }
  function draw() { form(); result(); try { history.replaceState(null, '', '#' + ph + '-' + [st.Vg, st.Vw, st.H || '0', st.X || '0', st.Wg, st.Wb, st.Wc, st.S, st.M].join('')); } catch (e) {} }
  function load(h) {
    const m = (h || '').match(/^#([DN])-(\d)(\d)([0gwHc])([0gw])(\d)(\d)(\d)(\d)(\d)$/);
    if (!m) return;
    ph = m[1]; st.Vg = +m[2]; st.Vw = +m[3]; st.H = m[4] === '0' ? '' : m[4]; st.X = m[5] === '0' ? '' : m[5];
    st.Wg = +m[6]; st.Wb = +m[7]; st.Wc = +m[8]; st.S = +m[9]; st.M = +m[10];
  }
  function grayTable() {
    const rows = [];
    for (let n = 3; n <= 9; n++) for (let w = 1; w <= 2; w++) for (const h of [1, 0]) for (const x of [0, 1]) {
      const v = n - w - h - x; if (v < 0 || v > 4 || 2 * w >= n) continue;
      const c = D.pairs.map(([r, s]) => (r === 'V' && s === 'g' ? v : r === 'H' && s === 'g' ? h : r === 'X' && s === 'g' ? x : r === 'W' && s === 'g' ? w : 0));
      const e = D.states[c.join('')]; if (!e) continue;
      rows.push({ n, w, h, x, v, e });
    }
    const t = document.createElement('table'); t.className = 'gt';
    t.innerHTML = '<thead><tr><th>生存</th><th>内訳</th><th>昼</th><th>夜</th></tr></thead>';
    const tb = document.createElement('tbody');
    for (const r of rows) {
      const tr = document.createElement('tr');
      const name = [r.v ? `村${r.v}` : '', r.h ? '狩' : '', r.x ? '狂' : '', `狼${r.w}`].filter(Boolean).join('・');
      tr.innerHTML = `<td class="n">${r.n}</td><td class="nw">${name}</td>`;
      for (const p of ['D', 'N']) {
        const td = document.createElement('td'); td.className = 'n c'; td.innerHTML = `${pct(r.e[p][0])}${frh(r.e[p][0])}`;
        td.onclick = () => { Object.assign(st, { Vg: r.v, Vw: 0, H: r.h ? 'g' : '', X: r.x ? 'g' : '', Wg: r.w, Wb: 0, Wc: 0, S: 0, M: 0 }); ph = p; draw(); $('#calc').scrollIntoView(); };
        tr.append(td);
      }
      tb.append(tr);
    }
    t.append(tb); $('#graytable').append(t);
  }
  document.querySelectorAll('.sg').forEach((b) => b.addEventListener('click', () => { ph = b.dataset.ph; draw(); }));
  fetch('data/states.json').then((r) => r.json()).then((d) => {
    D = d; load(location.hash);
    const pr = $('#presets');
    for (const [name, s, p] of PRE) {
      const b = document.createElement('button'); b.type = 'button'; b.className = 'btn'; b.textContent = name; b.style.margin = '0 6px 6px 0';
      b.onclick = () => { Object.assign(st, s); ph = p; draw(); };
      pr.append(b);
    }
    draw(); grayTable();
  }).catch((e) => { $('#result').textContent = 'データを読み込めませんでした：' + e.message; });
})();
