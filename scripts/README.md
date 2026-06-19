# 数据获取与清洗脚本

本项目数据分三类：

1. `house_price_monthly.json`
   - 来源：国家统计局“70个大中城市商品住宅销售价格变动情况”月度发布网页。
   - 获取方式：先整理每个月发布页 URL，再用 `fetch_nbs_house_price.py` 抓取网页表格。
   - 示例页面：https://www.stats.gov.cn/sj/zxfb/202604/t20260416_1963320.html

2. `province_population_flow.json`
   - 来源：中国统计年鉴、国家统计局年度数据、各省统计公报中的省级常住人口和城镇化率。
   - 获取方式：该类数据没有稳定统一网页 API，先整理为 CSV，再用 `build_province_population_flow.py` 计算人口增量和增长率。

3. `city_population_flow.json`
   - 来源：United Nations World Urbanization Prospects 2025，城市人口表 `WUP2025-F21-DEGURBA-Cities_Pop.xlsx`。
   - 获取方式：`fetch_city_population_wup.py` 直接下载 Excel，抽取 16 个重点城市，单位从 thousand persons 换算为“万人”。

## 房价数据

准备一个 URL 列表 CSV：

```csv
url
https://www.stats.gov.cn/sj/zxfb/202604/t20260416_1963320.html
```

运行：

```bash
python3 scripts/fetch_nbs_house_price.py \
  --urls-file scripts/house_price_urls.csv \
  --out src/static/house_price_monthly.json
```

也可以只测试单页：

```bash
python3 scripts/fetch_nbs_house_price.py \
  --url https://www.stats.gov.cn/sj/zxfb/202604/t20260416_1963320.html \
  --out /tmp/house_price_one_month.json
```

## 省级人口数据

准备 CSV，字段：

```csv
province,year,population,urbanization_rate
北京,2015,2188,86.71
北京,2016,2195,86.76
```

运行：

```bash
python3 scripts/build_province_population_flow.py \
  data/province_population_source.csv \
  --out src/static/province_population_flow.json
```

## 城市人口数据

运行：

```bash
python3 scripts/fetch_city_population_wup.py \
  --out src/static/city_population_flow.json
```

默认生成 2015-2024 年、16 个重点城市的人口序列。
