# 10a狩人用（tree10 から作成：狂人の毎晩の●○を人外の選択に加え、猫又の表示を除く）。
# engine7 の局面からラベル付きの全分岐ツリー（DAG）を書き出す。値は engine7.V と照合する。
# ラベルには狼に見える出来事だけを書く（狩人・猫又の位置、占いCO者が本物か狂人かは書かない）。
import json, sys
import engine10 as E

def cname(r):
    if not any(r): return '灰'
    marks = {1: '○', 2: '●'}
    if len(r) == 1: return f'占いの{marks[r[0]]}'
    return '・'.join(f'占い{i + 1}の{marks[x]}' for i, x in enumerate(r) if x)

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
def night_outcomes_l(s, bite, fk, rep):
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
            gj = 0.0
            if hunter:
                gt = E.guard_target(slots, meds, T, TM)
                if isinstance(gt, list): gj = 1.0 / len(gt) if who in gt else 0.0
                elif gt is not None: gj = 1.0 if who == gt else 0.0
                else: gj = 1.0 / max(n_alive - 1, 1)
            if gj > 0: nxt.append((p * gj, wd.cp(), [], ['噛み失敗（GJ）']))
            if gj < 1:
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
                if isw: whos = [(1.0, ('c', r, True, None))]
                else: whos = [(q, ('c', r, False, kind)) for q, kind in E.take_human(wd0, r)]
            else: whos = [(1.0, tg)]
            for q, who in whos:
                w1 = wd0.cp()
                iscat = E.kill(w1, who)
                if who[0] == 'c': col = 2 if who[2] else 1; lst = ('c', who[1], col)
                elif who[0] == 's': col = 2 if slots[who[1]][0] else 1; lst = ('s', who[1], col)
                else: col = 2 if meds[who[1]][0] else 1; lst = ('m', who[1], col)
                base = f"{how}：{who_desc(who if who[0] != 'c' else ('c', who[1], who[2]), slots, meds)}を吊る"
                outs = [(1.0, w1, base)]
                if iscat and E.term(w1.sl, w1.md, E.cats_t(w1.cd)) is None:
                    ev = E.everyone(w1); t2 = sum(x for x, _ in ev)
                    outs = []
                    for x, v in ev:
                        w2 = w1.cp(); E.kill(w2, v)
                        vd = who_desc(v if v[0] != 'c' else ('c', v[1], v[2]), slots, meds)
                        outs.append((x / t2, w2, f'{base}（猫又だった）→ 道連れ：{vd}'))
                elif iscat:
                    outs = [(1.0, w1, f'{base}（猫又だった）')]
                for q2, w2, lab in outs:
                    w2.dead = []
                    res.append((p0 * q * q2, E.visible(w2, T, TM, lst, nt), E.kof(w2), lab))
    return agg_labeled(res, 'N')

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
        nd.update(v=v, d=nt, pub=pub, hid=hid, ph='day' if ph == 'D' else 'night', q=E.tag_mass(bel))
        self.nodes[nid] = nd
        self.check(nd)
        return nid

    def check(self, nd):
        if nd['k'] == 'chance': got = sum(c[0] * self.nodes[c[2]]['v'] for c in nd['c'])
        elif nd['k'] == 'wolf': got = min(self.nodes[c[2]]['v'] for c in nd['c'])
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
        for bite in bites:
            for fk in (itertools.product(*fakes) if fakes else [()]):
                for rep, mc in itertools.product(reps, (1, 2) if E.POL['mad'] == 'A' and E.mad_may_divine(s) and not (E.POL.get('w0') and s[7] == 0) else (None,)):
                    if mc: E._MC[0] = mc
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
        if len(opts) == 1:
            opts[0][3] = 'fixed'
            return dict(k='fixed', c=opts, t='夜の行動')
        mv = min(self.nodes[o[2]]['v'] for o in opts); best = next(i for i, o in enumerate(opts) if self.nodes[o[2]]['v'] <= mv + E.TIE)
        return dict(k='wolf', c=opts, best=best, t='人外の選択（夜）')

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
        return dict(k='chance', c=ch, t='信用する占い師を決める')

    def after_trust(self, s):
        ph, slots, meds, T, TM, cats, last, nt, bel = s
        w, n = E.counts(slots, meds, cats)
        if n >= 5 and 2 * (w + 1) >= n:
            pm = sum(p for k, p in bel if E.mad_alive(k[1], slots, meds))
            if pm > 0:
                ch = []
                if 2 * (w + 1) > n:
                    yes = self.new(dict(k='end', v=0.0, ph='end', d=nt, t='狼の勝ち（PPで人外が過半数）', pub='', hid='', q=E.tag_mass(E.norm_bel({k: p for k, p in bel if E.mad_alive(k[1], slots, meds)}))))
                else:
                    d = {k: p for k, p in bel if E.mad_alive(k[1], slots, meds)}
                    h = self.hang(s[:8] + (E.norm_bel(d),))
                    qd = E.tag_mass(E.norm_bel(d))
                    lose = self.new(dict(k='end', v=0.0, ph='end', d=nt, t='狼の勝ち（PPの同票決選に負け）', pub='', hid='', q=qd))
                    yes = self.sub('chance', 'day', 'PP（同数）：決選はランダム', [[0.5, '村の吊りが通る', h, 'chance'], [0.5, '人外が吊りを通す', lose, 'chance']], 0.5 * self.nodes[h]['v'], qd)
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
        d = E.designator(s)
        how = {'h': '指定', 'w': '指定（狼の指定役）', None: '投票'}[d]
        lot = d is None and E.POL.get('lot')
        if lot: how = '乱数'
        if d == 'w':
            hum = [u for u in units if not ((u[1][0] == 'c' and u[1][2]) or (u[1][0] == 's' and slots[u[1][1]][0]) or (u[1][0] == 'm' and meds[u[1][1]][0]))]
            opts = []
            for u in (hum or units):
                outs = hang_outcomes_l(s, [(1, u[1])], how)
                ch = [[p, lab, self.state(c), 'chance'] for p, lab, c in outs]
                v = sum(x[0] * self.nodes[x[2]]['v'] for x in ch)
                opts.append([None, f'{who_desc(u[1] if u[1][0] != "c" else ("c", u[1][1], u[1][2]), slots, meds)}を指定', self.sub('chance', 'day', '吊り', ch, v, E.tag_mass(bel)), 'wolf'])
            mv = min(self.nodes[o[2]]['v'] for o in opts); best = next(i for i, o in enumerate(opts) if self.nodes[o[2]]['v'] <= mv + E.TIE)
            return self.new(dict(k='wolf', c=opts, best=best, ph='day', t='狼の指定役が吊り先を選ぶ', v=self.nodes[opts[best][2]]['v'], q=E.tag_mass(bel)))
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
            elif nd['k'] == 'wolf': r = vt(nd['c'][nd['best']][2])
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
    E.setpol(**pol)
    s0 = e10a.initial10(key)
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
        if nd['k'] == 'wolf': kids = [kids[nd['best']]]
        for c in kids: stack.append((c[2], 0))
    reach = {root: 1.0}
    out = {}
    for i in reversed(order):
        r = reach.get(i, 0.0); nd = T.nodes[i]
        if 'sym' in nd: out[nd['sym']] = out.get(nd['sym'], 0.0) + r
        kids = nd.get('c', [])
        if nd['k'] == 'wolf': kids = [kids[nd['best']]]
        for c in kids:
            p = 1.0 if c[0] is None else c[0]
            reach[c[2]] = reach.get(c[2], 0.0) + r * p
    return out
