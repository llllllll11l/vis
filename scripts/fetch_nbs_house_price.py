#!/usr/bin/env python3
"""Fetch NBS 70-city monthly house price tables into project JSON.

The script parses the first two aggregate tables on each NBS monthly page:
- table 1: new commercial housing price index
- table 2: second-hand housing price index

It intentionally uses only Python standard library modules.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import time
import urllib.request
from collections import defaultdict
from html.parser import HTMLParser
from pathlib import Path


CITY_PROVINCE = {
    "北京": "北京",
    "天津": "天津",
    "石家庄": "河北",
    "唐山": "河北",
    "秦皇岛": "河北",
    "太原": "山西",
    "呼和浩特": "内蒙古",
    "包头": "内蒙古",
    "沈阳": "辽宁",
    "大连": "辽宁",
    "丹东": "辽宁",
    "锦州": "辽宁",
    "长春": "吉林",
    "吉林": "吉林",
    "哈尔滨": "黑龙江",
    "牡丹江": "黑龙江",
    "上海": "上海",
    "南京": "江苏",
    "无锡": "江苏",
    "徐州": "江苏",
    "扬州": "江苏",
    "杭州": "浙江",
    "宁波": "浙江",
    "温州": "浙江",
    "金华": "浙江",
    "合肥": "安徽",
    "蚌埠": "安徽",
    "安庆": "安徽",
    "福州": "福建",
    "厦门": "福建",
    "泉州": "福建",
    "南昌": "江西",
    "九江": "江西",
    "赣州": "江西",
    "济南": "山东",
    "青岛": "山东",
    "烟台": "山东",
    "济宁": "山东",
    "郑州": "河南",
    "洛阳": "河南",
    "平顶山": "河南",
    "武汉": "湖北",
    "宜昌": "湖北",
    "襄阳": "湖北",
    "长沙": "湖南",
    "岳阳": "湖南",
    "常德": "湖南",
    "广州": "广东",
    "深圳": "广东",
    "韶关": "广东",
    "湛江": "广东",
    "惠州": "广东",
    "南宁": "广西",
    "桂林": "广西",
    "北海": "广西",
    "海口": "海南",
    "三亚": "海南",
    "重庆": "重庆",
    "成都": "四川",
    "泸州": "四川",
    "南充": "四川",
    "贵阳": "贵州",
    "遵义": "贵州",
    "昆明": "云南",
    "大理": "云南",
    "西安": "陕西",
    "兰州": "甘肃",
    "西宁": "青海",
    "银川": "宁夏",
    "乌鲁木齐": "新疆",
}


class TableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.tables: list[list[list[str]]] = []
        self._table: list[list[str]] | None = None
        self._row: list[str] | None = None
        self._cell: list[str] | None = None
        self._in_cell = False

    def handle_starttag(self, tag: str, attrs) -> None:
        tag = tag.lower()
        if tag == "table":
            self._table = []
        elif tag == "tr" and self._table is not None:
            self._row = []
        elif tag in {"td", "th"} and self._row is not None:
            self._cell = []
            self._in_cell = True

    def handle_data(self, data: str) -> None:
        if self._in_cell and self._cell is not None:
            self._cell.append(data)

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in {"td", "th"} and self._cell is not None and self._row is not None:
            text = re.sub(r"\s+", " ", "".join(self._cell)).strip()
            self._row.append(text)
            self._cell = None
            self._in_cell = False
        elif tag == "tr" and self._row is not None and self._table is not None:
            if any(cell for cell in self._row):
                self._table.append(self._row)
            self._row = None
        elif tag == "table" and self._table is not None:
            self.tables.append(self._table)
            self._table = None


def normalize_city(value: str) -> str:
    return re.sub(r"\s+", "", value).replace("\u3000", "")


def to_float(value: str) -> float | None:
    value = value.strip()
    if not value or value in {"—", "-", "…"}:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def fetch_text(url: str) -> str:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 data-collection script for academic visualization project"
        },
    )
    raw = urllib.request.urlopen(request, timeout=30).read()
    for encoding in ("utf-8", "gb18030"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="ignore")


def parse_year_month(html: str, fallback_url: str) -> tuple[int, int]:
    match = re.search(r"(\d{4})年\s*(\d{1,2})月份", html)
    if match:
        return int(match.group(1)), int(match.group(2))
    raise ValueError(f"Cannot parse year/month from page: {fallback_url}")


def parse_aggregate_table(table: list[list[str]]) -> dict[str, dict[str, float]]:
    records: dict[str, dict[str, float]] = {}
    for row in table:
        for offset in (0, 4):
            if len(row) <= offset + 2:
                continue
            city = normalize_city(row[offset])
            mom = to_float(row[offset + 1])
            yoy = to_float(row[offset + 2])
            if city in CITY_PROVINCE and mom is not None:
                records[city] = {"mom": mom, "yoy": yoy if yoy is not None else 0.0}
    return records


def parse_page(url: str) -> list[dict]:
    html = fetch_text(url)
    year, month = parse_year_month(html, url)
    parser = TableParser()
    parser.feed(html)

    aggregate_tables = []
    for table in parser.tables:
        records = parse_aggregate_table(table)
        if len(records) >= 60:
            aggregate_tables.append(records)

    if len(aggregate_tables) < 2:
        raise ValueError(f"Cannot find new/second-hand aggregate tables: {url}")

    new_house = aggregate_tables[0]
    second_hand = aggregate_tables[1]
    rows = []
    for city, province in CITY_PROVINCE.items():
        if city not in new_house or city not in second_hand:
            continue
        rows.append(
            {
                "city": city,
                "province": province,
                "date": f"{year:04d}-{month:02d}",
                "year": year,
                "month": month,
                "new_house_index": new_house[city]["mom"],
                "second_hand_index": second_hand[city]["mom"],
                "new_house_yoy": round(new_house[city]["yoy"] - 100, 1),
                "second_hand_yoy": round(second_hand[city]["yoy"] - 100, 1),
            }
        )
    return rows


def read_urls(args: argparse.Namespace) -> list[str]:
    urls = list(args.url or [])
    if args.urls_file:
        with open(args.urls_file, encoding="utf-8-sig", newline="") as file:
            reader = csv.DictReader(file)
            if "url" not in reader.fieldnames:
                raise ValueError("urls file must contain a 'url' column")
            urls.extend(row["url"].strip() for row in reader if row.get("url"))
    return list(dict.fromkeys(urls))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", action="append", help="NBS monthly page URL; can be repeated")
    parser.add_argument("--urls-file", help="CSV file with a url column")
    parser.add_argument("--out", default="src/static/house_price_monthly.json")
    parser.add_argument("--sleep", type=float, default=0.5, help="seconds between requests")
    args = parser.parse_args()

    urls = read_urls(args)
    if not urls:
        parser.error("provide --url or --urls-file")

    by_city: dict[str, dict] = {}
    for index, url in enumerate(urls, start=1):
        print(f"[{index}/{len(urls)}] {url}")
        for row in parse_page(url):
            city = row.pop("city")
            province = row.pop("province")
            by_city.setdefault(city, {"city": city, "province": province, "series": []})
            by_city[city]["series"].append(row)
        time.sleep(args.sleep)

    result = []
    for city in CITY_PROVINCE:
        item = by_city.get(city)
        if not item:
            continue
        item["series"] = sorted(item["series"], key=lambda row: (row["year"], row["month"]))
        result.append(item)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {out} ({len(result)} cities)")


if __name__ == "__main__":
    main()
