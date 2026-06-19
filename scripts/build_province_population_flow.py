#!/usr/bin/env python3
"""Build province_population_flow.json from a cleaned province CSV."""

from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path


REGION = {
    "北京": "东部",
    "天津": "东部",
    "河北": "东部",
    "上海": "东部",
    "江苏": "东部",
    "浙江": "东部",
    "福建": "东部",
    "山东": "东部",
    "广东": "东部",
    "海南": "东部",
    "山西": "中部",
    "安徽": "中部",
    "江西": "中部",
    "河南": "中部",
    "湖北": "中部",
    "湖南": "中部",
    "内蒙古": "西部",
    "广西": "西部",
    "重庆": "西部",
    "四川": "西部",
    "贵州": "西部",
    "云南": "西部",
    "西藏": "西部",
    "陕西": "西部",
    "甘肃": "西部",
    "青海": "西部",
    "宁夏": "西部",
    "新疆": "西部",
    "辽宁": "东北",
    "吉林": "东北",
    "黑龙江": "东北",
}

COORDINATE = {
    "北京": [116.4, 39.9],
    "天津": [117.2, 39.1],
    "河北": [114.5, 38.0],
    "山西": [112.5, 37.9],
    "内蒙古": [111.7, 40.8],
    "辽宁": [123.4, 41.8],
    "吉林": [125.3, 43.9],
    "黑龙江": [126.6, 45.8],
    "上海": [121.5, 31.2],
    "江苏": [118.8, 32.1],
    "浙江": [120.2, 30.3],
    "安徽": [117.3, 31.8],
    "福建": [119.3, 26.1],
    "江西": [115.9, 28.7],
    "山东": [117.0, 36.7],
    "河南": [113.6, 34.8],
    "湖北": [114.3, 30.6],
    "湖南": [112.9, 28.2],
    "广东": [113.3, 23.1],
    "广西": [108.3, 22.8],
    "海南": [110.3, 20.0],
    "重庆": [106.5, 29.6],
    "四川": [104.1, 30.7],
    "贵州": [106.7, 26.6],
    "云南": [102.7, 25.0],
    "西藏": [91.1, 29.7],
    "陕西": [108.9, 34.3],
    "甘肃": [103.8, 36.1],
    "青海": [101.8, 36.6],
    "宁夏": [106.2, 38.5],
    "新疆": [87.6, 43.8],
}

ORDER = list(REGION.keys())


def to_float(value: str) -> float:
    return float(str(value).replace(",", "").strip())


def compact_number(value: float, digits: int = 1):
    rounded = round(value, digits)
    return int(rounded) if rounded == int(rounded) else rounded


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("csv_file", help="CSV with province,year,population,urbanization_rate")
    parser.add_argument("--out", default="src/static/province_population_flow.json")
    args = parser.parse_args()

    by_province = defaultdict(list)
    with open(args.csv_file, encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        required = {"province", "year", "population"}
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"missing columns: {sorted(missing)}")
        for row in reader:
            province = row["province"].strip()
            by_province[province].append(
                {
                    "year": int(row["year"]),
                    "population": to_float(row["population"]),
                    "urbanization_rate": to_float(row["urbanization_rate"]) if row.get("urbanization_rate") else None,
                }
            )

    result = []
    for province in ORDER:
        rows = sorted(by_province.get(province, []), key=lambda row: row["year"])
        if not rows:
            continue
        previous = None
        series = []
        for row in rows:
            population = row["population"]
            if previous is None:
                growth = 0.0
                growth_rate = 0.0
            else:
                growth = round(population - previous, 1)
                growth_rate = round((growth / previous) * 100, 2) if previous else 0.0
            record = {
                "year": row["year"],
                "population": compact_number(population),
                "population_growth": compact_number(growth),
                "growth_rate": growth_rate,
                "urbanization_rate": row["urbanization_rate"],
                "population_change_type": "increase" if growth > 0 else "decrease" if growth < 0 else "flat",
            }
            series.append(record)
            previous = population
        result.append(
            {
                "province": province,
                "region": REGION[province],
                "coordinate": COORDINATE[province],
                "series": series,
            }
        )

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {out} ({len(result)} provinces)")


if __name__ == "__main__":
    main()
