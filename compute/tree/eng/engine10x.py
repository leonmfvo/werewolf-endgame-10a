# engine10：engine9 に 0-2（占いCOなし・霊能CO2人）を加えたもの。狂人の霊能CO者を belief の中で「霊能CO者 j」（m = -10 - j）として持てるようにし、
# 2人の霊能CO者のどちらが狂人かを狼が知らない形にする。
# 12A猫 序盤エンジン v4（engine9）：engine8 に村の進行の選択肢（指定役 ds・霊能CO者を吊る hm）と、
# belief の内訳の目印（5番目の要素）を加えたもの。狼に見分けのつかない内訳をまとめた1つのゲームを解ける。
# 12A猫 序盤エンジン v3（engine8）：engine7 に「狂人が灰に潜伏」「狂人が霊能を騙る」を加えたもの。
# belief の狂人の位置 m：占いCO者の番号 / -1 死亡・不在 / -2 霊能CO者 MADMED / 分類 r（灰に潜伏）
# 12A猫 序盤エンジン v2（engine7）
# 占いCO者・霊能CO者を個別の枠（slot）として持ち、各占い師が誰に○/●を出したかを公開情報として追跡する。
#  - 村：情報を使った決め打ち（霊能結果との矛盾で破綻→乗り換え、噛まれた占い師を真と見る、
#        灰の吊り先を結果で選ぶ）を固定ルールとして持つ。
#  - 狼：噛み先・偽占いの占い先と結果（囲い／人間に白／人間に黒）・偽霊能の結果を最適化する。
#  - 狂人：結果の出し方は方針（全部黒 / 全部白 / 初回黒→以後白 / 初回白→以後黒）。村に不利な方を採用。
# 狼は 狩人・猫又の位置、人間の占いCO者のどちらが本物か を知らない → belief（分布）で持つ。
#
# 状態 s = (ph, slots, meds, T, TM, cats, last, nt, bel)
#   ph    : 'D' 昼 / 'N' 夜
#   slots : 占いCO者 ((狼?, 生存?, 破綻?), ...)
#   meds  : 霊能CO者 ((狼?, 生存?, 破綻?), ...)
#   T, TM : 信用している占い師 / 霊能者の番号（-1 なし）
#   cats  : 非CO者の分類 ((r, 狼の数, 人間の数), ...)  r[i] = 占いCO者 i の結果 0 なし / 1 ○ / 2 ●
#   last  : 前日に吊った人 (種類, 参照, 色) 種類 'c' 非CO者（参照 r）/ 's' 占いCO者 / 'm' 霊能CO者、色 1 人間 / 2 狼
#   nt    : 次の夜の番号（初日夜 = 0）
#   bel   : (((本物占いの枠, 狂人の枠, 狩人の分類, 猫又の分類), 確率), ...)  -1 / None は不在・死亡
from functools import lru_cache
from fractions import Fraction as F   # engine10x：engine10 を分数（厳密な有理数）で計算する版（gen_x.py で生成）

POL = dict(sp='trust', mp='trust', cr='tm', gp='info', bt='switch', mad='B', tp='rand', mm='contra', ds='seer', hm=False)
# ds: 吊り先の指定役 'seer' 信用占い師（いなければ信用霊能）/ 'medium' 信用霊能（いなければ信用占い師）/ 'none' 指定なし（自由投票）。狩人は指定役の順で護衛する
# hm: True なら（信用占い師の●・破綻者の次に）霊能CO者を吊る
MADMED = [-1]   # 狂人の霊能CO者の番号（いなければ -1）
# mm: 狂人の霊能結果 'contra' 吊った人に信用占い師の結果があれば逆を言う（なければ○）/ 'agree' 同じことを言う / 'W' 常に○ / 'B' 常に●
# sp : 'trust' 決め打ちして他の占いCO者を吊る / 'keep' 決め打ちして他は残す / 'roller' 占いローラー / 'ignore' 占いを見ない
# mp : 霊能CO者が2人のとき 'trust' ランダムに1人を信用 / 'roller' 両方吊る
# cr : 信用占い師の結果と信用霊能の結果が矛盾したとき 'tm' 霊能を信じる（占い師が破綻）/ 'ts' 占い師を信じる（霊能が破綻）
# gp : 灰の吊り先 'plain' ランダム / 'info' 他の占いCO者の●を優先し、○の少ない人を優先 / 'anti' 真置きしていない占いCO者の○を優先 / 'infoa' 全占いの●優先（fix2 でも未破綻の占い全員の結果を見る）
# bt : 'switch' 信用していない占い師が噛まれたら（その朝の死者が1人のとき）そちらを真と見て乗り換える / 'stay' 乗り換えない
# tp : 信用する占い師の選び方 'rand' ランダム / 'white' 生存者に出している●が少ない人 / 'black' ●が多い人
# mad: 狂人の結果 'B' 全部● / 'W' 全部○ / 'BW' 初回●→以後○ / 'WB' 初回○→以後●

def setpol(**kw):
    POL.update(kw)
    V.cache_clear()

_MC = [1]
_CC = [None]   # hco：GJ が出たとき対抗の狩人COをする灰の狼の分類（None ならしない）。夜の手と一緒に狼が選ぶ
def mad_color(nt):
    m = POL['mad']
    if POL.get('w0') and nt == 0: return 1     # w0：初日は●を出せない（10a）
    if m == 'A': return _MC[0]   # 毎晩選ぶ（night_value で min を取る）
    if m == 'B': return 2
    if m == 'W': return 1
    if m == 'BW': return 2 if nt == 0 else 1
    return 1 if nt == 0 else 2

def RQ(x): return x   # 分数なので丸めない

def norm_bel(d):
    tot = sum(d.values())
    return tuple(sorted(((k, RQ(v / tot)) for k, v in d.items() if v > 0), key=lambda kv: repr(kv[0])))

def cats_t(cd):
    return tuple(sorted((r, w, h) for r, (w, h) in cd.items() if w + h > 0))

def counts(slots, meds, cats):
    w = sum(c[1] for c in cats) + sum(1 for x in slots if x[0] and x[1]) + sum(1 for x in meds if x[0] and x[1])
    n = sum(c[1] + c[2] for c in cats) + sum(1 for x in slots if x[1]) + sum(1 for x in meds if x[1])
    return w, n

def term(slots, meds, cats):
    w, n = counts(slots, meds, cats)
    if w == 0: return F(1)
    if 2 * w >= n: return F(0)
    return None

# ---------------------------------------------------------------- 世界（1つの belief 項目について確定した状態）
class W:
    __slots__ = ('cd', 'sl', 'md', 'S', 'm', 'H', 'c', 'dead', 'g')
    def __init__(s, cd, sl, md, S, m, H, c, dead, g=None):
        s.cd, s.sl, s.md, s.S, s.m, s.H, s.c, s.dead, s.g = cd, sl, md, S, m, H, c, dead, g
    def cp(s):
        return W({k: list(v) for k, v in s.cd.items()}, [list(x) for x in s.sl], [list(x) for x in s.md], s.S, s.m, s.H, s.c, list(s.dead), s.g)

def kof(w):
    return (w.S, w.m, w.H, w.c) if w.g is None else (w.S, w.m, w.H, w.c, w.g)

def mk_world(s, k):
    _, slots, meds, T, TM, cats, last, nt, bel = s
    return W({r: [w, h] for r, w, h in cats}, [list(x) for x in slots], [list(x) for x in meds], k[0], k[1], k[2], k[3], [], k[4] if len(k) > 4 else None)

def take_human(wd, r):
    """category r の人間をランダムに1人選ぶ：[(prob, kind)] kind 'H' 'c' 'v'"""
    nh = wd.cd[r][1]
    out = []
    if wd.H == r: out.append((F(1) / nh, 'H'))
    if wd.c == r: out.append((F(1) / nh, 'c'))
    if wd.m == r: out.append((F(1) / nh, 'm'))
    rest = nh - (wd.H == r) - (wd.c == r) - (wd.m == r)
    if rest: out.append((F(rest, nh), 'v'))
    return out

def remove_human(wd, r, kind):
    wd.cd[r][1] -= 1
    if kind == 'H': wd.H = None
    elif kind == 'c': wd.c = None
    elif kind == 'm': wd.m = -1

def move(wd, r, isw, kind, i, col):
    r2 = r[:i] + (col,) + r[i + 1:]
    e = wd.cd.setdefault(r2, [0, 0])
    if isw:
        wd.cd[r][0] -= 1; e[0] += 1
    else:
        wd.cd[r][1] -= 1; e[1] += 1
        if kind == 'H': wd.H = r2
        elif kind == 'c': wd.c = r2
        elif kind == 'm': wd.m = r2

def everyone(wd, excl_cat=False):
    """生存者全員を個人単位で：[(weight, ('c', r, isw, kind) | ('s', i) | ('m', j))]"""
    out = []
    for r, (w, h) in wd.cd.items():
        if w: out.append((w, ('c', r, True, None)))
        if h:
            if wd.H == r: out.append((1, ('c', r, False, 'H')))
            if wd.c == r and not excl_cat: out.append((1, ('c', r, False, 'c')))
            if wd.m == r: out.append((1, ('c', r, False, 'm')))
            rest = h - (wd.H == r) - (wd.c == r) - (wd.m == r)
            if rest: out.append((rest, ('c', r, False, 'v')))
    for i, x in enumerate(wd.sl):
        if x[1]: out.append((1, ('s', i)))
    for j, x in enumerate(wd.md):
        if x[1]: out.append((1, ('m', j)))
    return out

def kill(wd, who):
    """who を死亡させる。戻り値：猫又だったか"""
    if who[0] == 'c':
        _, r, isw, kind = who
        if isw: wd.cd[r][0] -= 1
        else: remove_human(wd, r, kind)
        wd.dead.append(r)
        return kind == 'c'
    if who[0] == 's': wd.sl[who[1]][1] = 0
    else: wd.md[who[1]][1] = 0
    return False

def wolves_of(wd):
    out = []
    for r, (w, h) in wd.cd.items():
        if w: out.append((w, ('c', r, True, None)))
    for i, x in enumerate(wd.sl):
        if x[1] and x[0]: out.append((1, ('s', i)))
    for j, x in enumerate(wd.md):
        if x[1] and x[0]: out.append((1, ('m', j)))
    return out

def spread(worlds, items, fn):
    """worlds: [(p, wd)], items(wd) -> [(w, x)] ; fn(wd, x) mutates copy"""
    out = []
    for p, wd in worlds:
        its = items(wd)
        tot = sum(w for w, _ in its)
        if not its or tot == 0:
            out.append((p, wd)); continue
        for w, x in its:
            nw = wd.cp(); fn(nw, x)
            out.append((p * w / tot, nw))
    return out

# ---------------------------------------------------------------- 公開情報の更新（朝）
def visible(wd, T, TM, last, nt):
    return (tuple(tuple(x) for x in wd.sl), tuple(tuple(x) for x in wd.md), T, TM, cats_t(wd.cd), last, nt)

def aggregate(worlds_with_vis):
    """[(p, vis, k)] -> [(prob, state)]"""
    acc = {}
    for p, vis, k in worlds_with_vis:
        if p <= 0: continue
        d = acc.setdefault(vis, {})
        d[k] = d.get(k, 0) + p
    out = []
    for vis, d in acc.items():
        tot = sum(d.values())
        sl, md, T, TM, cats, last, nt = vis
        out.append((tot, ('D', sl, md, T, TM, cats, last, nt, norm_bel(d))))
    return out

def medium_report(md, TM, T, last, rep, m=-2):
    """信用霊能者 TM が前日に吊った人について出す結果（1 ○ / 2 ●）。m はその世界での狂人の位置"""
    if md[TM][0]: return rep
    if (TM == MADMED[0] and m == -2) or m == -10 - TM:
        r_ = last[1] if last[0] == 'c' else None
        tres = r_[T] if (r_ is not None and T >= 0) else 0
        mm = POL['mm']
        return (3 - tres if tres else 1) if mm == 'contra' else ((tres or 1) if mm == 'agree' else (1 if mm == 'W' else 2))
    return last[2]

# mr：霊能CO者2人の結果を見比べる（0-2 用）。1 / 2 = 結果が割れたら ○ / ● を出した方を信じ、もう1人を偽とみなして吊る
def reports2(md, T, last, rep, m):
    """霊能CO者2人がそれぞれ出す結果（1 ○ / 2 ● / 0 死亡）。mr のときだけ"""
    if not POL.get('mr') or len(md) != 2 or last is None: return None
    return tuple(medium_report(md, j, T, last, rep, m) if md[j][1] else 0 for j in range(2))

def morning_update(wd, T, TM, last, rep, deaths_public):
    """霊能結果・噛みによる乗り換え。wd は変更される。戻り値 (T, TM)"""
    sl, md = wd.sl, wd.md
    cols = reports2(md, T, last, rep, wd.m)
    if cols and all(cols) and not md[0][2] and not md[1][2] and cols[0] != cols[1]:
        md[0 if cols[0] != POL['mr'] else 1][2] = 1
    # 霊能結果
    if last is not None and TM >= 0 and md[TM][1]:
        col = medium_report(md, TM, T, last, rep, wd.m)
        if last[0] == 'c':
            r = last[1]
            bad = [i for i in range(len(sl)) if r[i] and r[i] != col]
            Tv = T >= 0 and not sl[T][2]
            # fix2：占い1CO・霊能2CO以上では、信用占いと信用霊能が矛盾したら霊能の方を偽とみなす
            if Tv and T in bad and (POL['cr'] == 'ts' or (POL.get('fix2') and len(sl) == 1 and len(md) >= 2)):
                md[TM][2] = 1
            else:
                for i in bad: sl[i][2] = 1
            # g2（2d灰吊り）：まだ占いを決めていないうちに吊った灰が●なら、占いロラ（1●止め）に切り替える（T = -2）
            if POL['sp'] == 'g2' and T == -1 and col == 2: T = -2
            # hco：狩人CO者2人の片方を吊って霊能結果●なら、残った方を本物の狩人（人間確定）とする
            if len(r) > len(sl) and r[-1] == 2 and col == 2:
                for r2, (w2, h2) in list(wd.cd.items()):
                    if len(r2) > len(sl) and r2[-1] == 2:
                        for _ in range(h2): mv_flag(wd, r2, False, 'H' if wd.H == r2 else 'v', 1)
        elif last[0] == 's' and POL.get('fix2'):
            # fix2：吊った占いCO者に霊能が●を出したら、その占い師を破綻扱いにする（以後その結果を使わない）
            if col == 2: sl[last[1]][2] = 1
            # 占い1●止めロラで占いCO者が2人：吊った占いが○なら、その占い師を真とみなして結果を使う
            elif (POL['sp'] == 'rstop' or (POL['sp'] == 'g2' and T == -2)) and len(sl) == 2: T = last[1]
    # 噛まれた占い師を真と見る
    if POL['bt'] == 'switch' and POL['sp'] != 'ignore' and len(deaths_public) == 1 and deaths_public[0][0] == 's':
        j = deaths_public[0][1]
        if j != T and not sl[j][2]: T = j
    return T, TM

# ---------------------------------------------------------------- 夜
def night_options(s):
    _, slots, meds, T, TM, cats, last, nt, bel = s
    bites = [None] if nt == 0 else []
    if nt > 0:
        for r, w, h in cats:
            if h: bites.append(('c', r))
        for i, x in enumerate(slots):
            if x[1] and not x[0]: bites.append(('s', i))
        for j, x in enumerate(meds):
            if x[1] and not x[0]: bites.append(('m', j))
    fakes = []   # per wolf seer slot
    for i, x in enumerate(slots):
        if x[1] and x[0]:
            opts = []
            for r, w, h in cats:
                if r[i]: continue
                if w: opts.append((i, r, True, 1))          # 囲い
                if h: opts.append((i, r, False, 1))
                if h and not (POL.get('w0') and nt == 0): opts.append((i, r, False, 2))
            fakes.append(opts or [None])
    if POL.get('cross') and nt == POL.get('sstart', 3) - 2:   # cross：その夜は占い師全員が同じ灰を占う。偽占いは色だけ選ぶ
        fakes = [[(i, None, None, 1), (i, None, None, 2)] for i, x in enumerate(slots) if x[1] and x[0]]
    reps = [None]
    if TM >= 0 and meds[TM][1] and meds[TM][0] and last is not None: reps = [1, 2]
    if POL.get('mr') and last is not None and any(x[0] and x[1] for x in meds): reps = [1, 2]   # 狼の霊能は、信用されていなくても結果を出す
    return bites, fakes, reps

def guard_target(slots, meds, T, TM):
    """狩人の護衛先（指定役の順）。None ならランダム"""
    # hg='co2'：指定役がいても、生きている占いCO者の中からランダムに護衛する（占いロラの終盤でGJを出さないため）
    if POL.get('hg') == 'co2':
        cos = [('s', i) for i, x in enumerate(slots) if x[1]]
        if cos: return cos
    order = [('m', TM), ('s', T)] if POL['ds'] == 'medium' else [('s', T), ('m', TM)]
    for kind, i in order:
        if i >= 0 and (slots if kind == 's' else meds)[i][1]:
            # hgm：確率 hgm で指定役を、残りはランダムに護衛する（混合）
            if POL.get('hgm') is not None: return ('mix', POL['hgm'], (kind, i))
            return (kind, i)
    # hg='co'：指定役がいないときは、生きている占いCO者の中からランダムに護衛する（灰でGJを出さない）
    if POL.get('hg') == 'co':
        cos = [('s', i) for i, x in enumerate(slots) if x[1]]
        if cos: return cos
    return None

def night_outcomes(s, bite, fk, rep, gjmode=None):
    """gjmode（hcoopt 用）：'skip' GJ でない場合だけ / 'no' GJ の場合だけ（狩人は潜伏）/ 'co' GJ の場合だけ（狩人がCO）"""
    _, slots, meds, T, TM, cats, last, nt, bel = s
    res = []
    n_alive = counts(slots, meds, cats)[1]
    for k, pk in bel:
        wd0 = mk_world(s, k)
        # 噛み
        worlds = []
        if bite is None:
            worlds = [(pk, wd0, None)]
        elif bite[0] == 'c':
            for q, kind in take_human(wd0, bite[1]):
                worlds.append((pk * q, wd0, ('c', bite[1], False, kind)))
        else:
            worlds = [(pk, wd0, bite)]
        nxt = []
        for p, wd, who in worlds:
            if who is None:
                nxt.append((p, wd.cp(), [])); continue
            # 護衛
            hunter = wd.H is not None and not (who[0] == 'c' and who[3] == 'H')
            gj = F(0)
            if hunter:
                gt = guard_target(slots, meds, T, TM)
                if isinstance(gt, list): gj = F(1) / len(gt) if who in gt else F(0)
                elif gt is not None and gt[0] == 'mix': gj = gt[1] * (F(1) if who == gt[2] else F(0)) + (1 - gt[1]) * F(1) / max(n_alive - 1, 1)
                elif gt is not None: gj = F(1) if who == gt else F(0)
                else: gj = F(1) / max(n_alive - 1, 1)
            if gj > 0 and gjmode != 'skip':
                wg = wd.cp()
                if gjmode == 'co': hunter_co(wg, who, force=True)
                elif gjmode is None and POL.get('hco'): hunter_co(wg, who)
                nxt.append((p * gj, wg, []))
            if gj < 1 and gjmode not in ('no', 'co'):
                w2 = wd.cp()
                iscat = kill(w2, who)
                deaths = [who]
                if iscat:
                    wl = wolves_of(w2); tot = sum(x for x, _ in wl)
                    for ww, wv in wl:
                        w3 = w2.cp(); kill(w3, wv)
                        nxt.append((p * (1 - gj) * ww / tot, w3, deaths + [wv]))
                else:
                    nxt.append((p * (1 - gj), w2, deaths))
        # 占い結果
        cross = POL.get('cross') and nt == POL.get('sstart', 3) - 2
        for p, wd, deaths in nxt:
            if cross:   # 投票予告（クロス占い）：結果のない灰からランダムに1人 B を選び、生きている占いCO者全員が B を占う
                ns = len(slots)
                pool = []
                for r, (w, h) in wd.cd.items():
                    if any(r[:ns]) or flagged(r, slots): continue
                    if w: pool.append((w, ('c', r, True, None)))
                    if h:
                        for q2, kind in take_human(wd, r): pool.append((h * q2, ('c', r, False, kind)))
                tot = sum(x for x, _ in pool)
                if tot:
                    for x, who in pool:
                        w1 = wd.cp(); _, r, isw, kind = who; ok = True
                        for i in range(ns):
                            if not (slots[i][1] and w1.sl[i][1]): continue
                            if slots[i][0]:
                                col = next((sp[3] for sp in fk if sp and sp[0] == i), 1)
                            elif k[0] == i: col = 2 if isw else 1
                            elif isinstance(k[1], int) and k[1] == i: col = mad_color(nt)
                            else: continue
                            move(w1, r, isw, kind, i, col); r = r[:i] + (col,) + r[i + 1:]
                        rp = None
                        if last is not None and TM >= 0 and w1.md[TM][1]: rp = ('rep', medium_report(w1.md, TM, T, last, rep, w1.m))
                        Tn, TMn = morning_update(w1, T, TM, last, rep, deaths)
                        w1.dead = []
                        res.append((p * x / tot, visible(w1, Tn, TMn, rp, nt + 1), kof(w1)))
                    continue
            ws = [(p, wd)]
            # 偽占い（狼）
            for spec in fk:
                if spec is None: continue
                i, r, isw, col = spec
                if not wd.sl[i][1]: continue
                nw = []
                for q, w1 in ws:
                    e = w1.cd.get(r)
                    if e is None or (isw and e[0] == 0) or (not isw and e[1] == 0):
                        nw.append((q, w1)); continue
                    if isw:
                        w2 = w1.cp(); move(w2, r, True, None, i, col); nw.append((q, w2))
                    else:
                        for q2, kind in take_human(w1, r):
                            w2 = w1.cp(); move(w2, r, False, kind, i, col); nw.append((q * q2, w2))
                ws = nw
            # 本物占い・狂人
            for who_slot, is_real in ((k[0], True), (k[1], False)):
                if not isinstance(who_slot, int) or who_slot < 0: continue
                if not slots[who_slot][1] or not wd.sl[who_slot][1]: continue
                i = who_slot
                nw = []
                for q, w1 in ws:
                    noop = sum(1 for d in w1.dead if d[i] == 0)
                    its = []
                    for r, (w, h) in w1.cd.items():
                        if r[i]: continue
                        # w0：本物の初日占いは狼以外から選ばれ、必ず○（初日白通知）
                        if w and not (is_real and POL.get('w0') and nt == 0): its.append((w, ('c', r, True, None)))
                        if h:
                            for q2, kind in take_human(w1, r): its.append((h * q2, ('c', r, False, kind)))
                    tot = sum(x for x, _ in its) + noop
                    if tot == 0: nw.append((q, w1)); continue
                    if noop: nw.append((q * noop / tot, w1))
                    for x, who in its:
                        _, r, isw, kind = who
                        col = (2 if isw else 1) if is_real else mad_color(nt)
                        w2 = w1.cp(); move(w2, r, isw, kind, i, col)
                        nw.append((q * x / tot, w2))
                ws = nw
            for q, w1 in ws:
                rp = None
                if last is not None and TM >= 0 and w1.md[TM][1]: rp = ('rep', medium_report(w1.md, TM, T, last, rep, w1.m))
                c2 = reports2(w1.md, T, last, rep, w1.m)
                if c2 and any(c2): rp = ('rep2', c2)
                Tn, TMn = morning_update(w1, T, TM, last, rep, deaths)
                w1.dead = []
                res.append((q, visible(w1, Tn, TMn, rp, nt + 1), kof(w1)))
    return aggregate(res)

def mad_may_divine(s):
    _, slots, meds, T, TM, cats, last, nt, bel = s
    return any(isinstance(k[1], int) and k[1] >= 0 and slots[k[1]][1] for k, p in bel)

def night_value(s):
    bites, fakes, reps = night_options(s)
    best = 2.0
    import itertools
    for bite in bites:
        for fk in itertools.product(*fakes) if fakes else [()]:
            for rep in reps:
                for mc in ((1, 2) if POL['mad'] == 'A' and mad_may_divine(s) and not (POL.get('w0') and s[7] == 0) else (1,)):
                    _MC[0] = mc
                    if POL.get('hcoopt') and bite is not None:
                        # hcoopt：GJ が出たら、狩人は「COして護衛先を申告」と「潜伏を続ける」の村勝率が高い方を選ぶ。
                        # COしたあと狼は対抗の狩人COをするかを選ぶ（村勝率が低くなる方）
                        # 先に朝の局面をすべて作ってから値を求める（値を求める途中で _MC・_CC が書き換わるため）
                        o_skip = night_outcomes(s, bite, fk, rep, 'skip')
                        o_no = night_outcomes(s, bite, fk, rep, 'no')
                        o_co = []
                        if gj_possible(s, bite):
                            for cc in counter_options(s, bite, force=True):
                                _CC[0] = cc
                                o_co.append(night_outcomes(s, bite, fk, rep, 'co'))
                        _CC[0] = None
                        v = sum(p * V(c) for p, c in o_skip)
                        vno = sum(p * V(c) for p, c in o_no)
                        vco = min(sum(p * V(c) for p, c in o) for o in o_co) if o_co else vno
                        if o_co:
                            if vco > vno + 1e-12: HCO_LOG.append((s[7] + 1, counts(s[1], s[2], s[5])[1] - 1, bite[0]))
                        v += max(vno, vco)
                        if v < best: best = v
                        continue
                    for cc in counter_options(s, bite):
                        _CC[0] = cc; _MC[0] = mc
                        v = sum(p * V(c) for p, c in night_outcomes(s, bite, fk, rep))
                        if v < best: best = v
                    _CC[0] = None
    return best

# ---------------------------------------------------------------- 昼
def trust_choices(s):
    """信用する占い師・霊能者の選び直し（chance）"""
    ph, slots, meds, T, TM, cats, last, nt, bel = s
    tch = [(F(1), T)]
    # tdelay：霊ロラが終わるまで占いを真置きしない（霊能CO者が生きている間は待つ）
    wait = POL.get('tdelay') and POL['mp'] == 'roller' and any(x[1] for x in meds)
    # sdelay：占いを吊り始める日（sstart、既定 3d）より前は占いを真置きしない（指定役は霊能）
    if POL.get('sdelay') and nt + 1 < POL.get('sstart', 3): wait = True
    if POL['sp'] in ('trust', 'keep') and (T < 0 or slots[T][2]) and not wait:
        c = [i for i, x in enumerate(slots) if x[1] and not x[2]]
        # fix2：生きている未破綻の占いがいなければ、吊られた（死んだ）未破綻の占いを真とみなして結果を使う
        if not c and POL.get('fix2'): c = [i for i, x in enumerate(slots) if not x[2]]
        if len(c) > 1 and POL['tp'] != 'rand':
            nb = {i: sum(w + h for r, w, h in cats if r[i] == 2) for i in c}
            tgt = min(nb.values()) if POL['tp'] == 'white' else max(nb.values())
            c = [i for i in c if nb[i] == tgt]
        tch = [(F(1) / len(c), i) for i in c] if c else [(F(1), -1)]
    elif POL['sp'] == 'rstop' and (T < 0 or slots[T][2]) and any(not x[1] and x[2] for x in slots):
        # 占い1●止めロラ：●が出てロラを止めたあと、生きている未破綻の占いが1人だけならその占いを真置きする
        c = [i for i, x in enumerate(slots) if x[1] and not x[2]]
        tch = [(F(1), c[0])] if len(c) == 1 else [(F(1), -1)]
    elif POL['sp'] == 'g2':
        # g2：2d は真置きしない。3d 朝、2d の灰が●ならロラ（T = -2、●が出たら止めて残り1人を真置き）、そうでなければ未破綻の占いから真置き
        if nt + 1 < 3 or (T >= 0 and not slots[T][2]): pass
        elif T == -2:
            if any(not x[1] and x[2] for x in slots):
                c = [i for i, x in enumerate(slots) if x[1] and not x[2]]
                if len(c) == 1: tch = [(F(1), c[0])]
        else:
            c = [i for i, x in enumerate(slots) if x[1] and not x[2]] or [i for i, x in enumerate(slots) if not x[2]]
            tch = [(F(1) / len(c), i) for i in c] if c else [(F(1), -1)]
    elif T >= 0 and slots[T][2]:
        tch = [(F(1), -1)]
    mch = [(F(1), TM)]
    if TM < 0 or meds[TM][2]:
        c = [j for j, x in enumerate(meds) if x[1] and not x[2]]
        if len(meds) >= 2 and POL['mp'] == 'roller': c = []
        mch = [(F(1) / len(c), j) for j in c] if c else [(F(1), -1)]
    return [(p * q, t, m) for p, t in tch for q, m in mch]

def hang_candidates(s):
    ph, slots, meds, T, TM, cats, last, nt, bel = s
    Tv = T >= 0 and not slots[T][2]
    tiers = []
    tiers.append([('c', r) for r, w, h in cats if Tv and r[T] == 2])
    tiers.append([('s', i) for i, x in enumerate(slots) if x[1] and x[2]] + [('m', j) for j, x in enumerate(meds) if x[1] and x[2]])
    tiers.append([('c', r) for r, w, h in cats if len(r) > len(slots) and r[-1] == 2])   # hco：狩人CO者2人（本物と狼の対抗）
    # rstop（占い1●止めロラ）：死んだ占いCO者から●（破綻）が出るまではロラを続ける
    rolling = (POL['sp'] == 'rstop' or (POL['sp'] == 'g2' and T == -2)) and not any(not x[1] and x[2] for x in slots)
    # sstart：その日（3 なら 3d）より前は占いCO者を吊らずに灰を吊る
    early = (POL.get('sstart') and nt + 1 < POL['sstart']) or (POL['sp'] == 'g2' and nt + 1 < 3)
    if (POL['sp'] == 'roller' or rolling or (POL['sp'] in ('trust', 'g2') and Tv)) and not early:
        tiers.append([('s', i) for i, x in enumerate(slots) if x[1] and i != T])
    # flex：GJ などで生存者が予定より多い（縄に余裕がある）日は、真置きの占いも含めて占いCO者を吊る（占いロラに切り替え）
    if POL.get('flex') and counts(slots, meds, cats)[1] > POL.get('n2', 9) + 4 - 2 * (nt + 1):
        tiers.append([('s', i) for i, x in enumerate(slots) if x[1]])
    if len(meds) >= 2 and POL['mp'] == 'roller' and nt + 1 >= POL.get('mstart', 2):   # mstart：霊ロラを始める日
        tiers.append([('m', j) for j, x in enumerate(meds) if x[1]])
    if POL['hm']:
        tiers.append([('m', j) for j, x in enumerate(meds) if x[1]])
    # hu：その日（2d なら 2）から、真置きしていない方の霊能CO者を吊る（じゃんけんで負けた方を吊るのと同じ）
    if POL.get('hu') and nt + 1 >= POL['hu'] and TM >= 0 and sum(1 for x in meds if x[1]) >= 2:
        tiers.insert(0, [('m', j) for j, x in enumerate(meds) if x[1] and j != TM])
    gray = [(r, w, h) for r, w, h in cats if not (Tv and r[T] == 1) and not marked(r, slots)]
    g2early = POL['sp'] == 'g2' and early
    if g2early:   # g2 の 2d。g2d：'protect' 占いの○を除いた完全灰から / 'include' ○も含めてランダム / 'target' ○をもらった人から
        mode = POL.get('g2d', 'protect')
        res = lambda r: [r[i] for i, y in enumerate(slots) if y[1] and not y[2]]
        if mode == 'protect': g0 = [x for x in gray if not any(res(x[0]))]
        elif mode == 'target': g0 = [x for x in gray if 1 in res(x[0])]
        else: g0 = gray
        gray = g0 or gray
    # infos：●で止まった後だけ●優先。霊能結果●で破綻した占いCO者がいて、生きている未破綻の占いCO者がいるときだけ●優先にし、それ以外は灰ランダム
    #  （ロラ中に霊能者が噛まれると、狼の占いCO者が破綻しないまま吊られ、その偽●が「未破綻の占いの●」として残るため）
    infos_on = POL['gp'] == 'infos' and any(not x[1] and x[2] for x in slots) and any(x[1] and not x[2] for x in slots)
    if gray and (POL['gp'] in ('info', 'anti', 'infoa') or infos_on) and not g2early:
        def score(r):
            if POL.get('fix2') and POL['gp'] != 'infoa':   # infos は info と同じ点数   # infoa：全占いの●優先（fix2 前の●優先と同じ。未破綻の占い全員の結果を見る）
                # fix2：○優先は「真置きがいればそれ以外、いなければ破綻した占い」の○だけ。●優先は「真置きがいればその占い、いなければ未破綻の占い」の結果だけ
                if POL['gp'] == 'anti':
                    return (sum(1 for i, v in enumerate(r[:len(slots)]) if v == 1 and i != T and (T >= 0 or slots[i][2])),)
                ok = lambda i: not slots[i][2] and (T < 0 or i == T)
                return (sum(1 for i, v in enumerate(r[:len(slots)]) if v == 2 and ok(i)), -sum(1 for i, v in enumerate(r[:len(slots)]) if v == 1 and ok(i)))
            if POL['gp'] == 'anti':   # anti：真置きしていない占いCO者の○を優先して吊る（囲いを疑う）
                return (sum(1 for i, v in enumerate(r[:len(slots)]) if v == 1 and i != T),)
            return (sum(1 for i, v in enumerate(r[:len(slots)]) if v == 2 and not slots[i][2]), -sum(1 for i, v in enumerate(r[:len(slots)]) if v == 1 and not slots[i][2]))
        best = max(score(r) for r, w, h in gray)
        gray = [x for x in gray if score(x[0]) == best]
    gm = POL.get('gm', 0)   # gm：灰と一緒に霊能CO者も吊り候補にする（1：真置きしていない方だけ、2：両方）
    tiers.append([('c', r) for r, w, h in gray] + ([('m', j) for j, x in enumerate(meds) if x[1] and (gm == 2 or j != TM)] if gm else []))
    tiers.append([('c', r) for r, w, h in cats])
    tiers.append([('s', i) for i, x in enumerate(slots) if x[1] and i != T] + [('m', j) for j, x in enumerate(meds) if x[1] and j != TM])
    tiers.append([('m', j) for j, x in enumerate(meds) if x[1]])
    tiers.append([('s', i) for i, x in enumerate(slots) if x[1]])
    for t in tiers:
        if t: return t
    return []

def designator(s):
    ph, slots, meds, T, TM, cats, last, nt, bel = s
    if POL['ds'] == 'none': return None
    order = [('m', TM), ('s', T)] if POL['ds'] == 'medium' else [('s', T), ('m', TM)]
    for kind, i in order:
        xs = slots if kind == 's' else meds
        if i >= 0 and xs[i][1] and not xs[i][2]: return 'w' if xs[i][0] else 'h'
    if POL.get('cw') and white_pool(s)[1]: return 'h'
    if POL.get('dchain') and gray_pool(s)[1]: return 'h'
    return None

# dchain：指定役も確定白もいなければ、生きている灰（非CO者）からランダムに1人を指定役にする
def gray_pool(s):
    cats = s[5]
    w = sum(c[1] for c in cats); return w, w + sum(c[2] for c in cats)

# 確定白（cw）：指定役（真置きの占い・霊能）がいなくなったら、確定白の灰が指定役を引き継ぐ。
# 確定白＝「破綻していない占いCO者全員（1人以上）から○」の灰、または仮指定（chain）で人間確定した灰（r の最後の目印が 1）。
# 確定白の中から1人をランダムに指定役にする（その人が狼である確率は、まとめて人数の比で扱う。日ごとに選び直す近似）
def flagged(r, slots):
    return len(r) > len(slots) and r[-1] == 1

def marked(r, slots):
    """目印つき（1 人間確定 / 2 狩人CO者が2人いるときのその2人）"""
    return len(r) > len(slots) and r[-1] != 0

# hco（GJ のあと狩人がCOして護衛先を申告する）：噛まれた人（灰の人間）を人間確定にし、狩人を人間確定にする。
# 狼が対抗する（_CC に灰の狼の分類がある）と、狩人とその狼が「狩人CO者2人」（目印 2）になり、村はその2人から吊る
def mv_flag(wd, r, isw, kind, val):
    r2 = r[:-1] + (val,)
    e = wd.cd.setdefault(r2, [0, 0])
    if isw:
        wd.cd[r][0] -= 1; e[0] += 1
    else:
        wd.cd[r][1] -= 1; e[1] += 1
        if kind == 'H': wd.H = r2
        elif kind == 'c': wd.c = r2
        elif kind == 'm': wd.m = r2

def hunter_co(wd, who, force=False):
    # hco_n：その朝の生存者がこの人数以下のときだけ狩人がCOする（それより前の GJ は潜伏したまま、申告もしない）
    if not force and counts(wd.sl, wd.md, cats_t(wd.cd))[1] > POL.get('hco_n', 99): return
    if who[0] == 'c' and not who[2] and who[1][-1] == 0: mv_flag(wd, who[1], False, who[3], 1)
    if wd.H is None or wd.H[-1] != 0: return   # 狩人は死亡、または既にCO済み
    cc = _CC[0]
    if cc is not None and wd.cd.get(cc, [0, 0])[0] > 0:
        mv_flag(wd, wd.H, False, 'H', 2); mv_flag(wd, cc, True, None, 2)
    else:
        mv_flag(wd, wd.H, False, 'H', 1)

def add_flag(s):
    """灰の分類 r の最後に目印（0 なし / 1 人間確定 / 2 狩人CO者2人）を足す（hco / hcoopt / 仮指定で使う）"""
    ns = len(s[1])
    f = lambda r: r + (0,) if isinstance(r, tuple) and len(r) == ns else r
    ph, slots, meds, T, TM, cats, last, nt, bel = s
    return (ph, slots, meds, T, TM, tuple((f(r), w, h) for r, w, h in cats), last, nt, norm_bel({tuple(f(x) for x in k): p for k, p in bel}))

HCO_LOG = []   # hcoopt：COを選んだ場面（日, その朝の生存者, 噛まれた人の種類）。試算の集計用

def gj_possible(s, bite):
    """狩人が生きていて、まだCOしていない世界があるか（そうでなければCOの選択はない）"""
    return any(k[2] is not None and k[2][-1] == 0 for k, p in s[8])

def counter_options(s, bite, force=False):
    if not (POL.get('hco') or force) or bite is None: return [None]
    slots, cats = s[1], s[5]
    if any(len(r) > len(slots) and r[-1] == 2 for r, w, h in cats): return [None]
    return [None] + [r for r, w, h in cats if w and len(r) > len(slots) and r[-1] == 0]

def is_white(r, slots):
    if flagged(r, slots): return True
    ok = [i for i, x in enumerate(slots) if not x[2]]
    return bool(ok) and all(r[i] == 1 for i in ok)

def white_pool(s):
    ph, slots, meds, T, TM, cats, last, nt, bel = s
    w = sum(c[1] for c in cats if is_white(c[0], slots)); h = sum(c[2] for c in cats if is_white(c[0], slots))
    return w, w + h

def designator_mix(s):
    """[(確率, 'w' | 'h' | None)]：指定役が狼か人間か"""
    d = designator(s)
    ph, slots, meds, T, TM, cats, last, nt, bel = s
    if d == 'h' and (POL.get('cw') or POL.get('dchain')):
        order = [('m', TM), ('s', T)] if POL['ds'] == 'medium' else [('s', T), ('m', TM)]
        if not any(i >= 0 and (slots if k == 's' else meds)[i][1] and not (slots if k == 's' else meds)[i][2] for k, i in order):
            w, n = white_pool(s) if POL.get('cw') and white_pool(s)[1] else gray_pool(s)
            pw = F(1) * w / n
            return [(x, y) for x, y in ((pw, 'w'), (1 - pw, 'h')) if x > 0]
    return [(F(1), d)]

def hang_outcomes(s, picks, mark=None):
    """picks: [(weight, target)] target ('c', r, isw) / ('s', i) / ('m', j)  -> aggregated night states"""
    ph, slots, meds, T, TM, cats, last, nt, bel = s
    tot = sum(w for w, _ in picks)
    res = []
    for k, pk in bel:
        wd0 = mk_world(s, k)
        for w, tg in picks:
            p0 = pk * w / tot
            if tg[0] == 'c':
                r, isw = tg[1], tg[2]
                if isw: whos = [(F(1), ('c', r, True, None))]
                else: whos = [(q, ('c', r, False, kind)) for q, kind in take_human(wd0, r)]
            else:
                whos = [(F(1), tg)]
            for q, who in whos:
                w1 = wd0.cp()
                iscat = kill(w1, who)
                if who[0] == 'c': col = 2 if who[2] else 1; lst = ('c', who[1], col)
                elif who[0] == 's': col = 2 if slots[who[1]][0] else 1; lst = ('s', who[1], col)
                else: col = 2 if meds[who[1]][0] else 1; lst = ('m', who[1], col)
                outs = [(F(1), w1)]
                if iscat and term(w1.sl, w1.md, cats_t(w1.cd)) is None:
                    ev = everyone(w1); t2 = sum(x for x, _ in ev)
                    outs = []
                    for x, v in ev:
                        w2 = w1.cp(); kill(w2, v); outs.append((F(x, t2), w2))
                if mark is not None:   # chain：X（分類 mark の人間）を人間確定の分類に移す
                    o2 = []
                    for q2, w2 in outs:
                        for q3, kind in take_human(w2, mark):
                            w3 = w2.cp(); rr = mark[:-1] + (1,)
                            w3.cd[mark][1] -= 1; w3.cd.setdefault(rr, [0, 0])[1] += 1
                            if kind == 'H': w3.H = rr
                            elif kind == 'c': w3.c = rr
                            elif kind == 'm': w3.m = rr
                            o2.append((q2 * q3, w3))
                    outs = o2
                for q2, w2 in outs:
                    w2.dead = []
                    res.append((p0 * q * q2, visible(w2, T, TM, lst, nt), kof(w2)))
    out = []
    for p, st in aggregate(res):
        out.append((p, ('N',) + st[1:]))
    return out

def day_value(s):
    ph, slots, meds, T, TM, cats, last, nt, bel = s
    v = F(0)
    for p, t, m in trust_choices(s):
        v += p * day_after_trust((ph, slots, meds, t, m, cats, last, nt, bel))
    return v

def mad_alive(m, slots, meds):
    if isinstance(m, tuple): return True
    if m == -2: return bool(meds[MADMED[0]][1])
    if isinstance(m, int) and m <= -10: return bool(meds[-10 - m][1])
    return m >= 0 and bool(slots[m][1])

def day_after_trust(s):
    ph, slots, meds, T, TM, cats, last, nt, bel = s
    w, n = counts(slots, meds, cats)
    # PP（5人以上、狂人が生存していて人外が過半数以上）
    if n >= 5 and 2 * (w + 1) >= n:
        pm = sum(p for k, p in bel if mad_alive(k[1], slots, meds))
        if pm > 0:
            if 2 * (w + 1) > n: yes = F(0)
            else:
                d = {k: p for k, p in bel if mad_alive(k[1], slots, meds)}
                yes = F(1, 2) * hang_value(s[:8] + (norm_bel(d),))
            rest = F(0)
            if pm < 1:
                d = {k: p for k, p in bel if not (mad_alive(k[1], slots, meds))}
                rest = hang_value(s[:8] + (norm_bel(d),))
            return pm * yes + (1 - pm) * rest
    return hang_value(s)

def hang_value(s):
    cand = hang_candidates(s)
    ph, slots, meds, T, TM, cats, last, nt, bel = s
    cd = {r: (w, h) for r, w, h in cats}
    units = []   # (weight, target)
    for c in cand:
        if c[0] == 'c':
            w, h = cd[c[1]]
            if w: units.append((w, ('c', c[1], True)))
            if h: units.append((h, ('c', c[1], False)))
        else: units.append((1, c))
    mix = designator_mix(s)
    if len(mix) > 1: return sum(q * hang_value_d(s, units, d) for q, d in mix)
    return hang_value_d(s, units, mix[0][1])

def hang_value_d(s, units, d):
    ph, slots, meds, T, TM, cats, last, nt, bel = s
    if d == 'w':
        hum = [u for u in units if not ((u[1][0] == 'c' and u[1][2]) or (u[1][0] == 's' and slots[u[1][1]][0]) or (u[1][0] == 'm' and meds[u[1][1]][0]))]
        opts = hum or units
        return min(sum(p * V(c) for p, c in hang_outcomes(s, [(1, u[1])])) for u in opts)
    if d == 'h' and POL.get('chain') is not None and len(units) >= 2 and all(u[1][0] == 'c' for u in units):
        return chain_value(s, units, POL['chain'])
    rnd = sum(p * V(c) for p, c in hang_outcomes(s, vote_units(s, units)))
    hum = bloc_humans(s, units)
    if hum:
        b = POL['bloc']
        wv = min(sum(p * V(c) for p, c in hang_outcomes(s, [(1, u[1])])) for u in hum)
        return (1 - b) * rnd + b * wv
    return rnd

# chain（仮指定）：人間の指定役が灰から X を仮指定し、X がもう1人 Y を挙げる。確率 p で X、1-p で Y を吊る。
# 狼の X は相方を挙げず人間の Y を（狼に一番得なように）選ぶ。人間の X は残りの灰からランダムに Y を選ぶ。
# Y が狼（霊能結果●）なら X を人間確定にする（r の最後の目印を 1 に。霊能結果が正しい前提）
def hang_value_1(s, tg, mark=None):
    return sum(p * V(c) for p, c in hang_outcomes(s, [(1, tg)], mark))

def chain_value(s, units, p):
    tot = sum(w for w, _ in units)
    v = F(0)
    for wx, ux in units:
        _, rx, xw = ux
        vx = hang_value_1(s, ux) if p > 0 else F(0)
        if xw:
            hums = [u for w, u in units if not u[2]]
            vy = min(hang_value_1(s, u) for u in hums) if hums else vx
        else:
            ys = [(w - (1 if u == ux else 0), u) for w, u in units]
            ys = [(w, u) for w, u in ys if w > 0]
            ty = sum(w for w, _ in ys)
            vy = sum(F(1) * w / ty * hang_value_1(s, u, mark=rx if u[2] else None) for w, u in ys) if ty else vx
        v += F(1) * wx / tot * (p * vx + (1 - p) * vy)
    return v

# nwv：狼は身内（仲間の狼）に投票しない。自由投票の日、村人・狂人は候補（自分以外）から無作為に、狼は候補の人間から無作為に投票し、
# 吊られる確率は集まると見込まれる票の数に比例するとする。units の重み（人数）を、1人あたりの見込み票数を掛けたものに変える
def vote_units(s, units):
    ph, slots, meds, T, TM, cats, last, nt, bel = s
    if POL.get('lot') and designator(s) is None: return units   # 乱数吊り：候補から等確率
    if not POL.get('nwv') or designator(s) is not None or len(units) < 2: return units
    def is_w(t):
        return (t[0] == 'c' and t[2]) or (t[0] == 's' and slots[t[1]][0]) or (t[0] == 'm' and meds[t[1]][0])
    C = sum(w for w, _ in units)
    WC = sum(w for w, t in units if is_w(t)); HC = C - WC
    nw, n = counts(slots, meds, cats); nh = n - nw
    if C < 2: return units
    if HC == 0: return units
    if POL.get('plur'):   # 多数決（最多票を吊る・同票はランダム）
        from plurx import plurality
        vh, vw = plurality(HC, WC, nh - HC, nw)
        return [(w * (vw if is_w(t) else vh), t) for w, t in units]
    # 1人あたりの見込み票数
    vh = (HC - 1) / (C - 1) + (nh - HC) / C + nw / HC      # 人間の候補
    vw = HC / (C - 1) + (nh - HC) / C                      # 狼の候補（狼からは入らない）
    return [(w * (vw if is_w(t) else vh), t) for w, t in units]

# bloc：自由投票（指定役がいない日）のとき、確率 bloc で狼の身内票が通り、狼が人間の中から吊り先を選ぶ。
# 身内票が効く日なら、狼が選べる吊り先（人間）を返す。効かない日は空
def bloc_humans(s, units):
    ph, slots, meds, T, TM, cats, last, nt, bel = s
    if POL.get('lot'): return []
    if POL.get('bloc', 0) <= 0 or designator(s) is not None or len(units) < 2: return []
    return [u for u in units if not ((u[1][0] == 'c' and u[1][2]) or (u[1][0] == 's' and slots[u[1][1]][0]) or (u[1][0] == 'm' and meds[u[1][1]][0]))]

# ---------------------------------------------------------------- 値
# 局面そのものではなく hash だけを鍵にして覚える（メモリ節約。64bit hash の衝突は無視できる程度）
_VC = {}
HKEY = [False]   # True なら局面の hash だけを鍵にする（メモリ節約）。既定は局面そのもの
def V(s):
    h = hash(s) if HKEY[0] else s
    v = _VC.get(h)
    if v is None:
        ph, slots, meds, T, TM, cats, last, nt, bel = s
        t = term(slots, meds, cats)
        v = t if t is not None else (day_value(s) if ph == 'D' else night_value(s))
        if isinstance(v, float): raise TypeError(f'float が混ざった: {s[0]} nt={s[7]}')
        _VC[h] = v
    return v
V.cache_clear = _VC.clear

# ---------------------------------------------------------------- 初期状態
def initial(dummy, fs, fm):
    """dummy: 初日犠牲者 'S' 'M' 'H' 'm' 'V'。fs/fm: 占い/霊能を騙る狼の数（0/1）"""
    slots = []
    if dummy != 'S': slots.append((0, 1, 0))
    if dummy != 'm': slots.append((0, 1, 0))
    slots += [(1, 1, 0)] * fs
    meds = ([(0, 1, 0)] if dummy != 'M' else []) + [(1, 1, 0)] * fm
    ns = len(slots)
    r0 = (0,) * ns
    gw = 3 - fs - fm
    gh = 11 - ns - len(meds) - gw
    H = r0 if dummy != 'H' else None
    bel = {}
    nonw = [i for i, x in enumerate(slots) if not x[0]]
    if dummy == 'S': bel[(-1, nonw[0], H, r0)] = F(1)
    elif dummy == 'm': bel[(nonw[0], -1, H, r0)] = F(1)
    else:
        bel[(nonw[0], nonw[1], H, r0)] = F(1, 2)
        bel[(nonw[1], nonw[0], H, r0)] = F(1, 2)
    return ('N', tuple(slots), tuple(meds), -1, -1, ((r0, gw, gh),), None, 0, norm_bel(bel))

def value(dummy, fs, fm):
    return V(initial(dummy, fs, fm))

def initial_mix(dummies, fs, fm):
    """同じ盤面・同じ騙り方になる初日犠牲者の候補 [(dummy, 重み)] をまとめた1つのゲーム（狼は初日犠牲者の役職を知らない）"""
    sts = [(initial(d, fs, fm), w) for d, w in dummies]
    base = sts[0][0]
    for s, w in sts: assert s[:8] == base[:8], 'visible structure differs'
    tot = sum(w for _, w in sts)
    bel = {}
    for s, w in sts:
        for k, p in s[8]: bel[k] = bel.get(k, 0) + p * w / tot
    return base[:8] + (norm_bel(bel),)


# ---------------------------------------------------------------- 1-1 の内訳
NAIWAKE = {
    'TT_d': '真-真（狂欠け）',
    'TT_h': '真-真',
    'MT':   '狂-真',
    'WT':   '狼-真',
    'TM':   '真-狂',
    'TW':   '真-狼',
}
GROUP = ('TT_d', 'TT_h', 'MT', 'TM')   # 狼が誰も騙らないときの内訳（狼には見分けがつかない）

def initial_group(weights):
    """weights: {内訳: 重み}（GROUP の中）。狼は内訳を知らない1つのゲーム。belief の5番目の要素が内訳の目印"""
    tot = sum(weights.values())
    base = None; bel = {}
    for key, w in weights.items():
        if w <= 0: continue
        s = initial11(key)
        if base is None: base = s[:8]
        assert s[:8] == base, key
        for k, p in s[8]: bel[k + (key,)] = bel.get(k + (key,), 0) + p * w / tot
    MADMED[0] = 0
    return base + (norm_bel(bel),)

def initial11(key, tag=False):
    """1-1 の内訳ごとの初期状態（11人、初日の夜）。狼は内訳を知っている。"""
    r0 = (0,)
    S_, W_ = (0, 1, 0), (1, 1, 0)
    MADMED[0] = -1
    if key == 'TT_d':
        slots, meds, gw = (S_,), (S_,), 3
        bel = {(0, -1, r0, r0): F(1)}
    elif key == 'TT_h':   # 初日犠牲は狩人（1/8）か村人（1/2）
        slots, meds, gw = (S_,), (S_,), 3
        bel = {(0, r0, None, r0): 0.2, (0, r0, r0, r0): 0.8}
    elif key == 'MT':
        slots, meds, gw = (S_,), (S_,), 3
        bel = {(-1, 0, r0, r0): F(1)}
    elif key == 'WT':
        slots, meds, gw = (W_,), (S_,), 2
        bel = {(-1, r0, r0, r0): F(1)}
    elif key == 'TM':
        slots, meds, gw = (S_,), (S_,), 3
        MADMED[0] = 0
        bel = {(0, -2, r0, r0): F(1)}
    elif key == 'TW':
        slots, meds, gw = (S_,), (W_,), 2
        bel = {(0, r0, r0, r0): F(1)}
    gh = 11 - 2 - gw
    if tag: bel = {k + (key,): p for k, p in bel.items()}
    MADMED[0] = 0
    return ('N', slots, meds, -1, -1, ((r0, gw, gh),), None, 0, norm_bel(bel))

# ---------------------------------------------------------------- 内訳ごとの勝率（まとめたゲームの中で）
# 狼は内訳を知らずに V（まとめた値）を最小にする手を選ぶ。その手のまま、実際の内訳が tag だったときの村勝率を求める。
# 同じ値の手が複数あるときは、並び順で最初のものを選ぶ（ツリーと同じ）。
TIE = 1e-12

def tag_mass(bel):
    m = {}
    for k, p in bel:
        if len(k) > 4: m[k[4]] = m.get(k[4], 0) + p
    return m

def combine(s, outs, sub):
    """outs: [(prob, child_state)] ; sub(child) -> {tag: value}"""
    m = tag_mass(s[8]); res = {t: F(0) for t in m}
    for p, c in outs:
        mc = tag_mass(c[8]); vc = sub(c)
        for t, x in mc.items():
            if t in res and m[t] > 0: res[t] += p * x / m[t] * vc[t]
    return res

@lru_cache(None)
def VT(s):
    ph, slots, meds, T, TM, cats, last, nt, bel = s
    t = term(slots, meds, cats)
    if t is not None: return {g: t for g in tag_mass(bel)}
    if ph == 'D':
        res = {}
        for p, tt, mm_ in trust_choices(s):
            r = DAT((ph, slots, meds, tt, mm_, cats, last, nt, bel))
            for g, v in r.items(): res[g] = res.get(g, 0) + p * v
        return res
    bites, fakes, reps = night_options(s)
    import itertools
    best = None; bestv = None
    for bite in bites:
        for fk in (itertools.product(*fakes) if fakes else [()]):
            for rep in reps:
                outs = night_outcomes(s, bite, fk, rep)
                v = sum(p * V(c) for p, c in outs)
                if bestv is None or v < bestv - TIE: best, bestv = outs, v
    return combine(s, best, VT)

def DAT(s):
    ph, slots, meds, T, TM, cats, last, nt, bel = s
    w, n = counts(slots, meds, cats)
    if n >= 5 and 2 * (w + 1) >= n:
        pm = sum(p for k, p in bel if mad_alive(k[1], slots, meds))
        if pm > 0:
            m = tag_mass(bel)
            dy = {k: p for k, p in bel if mad_alive(k[1], slots, meds)}
            dn = {k: p for k, p in bel if not mad_alive(k[1], slots, meds)}
            my = tag_mass(norm_bel(dy)); mn = tag_mass(norm_bel(dn)) if dn else {}
            vy = {g: F(0) for g in my} if 2 * (w + 1) > n else {g: F(1, 2) * v for g, v in HV(s[:8] + (norm_bel(dy),)).items()}
            vn = HV(s[:8] + (norm_bel(dn),)) if dn else {}
            res = {}
            for g in m:
                res[g] = (pm * my.get(g, 0) * vy.get(g, 0) + (1 - pm) * mn.get(g, 0) * vn.get(g, 0)) / m[g]
            return res
    return HV(s)

def HV(s):
    ph, slots, meds, T, TM, cats, last, nt, bel = s
    cand = hang_candidates(s)
    cd = {r: (w, h) for r, w, h in cats}
    units = []
    for c in cand:
        if c[0] == 'c':
            w, h = cd[c[1]]
            if w: units.append((w, ('c', c[1], True)))
            if h: units.append((h, ('c', c[1], False)))
        else: units.append((1, c))
    if designator(s) == 'w':
        hum = [u for u in units if not ((u[1][0] == 'c' and u[1][2]) or (u[1][0] == 's' and slots[u[1][1]][0]) or (u[1][0] == 'm' and meds[u[1][1]][0]))]
        best = None; bestv = None
        for u in (hum or units):
            outs = hang_outcomes(s, [(1, u[1])])
            v = sum(p * V(c) for p, c in outs)
            if bestv is None or v < bestv - TIE: best, bestv = outs, v
        return combine(s, best, VT)
    rnd = combine(s, hang_outcomes(s, vote_units(s, units)), VT)
    hum = bloc_humans(s, units)
    if hum:
        b = POL['bloc']; best = None; bestv = None
        for u in hum:
            outs = hang_outcomes(s, [(1, u[1])])
            v = sum(p * V(c) for p, c in outs)
            if bestv is None or v < bestv - TIE: best, bestv = outs, v
        w = combine(s, best, VT)
        return {g: (1 - b) * rnd[g] + b * w.get(g, 0) for g in rnd}
    return rnd

_setpol_old = setpol
def setpol(**kw):
    _setpol_old(**kw)
    VT.cache_clear()


# ---------------------------------------------------------------- 0-2 の内訳
# 0-2 になるのは、初日犠牲者が本物の占い師のときだけ。
#   'M2'：霊能CO者が 本物・狂人（狼は騙らない。狂人がどちらかは狼も知らない）
#   'W2'：霊能CO者が 本物・狼（狂人は灰に潜伏）
NAIWAKE02 = {'M2': '真-狂', 'W2': '真-狼'}

def initial02(key):
    r0 = ()
    S_, W_ = (0, 1, 0), (1, 1, 0)
    MADMED[0] = -1
    if key == 'M2':
        meds, gw = (S_, S_), 3
        bel = {(-1, -10, r0, r0): F(1, 2), (-1, -11, r0, r0): F(1, 2)}
    else:
        meds, gw = (S_, W_), 2
        bel = {(-1, r0, r0, r0): F(1)}
    gh = 11 - 2 - gw
    return ('N', (), meds, -1, -1, ((r0, gw, gh),), None, 0, norm_bel(bel))
