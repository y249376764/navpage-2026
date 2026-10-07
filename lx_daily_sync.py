#!/usr/bin/env python3
# 每日同步：抓取音源直通车 → 更新音乐板块 → 推送 GitHub（触发 surge 自动部署）
import re, urllib.parse, urllib.request, json, sys, os, base64

LX_URL = "https://77f77.48364836.xyz/lx/"
GHPROXY = "https://gh-proxy.com/"
REPO = "y249376764/navpage-2026"
TOKEN = os.environ.get("GH_TOKEN", "")

def fetch(url, timeout=30):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    return urllib.request.urlopen(req, timeout=timeout).read().decode('utf-8', 'ignore')

def make_music_block():
    print("① 抓取直通车...")
    h = fetch(LX_URL).replace('\\/', '/')
    links = re.findall(r'https://raw\.githubusercontent\.com/sowahsun/lxmusic-/main/([^"<\s]+\.js)', h)

    seen, items = set(), []
    for l in links:
        parts = l.split('/')
        if len(parts) < 3 or l in seen:
            continue
        seen.add(l)
        items.append({
            "group": parts[1],
            "name": urllib.parse.unquote(parts[-1]),
            "url": GHPROXY + "https://raw.githubusercontent.com/sowahsun/lxmusic-/main/" + l,
        })

    def rank(g):
        if '推荐' in g: return 0
        if '优质' in g: return 1
        if '良好' in g: return 2
        return 3
    items.sort(key=lambda x: (rank(x["group"]), x["name"]))

    picked, seen2 = [], set()
    for it in items:
        if any(k in it["name"] for k in ['停用', '需自行配置', '野花', '野草', 'FreeListen', '春日影']):
            continue
        if it["name"] in seen2:
            continue
        seen2.add(it["name"])
        picked.append(it)
        if len(picked) >= 12:
            break

    html = '<div class="sec">\n  <div class="sec-t">🎵 洛雪音乐音源（每日自动更新 · 精选 {n} 个）</div>\n  <div class="sec-d">复制链接 → 洛雪App「设置 → 自定义源管理 → 在线导入」· 每日自动从音源直通车抓取最新</div>\n'.format(n=len(picked))
    for p in picked:
        html += '  <div class="item">\n    <span class="it-name">{name}</span>\n    <button class="copy-btn" onclick="copyText(this,&#39;{url}&#39;)">复制</button>\n  </div>\n'.format(name=p["name"], url=p["url"])
    html += '</div>'
    print(f"② 精选 {len(picked)} 个音源")
    return html, picked

def replace_block(index_html, new_block):
    import re
    pat = re.compile(r'<div class="sec">\n\s*<div class="sec-t">🎵 洛雪音乐音源.*?(?=\n  <div class="sec">|\n\n  <div class="sec">)', re.S)
    m = pat.search(index_html)
    if not m:
        raise Exception("找不到音乐板块!")
    return index_html[:m.start()] + new_block + index_html[m.end():]

def github_put(path, content_bytes, msg):
    url = f"https://api.github.com/repos/{REPO}/contents/{path}"
    payload = {"message": msg, "content": base64.b64encode(content_bytes).decode()}
    # 已存在的文件必须带 sha（当前版本）
    try:
        url_get = f"https://api.github.com/repos/{REPO}/contents/{path}"
        req_get = urllib.request.Request(url_get, headers={"Authorization": "token " + TOKEN, "Accept": "application/vnd.github+json"})
        data = json.loads(urllib.request.urlopen(req_get, timeout=30).read())
        payload["sha"] = data["sha"]
    except Exception:
        pass  # 新文件无 sha
    req = urllib.request.Request(url, data=json.dumps(payload).encode(),
        headers={"Authorization": "token " + TOKEN, "Accept": "application/vnd.github+json"},
        method="PUT")
    try:
        urllib.request.urlopen(req, timeout=30).read()
        return True
    except Exception as e:
        print(f"✗ 推送失败: {e}")
        return False

def github_get(path):
    url = f"https://api.github.com/repos/{REPO}/contents/{path}"
    req = urllib.request.Request(url, headers={"Authorization": "token " + TOKEN, "Accept": "application/vnd.github+json"})
    data = json.loads(urllib.request.urlopen(req, timeout=30).read())
    return base64.b64decode(data["content"]).decode('utf-8')

def main():
    if not TOKEN:
        print("缺少 GH_TOKEN")
        sys.exit(1)
    block, picked = make_music_block()

    print("③ 拉取当前 index.html（API）...")
    cur = github_get("index.html")
    new_html = replace_block(cur, block)

    if new_html == cur:
        print("无变化，跳过推送")
        return
    print(f"④ 更新 index.html ({len(cur)} -> {len(new_html)} 字节)")
    github_put("index.html", new_html.encode('utf-8'), "每日自动同步音源直通车（音乐板块更新）")
    print("⑤ 完成，GitHub Actions 将自动部署到 surge")

if __name__ == "__main__":
    main()
