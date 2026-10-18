import json, os, time, urllib.request as u, urllib.parse as up
from concurrent.futures import ThreadPoolExecutor, as_completed

for k in list(os.environ):
    if 'PROXY' in k.upper():
        os.environ.pop(k)

MAP_FILE = 'zh_map.json'
FAIL_FILE = 'zh_failed.json'

def translate_one(text, retries=4):
    url = 'https://clients5.google.com/translate_a/t?client=dict-chrome-ex&sl=en&tl=zh-CN&q=' + up.quote(text)
    last = None
    for i in range(retries):
        try:
            req = u.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            data = json.loads(u.urlopen(req, timeout=15).read().decode('utf-8', 'ignore'))
            # clients5: ["译文"] ；googleapis: [[["译文","原文",...]]]
            if isinstance(data, list) and data and isinstance(data[0], str):
                zh = data[0].strip()
            elif isinstance(data, list) and data and isinstance(data[0], list):
                zh = ''.join(s[0] for s in data[0] if isinstance(s, list) and s and isinstance(s[0], str)).strip()
            else:
                zh = ''
            if zh:
                return zh
            last = 'empty'
        except Exception as e:
            last = str(e)[:60]
            time.sleep(1.5 * (i + 1))
    return None

def main():
    tasks = json.load(open('zh_tasks.json', encoding='utf-8'))
    done = {}
    if os.path.exists(MAP_FILE):
        done = json.load(open(MAP_FILE, encoding='utf-8'))
    todo = [x['t'] for x in tasks if x['t'] not in done]
    print(f'总任务 {len(tasks)}  已完成 {len(done)}  本次 {len(todo)}', flush=True)
    if not todo:
        print('全部完成'); return
    t0 = time.time()
    n = 0
    failed = []
    with ThreadPoolExecutor(max_workers=8) as ex:
        futs = {ex.submit(translate_one, t): t for t in todo}
        for fut in as_completed(futs):
            t = futs[fut]
            try:
                zh = fut.result()
            except Exception:
                zh = None
            if zh:
                done[t] = zh
            else:
                failed.append(t)
            n += 1
            if n % 200 == 0:
                json.dump(done, open(MAP_FILE, 'w', encoding='utf-8'), ensure_ascii=False)
                rate = n / max(time.time() - t0, 0.1)
                eta = (len(todo) - n) / max(rate, 0.1) / 60
                print(f'  {n}/{len(todo)}  失败{len(failed)}  {rate:.1f}条/s  剩余约{eta:.1f}分钟', flush=True)
    json.dump(done, open(MAP_FILE, 'w', encoding='utf-8'), ensure_ascii=False)
    json.dump(failed, open(FAIL_FILE, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'DONE 成功 {len(done)}  本次失败 {len(failed)}  耗时 {(time.time()-t0)/60:.1f} 分钟', flush=True)
    if failed[:10]:
        print('失败样例:', failed[:10])

if __name__ == '__main__':
    main()
