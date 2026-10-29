// 10a狩 盤面別勝率：data/b<人数>.json を読み、左に盤面の一覧、右に選んだ盤面（#b5-02 のような URL）を出す
(function () {
  const $ = (s) => document.querySelector(s);
  const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  const val = (s) => { const [a, b] = String(s).split('/'); return b ? a / b : +a; };
  const pct = (s) => (val(s) * 100).toFixed(1) + '%';
  const tex = (t, plain) => (window.katex ? katex.renderToString(t, { throwOnError: false }) : esc(plain || t));
  const fx = (s) => { const [a, b] = String(s).split('/'); return b ? `\\tfrac{${a}}{${b}}` : a; };
  const mul = (x, y) => {
    const [a, b = '1'] = String(x).split('/'), [c, d = '1'] = String(y).split('/');
    let n = BigInt(a) * BigInt(c), m = BigInt(b) * BigInt(d);
    const g0 = (p, q) => (q === 0n ? p : g0(q, p % q)); const g = g0(n < 0n ? -n : n, m);
    if (g > 1n) { n /= g; m /= g; }
    return m === 1n ? String(n) : `${n}/${m}`;
  };
  const TREE = 'https://leonmfvo.github.io/werewolf-tree-10a/tree.html?t=';
  const DAYS = [9, 8, 7, 6, 5, 4, 3];
  const D = {}, BY = {};
  const LEGEND = '<div class="legend"><b>記号</b>　占a・占b・占c＝占いCO者、霊・霊a・霊b＝霊能CO者、白a＝占aの○、白ab＝占aと占bの○、黒a＝占aの●、確白＝人間確定（GJの翌朝にCOした狩人と護衛先）、狩＝狩人CO者（対抗あり）、灰＝グレー。'
    + '◎＝真置きしている占い師（の結果）、✕＝破綻した占い師（の結果）。w＝狼、k＝狂人（1w1k生存＝狼1人と狂人が生きている）。（狩生存）＝灰に狩人が潜伏、（狩CO済み）＝狩人はCO済み。内訳は 真＝本物・狂＝狂人・狼＝狼。</div>';
  const cnt = (b, p) => b.lab.split(',').filter((x) => x.startsWith(p)).length;
  const order = (a, b) => {
    for (const p of ['占', '霊', '狩', '灰']) { const d = cnt(b, p) - cnt(a, p); if (d) return d; }
    return a.lab < b.lab ? -1 : a.lab > b.lab ? 1 : (a.note < b.note ? -1 : 1);
  };

  function side(cur) {
    let h = '<div class="mb"><div class="mh">メニュー</div><a href="#">トップページ</a><a href="#rules">前提</a><a href="https://leonmfvo.github.io/werewolf-tree-10a/">分岐サイト</a><a href="../index.html">終盤表</a></div>';
    for (const n of DAYS) {
      if (!D[n]) continue;
      h += `<details class="mb"${cur && cur.n === n ? ' open' : ''}><summary class="mh">${n}人日（${D[n].length}）</summary><ul>`;
      for (const b of D[n]) h += `<li><a href="#${b.id}"${cur && cur.id === b.id ? ' class="cur"' : ''}>${esc(b.lab)}${b.note ? `<span>${esc(b.note)}</span>` : ''}</a></li>`;
      h += '</ul></details>';
    }
    $('#side').innerHTML = h;
  }

  const avg = (b) => { let s = 0, k = 0; for (const g of b.groups) for (const o of g.opts) { s += val(o.v); k++; } return k ? s / k : 0; };
  function top() {
    let h = '<h1 class="pt">10a狩 盤面別勝率</h1><p>分岐サイトに出てくる昼の盤面のうち、出やすいものを人数ごとに並べています。盤面を開くと、生存状況（1w1k生存・（狩生存）など）と内訳ごとの村勝率と、次の昼にどの盤面へ帰着するかが出ます。</p>' + LEGEND;
    for (const n of DAYS) {
      if (!D[n]) continue;
      h += `<h2>${n}人日（${D[n].length}盤面）</h2><ul class="blist">`;
      for (const b of D[n]) h += `<li><a href="#${b.id}">${esc(b.lab)}${b.note ? `<span class="sm">（${esc(b.note)}）</span>` : ''}</a><span class="v">${(avg(b) * 100).toFixed(1)}%</span></li>`;
      h += '</ul>';
    }
    h += `<p class="sm">右の数字は、その盤面の生存状況・内訳の村勝率を単純に平均したもの（目安）。</p>
<h2 id="rules">前提</h2><ul>
<li>規則と計算は<a href="https://leonmfvo.github.io/werewolf-tree-10a/">分岐サイト</a>と同じエンジン（吊りは指定役か自由投票、狼は見え方の区分で噛む、狂人は狼と示し合わせる、GJの朝は狩人がCOするかを村が選ぶ、など）。村の進行は、分岐サイトでその内訳に使っている進行。</li>
<li>条件（内訳・狼の位置・狂人の生死・狩人が灰に潜伏／CO済み／死亡）は、狼も知っているものとして解いている。狩人と狂人が灰の誰かは、狼には分からない。</li>
<li>帰着先：その進行と人外の最善の手で、次の昼にどの盤面になるか。噛まれたのが狩人かどうかなど、狼にも村にも分からないことは「灰に狩80%」のように確率で書く。村勝率は帰着先の村勝率の重みつき和。</li>
<li>載せている盤面：分岐サイトの全分岐ツリーに出てくる昼の盤面のうち、出やすい順に各人数40個まで。ツリーがない内訳（3-0・3-1の一部・4-0 など）から来る盤面は入っていない。1つの盤面には出やすい内訳・狼の位置を6つまで載せている。</li>
</ul>`;
    return h;
  }

  function page(n, b) {
    const sits = [];
    for (const g of b.groups) for (const o of g.opts) if (!sits.includes(o.sit)) sits.push(o.sit);
    let h = `<h1 class="pt">${esc(b.lab)}<span class="day">${n}人日</span></h1>`;
    if (b.note) h += `<p class="cond">${esc(b.note)}</p>`;
    h += LEGEND;
    // まとめ（内訳 × 生存状況）
    h += '<h2>まとめ</h2><div class="tbl"><table class="cmp"><thead><tr><th>内訳</th>' + sits.map((s, i) => `<th><a href="#${b.id}-s${i + 1}">${esc(s)}</a></th>`).join('') + '</tr></thead><tbody>';
    for (const g of b.groups) {
      h += `<tr><td>${esc(g.name)}</td>` + sits.map((s) => { const o = g.opts.find((x) => x.sit === s); return `<td class="n">${o ? `${tex(fx(o.v), o.v)} <span class="sm">${pct(o.v)}</span>` : '—'}</td>`; }).join('') + '</tr>';
    }
    h += '</tbody></table></div>';
    h += '<nav class="toc"><b>目次</b><ol>' + sits.map((s, i) => `<li><a href="#${b.id}-s${i + 1}">${esc(s)}</a></li>`).join('') + '</ol></nav>';
    sits.forEach((s, si) => {
      h += `<h2 id="s${si + 1}">${esc(s)}</h2>`;
      for (const g of b.groups) {
        const o = g.opts.find((x) => x.sit === s);
        if (!o) continue;
        h += `<h3>${esc(g.name)} → ${pct(o.v)}${String(o.v).includes('/') && o.v.length <= 11 ? `（${esc(o.v)}）` : ''}</h3>`;
        h += `<p class="sm">進行：${esc(g.policy)}（内訳 ${esc(g.key)}）　<a href="${TREE}${esc(g.tree)}">分岐ツリー</a></p>`;
        for (const c of o.choices) h += `<p class="sm">${c.who}の選択：${c.alts.map(([l, v, best]) => (best ? `<b>${esc(l)}→${pct(v)}</b>` : `${esc(l)}→${pct(v)}`)).join('、')}</p>`;
        for (const pt of o.pats) {
          const head = pt.end ? (val(pt.v) === 1 ? '村勝ちになるパターン' : val(pt.v) === 0 ? '狼勝ちになるパターン' : `${pct(pt.v)}で決着するパターン`) : `${pct(pt.v)}の盤面に進むパターン`;
          h += `<p class="sub">${head}（${pct(pt.tp)}）</p><ol class="terms">`;
          for (const l of pt.lines) {
            let t = '';
            if (l.tgt) {
              const name = `${l.tgt.n}人日 ${esc(l.tgt.lab)}${l.tgt.note ? `（${esc(l.tgt.note)}）` : ''}［${esc(l.tgt.cond)}］`;
              t = ' → ' + (l.tgt.href ? `<a href="#${l.tgt.href}">${name}</a>` : name);
            }
            h += `<li><span class="tw">${esc(l.labs)}${t}</span>：<span class="tm">${tex(fx(l.p))}</span></li>`;
          }
          if (pt.more) h += `<li class="sm">ほか ${pt.more} 通り</li>`;
          h += '</ol>';
        }
        const terms = o.pats.filter((p) => val(p.v) > 0);
        h += `<p class="total">${tex('P = ' + (terms.length ? terms.map((p) => `${fx(p.tp)}\\times${fx(p.v)}`).join('+') : '0') + ' = ' + fx(o.v))}</p>`;
      }
    });
    return h;
  }

  function route() {
    const m = location.hash.match(/^#(b(\d+)-\d+)(?:-(s\d+))?$/);
    if (m && BY[m[1]]) {
      const b = BY[m[1]], n = +m[2];
      side({ n, id: b.id }); $('#page').innerHTML = page(n, b);
      const el = m[3] && document.getElementById(m[3]); if (el) el.scrollIntoView(); else window.scrollTo(0, 0);
      document.title = `${n}人日 ${b.lab} - 10a狩 盤面別勝率`; return;
    }
    side(null); $('#page').innerHTML = top(); document.title = '10a狩 盤面別勝率';
    if (location.hash === '#rules') setTimeout(() => { const el = document.getElementById('rules'); if (el) el.scrollIntoView(); }, 0);
  }
  $('#totop').addEventListener('click', (e) => { e.preventDefault(); window.scrollTo(0, 0); });
  window.addEventListener('hashchange', route);
  Promise.all(DAYS.map((n) => fetch(`data/b${n}.json`).then((r) => (r.ok ? r.json() : null)).then((d) => {
    if (!d) return; d.sort(order); D[n] = d; for (const b of d) BY[b.id] = b;
  }).catch(() => {}))).then(route);
})();
