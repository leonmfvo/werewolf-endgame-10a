# 終盤表のサイトを site/ に作る：data/states.json（局面 → 村勝率と、吊り先・噛み先ごとの値）と静的ページ
import sys, json, os, shutil
sys.setrecursionlimit(100000)
from endgame import *

OUT = sys.argv[1] if len(sys.argv) > 1 else 'site'

def fr(v): return [v.numerator, v.denominator]

def build():
    os.makedirs(f'{OUT}/data', exist_ok=True)
    S = all_states()
    data = {}
    for c in S:
        k = ''.join(map(str, c))
        d = {'D': [fr(V(('D', c, -1))), {st: fr(v) for st, v in options_day(c).items()}],
             'N': [fr(V(('N', c, -1))), {st: fr(v) for st, v in options_night(c).items()}]}
        data[k] = d
    json.dump(dict(pairs=[list(p) for p in PAIRS], states=data), open(f'{OUT}/data/states.json', 'w'), ensure_ascii=False, separators=(',', ':'))
    for f in os.listdir('static'): shutil.copy(f'static/{f}', f'{OUT}/{f}')   # ページの雛形
    open(f'{OUT}/.nojekyll', 'w').close()
    print('states', len(S), 'bytes', os.path.getsize(f'{OUT}/data/states.json'))

if __name__ == '__main__':
    build()
