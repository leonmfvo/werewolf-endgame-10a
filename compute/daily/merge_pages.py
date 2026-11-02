# 並行して作ったページ（d<n>*.new.json と、その翌日の状態 s<n>*.new.json）を1つにまとめる。
# 翌日の状態の番号はファイルごとに 0 から振ってあるので、後ろのファイルの番号はずらしてつなぐ。同じ盤面は先のファイルを使う
# 使い方：python3 merge_pages.py 5 ../data/d5.json ../data/s5.json d5.new:s5a.new d5b.new:s5b.new d5c.new:s5c.new
import sys, json, os

def shift(paths, off):
    for p in paths:
        if len(p) > 3: p[3] += off

def main():
    n, dout, sout = sys.argv[1], sys.argv[2], sys.argv[3]
    base = os.path.dirname(dout)
    pages, states, seen = [], [], set()
    for pair in sys.argv[4:]:
        dname, sname = pair.split(':')
        d = json.load(open(os.path.join(base, dname + '.json')))
        s = json.load(open(os.path.join(base, sname + '.json')))
        off = len(states)
        for e in s:
            for sec in e['secs']:
                for it in sec['items']: shift(it['paths'], off)
        states += s
        for b in d:
            k = ','.join(b['board'])
            if k in seen: continue
            seen.add(k)
            for sec in b['secs']:
                for it in sec['items']: shift(it['paths'], off)
            pages.append(b)
    json.dump(pages, open(dout, 'w'), ensure_ascii=False, separators=(',', ':'))
    json.dump(states, open(sout, 'w'), ensure_ascii=False, separators=(',', ':'))
    print(len(pages), 'boards', len(states), 'states')

if __name__ == '__main__':
    main()
