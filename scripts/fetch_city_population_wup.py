#!/usr/bin/env python3
"""Download UN WUP city population Excel and build city_population_flow.json."""

from __future__ import annotations

import argparse
import json
import urllib.request
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path


WUP_URL = "https://population.un.org/wup/assets/Download/Cities/WUP2025-F21-DEGURBA-Cities_Pop.xlsx"

TARGETS = {
    "北京": {"province": "北京", "region": "东部", "source_city": "Beijing"},
    "上海": {"province": "上海", "region": "东部", "source_city": "Shanghai"},
    "深圳": {"province": "广东", "region": "东部", "source_city": "Shenzhen"},
    "广州": {"province": "广东", "region": "东部", "source_city": "Guangzhou"},
    "杭州": {"province": "浙江", "region": "东部", "source_city": "Hangzhou"},
    "南京": {"province": "江苏", "region": "东部", "source_city": "Nanjing"},
    "成都": {"province": "四川", "region": "西部", "source_city": "Chengdu"},
    "重庆": {"province": "重庆", "region": "西部", "source_city": "Chongqing"},
    "西安": {"province": "陕西", "region": "西部", "source_city": "Xi'an"},
    "武汉": {"province": "湖北", "region": "中部", "source_city": "Wuhan"},
    "长沙": {"province": "湖南", "region": "中部", "source_city": "Changsha"},
    "郑州": {"province": "河南", "region": "中部", "source_city": "Zhengzhou"},
    "合肥": {"province": "安徽", "region": "中部", "source_city": "Hefei"},
    "沈阳": {"province": "辽宁", "region": "东北", "source_city": "Shenyang"},
    "长春": {"province": "吉林", "region": "东北", "source_city": "Changchun"},
    "哈尔滨": {"province": "黑龙江", "region": "东北", "source_city": "Harbin"},
}

NS = {"main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}


def col_index(cell_ref: str) -> int:
    letters = "".join(ch for ch in cell_ref if ch.isalpha())
    index = 0
    for ch in letters:
        index = index * 26 + ord(ch) - ord("A") + 1
    return index - 1


def parse_shared_strings(zf: zipfile.ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in zf.namelist():
        return []
    root = ET.fromstring(zf.read("xl/sharedStrings.xml"))
    return [
        "".join(node.text or "" for node in item.findall(".//main:t", NS))
        for item in root.findall("main:si", NS)
    ]


def cell_value(cell: ET.Element, shared: list[str]) -> str:
    if cell.get("t") == "inlineStr":
        return "".join(node.text or "" for node in cell.findall(".//main:t", NS))
    value_node = cell.find("main:v", NS)
    if value_node is None:
        return ""
    value = value_node.text or ""
    if cell.get("t") == "s":
        return shared[int(value)]
    return value


def read_rows(xlsx: Path) -> list[list[str]]:
    with zipfile.ZipFile(xlsx) as zf:
        shared = parse_shared_strings(zf)
        root = ET.fromstring(zf.read("xl/worksheets/sheet2.xml"))
        rows = []
        for row in root.findall(".//main:sheetData/main:row", NS):
            values = {}
            for cell in row.findall("main:c", NS):
                values[col_index(cell.get("r", ""))] = cell_value(cell, shared)
            if values:
                rows.append([values.get(i, "") for i in range(max(values) + 1)])
        return rows


def download_xlsx(cache_path: Path) -> Path:
    if cache_path.exists() and is_valid_xlsx(cache_path):
        return cache_path
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    print(f"downloading {WUP_URL}")
    part_path = cache_path.with_suffix(cache_path.suffix + ".part")
    urllib.request.urlretrieve(WUP_URL, part_path)
    if not is_valid_xlsx(part_path):
        raise RuntimeError(f"downloaded file is not a complete xlsx: {part_path}")
    part_path.replace(cache_path)
    return cache_path


def is_valid_xlsx(path: Path) -> bool:
    if not path.exists() or path.stat().st_size < 1_000_000:
        return False
    try:
        with zipfile.ZipFile(path) as zf:
            return "xl/worksheets/sheet2.xml" in zf.namelist()
    except zipfile.BadZipFile:
        return False


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="src/static/city_population_flow.json")
    parser.add_argument("--cache", default=".cache/WUP2025-F21-DEGURBA-Cities_Pop.xlsx")
    parser.add_argument("--start-year", type=int, default=2015)
    parser.add_argument("--end-year", type=int, default=2024)
    args = parser.parse_args()

    years = list(range(args.start_year, args.end_year + 1))
    rows = read_rows(download_xlsx(Path(args.cache)))
    header = next((row for row in rows if "ISO3_Code" in row and "City_Name" in row), None)
    if header is None:
        raise RuntimeError("cannot find Data sheet header")

    idx = {name: header.index(name) for name in ["ISO3_Code", "City_Name", "PWCent_Longitude", "PWCent_Latitude"]}
    year_idx = {year: header.index(str(year)) for year in years}
    source_names = {meta["source_city"] for meta in TARGETS.values()}

    candidates = {}
    for row in rows:
        if len(row) <= idx["City_Name"] or row[idx["ISO3_Code"]] != "CHN":
            continue
        source_city = row[idx["City_Name"]]
        if source_city not in source_names:
            continue
        current = candidates.get(source_city)
        value_2024 = float(row[year_idx[min(2024, args.end_year)]])
        if current is None or value_2024 > float(current[year_idx[min(2024, args.end_year)]]):
            candidates[source_city] = row

    result = []
    for city, meta in TARGETS.items():
        row = candidates.get(meta["source_city"])
        if row is None:
            raise RuntimeError(f"missing city: {city}")
        previous = None
        series = []
        for year in years:
            population = round(float(row[year_idx[year]]) / 10, 1)
            if previous is None:
                growth = 0.0
                growth_rate = 0.0
            else:
                growth = round(population - previous, 1)
                growth_rate = round((growth / previous) * 100, 2) if previous else 0.0
            series.append(
                {
                    "year": year,
                    "population": population,
                    "population_growth": growth,
                    "growth_rate": growth_rate,
                    "population_change_type": "increase" if growth > 0 else "decrease" if growth < 0 else "flat",
                }
            )
            previous = population
        result.append(
            {
                "city": city,
                "province": meta["province"],
                "region": meta["region"],
                "coordinate": [
                    round(float(row[idx["PWCent_Longitude"]]), 4),
                    round(float(row[idx["PWCent_Latitude"]]), 4),
                ],
                "source_city": meta["source_city"],
                "population_scope": "UN WUP DEGURBA city/urban centre population estimate",
                "series": series,
            }
        )

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {out} ({len(result)} cities, {years[0]}-{years[-1]})")


if __name__ == "__main__":
    main()
