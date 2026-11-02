# 日ごとに解く（辞書方式）で、人数ごとの全盤面を解く。辞書は data/dict.json にためて次回も使う
import sys, json, time, os
from fractions import Fraction as F
import daily as D

PATH = os.environ.get('DICT_PATH') or os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'dict.json')   # 長い計算中は DICT_PATH（git管理外）に保存し、終わってから dict.json へ

def load():
    if os.path.exists(PATH):
        for k, v, info in json.load(open(PATH)):
            key = (tuple(k[0]), tuple((tuple(a), tuple(b), c) for a, b, c in k[1]))
            D.DICT[key] = F(v)
            if info: D.INFO[key] = info

def save():
    out = [[[list(k[0]), [[list(a), list(b), c] for a, b, c in k[1]]], str(v), D.INFO.get(k)] for k, v in D.DICT.items()]
    json.dump(out, open(PATH + '.tmp', 'w'), ensure_ascii=False); os.replace(PATH + '.tmp', PATH)

def board_list(n):
    import boards10
    return boards10.load().get(n, [])

if __name__ == '__main__':
    load()
    D.SAVE_HOOK = save; D.LAST_SAVE = time.time()
    for n in map(int, sys.argv[1:]):
        res = {}
        sel = os.environ.get('PART')   # 並行して解くとき：'k/m/s' なら s 番目以降の盤面のうち、番号を m で割った余りが k のものだけ
        bl = [b for b in board_list(n) if D.GM.worlds(b)]
        if sel and n >= 5:
            k, m, s0 = map(int, sel.split('/'))
            bl = [b for i, b in enumerate(bl) if i >= s0 and (i - s0) % m == k]
        if os.environ.get('BOARDS'):   # 解く盤面を直接指定（'霊,霊,灰,灰,灰;…'）
            bl = [x.split(',') for x in os.environ['BOARDS'].split(';')]; sel = sel or 'list'
        for b in bl:
            res[','.join(b)] = {}
            for si, (sit, k) in enumerate(D.board_keys(b).items()):   # 生存状況ごと（全員が知っている）
                if os.environ.get('SIT') and si != int(os.environ['SIT']): continue   # 並行して解くとき：この番号の生存状況だけ
                t = time.time(); v = D.value(k)
                res[','.join(b)][sit] = str(v)
                print(n, ','.join(b), sit, v, f'{float(v) * 100:.1f}%', round(time.time() - t, 1), 's', len(D.DICT), 'states', flush=True)
            save()
        if not sel: json.dump(res, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', f'daily{n}.json'), 'w'), ensure_ascii=False)
