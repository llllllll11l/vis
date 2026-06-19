<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import * as echarts from 'echarts'
import chinaGeo from '../static/china_geo.json'
import {
  average,
  formatNumber,
  formatPct,
  formatSigned,
  fullProvinceToShort,
  getHouseRecord,
  getPopulationByYear,
  getPopulationRecord,
  getPopulationYears,
  getProvinceHouseAnnual,
  populationFlowData,
  provinceFullNames,
  regionColors,
  regionOrder
} from '../utils/visualData'

echarts.registerMap('china', chinaGeo)

const metricOptions = [
  { value: 'new', label: '新建住宅' },
  { value: 'second', label: '二手住宅' }
]

const mapModeOptions = [
  { value: 'house', label: '房价-人口' },
  { value: 'population', label: '人口流动' }
]

const selectedYear = ref(2024)
const selectedProvince = ref('广东')
const metric = ref('new')
const mapMode = ref('house')
const mapChartRef = ref(null)
const trendChartRef = ref(null)
const regionChartRef = ref(null)

let mapChart
let trendChart
let regionChart

const years = computed(() => getPopulationYears().filter((year) => year >= 2015 && year <= 2024))
const selectedMetricLabel = computed(() => metricOptions.find((item) => item.value === metric.value)?.label || '新建住宅')
const currentMapTitle = computed(() => (mapMode.value === 'house' ? '房价-人口双变量空间地图' : '人口增减空间格局'))
const currentMapSubtitle = computed(() =>
  mapMode.value === 'house' ? '底色为房价指数，圆点为人口增减规模' : '底色表示人口增减，弧线表示趋势性集聚方向'
)
const yearTrendDots = computed(() => {
  const houseAnnual = getProvinceHouseAnnual(metric.value)
  const dots = years.value.map((year) => {
    const values = [...houseAnnual.byProvince.values()]
      .map((series) => series.find((item) => item.year === year)?.annual_growth)
      .filter((value) => value !== undefined)
    return {
      year,
      value: Number(average(values).toFixed(2))
    }
  })
  const maxAbs = Math.max(...dots.map((item) => Math.abs(item.value)), 1)

  return dots.map((item) => ({
    ...item,
    direction: getTrendDirection(item.value),
    size: getTrendDotSize(item.value, maxAbs),
    label: `${item.year}年全国${selectedMetricLabel.value}平均涨幅 ${formatPct(item.value)}`
  }))
})

const currentData = computed(() =>
  getPopulationByYear(selectedYear.value).map((item) => {
    const house = getHouseRecord(item.province, selectedYear.value, metric.value)
    return {
      ...item,
      house_index: house?.index ?? null,
      house_growth: house?.annual_growth ?? null,
      city_count: house?.city_count ?? 0
    }
  })
)

const selectedRecord = computed(() => currentData.value.find((item) => item.province === selectedProvince.value))

const selectedType = computed(() => {
  const record = selectedRecord.value
  if (!record || record.house_growth === null) return '数据待补'
  if (record.population_growth > 0 && record.house_growth > 0) return '强吸引型'
  if (record.population_growth < 0 && record.house_growth > 0) return '价格支撑型'
  if (record.population_growth < 0 && record.house_growth <= 0) return '收缩压力型'
  if (record.population_growth > 0 && record.house_growth <= 0) return '人口承接型'
  return '平稳型'
})

const summaryText = computed(() => {
  const record = selectedRecord.value
  if (!record) return ''
  if (selectedType.value === '数据待补') return `${record.province}有省级人口数据，暂无70城房价样本覆盖。`
  return `${record.province}${selectedYear.value}年${selectedMetricLabel.value}房价指数涨幅${formatPct(record.house_growth)}，人口增减${formatSigned(record.population_growth, '万人')}。`
})

function updateMapChart() {
  if (!mapChart) return

  if (mapMode.value === 'population') {
    const populationValues = currentData.value.map((item) => item.population_growth)
    const maxAbs = Math.ceil(Math.max(...populationValues.map((value) => Math.abs(value)), 10) / 10) * 10
    const lines = buildTrendLines(currentData.value)

    mapChart.setOption(
      {
        tooltip: {
          trigger: 'item',
          borderWidth: 0,
          backgroundColor: 'rgba(18, 24, 38, 0.94)',
          textStyle: { color: '#fff' },
          formatter(params) {
            if (params.seriesType === 'lines') {
              return `${params.data.fromName} -> ${params.data.toName}<br/>趋势强度：${formatSigned(params.data.value, '万人')}`
            }
            if (!params.data) return params.name
            return [
              `<strong>${params.data.province}</strong>`,
              `人口增减：${formatSigned(params.data.value, '万人')}`,
              `人口增长率：${formatPct(params.data.growthRate, 2)}`,
              `常住人口：${params.data.population}万人`
            ].join('<br/>')
          }
        },
        visualMap: {
          min: -maxAbs,
          max: maxAbs,
          left: 18,
          bottom: 22,
          text: ['增长', '减少'],
          inRange: {
            color: ['#2563eb', '#dbeafe', '#f8fafc', '#fed7aa', '#c2410c']
          },
          textStyle: {
            color: '#596374'
          }
        },
        geo: {
          map: 'china',
          roam: true,
          zoom: 1.13,
          label: { show: false },
          itemStyle: {
            borderColor: '#cbd5e1',
            borderWidth: 0.8
          },
          emphasis: {
            label: {
              show: true,
              color: '#172033'
            },
            itemStyle: {
              areaColor: '#f3c35b'
            }
          }
        },
        series: [
          {
            name: '人口增减',
            type: 'map',
            map: 'china',
            geoIndex: 0,
            data: currentData.value.map((item) => ({
              name: provinceFullNames[item.province],
              province: item.province,
              value: item.population_growth,
              growthRate: item.growth_rate,
              population: item.population
            }))
          },
          {
            name: '人口流动趋势示意',
            type: 'lines',
            coordinateSystem: 'geo',
            zlevel: 2,
            effect: {
              show: true,
              period: 5,
              trailLength: 0.25,
              symbol: 'arrow',
              symbolSize: 8
            },
            lineStyle: {
              color: '#d97706',
              width: 1.8,
              opacity: 0.58,
              curveness: 0.28
            },
            data: lines
          },
          {
            name: '重点增长地区',
            type: 'effectScatter',
            coordinateSystem: 'geo',
            zlevel: 3,
            rippleEffect: { brushType: 'stroke' },
            symbolSize(value) {
              return Math.max(8, Math.min(24, value[2] / 3))
            },
            itemStyle: { color: '#c2410c' },
            data: currentData.value
              .filter((item) => item.population_growth > 10)
              .map((item) => ({
                name: item.province,
                value: [...item.coordinate, item.population_growth]
              }))
          }
        ]
      },
      true
    )

    bindMapClick()
    return
  }

  const houseValues = currentData.value.map((item) => item.house_index).filter((value) => value !== null)
  const minHouse = Math.floor(Math.min(...houseValues) / 5) * 5
  const maxHouse = Math.ceil(Math.max(...houseValues) / 5) * 5

  const mapData = currentData.value.map((item) => ({
    name: provinceFullNames[item.province],
    value: item.house_index,
    province: item.province,
    houseGrowth: item.house_growth,
    populationGrowth: item.population_growth,
    population: item.population,
    itemStyle:
      item.house_index === null
        ? {
            areaColor: '#e5e7eb'
          }
        : undefined
  }))

  const scatterData = currentData.value.map((item) => ({
    name: item.province,
    value: [
      item.coordinate[0],
      item.coordinate[1],
      Math.abs(item.population_growth),
      item.population_growth,
      item.house_index,
      item.house_growth
    ],
    itemStyle: {
      color: item.population_growth >= 0 ? '#c2410c' : '#2563eb'
    }
  }))

  mapChart.setOption(
    {
      tooltip: {
        trigger: 'item',
        borderWidth: 0,
        backgroundColor: 'rgba(18, 24, 38, 0.94)',
        textStyle: { color: '#fff' },
        formatter(params) {
          if (params.seriesType === 'effectScatter') {
            return [
              `<strong>${params.name}</strong>`,
              `人口增减：${formatSigned(params.value[3], '万人')}`,
              `房价指数：${formatNumber(params.value[4])}`,
              `房价涨幅：${formatPct(params.value[5])}`
            ].join('<br/>')
          }
          if (!params.data) return params.name
          return [
            `<strong>${params.data.province}</strong>`,
            `房价指数：${formatNumber(params.data.value)}`,
            `房价涨幅：${formatPct(params.data.houseGrowth)}`,
            `人口增减：${formatSigned(params.data.populationGrowth, '万人')}`
          ].join('<br/>')
        }
      },
      visualMap: {
        min: minHouse,
        max: maxHouse,
        left: 18,
        bottom: 22,
        text: ['高指数', '低指数'],
        inRange: {
          color: ['#e0f2fe', '#9bd3d0', '#f5d06f', '#d97706', '#9a3412']
        },
        textStyle: {
          color: '#596374'
        }
      },
      geo: {
        map: 'china',
        roam: true,
        zoom: 1.13,
        label: { show: false },
        itemStyle: {
          borderColor: '#cbd5e1',
          borderWidth: 0.8
        },
        emphasis: {
          label: {
            show: true,
            color: '#172033'
          },
          itemStyle: {
            areaColor: '#f3c35b'
          }
        }
      },
      series: [
        {
          name: '房价指数',
          type: 'map',
          map: 'china',
          geoIndex: 0,
          data: mapData
        },
        {
          name: '人口增减',
          type: 'effectScatter',
          coordinateSystem: 'geo',
          zlevel: 2,
          rippleEffect: {
            brushType: 'stroke',
            scale: 2.3
          },
          symbolSize(value) {
            return Math.max(7, Math.min(28, value[2] / 2.8))
          },
          data: scatterData
        }
      ]
    },
    true
  )

  bindMapClick()
}

function bindMapClick() {
  mapChart.off('click')
  mapChart.on('click', (params) => {
    const province = fullProvinceToShort[params.name] || params.name
    if (populationFlowData.some((item) => item.province === province)) {
      selectedProvince.value = province
    }
  })
}

function buildTrendLines(data) {
  const negative = [...data]
    .filter((item) => item.population_growth < -10)
    .sort((a, b) => a.population_growth - b.population_growth)
    .slice(0, 6)
  const positive = [...data]
    .filter((item) => item.population_growth > 10)
    .sort((a, b) => b.population_growth - a.population_growth)
    .slice(0, 4)

  if (!positive.length) return []

  return negative.map((source, index) => {
    const target = positive[index % positive.length]
    return {
      fromName: source.province,
      toName: target.province,
      coords: [source.coordinate, target.coordinate],
      value: Math.min(Math.abs(source.population_growth), Math.abs(target.population_growth))
    }
  })
}

function getTrendDirection(value) {
  if (value > 0) return 'increase'
  if (value < 0) return 'decrease'
  return 'flat'
}

function getTrendDotSize(value, maxAbs) {
  return `${Math.round(10 + (Math.abs(value) / maxAbs) * 12)}px`
}

function updateTrendChart() {
  if (!trendChart) return

  const houseAnnual = getProvinceHouseAnnual(metric.value)
  const nationalHouse = years.value.map((year) => {
    const values = [...houseAnnual.byProvince.values()]
      .map((series) => series.find((item) => item.year === year)?.index)
      .filter((value) => value !== undefined)
    return Number(average(values).toFixed(1))
  })

  const nationalPopulation = years.value.map((year) =>
    Number(
      getPopulationByYear(year)
        .reduce((sum, item) => sum + item.population_growth, 0)
        .toFixed(1)
    )
  )

  trendChart.setOption(
    {
      tooltip: {
        trigger: 'axis'
      },
      legend: {
        top: 6,
        right: 10,
        textStyle: { color: '#596374' }
      },
      grid: {
        left: 54,
        right: 56,
        top: 56,
        bottom: 42
      },
      xAxis: {
        type: 'category',
        data: years.value,
        axisLabel: { color: '#596374' }
      },
      yAxis: [
        {
          type: 'value',
          name: '房价指数',
          axisLabel: { color: '#596374' },
          splitLine: {
            lineStyle: {
              type: 'dashed',
              color: '#e3e8f0'
            }
          }
        },
        {
          type: 'value',
          name: '万人',
          axisLabel: { color: '#596374' },
          splitLine: { show: false }
        }
      ],
      series: [
        {
          name: `${selectedMetricLabel.value}指数`,
          type: 'line',
          smooth: true,
          yAxisIndex: 0,
          data: nationalHouse,
          symbolSize(_value, params) {
            return years.value[params.dataIndex] === selectedYear.value ? 12 : 7
          },
          itemStyle: { color: '#15616d' },
          lineStyle: { width: 3.5 }
        },
        {
          name: '全国人口增减',
          type: 'bar',
          yAxisIndex: 1,
          data: nationalPopulation.map((value) => ({
            value,
            itemStyle: {
              color: value >= 0 ? '#c2410c' : '#2563eb',
              borderRadius: value >= 0 ? [5, 5, 0, 0] : [0, 0, 5, 5]
            }
          }))
        }
      ]
    },
    true
  )
}

function updateRegionChart() {
  if (!regionChart) return

  const rows = regionOrder.map((region) => {
    const items = currentData.value.filter((item) => item.region === region)
    const houseItems = items.filter((item) => item.house_growth !== null)
    return {
      name: region,
      value: [
        Number(items.reduce((sum, item) => sum + item.population_growth, 0).toFixed(1)),
        Number(average(houseItems.map((item) => item.house_growth)).toFixed(2)),
        Number(average(houseItems.map((item) => item.house_index)).toFixed(1))
      ],
      itemStyle: {
        color: regionColors[region]
      }
    }
  })

  regionChart.setOption(
    {
      tooltip: {
        trigger: 'item',
        borderWidth: 0,
        backgroundColor: 'rgba(18, 24, 38, 0.94)',
        textStyle: { color: '#fff' },
        formatter(params) {
          const [populationGrowth, houseGrowth, houseIndex] = params.value
          return [
            `<strong>${params.name}</strong>`,
            `人口增减：${formatSigned(populationGrowth, '万人')}`,
            `房价涨幅：${formatPct(houseGrowth)}`,
            `房价指数：${formatNumber(houseIndex)}`
          ].join('<br/>')
        }
      },
      grid: {
        left: 58,
        right: 28,
        top: 36,
        bottom: 52
      },
      xAxis: {
        type: 'value',
        name: '人口增减 / 万人',
        nameLocation: 'middle',
        nameGap: 34,
        axisLabel: { color: '#596374' },
        splitLine: {
          lineStyle: {
            type: 'dashed',
            color: '#e3e8f0'
          }
        }
      },
      yAxis: {
        type: 'value',
        name: '房价涨幅',
        axisLabel: {
          color: '#596374',
          formatter: '{value}%'
        },
        splitLine: {
          lineStyle: {
            type: 'dashed',
            color: '#e3e8f0'
          }
        }
      },
      series: [
        {
          type: 'scatter',
          data: rows,
          symbolSize(value) {
            return Math.max(18, Math.min(48, value[2] / 4.2))
          },
          label: {
            show: true,
            formatter: '{b}',
            position: 'top',
            color: '#263244',
            fontWeight: 700
          },
          markLine: {
            symbol: 'none',
            silent: true,
            lineStyle: {
              color: '#94a3b8',
              type: 'dashed'
            },
            data: [{ xAxis: 0 }, { yAxis: 0 }]
          }
        }
      ]
    },
    true
  )
}

function updateCharts() {
  nextTick(() => {
    updateMapChart()
    updateTrendChart()
    updateRegionChart()
  })
}

function resizeCharts() {
  mapChart?.resize()
  trendChart?.resize()
  regionChart?.resize()
}

watch([selectedYear, metric, mapMode], updateCharts)
watch(selectedProvince, updateCharts)

onMounted(() => {
  mapChart = echarts.init(mapChartRef.value)
  trendChart = echarts.init(trendChartRef.value)
  regionChart = echarts.init(regionChartRef.value)
  updateCharts()
  window.addEventListener('resize', resizeCharts)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', resizeCharts)
  mapChart?.dispose()
  trendChart?.dispose()
  regionChart?.dispose()
})
</script>

<template>
  <main class="overview-page">
    <header class="overview-header">
      <div class="title-block">
        <span class="eyebrow">Page 01</span>
        <h1>全国房价-人口空间格局总览</h1>
        <p>{{ years[0] }} 至 {{ years[years.length - 1] }} · {{ selectedMetricLabel }} · 省级人口年度增减</p>
      </div>

      <div class="overview-controls">
        <div class="segmented" role="tablist" aria-label="住宅类型">
          <button
            v-for="option in metricOptions"
            :key="option.value"
            type="button"
            :class="{ active: metric === option.value }"
            @click="metric = option.value"
          >
            {{ option.label }}
          </button>
        </div>
        <label class="year-control">
          <span>{{ selectedYear }}</span>
          <div class="year-dots" aria-label="年份选择">
            <button
              v-for="item in yearTrendDots"
              :key="item.year"
              type="button"
              :class="['trend-dot', item.direction, { active: selectedYear === item.year }]"
              :style="{ '--dot-size': item.size }"
              :title="item.label"
              :aria-label="item.label"
              @click="selectedYear = item.year"
            >
              <i></i>
              <small>{{ item.year }}</small>
            </button>
          </div>
        </label>
      </div>
    </header>

    <section class="overview-grid">
      <section class="panel map-panel">
        <div class="panel-head">
          <div>
            <h2>{{ currentMapTitle }}</h2>
            <p>{{ currentMapSubtitle }}</p>
          </div>
          <div class="map-panel-actions">
            <div class="map-switch" role="tablist" aria-label="地图模式">
              <button
                v-for="option in mapModeOptions"
                :key="option.value"
                type="button"
                :class="{ active: mapMode === option.value }"
                @click="mapMode = option.value"
              >
                {{ option.label }}
              </button>
            </div>
            <div class="legend-pair">
              <span class="is-positive">● 增长</span>
              <span class="is-negative">● 减少</span>
            </div>
          </div>
        </div>
        <div v-if="selectedRecord" class="map-insight-card">
          <strong>{{ selectedRecord.province }} · {{ selectedType }}</strong>
          <span>{{ selectedMetricLabel }}：{{ formatNumber(selectedRecord.house_index) }} / {{ formatPct(selectedRecord.house_growth) }}</span>
          <span>人口：{{ formatSigned(selectedRecord.population_growth, '万') }} / {{ formatPct(selectedRecord.growth_rate, 2) }}</span>
        </div>
        <div ref="mapChartRef" class="chart china-map"></div>
      </section>

      <aside class="side-stack">
        <section class="panel chart-panel">
          <div class="panel-head compact">
            <h2>全国趋势缩略图</h2>
          </div>
          <div ref="trendChartRef" class="chart trend-chart"></div>
        </section>

        <section class="panel chart-panel">
          <div class="panel-head compact">
            <h2>区域房价-人口对比</h2>
          </div>
          <div ref="regionChartRef" class="chart region-chart"></div>
        </section>
      </aside>
    </section>
  </main>
</template>

<style scoped>
.overview-page {
  width: min(1440px, calc(100vw - 32px));
  min-height: calc(100vh - 72px);
  margin: 0 auto;
  padding: 22px 0 28px;
}

.overview-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 20px;
  margin-bottom: 16px;
}

.title-block h1,
.panel h2 {
  margin: 0;
  letter-spacing: 0;
}

.title-block h1 {
  font-size: clamp(28px, 3vw, 42px);
  line-height: 1.08;
}

.title-block p,
.panel-head p {
  margin: 8px 0 0;
  color: #647084;
  font-size: 13px;
}

.eyebrow {
  display: inline-flex;
  margin-bottom: 6px;
  color: #15616d;
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0;
  text-transform: uppercase;
}

.overview-controls {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  flex-wrap: wrap;
  gap: 10px;
}

.segmented {
  display: inline-grid;
  grid-template-columns: repeat(2, minmax(78px, 1fr));
  padding: 3px;
  border: 1px solid #d6dde8;
  border-radius: 8px;
  background: #ffffff;
}

.segmented button {
  min-height: 34px;
  border: 0;
  border-radius: 6px;
  color: #4b5563;
  background: transparent;
}

.segmented button.active {
  color: #ffffff;
  background: #15616d;
}

.year-control {
  display: grid;
  min-width: min(470px, 48vw);
  gap: 8px;
  padding: 9px 12px 10px;
  border: 1px solid #d6dde8;
  border-radius: 8px;
  background: #ffffff;
  color: #15616d;
  font-weight: 800;
}

.year-dots {
  display: grid;
  grid-template-columns: repeat(10, minmax(28px, 1fr));
  gap: 6px;
}

.year-dots button {
  display: grid;
  place-items: center;
  gap: 3px;
  min-height: 34px;
  min-width: 0;
  padding: 0;
  border: 0;
  background: transparent;
  color: #7b8798;
}

.year-dots i {
  width: var(--dot-size, 10px);
  height: var(--dot-size, 10px);
  border: 2px solid var(--dot-color, #cbd5e1);
  border-radius: 50%;
  background: var(--dot-color, #cbd5e1);
  opacity: 0.82;
  transition:
    width 0.2s ease,
    height 0.2s ease,
    box-shadow 0.2s ease,
    opacity 0.2s ease;
}

.year-dots small {
  font-size: 10px;
  font-weight: 700;
  line-height: 1.15;
}

.year-dots button.active {
  color: #15616d;
}

.year-dots button.increase {
  --dot-color: #16a34a;
}

.year-dots button.decrease {
  --dot-color: #dc2626;
}

.year-dots button.flat {
  --dot-color: #94a3b8;
}

.year-dots button.active i {
  opacity: 1;
  box-shadow:
    0 0 0 4px rgba(21, 97, 109, 0.14),
    0 0 0 1px #ffffff inset;
}

.overview-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(360px, 408px);
  gap: 16px;
  min-width: 0;
}

.panel {
  border: 1px solid #dfe5ee;
  border-radius: 8px;
  background: #ffffff;
  box-shadow: 0 14px 30px rgba(23, 32, 51, 0.07);
  min-width: 0;
}

.map-panel,
.summary-panel,
.chart-panel {
  padding: 18px;
}

.panel-head,
.summary-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.panel-head h2,
.summary-head h2 {
  font-size: 18px;
}

.panel-head.compact {
  min-height: 28px;
}

.legend-pair {
  display: inline-flex;
  gap: 12px;
  color: #647084;
  font-size: 12px;
  white-space: nowrap;
}

.map-panel-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  flex-wrap: wrap;
  gap: 10px;
}

.map-switch {
  display: inline-grid;
  grid-template-columns: repeat(2, minmax(76px, 1fr));
  padding: 3px;
  border: 1px solid #d6dde8;
  border-radius: 8px;
  background: #ffffff;
}

.map-switch button {
  min-height: 32px;
  padding: 0 10px;
  border: 0;
  border-radius: 6px;
  color: #4b5563;
  background: transparent;
  white-space: nowrap;
}

.map-switch button.active {
  color: #ffffff;
  background: #15616d;
}

.is-positive {
  color: #c2410c;
}

.is-negative {
  color: #2563eb;
}

.chart {
  width: 100%;
  min-width: 0;
}

.china-map {
  height: min(68vh, 690px);
  min-height: 620px;
}

.side-stack {
  display: grid;
  grid-template-rows: minmax(260px, 1fr) minmax(260px, 1fr);
  gap: 16px;
}

.map-insight-card {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px 14px;
  margin-top: 12px;
  padding: 10px 12px;
  border-radius: 8px;
  background: #172033;
  color: rgba(255, 255, 255, 0.82);
  font-size: 12px;
  line-height: 1.35;
}

.map-insight-card strong {
  color: #ffffff;
  font-size: 13px;
}

.summary-head h2 {
  margin: 0;
}

.type-pill {
  padding: 7px 10px;
  border-radius: 999px;
  background: #eef6f7;
  color: #15616d;
  font-size: 12px;
  font-weight: 800;
}

.summary-metrics {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
  margin-top: 14px;
}

.metric-card {
  min-height: 82px;
  padding: 12px;
  border: 1px solid #e4e8ef;
  border-radius: 8px;
  background: #fbfcfe;
}

.metric-card span {
  display: block;
  color: #667085;
  font-size: 12px;
}

.metric-card strong {
  display: block;
  margin-top: 8px;
  color: #172033;
  font-size: 24px;
  line-height: 1.05;
}

.summary-text {
  margin: 14px 0 0;
  padding: 11px 12px;
  border-left: 3px solid #15616d;
  border-radius: 6px;
  background: #f1f7f7;
  color: #394557;
  font-size: 13px;
  line-height: 1.5;
}

.trend-chart,
.region-chart {
  height: 230px;
}

@media (max-width: 1120px) {
  .overview-header {
    flex-direction: column;
  }

  .overview-controls {
    width: 100%;
    justify-content: flex-start;
  }

  .overview-grid {
    grid-template-columns: 1fr;
  }

  .side-stack {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    grid-template-rows: auto;
  }
}

@media (max-width: 760px) {
  .overview-page {
    width: min(100vw - 20px, 720px);
    padding-top: 16px;
  }

  .overview-controls,
  .segmented,
  .year-control {
    width: 100%;
  }

  .year-control {
    min-width: 0;
  }

  .year-dots {
    overflow-x: auto;
    padding: 4px 2px;
  }

  .year-dots button {
    min-width: 34px;
  }

  .side-stack {
    grid-template-columns: 1fr;
  }

  .panel-head,
  .map-panel-actions {
    flex-direction: column;
    align-items: stretch;
  }

  .map-switch {
    width: 100%;
  }

  .china-map {
    height: 520px;
    min-height: 520px;
  }

  .summary-metrics {
    grid-template-columns: 1fr;
  }
}
</style>
