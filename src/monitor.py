#!/usr/bin/env python3
import json, os, re, hashlib, time
from datetime import datetime
import requests

SC_SENDKEY = os.environ.get("SC_SENDKEY", "")
SNAPSHOT_FILE = os.path.join(os.path.dirname(__file__), "snapshot.json")
TARGET_URL = "https://i2.y.qq.com/n3/cm/pages/vip/freevip/v2/index.html";
ACTIVITY_URL = "https://y.qq.com/portal/vipportal/activity.html";
MONITOR_URLS = [TARGET_URL, ACTIVITY_URL]
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "zh-CN,zh;q=0.9",
    "Referer": "https://y.qq.com/";
}
KEYWORDS = ["免费","0元","限时","领绿钻","领会员","体验卡","兑换","积分","赠送","0.01元","特惠","全球通","联通","电信","移动","招行","平安","开卡","联名","京东"]
EXCLUDE_KEYWORDS = ["隐私政策","应用权限","介绍"]


def fetch_page(url, timeout=15):
    try:
        resp = requests.get(url, headers=HEADERS, timeout=timeout)
        resp.encoding = resp.apparent_encoding or "utf-8"
        if resp.status_code == 200:
            return resp.text
        print(f"[!] HTTP {resp.status_code} for {url}")
        return None
    except Exception as e:
        print(f"[!] 请求失败 {url}: {e}")
        return None


def clean_text(text):
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def extract_activities(html, source_url):
    activities = []
    seen = set()
    plain_text = clean_text(html)
    patterns = [
        r'"title"\s*:\s*"([^"]+)"',
        r'"name"\s*:\s*"([^"]+)"',
        r'"text"\s*:\s*"([^"]+)"',
        r'"label"\s*:\s*"([^"]+)"',
        r'"activityName"\s*:\s*"([^"]+)"',
        r'title="([^"]+)"',
        r'>([^<]{2,50})<',
    ]
    for pattern in patterns:
        matches = re.findall(pattern, html)
        for match in matches:
            text = clean_text(match) if isinstance(match, str) else clean_text(match[0])
            if not text or len(text) < 2:
                continue
            if not any(kw in text for kw in KEYWORDS):
                continue
            if any(ex in text for ex in EXCLUDE_KEYWORDS):
                continue
            key = text[:25]
            if key in seen:
                continue
            seen.add(key)
            activities.append({"title": text, "source": source_url})
    return activities


def load_snapshot():
    if os.path.exists(SNAPSHOT_FILE):
        try:
            with open(SNAPSHOT_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_snapshot(snapshot):
    with open(SNAPSHOT_FILE, "w", encoding="utf-8") as f:
        json.dump(snapshot, f, ensure_ascii=False, indent=2)


def compute_hash(activities):
    text = json.dumps(activities, sort_keys=True, ensure_ascii=False)
    return hashlib.md5(text.encode()).hexdigest()


def send_serverchan(title, content):
    if not SC_SENDKEY:
        print("[!] 未配置 SC_SENDKEY，跳过推送")
        return False
    if SC_SENDKEY.startswith("http"):
        url = SC_SENDKEY
    else:
        url = f"https://sctapi.ftqq.com/{SC_SENDKEY}.send"
    try:
        resp = requests.post(url, data={"title": title, "desp": content}, timeout=10)
        result = resp.json()
        if result.get("code") == 0:
            print("[✓] Server酱推送成功")
            return True
        else:
            print(f"[!] Server酱推送失败: {result}")
            return False
    except Exception as e:
        print(f"[!] Server酱推送异常: {e}")
        return False


def format_notification(new_activities, all_activities):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = [
        f"## QQ音乐免费会员活动监控\n",
        f"**检测时间**: {now}\n",
        f"**当前活动总数**: {len(all_activities)} 个\n",
        f"**新增活动**: {len(new_activities)} 个\n\n",
    ]
    if new_activities:
        lines.append("### 🆕 新增活动\n")
        for i, act in enumerate(new_activities, 1):
            lines.append(f"**{i}. {act['title']}**\n")
            lines.append(f"   - 领取入口: [点击前往]({act['source']})\n\n")
    lines.append("---\n### 📋 当前全部免费活动\n\n")
    lines.append("| 序号 | 活动名称 | 领取入口 |\n|------|---------|----------|\n")
    for i, act in enumerate(all_activities, 1):
        lines.append(f"| {i} | {act['title']} | [前往领取]({act['source']}) |\n")
    lines.append(f"\n---\n💡 点击领取入口前往QQ音乐活动页，用你自己的QQ/微信登录后即可领取。\n⏰ 每6小时自动巡检一次\n")
    return "".join(lines)


def main():
    print(f"=== QQ音乐免费会员活动监控 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===\n")
    all_activities = []
    for url in MONITOR_URLS:
        print(f"[+] 抓取: {url}")
        html = fetch_page(url)
        if html:
            acts = extract_activities(html, url)
            print(f"    提取到 {len(acts)} 个活动")
            all_activities.extend(acts)
        else:
            print("    抓取失败")
        time.sleep(1)

    seen_titles = set()
    unique_activities = []
    for act in all_activities:
        key = act["title"][:25]
        if key not in seen_titles:
            seen_titles.add(key)
            unique_activities.append(act)
    print(f"\n[+] 去重后活动总数: {len(unique_activities)}")

    if not unique_activities:
        print("[!] 未提取到任何活动，跳过本次推送")
        return

    old_snapshot = load_snapshot()
    old_hash = old_snapshot.get("hash", "")
    new_hash = compute_hash(unique_activities)

    if new_hash == old_hash:
        print("[✓] 活动无变化，跳过推送")
        for act in unique_activities:
            print(f"  - {act['title']}")
        return

    old_titles = set()
    if "activities" in old_snapshot:
        for act in old_snapshot["activities"]:
            old_titles.add(act["title"][:25])
    new_activities = []
    for act in unique_activities:
        if act["title"][:25] not in old_titles:
            new_activities.append(act)
    print(f"[+] 新增活动: {len(new_activities)} 个")
    for act in new_activities:
        print(f"  🆕 {act['title']}")

    content = format_notification(new_activities, unique_activities)
    if new_activities:
        title = f"QQ音乐发现 {len(new_activities)} 个新免费活动！"
    elif not old_snapshot:
        title = f"QQ音乐免费会员活动监控已启动（共{len(unique_activities)}个活动）"
    else:
        title = "QQ音乐免费活动有更新"
    send_serverchan(title, content)
    save_snapshot({"hash": new_hash, "activities": unique_activities, "last_check": datetime.now().isoformat()})
    print(f"\n[✓] 本次检测完成，快照已保存")


if __name__ == "__main__":
    main()
