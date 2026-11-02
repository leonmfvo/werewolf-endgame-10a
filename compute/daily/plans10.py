# 10a狩：村の進め方の候補。12A猫（plans.py）と同じ考え方に、本物の占い師の占い先（div）を加えたもの。
#   des：吊りに指定する区分の順（1番目と2番目を選び、残りは決まった順）／ counter：本物のCO者は対抗に入れる／ mode：指定するか各自ランダムか
#   guard：護衛する区分（1番目を選ぶ）／ co：GJの翌朝に狩人がCOするか／ div：本物の占い師が占う区分（1番目を選ぶ。まだ自分が占っていない人から）
import itertools
from game10 import parse, label_key, is_alive_label

def candidates(labels):
    alive = [l for l in labels if is_alive_label(l)]
    present = sorted(set(alive), key=label_key)
    kinds = [parse(l)['kind'] for l in alive]
    des_orders = []
    for a in present:
        for b in [x for x in present if x != a] or [None]:
            des_orders.append(tuple([a] + ([b] if b else []) + [x for x in present if x not in (a, b)]))
    big = len(alive) >= 4
    guard_orders = [tuple([a] + [x for x in present if x != a]) for a in present] if big else [tuple(present)]
    has_counter = any(kinds.count(k) >= 2 for k in ('占', '霊', '狩'))
    seer_alive = '占' in kinds
    nonco = [l for l in present if parse(l)['kind'] in ('', '確白')]
    div_orders = [tuple([a] + [x for x in nonco if x != a]) for a in nonco] if (seer_alive and big and nonco) else [tuple(nonco)]
    out = []
    for des in des_orders:
        for counter in ((True, False) if has_counter else (False,)):
            for guard in guard_orders:
                for co in ((True, False) if big else (True,)):
                    for mode in ('designate', 'spread'):
                        for div in div_orders:
                            out.append(dict(des=des, counter=counter, guard=guard, co=co, mode=mode, div=div))
    return out
