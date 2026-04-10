#!/usr/bin/env python3
import argparse, csv, random, re
from collections import deque
from urllib.parse import urljoin, urlparse
import requests
from bs4 import BeautifulSoup

OLD_BASE = "https://robinlovelace.net/old-site/"
NEW_BASE = "https://robinlovelace.net/"
SKIP_PREFIXES = (
    "/old-site/category/",
)
SKIP_EXACT = {
    "/old-site/", "/old-site/post/", "/old-site/publication/", "/old-site/talk/", "/old-site/event/", "/old-site/software"
}


def crawl_old_site(limit=2000):
    seen = set()
    pages = set()
    q = deque([OLD_BASE])
    s = requests.Session()
    while q and len(seen) < limit:
        u = q.popleft()
        if u in seen:
            continue
        seen.add(u)
        try:
            r = s.get(u, timeout=20)
            if r.status_code != 200:
                continue
        except Exception:
            continue
        soup = BeautifulSoup(r.text, "html.parser")
        p = urlparse(u).path
        if p.startswith("/old-site/") and p.endswith("/") and p not in SKIP_EXACT and not any(p.startswith(x) for x in SKIP_PREFIXES):
            pages.add(u)
        for a in soup.select("a[href]"):
            v = urljoin(u, a["href"]).split("#", 1)[0]
            if not v.startswith(OLD_BASE):
                continue
            pp = urlparse(v).path.lower()
            if any(pp.endswith(ext) for ext in (".css", ".js", ".png", ".jpg", ".jpeg", ".gif", ".svg", ".xml", ".pdf", ".zip")):
                continue
            if v not in seen:
                q.append(v)
    return sorted(pages)


def load_new_urls():
    xml = requests.get(urljoin(NEW_BASE, "sitemap.xml"), timeout=20).text
    soup = BeautifulSoup(xml, "xml")
    return [x.text.strip() for x in soup.find_all("loc")]


def load_redirects(path):
    exact = {}
    wildcard = []
    with open(path) as f:
        for line in f:
            line=line.strip()
            if not line or line.startswith("#"):
                continue
            bits = line.split()
            if len(bits) >= 2 and bits[0].startswith("/old-site/"):
                src, tgt = bits[0], bits[1]
                if "*" in src:
                    wildcard.append((src, tgt))
                else:
                    exact[src] = tgt
    return exact, wildcard


def match_redirect(path, redirects_exact, redirects_wild):
    if path in redirects_exact:
        return redirects_exact[path]
    for pat, tgt in redirects_wild:
        prefix = pat.split("*", 1)[0]
        if path.startswith(prefix):
            return tgt
    return ""


def old_type(u):
    parts = urlparse(u).path.strip("/").split("/")
    return parts[1] if len(parts) > 1 else "unknown"


def slug(u):
    return urlparse(u).path.strip("/").split("/")[-1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample", type=int, default=100)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--redirects", default="_redirects")
    ap.add_argument("--out", default="coverage-sample.csv")
    args = ap.parse_args()

    old_pages = crawl_old_site()
    random.seed(args.seed)
    sample = random.sample(old_pages, min(args.sample, len(old_pages)))
    new_urls = load_new_urls()
    redirects_exact, redirects_wild = load_redirects(args.redirects)

    rows = []
    for u in sample:
        path = urlparse(u).path
        s = slug(u)
        exact = [n for n in new_urls if f"/{s}/" in n or n.rstrip("/").endswith("/" + s)]
        red = match_redirect(path, redirects_exact, redirects_wild)
        present = bool(exact) or bool(red)
        rows.append({
            "old_url": u,
            "type": old_type(u),
            "slug": s,
            "present": "yes" if present else "no",
            "matched_new_url": exact[0] if exact else "",
            "redirect_target": red,
        })

    with open(args.out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    total = len(rows)
    ok = sum(r["present"] == "yes" for r in rows)
    print(f"sample={total} present={ok} missing={total-ok} coverage={ok/total:.1%}")
    by = {}
    for r in rows:
        by.setdefault(r["type"], [0,0])
        by[r["type"]][0]+=1
        by[r["type"]][1]+= (1 if r["present"]=="yes" else 0)
    for k,(t,p) in sorted(by.items()):
        print(f"{k}: {p}/{t}")


if __name__ == "__main__":
    main()
