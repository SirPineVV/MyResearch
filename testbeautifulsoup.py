# scrape_iros25.py
import requests
from bs4 import BeautifulSoup
import csv
import json
import time
import re

BASE = "https://ras.papercept.net/conferences/conferences/IROS25/program/"
PAGES = [
    "IROS25_ContentListWeb_1.html",
    "IROS25_ContentListWeb_2.html",
    "IROS25_ContentListWeb_3.html",
    # 如果还有更多页，继续添加
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
}

def fetch(url, max_retries=3, backoff=1.0):
    for i in range(max_retries):
        try:
            r = requests.get(url, headers=HEADERS, timeout=15)
            r.raise_for_status()
            r.encoding = r.apparent_encoding  # 尝试修正编码问题
            return r.text
        except Exception as e:
            print(f"fetch error ({i+1}/{max_retries}) for {url}: {e}")
            time.sleep(backoff * (i+1))
    return None

def parse_page(html):
    soup = BeautifulSoup(html, "html.parser")
    rows = []

    for a in soup.find_all("a", onclick=True):
        onclick = a.get("onclick", "")
        m = re.search(r"viewAbstract\('(\d+)'\)", onclick)
        if not m:
            continue
        abs_id = m.group(1)
        title = a.get_text(strip=True)

        # 寻找作者
        # 找到这个链接 a 的最近 li 或 div 父节点（包含这一条论文记录）
        container = a
        for _ in range(3):  # 向上最多三级父节点
            if container.name in ("li", "div"):
                break
            container = container.parent

        author_list = []
        if container:
            for aa in container.find_all("a", href=True):
                href = aa["href"]
                if "IROS25_AuthorIndexWeb.html" in href:
                    author_list.append(aa.get_text(strip=True))

        # 摘要 / 关键词
        abstract_text = ""
        keyword_list = []
        pid = f"Ab{abs_id}"
        div = soup.find("div", id=pid)
        if div:
            full = div.get_text(" ", strip=True)
            abstract_text = full
            # 提取 Keywords
            # 比如 div 里有 <strong>Keywords:</strong> 然后是 a 标签
            for ka in div.find_all("a", href=True):
                if "KeywordIndexWeb" in ka["href"]:
                    keyword_list.append(ka.get_text(strip=True))
        else:
            # 如果没找到 div，可以考虑其他策略
            pass

        rows.append({
            "abs_id": abs_id,
            "title": title,
            "authors": author_list,
            "keywords": keyword_list,
            "abstract": abstract_text,
        })

    return rows

def main():
    all_rows = []
    for page in PAGES:
        url = BASE + page
        print("Fetching", url)
        html = fetch(url)
        if not html:
            print("Failed to fetch", url)
            continue
        rows = parse_page(html)
        print(f"Found {len(rows)} entries on {page}")
        all_rows.extend(rows)
        time.sleep(1.0)  # 抓取间隔，礼貌访问

    # 保存 CSV
    csvfile = "iros25_papers.csv"
    keys = ["abs_id", "title", "authors", "keywords", "abstract"]
    with open(csvfile, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        for r in all_rows:
            writer.writerow({
                "abs_id": r["abs_id"],
                "title": r["title"],
                "authors": "; ".join(r["authors"]),
                "keywords": "; ".join(r["keywords"]),
                "abstract": r["abstract"]
            })
    # 保存 JSON
    with open("iros25_papers.json", "w", encoding="utf-8") as f:
        json.dump(all_rows, f, ensure_ascii=False, indent=2)

    print(f"Saved {len(all_rows)} records to {csvfile} and iros25_papers.json")

if __name__ == "__main__":
    main()
