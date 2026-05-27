<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import * as echarts from 'echarts'
import chinaGeo from '../static/china_geo.json'
import {
  formatPct,
  formatSigned,
  fullProvinceToShort,
  getPopulationByYear,
  getPopulationRecord,
  getPopulationYears,
  populationFlowData,
  provinceFullNames,
  regionOrder
} from '../utils/visualData'

echarts.registerMap('china', chinaGeo)

const selectedYear = ref(2024)
const selectedProvince = ref('广东')
const mapChartRef = ref(null)
const rankChartRef = ref(null)
const trendChartRef = ref(null)
const structureChartRef = ref(null)

let mapChart
let rankChart
let trendChart
let structureChart

const years = computed(() => getPopulationYears())
const currentData = computed(() => getPopulationByYear(selectedYear.value))
const selectedRecord = computed(() => currentData.value.find((item) => item.province === selectedProvince.value))

function updateMapChart() {
  if (!mapChart) return

  const data = currentData.value
  const lines = buildTrendLines(data)

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
        min: -90,
        max: 90,
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
          data: data.map((item) => ({
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
          data: data
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

function updateRankChart() {
  if (!rankChart) return

  const sorted = [...currentData.value].sort((a, b) => a.population_growth - b.population_growth)
  const merged = [...sorted.slice(0, 8), ...sorted.slice(-8)]
  const names = merged.map((item) => item.province)

  rankChart.setOption(
    {
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'shadow' },
        formatter(params) {
          const item = params[0]
          return `${item.name}<br/>人口增减：${formatSigned(item.value, '万人')}`
        }
      },
      grid: {
        left: 74,
        right: 34,
        top: 18,
        bottom: 32
      },
      xAxis: {
        type: 'value',
        axisLabel: { color: '#596374' },
        splitLine: {
          lineStyle: {
            type: 'dashed',
            color: '#e3e8f0'
          }
        }
      },
      yAxis: {
        type: 'category',
        data: names,
        axisLabel: {
          color(value) {
            return value === selectedProvince.value ? '#d97706' : '#596374'
          },
          fontWeight(value) {
            return value === selectedProvince.value ? 800 : 400
          }
        }
      },
      series: [
        {
          type: 'bar',
          data: merged.map((item) => ({
            value: item.population_growth,
            itemStyle: {
              color:
                item.province === selectedProvince.value
                  ? '#d97706'
                  : item.population_growth >= 0
                    ? '#c2410c'
                    : '#2563eb',
              borderRadius: item.population_growth >= 0 ? [5, 5, 0, 0] : [0, 0, 5, 5]
            }
          })),
          label: {
            show: true,
            position(params) {
              return params.value >= 0 ? 'right' : 'left'
            },
            formatter(params) {
              return formatSigned(params.value)
            },
            color: '#334155',
            fontSize: 11
          }
        }
      ]
    },
    true
  )
}

function updateTrendChart() {
  if (!trendChart) return

  const series = years.value.map((year) => getPopulationRecord(selectedProvince.value, year)?.population_growth ?? 0)
  const population = years.value.map((year) => getPopulationRecord(selectedProvince.value, year)?.population ?? 0)

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
        right: 50,
        top: 56,
        bottom: 38
      },
      xAxis: {
        type: 'category',
        data: years.value,
        axisLabel: { color: '#596374' }
      },
      yAxis: [
        {
          type: 'value',
          name: '增减/万人',
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
          name: '常住人口',
          axisLabel: { color: '#596374' },
          splitLine: { show: false }
        }
      ],
      series: [
        {
          name: '人口增减',
          type: 'bar',
          data: series,
          itemStyle: {
            color(params) {
              return years.value[params.dataIndex] === selectedYear.value
                ? '#d97706'
                : params.data >= 0
                  ? '#c2410c'
                  : '#2563eb'
            },
            borderRadius: [5, 5, 0, 0]
          },
          markLine: {
            symbol: 'none',
            lineStyle: {
              color: '#94a3b8',
              type: 'dashed'
            },
            data: [{ yAxis: 0 }]
          }
        },
        {
          name: '常住人口',
          type: 'line',
          yAxisIndex: 1,
          smooth: true,
          data: population,
          itemStyle: { color: '#15616d' },
          lineStyle: { width: 3 }
        }
      ]
    },
    true
  )
}

function updateStructureChart() {
  if (!structureChart) return

  const growthData = regionOrder.map((region) =>
    currentData.value
      .filter((item) => item.region === region && item.population_growth > 0)
      .reduce((sum, item) => sum + item.population_growth, 0)
  )
  const lossData = regionOrder.map((region) =>
    currentData.value
      .filter((item) => item.region === region && item.population_growth < 0)
      .reduce((sum, item) => sum + Math.abs(item.population_growth), 0)
  )

  structureChart.setOption(
    {
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'shadow' }
      },
      legend: {
        top: 6,
        right: 10,
        textStyle: { color: '#596374' }
      },
      grid: {
        left: 54,
        right: 24,
        top: 54,
        bottom: 38
      },
      xAxis: {
        type: 'category',
        data: regionOrder,
        axisLabel: { color: '#596374' }
      },
      yAxis: {
        type: 'value',
        name: '万人',
        axisLabel: { color: '#596374' },
        splitLine: {
          lineStyle: {
            type: 'dashed',
            color: '#e3e8f0'
          }
        }
      },
      series: [
        {
          name: '人口增长',
          type: 'bar',
          stack: 'total',
          data: growthData,
          itemStyle: {
            color: '#c2410c',
            borderRadius: [5, 5, 0, 0]
          }
        },
        {
          name: '人口减少',
          type: 'bar',
          stack: 'total',
          data: lossData.map((value) => -value),
          itemStyle: {
            color: '#2563eb',
            borderRadius: [0, 0, 5, 5]
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
    updateRankChart()
    updateTrendChart()
    updateStructureChart()
  })
}

function resizeCharts() {
  mapChart?.resize()
  rankChart?.resize()
  trendChart?.resize()
  structureChart?.resize()
}

watch([selectedYear, selectedProvince], updateCharts)

onMounted(() => {
  mapChart = echarts.init(mapChartRef.value)
  rankChart = echarts.init(rankChartRef.value)
  trendChart = echarts.init(trendChartRef.value)
  structureChart = echarts.init(structureChartRef.value)
  updateCharts()
  window.addEventListener('resize', resizeCharts)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', resizeCharts)
  mapChart?.dispose()
  rankChart?.dispose()
  trendChart?.dispose()
  structureChart?.dispose()
})
</script>

<template>
  <main class="population-page">
    <header class="population-header">
      <div class="title-block">
        <span class="eyebrow">Page 03</span>
        <h1>人口增减与流动格局分析</h1>
        <p>{{ years[0] }} 至 {{ years[years.length - 1] }} · 省级常住人口年度变化</p>
      </div>

      <label class="year-control">
        <span>{{ selectedYear }}</span>
        <div class="year-dots" aria-label="年份选择">
          <button
            v-for="year in years"
            :key="year"
            type="button"
            :class="{ active: selectedYear === year }"
            @click="selectedYear = year"
          >
            <i></i>
            <small>{{ year }}</small>
          </button>
        </div>
      </label>
    </header>

    <section class="population-grid">
      <section class="panel map-panel">
        <div class="panel-head">
          <div>
            <h2>人口增减空间格局</h2>
            <p>底色表示人口增减方向与幅度，弧线表示趋势性集聚方向</p>
          </div>
          <div v-if="selectedRecord" class="selected-chip">
            {{ selectedProvince }} {{ formatSigned(selectedRecord.population_growth, '万') }}
          </div>
        </div>
        <div ref="mapChartRef" class="chart china-map"></div>
      </section>

      <aside class="side-stack">
        <section class="panel chart-panel">
          <div class="panel-head compact">
            <h2>净增长-净减少排名</h2>
          </div>
          <div ref="rankChartRef" class="chart rank-chart"></div>
        </section>

        <section class="panel chart-panel">
          <div class="panel-head compact">
            <h2>重点省份人口变化趋势</h2>
          </div>
          <div ref="trendChartRef" class="chart trend-chart"></div>
        </section>

        <section class="panel chart-panel">
          <div class="panel-head compact">
            <h2>区域人口增减结构</h2>
          </div>
          <div ref="structureChartRef" class="chart structure-chart"></div>
        </section>
      </aside>
    </section>
  </main>
</template>

<style scoped>
.population-page {
  width: min(1440px, calc(100vw - 32px));
  min-height: calc(100vh - 72px);
  margin: 0 auto;
  padding: 22px 0 28px;
}

.population-header {
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
  min-width: 0;
  padding: 0;
  border: 0;
  background: transparent;
  color: #7b8798;
}

.year-dots i {
  width: 10px;
  height: 10px;
  border: 2px solid #cbd5e1;
  border-radius: 50%;
  background: #ffffff;
}

.year-dots small {
  font-size: 10px;
  font-weight: 700;
  line-height: 1.15;
}

.year-dots button.active {
  color: #15616d;
}

.year-dots button.active i {
  border-color: #15616d;
  background: #15616d;
  box-shadow: 0 0 0 4px rgba(21, 97, 109, 0.12);
}

.population-grid {
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
.chart-panel {
  padding: 18px;
}

.panel-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.panel-head h2 {
  font-size: 18px;
}

.panel-head.compact {
  min-height: 28px;
}

.selected-chip {
  padding: 7px 10px;
  border-radius: 999px;
  background: #eef6f7;
  color: #15616d;
  font-size: 12px;
  font-weight: 800;
  white-space: nowrap;
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
  grid-template-rows: minmax(250px, 1fr) minmax(220px, 0.9fr) minmax(220px, 0.9fr);
  gap: 16px;
}

.rank-chart,
.trend-chart,
.structure-chart {
  height: 240px;
}

@media (max-width: 1120px) {
  .population-header {
    flex-direction: column;
  }

  .year-control {
    width: 100%;
    min-width: 0;
  }

  .population-grid {
    grid-template-columns: 1fr;
  }

  .side-stack {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    grid-template-rows: auto auto;
  }

  .side-stack .chart-panel:first-child {
    grid-column: 1 / -1;
  }
}

@media (max-width: 760px) {
  .population-page {
    width: min(100vw - 20px, 720px);
    padding-top: 16px;
  }

  .side-stack {
    grid-template-columns: 1fr;
  }

  .side-stack .chart-panel:first-child {
    grid-column: auto;
  }

  .panel-head {
    flex-direction: column;
  }

  .year-dots {
    overflow-x: auto;
    padding: 4px 2px;
  }

  .year-dots button {
    min-width: 34px;
  }

  .china-map {
    height: 520px;
    min-height: 520px;
  }
}
</style>
