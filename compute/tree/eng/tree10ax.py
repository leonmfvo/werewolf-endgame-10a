# 10a狩人用（tree10 から作成：狂人の毎晩の●○を人外の選択に加え、猫又の表示を除く）。
# engine7 の局面からラベル付きの全分岐ツリー（DAG）を書き出す。値は engine7.V と照合する。
# ラベルには狼に見える出来事だけを書く（狩人・猫又の位置、占いCO者が本物か狂人かは書かない）。
import json, sys
import engine10x as E   # tree10ax：tree10a を分数（厳密な有理数）で作る版
from fractions import Fraction as F

def cname(r):
    fl = 0
    if E.POL.get('hco') or E.POL.get('hcoopt'): r, fl = r[:-1], r[-1]   # 最後の要素は目印（1 人間確定 / 2 狩人CO者）
    tail = {0: '', 1: '（人間確定）', 2: '（狩人CO者）'}[fl]
    if not any(r): return ('灰' if not fl else '') + tail if fl != 1 else '人間確定'
    marks = {1: '○', 2: '●'}
    if len(r) == 1: return f'占いの{marks[r[0]]}' + tail
    return '・'.join(f'占い{i + 1}の{marks[x]}' for i, x in enumerate(r) if x) + tail

def who_desc(who, slots, meds):
    if who[0] == 'c':
        return f"{cname(who[1])}の{'狼' if who[2] else '人間'}"
    if who[0] == 's':
        return '占いCO者' + ('' if len(slots) == 1 else str(who[1] + 1)) + ('（狼）' if slots[who[1]][0] else '')
    return '霊能CO者' + ('' if len(meds) == 1 else str(who[1] + 1)) + ('（狼）' if meds[who[1]][0] else '')

def agg_labeled(items, ph):
    """items: [(p, vis, k, label)] -> [(prob, label, state)]"""
    acc = {}
    for p, vis, k, lab in items:
        if p <= 0: continue
        d = acc.setdefault((vis, lab), {})
        d[k] = d.get(k, 0) + p
    out = []
    for (vis, lab), d in acc.items():
        tot = sum(d.values())
        sl, md, T, TM, cats, last, nt = vis
        out.append((tot, lab, (ph, sl, md, T, TM, cats, last, nt, E.norm_bel(d))))
    out.sort(key=lambda x: -x[0])
    return out

# ---------------------------------------------------------------- 夜（ラベル付き）
def night_outcomes_l(s, bite, fk, rep, gjmode=None):
    _, slots, meds, T, TM, cats, last, nt, bel = s
    res = []
    n_alive = E.counts(slots, meds, cats)[1]
    for k, pk in bel:
        wd0 = E.mk_world(s, k)
        worlds = []
        if bite is None: worlds = [(pk, wd0, None)]
        elif bite[0] == 'c':
            for q, kind in E.take_human(wd0, bite[1]): worlds.append((pk * q, wd0, ('c', bite[1], False, kind)))
        else: worlds = [(pk, wd0, bite)]
        nxt = []
        for p, wd, who in worlds:
            if who is None:
                nxt.append((p, wd.cp(), [], [])); continue
            hunter = wd.H is not None and not (who[0] == 'c' and who[3] == 'H')
            gj = F(0)
            if hunter:
                gt = E.guard_target(slots, meds, T, TM)
                if isinstance(gt, list): gj = F(1, len(gt)) if who in gt else F(0)
                elif gt is not None and gt[0] == 'mix': gj = F(gt[1]) * (F(1) if who == gt[2] else F(0)) + (1 - F(gt[1])) * F(1, max(n_alive - 1, 1))
                elif gt is not None: gj = F(1) if who == gt else F(0)
                else: gj = F(1, max(n_alive - 1, 1))
            if gj > 0 and gjmode != 'skip':
                wg = wd.cp(); ev0 = ['噛み失敗（GJ）']
                if gjmode == 'co':
                    E.hunter_co(wg, who, force=True)
                    ev0.append('狩人がCOし、噛まれた人を護衛したと申告' + ('（狼が対抗の狩人CO）' if E._CC[0] is not None else ''))
                elif gjmode == 'no': ev0.append('狩人は潜伏を続ける')
                nxt.append((p * gj, wg, [], ev0))
            if gj < 1 and gjmode not in ('no', 'co'):
                w2 = wd.cp()
                iscat = E.kill(w2, who)
                d0 = who_desc(who if who[0] != 'c' else ('c', who[1], False), slots, meds)
                if iscat:
                    wl = E.wolves_of(w2); tot = sum(x for x, _ in wl)
                    for ww, wv in wl:
                        w3 = w2.cp(); E.kill(w3, wv)
                        nxt.append((p * (1 - gj) * ww / tot, w3, [who, wv], [f'噛んだ{d0}が猫又 → 狼（{who_desc(wv, slots, meds)}）が道連れ']))
                else:
                    nxt.append((p * (1 - gj), w2, [who], [f'{d0}が噛まれて死亡']))
        for p, wd, deaths, ev in nxt:
            ws = [(p, wd, list(ev))]
            for spec in fk:
                if spec is None: continue
                i, r, isw, col = spec
                if not wd.sl[i][1]: continue
                nw = []
                for q, w1, e1 in ws:
                    e = w1.cd.get(r)
                    if e is None or (isw and e[0] == 0) or (not isw and e[1] == 0):
                        nw.append((q, w1, e1)); continue
                    lab = f"占い{i + 1}（狼）の結果：{cname(r)}の{'狼' if isw else '人間'}に{'○' if col == 1 else '●'}"
                    if isw:
                        w2 = w1.cp(); E.move(w2, r, True, None, i, col); nw.append((q, w2, e1 + [lab]))
                    else:
                        for q2, kind in E.take_human(w1, r):
                            w2 = w1.cp(); E.move(w2, r, False, kind, i, col); nw.append((q * q2, w2, e1 + [lab]))
                ws = nw
            # 占い師の番号順に処理する（本物を先に書くと、ラベルの順番から本物が分かってしまう）
            for who_slot, is_real in sorted(((k[0], True), (k[1], False)), key=lambda x: x[0] if isinstance(x[0], int) and x[0] >= 0 else 99):
                if not isinstance(who_slot, int) or who_slot < 0: continue
                if not slots[who_slot][1] or not wd.sl[who_slot][1]: continue
                i = who_slot
                pre = '占い' if len(slots) == 1 else f'占い{i + 1}'
                nw = []
                for q, w1, e1 in ws:
                    noop = sum(1 for d in w1.dead if d[i] == 0)
                    its = []
                    for r, (w, h) in w1.cd.items():
                        if r[i]: continue
                        if w and not (is_real and E.POL.get('w0') and nt == 0): its.append((w, ('c', r, True, None)))
                        if h:
                            for q2, kind in E.take_human(w1, r): its.append((h * q2, ('c', r, False, kind)))
                    tot = sum(x for x, _ in its) + noop
                    if tot == 0: nw.append((q, w1, e1)); continue
                    if noop: nw.append((q * noop / tot, w1, e1 + [f'{pre}の結果：噛まれた人を占っていた']))
                    for x, who in its:
                        _, r, isw, kind = who
                        col = (2 if isw else 1) if is_real else E.mad_color(nt)
                        w2 = w1.cp(); E.move(w2, r, isw, kind, i, col)
                        nw.append((q * x / tot, w2, e1 + [f"{pre}の結果：{cname(r)}の{'狼' if isw else '人間'}に{'○' if col == 1 else '●'}"]))
                ws = nw
            for q, w1, e1 in ws:
                sl_before = [list(x) for x in w1.sl]; md_before = [list(x) for x in w1.md]
                rp = None
                if last is not None and TM >= 0 and w1.md[TM][1]: rp = ('rep', E.medium_report(w1.md, TM, T, last, rep, w1.m))
                c2 = E.reports2(w1.md, T, last, rep, w1.m)
                if c2 and any(c2): rp = ('rep2', c2)
                Tn, TMn = E.morning_update(w1, T, TM, last, rep, deaths)
                e2 = list(e1)
                if c2 and any(c2):
                    e2.insert(0, '・'.join(f"霊能{j + 1}の結果：{'○' if c == 1 else '●'}" for j, c in enumerate(c2) if c))
                elif last is not None and TM >= 0 and w1.md[TM][1]:
                    col = E.medium_report(w1.md, TM, T, last, rep, w1.m)
                    e2.insert(0, f"霊能の結果：前日に吊った人は{'○' if col == 1 else '●'}")
                for i in range(len(w1.sl)):
                    if w1.sl[i][2] and not sl_before[i][2]: e2.append(f"{'占いCO者' if len(slots) == 1 else f'占い{i + 1}'}が破綻（霊能結果と矛盾）")
                for j in range(len(w1.md)):
                    if w1.md[j][2] and not md_before[j][2]:
                        e2.append(f"霊能{j + 1}を偽とみなす（結果が割れたので{'○' if E.POL['mr'] == 1 else '●'}を出した方を信じる）" if c2 else '霊能CO者が破綻（信用占い師と矛盾）')
                if Tn != T and Tn >= 0:
                    if last is not None and last[0] == 's' and Tn == last[1]: e2.append(f'吊った占い{Tn + 1}を真とみなす（霊結果○）')
                    else: e2.append(f'噛まれた占い{Tn + 1}を真とみなす')
                w1.dead = []
                res.append((q, E.visible(w1, Tn, TMn, rp, nt + 1), E.kof(w1), '／'.join(e2) or '何も起きない'))
    return agg_labeled(res, 'D')

def bite_label(b, slots, meds):
    if b is None: return '初日犠牲者を噛む'
    if b[0] == 'c': return f'{cname(b[1])}の人間を噛む'
    return who_desc(b, slots, meds) + 'を噛む'

# ---------------------------------------------------------------- 吊り（ラベル付き）
def hang_outcomes_l(s, picks, how):
    ph, slots, meds, T, TM, cats, last, nt, bel = s
    tot = sum(w for w, _ in picks)
    res = []
    for k, pk in bel:
        wd0 = E.mk_world(s, k)
        for w, tg in picks:
            p0 = pk * w / tot
            if tg[0] == 'c':
                r, isw = tg[1], tg[2]
                if isw: whos = [(F(1), ('c', r, True, None))]
                else: whos = [(q, ('c', r, False, kind)) for q, kind in E.take_human(wd0, r)]
            else: whos = [(F(1), tg)]
            for q, who in whos:
                w1 = wd0.cp()
                iscat = E.kill(w1, who)
                if who[0] == 'c': col = 2 if who[2] else 1; lst = ('c', who[1], col)
                elif who[0] == 's': col = 2 if slots[who[1]][0] else 1; lst = ('s', who[1], col)
                else: col = 2 if meds[who[1]][0] else 1; lst = ('m', who[1], col)
                base = f"{how}：{who_desc(who if who[0] != 'c' else ('c', who[1], who[2]), slots, meds)}を吊る"
                outs = [(F(1), w1, base)]
                if iscat and E.term(w1.sl, w1.md, E.cats_t(w1.cd)) is None:
                    ev = E.everyone(w1); t2 = sum(x for x, _ in ev)
                    outs = []
                    for x, v in ev:
                        w2 = w1.cp(); E.kill(w2, v)
                        vd = who_desc(v if v[0] != 'c' else ('c', v[1], v[2]), slots, meds)
                        outs.append((F(x, t2), w2, f'{base}（猫又だった）→ 道連れ：{vd}'))
                elif iscat:
                    outs = [(F(1), w1, f'{base}（猫又だった）')]
                for q2, w2, lab in outs:
                    w2.dead = []
                    res.append((p0 * q * q2, E.visible(w2, T, TM, lst, nt), E.kof(w2), lab))
    return agg_labeled(res, 'N')

def night_syms(s):
    """夜の、実戦ではランダムにならない場面の記号と重み（その世界の確率）。
    S：本物の占い師の占い先（候補 g 人）／G：狩人のランダムな護衛（候補 g 人）。生存 n"""
    _, slots, meds, T, TM, cats, last, nt, bel = s
    n = E.counts(slots, meds, cats)[1]
    out = {}
    gt = E.guard_target(slots, meds, T, TM)
    for k, p in bel:
        i = k[0]
        if isinstance(i, int) and i >= 0 and slots[i][1]:
            g = sum(w + h for r, w, h in cats if not r[i])
            if g >= 2: out[('S', g, n)] = out.get(('S', g, n), 0) + p
        if k[2] is not None:   # 狩人が生きている
            if gt is None: key, wt = ('G', n - 1, n), p
            elif isinstance(gt, list): key, wt = ('G', len(gt), n), p if len(gt) >= 2 else 0
            elif gt[0] == 'mix': key, wt = ('G', n - 1, n), p * (1 - F(gt[1]))
            else: key, wt = None, 0
            if key and wt: out[key] = out.get(key, 0) + wt
    return sorted(out.items())

PRUNE = [False]   # True なら、人外・村が選ぶ場面で選んだ手だけを作る（大きな内訳の要約用。ツリーとしては載せない）

def engine_night_value(s, bite, fk, rep, mc):
    """夜の1つの手の値（エンジンと同じ式）"""
    E._MC[0] = mc if mc else 1
    if E.POL.get('hcoopt') and bite is not None:
        o_skip = E.night_outcomes(s, bite, fk, rep, 'skip'); o_no = E.night_outcomes(s, bite, fk, rep, 'no'); o_co = []
        if E.gj_possible(s, bite):
            for cc in E.counter_options(s, bite, force=True):
                E._CC[0] = cc; o_co.append(E.night_outcomes(s, bite, fk, rep, 'co'))
        E._CC[0] = None
        v = sum(p * E.V(c) for p, c in o_skip); vno = sum(p * E.V(c) for p, c in o_no)
        vco = min(sum(p * E.V(c) for p, c in o) for o in o_co) if o_co else vno
        return v + max(vno, vco)
    return sum(p * E.V(c) for p, c in E.night_outcomes(s, bite, fk, rep))

# ---------------------------------------------------------------- DAG
class Tree:
    def __init__(self):
        self.nodes = []; self.ids = {}; self.bad = 0; self.checked = 0

    def new(self, nd):
        self.nodes.append(nd); return len(self.nodes) - 1

    def summary(self, s):
        ph, slots, meds, T, TM, cats, last, nt, bel = s
        w, n = E.counts(slots, meds, cats)
        g = sum(c[1] + c[2] for c in cats if not any(c[0]))
        gw = sum(c[1] for c in cats if not any(c[0]))
        parts = [f'生存{n}（狼{w}）']
        for r, cw, ch in cats:
            parts.append(f'{cname(r)} {cw + ch}（狼{cw}）')
        for i, x in enumerate(slots):
            nm = '占いCO者' if len(slots) == 1 else f'占い{i + 1}'
            parts.append(nm + ('：死亡' if not x[1] else '') + ('・破綻' if x[2] else '') + ('・信用' if i == T else ''))
        for j, x in enumerate(meds):
            nm = '霊能CO者' if len(meds) == 1 else f'霊能{j + 1}'
            parts.append(nm + ('：死亡' if not x[1] else '') + ('・破綻' if x[2] else ''))
        pr = sum(p for k, p in bel if k[0] >= 0 and slots[k[0]][1])
        pm = sum(p for k, p in bel if E.mad_alive(k[1], slots, meds))
        ph_ = sum(p for k, p in bel if k[2] is not None)
        hid = f'狼から見た確率：本物の占い師が生存 {pr * 100:.0f}%・狂人生存 {pm * 100:.0f}%・狩人生存 {ph_ * 100:.0f}%'
        return '／'.join(parts), hid

    def state(self, s):
        if s in self.ids: return self.ids[s]
        ph, slots, meds, T, TM, cats, last, nt, bel = s
        v = E.V(s)
        t = E.term(slots, meds, cats)
        pub, hid = self.summary(s)
        if t is not None:
            nid = self.new(dict(k='end', v=t, ph='end', d=nt, pub=pub, hid=hid, t='村の勝ち' if t == 1 else '狼の勝ち', q=E.tag_mass(bel)))
            self.ids[s] = nid; return nid
        nid = self.new(None); self.ids[s] = nid
        if ph == 'D':
            nd = self.day(s)
        else:
            nd = self.night(s)
            sy = night_syms(s)
            if sy: nd['syms'] = sy
        nd.update(v=v, d=nt, pub=pub, hid=hid, ph='day' if ph == 'D' else 'night', q=E.tag_mass(bel))
        self.nodes[nid] = nd
        self.check(nd)
        return nid

    def check(self, nd):
        if nd['k'] == 'chance': got = sum(c[0] * self.nodes[c[2]]['v'] for c in nd['c'])
        elif nd['k'] == 'wolf': got = min(self.nodes[c[2]]['v'] for c in nd['c'])
        elif nd['k'] == 'vil': got = max(self.nodes[c[2]]['v'] for c in nd['c'])
        else: got = self.nodes[nd['c'][0][2]]['v']
        self.checked += 1
        if abs(got - nd['v']) > 1e-9:
            self.bad += 1
            if self.bad < 5: print('MISMATCH', nd['k'], got, nd['v'], file=sys.stderr)

    def sub(self, k, ph, label, children, v, q=None):
        nd = dict(k=k, c=children, ph=ph, v=v, t=label, q=q or {})
        return self.new(nd)

    def night(self, s):
        bites, fakes, reps = E.night_options(s)
        _, slots, meds, *_ = s
        import itertools
        opts = []
        allopts = [(bite, fk, rep, mc) for bite in bites for fk in (itertools.product(*fakes) if fakes else [()])
                   for rep, mc in itertools.product(reps, (1, 2) if E.POL['mad'] == 'A' and E.mad_may_divine(s) and not (E.POL.get('w0') and s[7] == 0) else (None,))]
        n_all = len(allopts)
        if PRUNE[0] and len(allopts) > 1:   # 要約用：最善の手だけを作る（ほかの手の値はエンジンで求める）
            ev = [engine_night_value(s, *o) for o in allopts]
            mv = min(ev); allopts = [allopts[next(i for i, x in enumerate(ev) if x <= mv + E.TIE)]]
        for bite, fk, rep, mc in allopts:
                    if mc: E._MC[0] = mc
                    if E.POL.get('hcoopt') and bite is not None:
                        ch = self.gj_children(s, bite, fk, rep, E._MC[0])
                    else:
                        outs = night_outcomes_l(s, bite, fk, rep)
                        ch = [[p, lab, self.state(c), 'chance'] for p, lab, c in outs]
                    v = sum(p * self.nodes[c[2]]['v'] for p, _, c, _ in [(x[0], x[1], x, None) for x in ch]) if False else sum(x[0] * self.nodes[x[2]]['v'] for x in ch)
                    lab = bite_label(bite, slots, meds)
                    for spec in fk:
                        if spec is not None: lab += f"／占い{spec[0] + 1}（狼）は{cname(spec[1])}の{'狼' if spec[2] else '人間'}に{'○' if spec[3] == 1 else '●'}"
                    if rep is not None: lab += f"／偽霊能は{'○' if rep == 1 else '●'}を出す"
                    if mc: lab += f"／狂人の占い結果は{'○' if mc == 1 else '●'}"
                    node = self.sub('chance', 'morning', '夜が明ける', ch, v, E.tag_mass(s[8]))
                    opts.append([None, lab, node, 'wolf'])
        if len(opts) == 1 and n_all == 1:
            opts[0][3] = 'fixed'
            return dict(k='fixed', c=opts, t='夜の行動')
        mv = min(self.nodes[o[2]]['v'] for o in opts); best = next(i for i, o in enumerate(opts) if self.nodes[o[2]]['v'] <= mv + E.TIE)
        return dict(k='wolf', c=opts, best=best, t='人外の選択（夜）')

    def gj_children(self, s, bite, fk, rep, mc):
        """hcoopt：GJ でない朝はそのまま、GJ の朝は「狩人がCOする／潜伏する」を村が選ぶ（村勝率が高い方）"""
        # 先に朝の局面をすべて作る（子の局面を作る途中で _MC・_CC が書き換わるため）
        E._MC[0] = mc; o_skip = night_outcomes_l(s, bite, fk, rep, 'skip')
        E._MC[0] = mc; no = night_outcomes_l(s, bite, fk, rep, 'no')
        alive_h = E.gj_possible(s, bite)
        o_cos = []
        if alive_h:
            for cc in E.counter_options(s, bite, force=True):
                E._CC[0] = cc; E._MC[0] = mc
                o_cos.append((cc, night_outcomes_l(s, bite, fk, rep, 'co')))
            E._CC[0] = None
        ch = [[p, lab, self.state(c), 'chance'] for p, lab, c in o_skip]
        pg = sum(p for p, _, _ in no)
        if pg == 0: return ch
        if PRUNE[0]:   # 要約用：村の選択（CO／潜伏）と狼の対抗はエンジンの値で決め、選んだ枝だけを作る
            vno = sum(p * E.V(c) for p, _, c in no)
            vco = {i: sum(p * E.V(c) for p, _, c in co) for i, (cc, co) in enumerate(o_cos)}
            bi = min(vco, key=lambda i: (vco[i], i)) if vco else None
            if bi is not None and vco[bi] > vno + 1e-12:
                cc, co = o_cos[bi]
                kco = [[p / pg, lab, self.state(c), 'chance'] for p, lab, c in co]
                cn = self.sub('chance', 'morning', '狩人がCO', kco, vco[bi] / pg, E.tag_mass(s[8]))
                if len(o_cos) > 1:
                    cn = self.new(dict(k='wolf', c=[[None, '狼は対抗しない' if cc is None else f'狼（{cname(cc)}）が対抗の狩人CO', cn, 'wolf']], best=0, ph='morning', t='人外の選択（狩人COへの対抗）', v=vco[bi] / pg, q=E.tag_mass(s[8])))
                lab, dec, node = '狩人がCOして、護衛先（噛まれた人）を申告する', 'co', cn
            else:
                kno = [[p / pg, lab, self.state(c), 'chance'] for p, lab, c in no]
                lab, dec, node = '狩人は潜伏を続ける', 'no', self.sub('chance', 'morning', '狩人は潜伏を続ける', kno, vno / pg, E.tag_mass(s[8]))
            if vco:
                vnode = self.new(dict(k='vil', c=[[None, lab, node, 'village']], best=0, ph='morning', t='GJ：狩人がCOするか（村が選ぶ）', v=self.nodes[node]['v'], q=E.tag_mass(s[8])))
                self.nodes[vnode]['gjd'] = (s[7] + 2, E.counts(s[1], s[2], s[5])[1], dec)
            else: vnode = node
            ch.append([pg, '噛み失敗（GJ）', vnode, 'chance'])
            return ch
        kno = [[p / pg, lab, self.state(c), 'chance'] for p, lab, c in no]
        vno = sum(x[0] * self.nodes[x[2]]['v'] for x in kno)
        n_no = self.sub('chance', 'morning', '狩人は潜伏を続ける', kno, vno, E.tag_mass(s[8]))
        opts = [[None, '狩人は潜伏を続ける', n_no, 'village']]
        if alive_h:
            copts = []
            for cc, co in o_cos:
                kco = [[p / pg, lab, self.state(c), 'chance'] for p, lab, c in co]
                vco = sum(x[0] * self.nodes[x[2]]['v'] for x in kco)
                copts.append([None, '狼は対抗しない' if cc is None else f'狼（{cname(cc)}）が対抗の狩人CO', self.sub('chance', 'morning', '狩人がCO', kco, vco, E.tag_mass(s[8])), 'wolf'])
            if len(copts) == 1: cnode = copts[0][2]
            else:
                mv = min(self.nodes[o[2]]['v'] for o in copts); best = next(i for i, o in enumerate(copts) if self.nodes[o[2]]['v'] <= mv + E.TIE)
                cnode = self.new(dict(k='wolf', c=copts, best=best, ph='morning', t='人外の選択（狩人COへの対抗）', v=self.nodes[copts[best][2]]['v'], q=E.tag_mass(s[8])))
            opts.append([None, '狩人がCOして、護衛先（噛まれた人）を申告する', cnode, 'village'])
        vals = [self.nodes[o[2]]['v'] for o in opts]
        best = max(range(len(opts)), key=lambda i: (vals[i] - (1e-12 if i else 0), -i))
        if len(opts) == 1: vnode = n_no
        else:
            vnode = self.new(dict(k='vil', c=opts, best=best, ph='morning', t='GJ：狩人がCOするか（村が選ぶ）', v=vals[best], q=E.tag_mass(s[8])))
            # 集計用：（GJ の朝の日, 生存者数, COしたか）
            self.nodes[vnode]['gjd'] = (s[7] + 2, E.counts(s[1], s[2], s[5])[1], 'co' if best == 1 else 'no')
        ch.append([pg, '噛み失敗（GJ）', vnode, 'chance'])
        return ch

    def day(self, s):
        ph, slots, meds, T, TM, cats, last, nt, bel = s
        tc = E.trust_choices(s)
        if len(tc) == 1:
            p, t, m = tc[0]
            nid = self.after_trust((ph, slots, meds, t, m, cats, last, nt, bel))
            lab = '信用する占い師：' + ('なし' if t < 0 else ('占いCO者' if len(slots) == 1 else f'占い{t + 1}'))
            return dict(k='fixed', c=[[None, lab, nid, 'village']], t='昼')
        ch = []
        for p, t, m in tc:
            nid = self.after_trust((ph, slots, meds, t, m, cats, last, nt, bel))
            lab = '信用する占い師：' + ('なし' if t < 0 else ('占いCO者' if len(slots) == 1 else f'占い{t + 1}')) + '（ランダムに選ぶ）'
            ch.append([p, lab, nid, 'village'])
        nd = dict(k='chance', c=ch, t='信用する占い師を決める')
        # T：ランダムに真置きする場面（人間なら選び方で勝率が変わる）。候補の人数 g、生存 n
        sy = []
        n = E.counts(slots, meds, cats)[1]
        gs = len({t for p, t, m in tc}); gm = len({m for p, t, m in tc})
        if gs >= 2: sy.append((('T', gs, n), 1))
        if gm >= 2: sy.append((('T', gm, n), 1))
        if sy: nd['syms'] = sy
        return nd

    def after_trust(self, s):
        ph, slots, meds, T, TM, cats, last, nt, bel = s
        w, n = E.counts(slots, meds, cats)
        if n >= 5 and 2 * (w + 1) >= n:
            pm = sum(p for k, p in bel if E.mad_alive(k[1], slots, meds))
            if pm > 0:
                ch = []
                if 2 * (w + 1) > n:
                    yes = self.new(dict(k='end', v=F(0), ph='end', d=nt, t='狼の勝ち（PPで人外が過半数）', pub='', hid='', q=E.tag_mass(E.norm_bel({k: p for k, p in bel if E.mad_alive(k[1], slots, meds)}))))
                else:
                    d = {k: p for k, p in bel if E.mad_alive(k[1], slots, meds)}
                    h = self.hang(s[:8] + (E.norm_bel(d),))
                    qd = E.tag_mass(E.norm_bel(d))
                    lose = self.new(dict(k='end', v=F(0), ph='end', d=nt, t='狼の勝ち（PPの同票決選に負け）', pub='', hid='', q=qd))
                    yes = self.sub('chance', 'day', 'PP（同数）：決選はランダム', [[F(1, 2), '村の吊りが通る', h, 'chance'], [F(1, 2), '人外が吊りを通す', lose, 'chance']], F(1, 2) * self.nodes[h]['v'], qd)
                ch.append([pm, '狂人が生存している → 人外がPPを仕掛ける', yes, 'chance'])
                if pm < 1:
                    d = {k: p for k, p in bel if not (E.mad_alive(k[1], slots, meds))}
                    h = self.hang(s[:8] + (E.norm_bel(d),))
                    ch.append([1 - pm, '狂人は死亡済み → PPなし', h, 'chance'])
                v = sum(c[0] * self.nodes[c[2]]['v'] for c in ch)
                return self.sub('chance', 'day', 'PPの可能性', ch, v, E.tag_mass(bel))
        return self.hang(s)

    def hang(self, s):
        ph, slots, meds, T, TM, cats, last, nt, bel = s
        cand = E.hang_candidates(s)
        cd = {r: (w, h) for r, w, h in cats}
        units = []
        for c in cand:
            if c[0] == 'c':
                w, h = cd[c[1]]
                if w: units.append((w, ('c', c[1], True)))
                if h: units.append((h, ('c', c[1], False)))
            else: units.append((1, c))
        mix = E.designator_mix(s)
        if len(mix) > 1:   # cw：確定白の中から指定役を選ぶ（狼が混ざっている可能性がある）
            ch = [[q, '確定白の指定役が狼' if dd == 'w' else '確定白の指定役が人間', self.hang_d(s, cand, units, dd), 'chance'] for q, dd in mix]
            v = sum(c[0] * self.nodes[c[2]]['v'] for c in ch)
            return self.sub('chance', 'day', '確定白から指定役を選ぶ', ch, v, E.tag_mass(bel))
        return self.hang_d(s, cand, units, mix[0][1])

    def hang_d(self, s, cand, units, d):
        ph, slots, meds, T, TM, cats, last, nt, bel = s
        how = {'h': '指定', 'w': '指定（狼の指定役）', None: '投票'}[d]
        # 日ごとの進行の要約用：（吊り方, 吊る対象の種類）
        kinds = []
        for c in cand:
            kk = {'c': '灰', 's': '占いCO', 'm': '霊能CO'}[c[0]]
            if c[0] == 'c' and 2 in c[1]: kk = '●'
            elif c[0] == 'c' and 1 in c[1]: kk = '○'
            if kk not in kinds: kinds.append(kk)
        des = '霊' if E.POL['ds'] == 'medium' else '占い'
        if d in ('h', 'w'):   # 狼が指定役でも、村から見れば同じ指定
            Tv = T >= 0 and slots[T][1]; Mv = TM >= 0 and meds[TM][1]
            des = ('占い' if Tv and (E.POL['ds'] != 'medium' or not Mv) else '霊')
            if not Tv and not Mv: des = '白'   # cw：確定白が指定役
        act = (('自由投票' if d is None else des + '指定') if not E.POL.get('lot') or d is not None else '乱数', '・'.join(kinds))
        lot = d is None and E.POL.get('lot')
        if lot: how = '乱数'
        if d == 'w':
            hum = [u for u in units if not ((u[1][0] == 'c' and u[1][2]) or (u[1][0] == 's' and slots[u[1][1]][0]) or (u[1][0] == 'm' and meds[u[1][1]][0]))]
            opts = []
            cands = hum or units
            if PRUNE[0] and len(cands) > 1:
                ev = [sum(p * E.V(c) for p, c in E.hang_outcomes(s, [(1, u[1])])) for u in cands]
                mv = min(ev); cands = [cands[next(i for i, x in enumerate(ev) if x <= mv + E.TIE)]]
            for u in cands:
                outs = hang_outcomes_l(s, [(1, u[1])], how)
                ch = [[p, lab, self.state(c), 'chance'] for p, lab, c in outs]
                v = sum(x[0] * self.nodes[x[2]]['v'] for x in ch)
                opts.append([None, f'{who_desc(u[1] if u[1][0] != "c" else ("c", u[1][1], u[1][2]), slots, meds)}を指定', self.sub('chance', 'day', '吊り', ch, v, E.tag_mass(bel)), 'wolf'])
            mv = min(self.nodes[o[2]]['v'] for o in opts); best = next(i for i, o in enumerate(opts) if self.nodes[o[2]]['v'] <= mv + E.TIE)
            return self.new(dict(k='wolf', c=opts, best=best, ph='day', t='狼の指定役が吊り先を選ぶ', v=self.nodes[opts[best][2]]['v'], q=E.tag_mass(bel), act=act))
        outs = hang_outcomes_l(s, E.vote_units(s, units) if d is None else units, how)
        ch = [[p, lab, self.state(c), 'chance'] for p, lab, c in outs]
        v = sum(x[0] * self.nodes[x[2]]['v'] for x in ch)
        tier = '、'.join(sorted({cname(c[1]) if c[0] == 'c' else who_desc(c, slots, meds) for c in cand}))
        hum = E.bloc_humans(s, units)
        if not hum:
            nid = self.sub('chance', 'day', f'{"乱数吊り" if lot else "吊り"}（候補：{tier}）', ch, v, E.tag_mass(bel))
            # 実戦ではランダムにならない場面の記号：A 自由投票 / D 人間の指定役による指定。（候補の人数 g, 生存 n）
            g = sum(w for w, _ in units)
            if g >= 2 and not lot: self.nodes[nid]['sym'] = ('A' if d is None else 'D', g, E.counts(slots, meds, cats)[1])
            self.nodes[nid]['act'] = act
            return nid
        # 組織票
        b = E.POL['bloc']
        rnd = self.sub('chance', 'day', f'組織票が通らず、各自の投票で吊られる（候補：{tier}）', ch, v, E.tag_mass(bel))
        opts = []
        for u in hum:
            o2 = hang_outcomes_l(s, [(1, u[1])], '投票（狼の組織票）')
            c2 = [[p, lab, self.state(c), 'chance'] for p, lab, c in o2]
            v2 = sum(x[0] * self.nodes[x[2]]['v'] for x in c2)
            opts.append([None, f'{who_desc(u[1] if u[1][0] != "c" else ("c", u[1][1], u[1][2]), slots, meds)}に票を集める', self.sub('chance', 'day', '吊り', c2, v2, E.tag_mass(bel)), 'wolf'])
        mv = min(self.nodes[o[2]]['v'] for o in opts); best = next(i for i, o in enumerate(opts) if self.nodes[o[2]]['v'] <= mv + E.TIE)
        wn = self.new(dict(k='wolf', c=opts, best=best, ph='day', t='狼が組織票で吊り先を選ぶ', v=self.nodes[opts[best][2]]['v'], q=E.tag_mass(bel)))
        vb = (1 - b) * v + b * self.nodes[wn]['v']
        return self.sub('chance', 'day', '自由投票', [[1 - b, '組織票が通らない', rnd, 'chance'], [b, '狼の組織票が通る', wn, 'chance']], vb, E.tag_mass(bel))

    def tag_values(self):
        """各ノードの内訳ごとの村勝率 vt（狼の手はまとめた値で選んだもの）"""
        import sys
        sys.setrecursionlimit(100000)
        memo = {}
        def vt(i):
            if i in memo: return memo[i]
            nd = self.nodes[i]; q = nd.get('q') or {}
            if nd['k'] == 'end': r = {g: nd['v'] for g in q}
            elif nd['k'] == 'fixed': r = vt(nd['c'][0][2])
            elif nd['k'] in ('wolf', 'vil'): r = vt(nd['c'][nd['best']][2])
            else:
                r = {g: 0.0 for g in q}
                for p, _, c, _ in nd['c']:
                    qc = self.nodes[c].get('q') or {}
                    vc = vt(c)
                    for g, x in qc.items():
                        if g in r and q[g] > 0: r[g] += p * x / q[g] * vc[g]
            memo[i] = r; nd['vt'] = r
            return r
        for i in range(len(self.nodes)): vt(i)

def build10(key, pol):
    import e10a
    e10a.E = E
    E.setpol(**pol)
    s0 = e10a.initial10(key)
    s0 = s0[:8] + (tuple((k, F(p).limit_denominator(10000)) for k, p in s0[8]),)
    T = Tree()
    root = T.state(s0)
    return T, root, E.V(s0)

def reach_symbols(T, root):
    """最善進行（人外は最善の手）で、各記号の場面に来る確率を求める：{(種類, g, n): 確率}"""
    order = []; seen = set(); stack = [(root, 0)]
    while stack:   # 後順で並べて、逆にすると親が子より先になる
        i, st = stack.pop()
        if st: order.append(i); continue
        if i in seen: continue
        seen.add(i); stack.append((i, 1))
        nd = T.nodes[i]
        kids = nd.get('c', [])
        if nd['k'] in ('wolf', 'vil'): kids = [kids[nd['best']]]
        for c in kids: stack.append((c[2], 0))
    reach = {root: 1.0}
    out = {}
    for i in reversed(order):
        r = reach.get(i, 0.0); nd = T.nodes[i]
        if 'sym' in nd: out[nd['sym']] = out.get(nd['sym'], 0.0) + r
        for sy, w in nd.get('syms', []): out[sy] = out.get(sy, 0.0) + r * float(w)
        kids = nd.get('c', [])
        if nd['k'] in ('wolf', 'vil'): kids = [kids[nd['best']]]
        for c in kids:
            p = 1.0 if c[0] is None else c[0]
            reach[c[2]] = reach.get(c[2], 0.0) + r * p
    return out

def reach_gj(T, root):
    """最善進行で、GJ の朝（狩人がCOするかを選ぶ場面）に来る確率：{(日, 生存者数, 'co' | 'no'): 確率}"""
    order = []; seen = set(); stack = [(root, 0)]
    while stack:
        i, st = stack.pop()
        if st: order.append(i); continue
        if i in seen: continue
        seen.add(i); stack.append((i, 1))
        nd = T.nodes[i]; kids = nd.get('c', [])
        if nd['k'] in ('wolf', 'vil'): kids = [kids[nd['best']]]
        for c in kids: stack.append((c[2], 0))
    reach = {root: 1.0}; out = {}
    for i in reversed(order):
        r = reach.get(i, 0.0); nd = T.nodes[i]
        if 'gjd' in nd: out[nd['gjd']] = out.get(nd['gjd'], 0.0) + float(r)
        kids = nd.get('c', [])
        if nd['k'] in ('wolf', 'vil'): kids = [kids[nd['best']]]
        for c in kids:
            p = 1.0 if c[0] is None else c[0]
            reach[c[2]] = reach.get(c[2], 0.0) + r * p
    return out

def wolf_plan(T, root):
    """最善進行で、人外が選ぶ場面（夜の噛み・偽の結果、狼の指定役の吊り先、狩人COへの対抗）ごとの選択と、その場面に来る確率。
    [(日, '夜' | '昼' | '朝', 場面, 選んだ手, 確率)]"""
    order = []; seen = set(); stack = [(root, 0)]
    while stack:
        i, st = stack.pop()
        if st: order.append(i); continue
        if i in seen: continue
        seen.add(i); stack.append((i, 1))
        nd = T.nodes[i]; kids = nd.get('c', [])
        if nd['k'] in ('wolf', 'vil'): kids = [kids[nd['best']]]
        for c in kids: stack.append((c[2], 0))
    reach = {root: 1.0}; out = {}
    day = {}
    for i in reversed(order):
        r = float(reach.get(i, 0.0)); nd = T.nodes[i]
        if nd.get('d', -1) is not None and nd.get('d', -1) >= 0: day[i] = nd['d']
        d = day.get(i, 0)
        kids = nd.get('c', [])
        if nd['k'] == 'wolf':
            lab = kids[nd['best']][1]
            ph = {'night': '夜', 'day': '昼', 'morning': '朝'}.get(nd.get('ph'), '')
            key = (d + 1, ph, nd.get('t', ''), lab)
            out[key] = out.get(key, 0.0) + r
        if nd['k'] in ('wolf', 'vil'): kids = [kids[nd['best']]]
        for c in kids:
            p = 1.0 if c[0] is None else c[0]
            reach[c[2]] = reach.get(c[2], 0.0) + r * float(p)
            if c[2] not in day: day[c[2]] = d
    return sorted([list(k) + [p] for k, p in out.items() if p > 1e-4], key=lambda x: (x[0], x[1] != '夜', -x[4]))

def day_actions(T, root):
    """最善進行で、日ごとに「どの吊り方で何を吊るか」が起こる確率：{日: {(吊り方, 対象): 確率}}。日は 2d から"""
    order = []; seen = set(); stack = [(root, 0)]
    while stack:
        i, st = stack.pop()
        if st: order.append(i); continue
        if i in seen: continue
        seen.add(i); stack.append((i, 1))
        nd = T.nodes[i]
        kids = nd.get('c', [])
        if nd['k'] in ('wolf', 'vil'): kids = [kids[nd['best']]]
        for c in kids: stack.append((c[2], 0))
    reach = {root: 1}; day = {root: 0}
    out = {}
    for i in reversed(order):
        r = reach.get(i, 0); nd = T.nodes[i]
        dd = nd.get('d', day.get(i, 0))
        if 'act' in nd:
            o = out.setdefault(dd + 1, {})
            o[nd['act']] = o.get(nd['act'], 0) + r
        kids = nd.get('c', [])
        if nd['k'] in ('wolf', 'vil'): kids = [kids[nd['best']]]
        for c in kids:
            p = 1 if c[0] is None else c[0]
            reach[c[2]] = reach.get(c[2], 0) + r * p
            day.setdefault(c[2], dd)
    return out
