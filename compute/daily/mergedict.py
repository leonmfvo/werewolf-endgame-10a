# 並行して解いた辞書（JSON の並び）を1つにまとめる。同じ状態の値は必ず同じ（違えば止まる）
import json, sys
def merge(out, paths):
    seen = {}; res = []
    for p in paths:
        for e in json.load(open(p)):
            k = json.dumps(e[0], ensure_ascii=False)
            if k in seen:
                assert seen[k] == e[1], p; continue
            seen[k] = e[1]; res.append(e)
    json.dump(res, open(out, 'w'), ensure_ascii=False)
    return len(res)
if __name__ == '__main__':
    print(merge(sys.argv[1], sys.argv[2:]))
