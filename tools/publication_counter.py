#!/usr/bin/env python3
"""Count a researcher's publications by year from public profile pages.

This utility intentionally reports each source separately. Adding Google Scholar
and ResearchGate counts would double count most of the same publications.
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import json
import os
import re
import sys
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

YEAR_RE = re.compile(r"(?<!\d)(?:19|20)\d{2}(?!\d)")


@dataclass
class SourceResult:
    source: str
    url: str
    profile_name: str
    counts: dict[int, int]
    items_seen: int
    items_without_year: int
    warning: str | None = None

    def interval_total(self, start_year: int, end_year: int) -> int:
        return sum(value for year, value in self.counts.items() if start_year <= year <= end_year)


def classify_url(url: str) -> str:
    host = (urlparse(url).hostname or "").lower()
    if host.startswith("scholar.google.") or ".scholar.google." in host:
        return "google_scholar"
    if host == "researchgate.net" or host.endswith(".researchgate.net"):
        return "researchgate"
    raise ValueError(f"不支持的网址：{url}")


def scholar_page_url(url: str, start: int) -> str:
    parsed = urlparse(url)
    query = parse_qs(parsed.query, keep_blank_values=True)
    query["cstart"] = [str(start)]
    query["pagesize"] = ["100"]
    return urlunparse(parsed._replace(query=urlencode(query, doseq=True)))


async def page_text(page: Any, selector: str) -> str:
    locator = page.locator(selector).first
    return (await locator.inner_text()).strip() if await locator.count() else ""


async def scrape_google_scholar(page: Any, url: str, delay: float) -> SourceResult:
    counts: Counter[int] = Counter()
    seen: set[str] = set()
    missing = 0
    name = ""
    warning = None

    for start in range(0, 10000, 100):
        await page.goto(scholar_page_url(url, start), wait_until="domcontentloaded")
        await page.wait_for_timeout(int(delay * 1000))
        if not name:
            name = await page_text(page, "#gsc_prf_in")
        body = await page.locator("body").inner_text()
        if "not a robot" in body.lower() or "异常流量" in body:
            raise RuntimeError("Google Scholar 要求人机验证；请稍后重试、降低频率或使用 --headed 手动验证。")

        rows = page.locator("tr.gsc_a_tr")
        row_count = await rows.count()
        if row_count == 0:
            break
        new_items = 0
        for index in range(row_count):
            row = rows.nth(index)
            title_link = row.locator("a.gsc_a_at").first
            title = (await title_link.inner_text()).strip() if await title_link.count() else ""
            href = await title_link.get_attribute("href") if await title_link.count() else None
            key = href or title
            if not key or key in seen:
                continue
            seen.add(key)
            new_items += 1
            year_text = await page_text(row, ".gsc_a_y")
            match = YEAR_RE.search(year_text)
            if match:
                counts[int(match.group())] += 1
            else:
                missing += 1
        if new_items == 0 or row_count < 100:
            break

    if not seen:
        warning = "未发现论文。主页可能不是公开作者主页，或页面结构已经变化。"
    return SourceResult("google_scholar", url, name, dict(sorted(counts.items())), len(seen), missing, warning)


async def load_cookies(context: Any, cookie_file: Path) -> None:
    raw = json.loads(cookie_file.read_text(encoding="utf-8"))
    cookies = raw.get("cookies", raw) if isinstance(raw, dict) else raw
    if not isinstance(cookies, list):
        raise ValueError("cookie 文件应为 Playwright storage_state 或 cookie 数组。")
    allowed = {"name", "value", "domain", "path", "expires", "httpOnly", "secure", "sameSite", "url"}
    await context.add_cookies([{k: v for k, v in cookie.items() if k in allowed} for cookie in cookies])


async def scrape_researchgate(page: Any, url: str, delay: float, max_scrolls: int, headed: bool = False) -> SourceResult:
    parsed = urlparse(url)
    clean_path = parsed.path.rstrip("/")
    if clean_path.endswith("/research"):
        clean_path = clean_path[:-len("/research")]
    research_url = urlunparse(parsed._replace(path=f"{clean_path}/research", query="", fragment=""))
    await page.goto(research_url, wait_until="domcontentloaded")
    await page.wait_for_timeout(int(delay * 1000))
    name = await page_text(page, "h1")
    if not name:
        # Logged-in ResearchGate currently renders the profile name without h1.
        # The stable /profile/<slug> URL is a safer fallback than a CSS class.
        slug = clean_path.split("/profile/", 1)[-1].split("/", 1)[0]
        name = re.sub(r"-\d+$", "", slug).replace("-", " ").strip()
    body = await page.locator("body").inner_text()
    body_lower = body.lower()
    blocked_markers = (
        "log in", "sign up", "security check", "verify you are human",
        "captcha", "访问验证", "安全验证", "人机验证",
    )
    if any(text in body_lower for text in blocked_markers) and "researchgate" in body_lower:
        login_warning = "页面可能受登录限制；若数据不完整，请使用 --cookies。"
    else:
        login_warning = None

    # In headed mode the caller may be completing login/CAPTCHA in the opened
    # browser. Wait for a publication link instead of immediately returning an
    # empty result. The persistent browser profile keeps the successful session.
    if login_warning and headed:
        print("ResearchGate 正在等待登录/验证（最多 5 分钟）…", flush=True)
        for _ in range(150):
            if (await page.locator('a[href*="/publication/"]').count()
                    or await page.locator('time[datetime]').count()):
                login_warning = None
                name = await page_text(page, "h1") or name
                break
            await page.wait_for_timeout(2000)

    # New ResearchGate pages do not necessarily render publication links. Their
    # publication cards do, however, expose a semantic <time datetime="...">
    # element. Keep the legacy URL parser as a fallback for older page variants.
    expected_match = re.search(r"\bResearch\s*\((\d+)\)", body, re.I)
    expected_total = int(expected_match.group(1)) if expected_match else None
    items: dict[str, str] = {}
    dated_items: dict[str, str] = {}
    unchanged = 0
    for _ in range(max_scrolls):
        before = max(len(items), len(dated_items))
        visible_dates = await page.locator(
            'ul.nova-legacy-v-entity-item__meta-data time[datetime]'
        ).evaluate_all("""elements => elements.map((element, index) => {
            const card = element.closest('.nova-legacy-v-entity-item') ||
                         element.closest('[class*="nova-legacy-v-entity-item"]');
            const text = (card?.innerText || element.parentElement?.parentElement?.innerText || '').trim();
            const title = text.split('\\n').find(line => line.trim().length > 8) || `item-${index}`;
            return {date: element.getAttribute('datetime') || '', title: title.slice(0, 300)};
        })""")
        for entry in visible_dates:
            dated_items[f"{entry['date']}|{entry['title']}"] = entry["date"]

        visible_links = await page.locator('a[href*="/publication/"]').evaluate_all(
            "elements => elements.map(a => ({href:(a.getAttribute('href') || '').split('?')[0], text:(a.innerText || '').trim()}))"
        )
        for entry in visible_links:
            if entry["href"]:
                items[entry["href"]] = entry["text"]

        current = max(len(items), len(dated_items))
        if expected_total and current >= expected_total:
            break
        more = page.get_by_role("button", name=re.compile(r"^(show|load) more$", re.I))
        if await more.count():
            try:
                await more.last.click(timeout=1500)
            except Exception:
                pass
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await page.wait_for_timeout(max(250, int(delay * 1000)))
        if current == before:
            unchanged += 1
            if unchanged >= 5:
                break
        else:
            unchanged = 0

    counts: Counter[int] = Counter()
    missing = 0
    date_values = list(dated_items.values())
    if date_values:
        for value in date_values:
            match = YEAR_RE.search(value or "")
            if match:
                counts[int(match.group())] += 1
            else:
                missing += 1
        item_count = len(date_values)
    else:
        for text in items.values():
            years = [int(value) for value in YEAR_RE.findall(text)]
            plausible = [year for year in years if 1900 <= year <= 2100]
            if plausible:
                counts[plausible[0]] += 1
            else:
                missing += 1
        item_count = len(items)
    warning = login_warning
    if not item_count:
        warning = "未发现论文；ResearchGate 可能要求登录，或页面结构已经变化。"
    elif expected_total and item_count < expected_total:
        warning = f"主页显示 {expected_total} 条，但本次加载到 {item_count} 条；可提高最大滚动次数后重试。"
    return SourceResult("researchgate", url, name, dict(sorted(counts.items())), item_count, missing, warning)


def print_report(results: Iterable[SourceResult], start: int, end: int) -> None:
    for result in results:
        print(f"\n来源: {result.source}")
        print(f"学者: {result.profile_name or '未知'}")
        print("年份    论文数")
        for year in range(start, end + 1):
            print(f"{year:<8}{result.counts.get(year, 0)}")
        print(f"{start}–{end} 合计: {result.interval_total(start, end)}")
        print(f"抓取条目: {result.items_seen}；无法识别年份: {result.items_without_year}")
        if result.warning:
            print(f"提示: {result.warning}")


def write_csv(path: Path, results: Iterable[SourceResult], start: int, end: int) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["source", "profile_name", "year", "publication_count"])
        for result in results:
            for year in range(start, end + 1):
                writer.writerow([result.source, result.profile_name, year, result.counts.get(year, 0)])
            writer.writerow([result.source, result.profile_name, f"{start}-{end} total", result.interval_total(start, end)])


async def run(args: argparse.Namespace) -> list[SourceResult]:
    try:
        from playwright.async_api import async_playwright
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "缺少 Playwright。请运行：python -m pip install -r requirements.txt；"
            "然后运行：python -m playwright install chromium"
        ) from exc
    async with async_playwright() as playwright:
        cdp_url = getattr(args, "cdp_url", None)
        connected_browser = None
        if cdp_url:
            try:
                connected_browser = await playwright.chromium.connect_over_cdp(cdp_url)
            except Exception as exc:
                raise RuntimeError(
                    f"无法连接当前 Chrome（{cdp_url}）。请先以远程调试模式启动 Chrome。"
                ) from exc
            if not connected_browser.contexts:
                raise RuntimeError("当前 Chrome 没有可用的浏览器上下文。")
            context = connected_browser.contexts[0]
        else:
            profile_dir = Path(getattr(args, "profile_dir", None) or
                               Path(os.environ.get("LOCALAPPDATA", Path.home())) / "NiuBToolbox" / "scholar_browser_profile")
            context = await playwright.chromium.launch_persistent_context(
                user_data_dir=str(profile_dir),
                headless=not args.headed,
                locale="zh-CN",
                user_agent=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                            "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"),
            )
        if args.cookies:
            await load_cookies(context, args.cookies)
        results: list[SourceResult] = []
        try:
            for url in args.urls:
                page = await context.new_page()
                try:
                    source = classify_url(url)
                    if source == "google_scholar":
                        results.append(await scrape_google_scholar(page, url, args.delay))
                    else:
                        results.append(await scrape_researchgate(
                            page, url, args.delay, args.max_scrolls, args.headed or bool(cdp_url)
                        ))
                finally:
                    await page.close()
        finally:
            # A CDP-connected Chrome belongs to the user and must remain open.
            if not connected_browser:
                await context.close()
        return results


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="统计学者主页中逐年及年份区间内的论文数量")
    parser.add_argument("urls", nargs="+", help="Google Scholar 和/或 ResearchGate 学者主页 URL")
    parser.add_argument("--start-year", type=int, required=True, help="起始年份（含）")
    parser.add_argument("--end-year", type=int, required=True, help="结束年份（含）")
    parser.add_argument("--csv", type=Path, help="将逐年统计写入 CSV")
    parser.add_argument("--json", type=Path, help="将完整结果写入 JSON")
    parser.add_argument("--cookies", type=Path, help="ResearchGate 登录 cookies/storage_state JSON")
    parser.add_argument("--profile-dir", type=Path, help="持久化浏览器配置目录（保存登录和验证状态）")
    parser.add_argument("--cdp-url", help="连接已登录 Chrome，例如 http://127.0.0.1:9222")
    parser.add_argument("--headed", action="store_true", help="显示浏览器窗口，便于手动处理登录/验证")
    parser.add_argument("--delay", type=float, default=0.45, help="翻页/滚动间隔秒数（默认 0.45）")
    parser.add_argument("--max-scrolls", type=int, default=300, help="ResearchGate 最大滚动次数")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if args.start_year > args.end_year:
        parser.error("--start-year 不能大于 --end-year")
    try:
        results = asyncio.run(run(args))
    except (ValueError, RuntimeError, TimeoutError) as exc:
        print(f"错误: {exc}", file=sys.stderr)
        return 2
    print_report(results, args.start_year, args.end_year)
    if args.csv:
        write_csv(args.csv, results, args.start_year, args.end_year)
    if args.json:
        payload = {
            "start_year": args.start_year,
            "end_year": args.end_year,
            "results": [dict(asdict(item), interval_total=item.interval_total(args.start_year, args.end_year)) for item in results],
        }
        args.json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

