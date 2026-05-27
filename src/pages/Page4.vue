<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import * as echarts from 'echarts'
import cityPopulationData from '../static/city_population_flow.json'
import {
  average,
  formatNumber,
  formatPct,
  formatSigned,
  getCityHouseAnnual,
  getCityHouseRecord,
  regionColors,
  regionOrder
} from '../utils/visualData'

const metricOptions = [
  { value: 'new', label: '新建住宅' },
  { value: 'second', label: '二手住宅' }
]

const typeColors = {
  强吸引型: '#c2410c',
  价格支撑型: '#d97706',
  收缩压力型: '#2563eb',
  人口承接型: '#2f855a',
  平稳观察型: '#64748b'
}

const selectedRegion = ref('全部')
const selectedMetric = ref('new')
const selectedYear = ref(2024)
const selectedCity = ref('深圳')
const scatterChartRef = ref(null)
const trendChartRef = ref(null)

let scatterChart
let trendChart

const regions = computed(() => ['全部', ...regionOrder])
const metricLabel = computed(() => metricOptions.find((item) => item.value === selectedMetric.value)?.label || '')
const populationYears = computed(() => cityPopulationData[0]?.series.map((item) => item.year) || [])
const availableYears = computed(() => {
  const houseYears = getCityHouseAnnual(selectedMetric.value).years
  return populationYears.value.filter((year) => houseYears.includes(year))
})

const cityRows = computed(() =>
  cityPopulationData
    .map((cityItem) => {
      const populationRecord = cityItem.series.find((item) => item.year === selectedYear.value)
      const houseRecord = getCityHouseRecord(cityItem.city, selectedYear.value, selectedMetric.value)
      if (!populationRecord || !houseRecord) return null

      return {
        city: cityItem.city,
        province: cityItem.province,
        region: cityItem.region,
        coordinate: cityItem.coordinate,
        population_scope: cityItem.population_scope,
        population: populationRecord.population,
        population_growth: populationRecord.population_growth,
        growth_rate: populationRecord.growth_rate,
        house_index: houseRecord.index,
        house_growth: houseRecord.annual_growth,
        cumulative_growth: houseRecord.cumulative_growth,
        year: houseRecord.year,
        date: houseRecord.date,
        month: houseRecord.month,
        type: getCouplingType(populationRecord.growth_rate, houseRecord.annual_growth)
      }
    })
    .filter(Boolean)
)

const filteredRows = computed(() =>
  selectedRegion.value === '全部'
    ? cityRows.value
    : cityRows.value.filter((item) => item.region === selectedRegion.value)
)

const selectedRow = computed(() => cityRows.value.find((item) => item.city === selectedCity.value) || cityRows.value[0])

const selectedPopulationSeries = computed(
  () => cityPopulationData.find((item) => item.city === selectedCity.value)?.series || []
)

const selectedHouseSeries = computed(() => getCityHouseAnnual(selectedMetric.value).byCity.get(selectedCity.value) || [])

const periodLabel = computed(() => {
  const row = selectedRow.value
  if (!row) return ''
  return row.month === 12 ? `${row.year}年` : `${row.year}年截至${row.month}月`
})

const profileMetrics = computed(() => {
  const row = selectedRow.value
  const rows = cityRows.value
  if (!row || !rows.length) return []

  const priceScore = scoreByRank(row.house_index, rows.map((item) => item.house_index))
  const houseGrowthScore = scoreByRank(row.house_growth, rows.map((item) => item.house_growth))
  const popGrowthScore = scoreByRank(row.population_growth, rows.map((item) => item.population_growth))
  const popRateScore = scoreByRank(row.growth_rate, rows.map((item) => item.growth_rate))
  const populationScore = scoreByRank(row.population, rows.map((item) => item.population))
  const couplingScore = Math.round(
    average([houseGrowthScore, popGrowthScore, popRateScore, populationScore].filter((item) => !Number.isNaN(item)))
  )

  return [
    {
      label: '房价指数',
      value: formatNumber(row.house_index, 1),
      score: priceScore,
      color: '#15616d'
    },
    {
      label: '房价涨幅',
      value: formatPct(row.house_growth),
      score: houseGrowthScore,
      color: '#c2410c'
    },
    {
      label: '人口增量',
      value: formatSigned(row.population_growth, '万'),
      score: popGrowthScore,
      color: '#d97706'
    },
    {
      label: '人口增长率',
      value: formatPct(row.growth_rate, 2),
      score: popRateScore,
      color: '#2f855a'
    },
    {
      label: '人口规模',
      value: formatPopulation(row.population),
      score: populationScore,
      color: '#2563eb'
    },
    {
      label: '综合耦合分',
      value: String(couplingScore),
      score: couplingScore,
      color: '#7c3aed'
    }
  ]
})

const relationInsight = computed(() => {
  const row = selectedRow.value
  if (!row) return ''
  const houseText = row.house_growth >= 0 ? '上涨' : '下跌'
  const popText = row.population_growth >= 0 ? '增加' : '减少'
  return `${row.city}${selectedYear.value}年表现为房价${houseText}、人口${popText}，归入${row.type}。`
})

function getCouplingType(popRate, houseGrowth) {
  if (Math.abs(popRate) < 0.05 && Math.abs(houseGrowth) < 0.1) return '平稳观察型'
  if (popRate >= 0 && houseGrowth >= 0) return '强吸引型'
  if (popRate < 0 && houseGrowth >= 0) return '价格支撑型'
  if (popRate < 0 && houseGrowth < 0) return '收缩压力型'
  if (popRate >= 0 && houseGrowth < 0) return '人口承接型'
  return '平稳观察型'
}

function scoreByRank(value, values) {
  const valid = values.filter((item) => item !== null && item !== undefined && !Number.isNaN(item)).sort((a, b) => a - b)
  if (valid.length <= 1) return 50
  const index = valid.findIndex((item) => item === value)
  return Math.round((index / (valid.length - 1)) * 100)
}

function formatPopulation(value) {
  if (value === null || value === undefined || Number.isNaN(value)) return '-'
  return `${Number(value).toLocaleString('zh-CN', { maximumFractionDigits: 1 })}万`
}

function formatAxisPct(value) {
  return `${value}%`
}

function barClass(value) {
  if (value > 0) return 'is-positive'
  if (value < 0) return 'is-negative'
  return 'is-flat'
}

function ringStyle(metric) {
  return {
    '--ring-color': metric.color,
    '--ring-degree': `${metric.score * 3.6}deg`
  }
}

function axisExtent(values, fallback = 1) {
  const maxAbs = Math.max(fallback, ...values.map((item) => Math.abs(item)))
  const padded = maxAbs * 1.25
  return {
    min: Number((-padded).toFixed(1)),
    max: Number(padded.toFixed(1))
  }
}

function updateScatterChart() {
  if (!scatterChart) return

  const rows = filteredRows.value
  const xExtent = axisExtent(rows.map((item) => item.growth_rate), 0.5)
  const yExtent = axisExtent(rows.map((item) => item.house_growth), 1)

  const series = regionOrder.map((region, regionIndex) => ({
    name: region,
    type: 'scatter',
    data: rows
      .filter((item) => item.region === region)
      .map((item) => ({
        name: item.city,
        value: [item.growth_rate, item.house_growth, item.house_index, item.population_growth, item.population],
        row: item,
        itemStyle: {
          color: item.city === selectedCity.value ? '#172033' : regionColors[item.region],
          borderColor: item.city === selectedCity.value ? '#f3c35b' : '#ffffff',
          borderWidth: item.city === selectedCity.value ? 3 : 1
        }
      })),
    symbolSize(value) {
      return Math.max(14, Math.min(44, Math.sqrt(value[4]) * 0.82))
    },
    label: {
      show: true,
      formatter: '{b}',
      position: 'top',
      color: '#344054',
      fontSize: 11
    },
    emphasis: {
      focus: 'series',
      scale: 1.18
    },
    markLine:
      regionIndex === 0
        ? {
            symbol: 'none',
            silent: true,
            lineStyle: {
              color: '#94a3b8',
              type: 'dashed',
              width: 1.2
            },
            data: [{ xAxis: 0 }, { yAxis: 0 }]
          }
        : undefined
  }))

  scatterChart.setOption(
    {
      color: regionOrder.map((item) => regionColors[item]),
      animationDuration: 500,
      tooltip: {
        trigger: 'item',
        borderWidth: 0,
        backgroundColor: 'rgba(18, 24, 38, 0.94)',
        textStyle: { color: '#fff' },
        formatter(params) {
          const row = params.data.row
          return [
            `<strong>${row.city}</strong>`,
            `区域：${row.region}`,
            `人口增长率：${formatPct(row.growth_rate, 2)}`,
            `人口增量：${formatSigned(row.population_growth, '万')}`,
            `${metricLabel.value}涨幅：${formatPct(row.house_growth)}`,
            `耦合类型：${row.type}`
          ].join('<br/>')
        }
      },
      legend: {
        top: 6,
        right: 12,
        itemGap: 16,
        textStyle: {
          color: '#596374'
        }
      },
      grid: {
        left: 70,
        right: 38,
        top: 70,
        bottom: 58
      },
      xAxis: {
        type: 'value',
        name: '人口增长率',
        min: xExtent.min,
        max: xExtent.max,
        nameLocation: 'middle',
        nameGap: 36,
        axisLabel: {
          formatter: formatAxisPct,
          color: '#596374'
        },
        splitLine: {
          lineStyle: {
            type: 'dashed',
            color: '#e4e8ef'
          }
        }
      },
      yAxis: {
        type: 'value',
        name: `${metricLabel.value}年度涨幅`,
        min: yExtent.min,
        max: yExtent.max,
        nameLocation: 'middle',
        nameGap: 46,
        axisLabel: {
          formatter: formatAxisPct,
          color: '#596374'
        },
        splitLine: {
          lineStyle: {
            type: 'dashed',
            color: '#e4e8ef'
          }
        }
      },
      graphic: [
        {
          type: 'text',
          left: '71%',
          top: '17%',
          style: {
            text: '强吸引型',
            fill: 'rgba(194,65,12,0.74)',
            fontSize: 15,
            fontWeight: 700
          }
        },
        {
          type: 'text',
          left: '16%',
          top: '17%',
          style: {
            text: '价格支撑型',
            fill: 'rgba(217,119,6,0.74)',
            fontSize: 15,
            fontWeight: 700
          }
        },
        {
          type: 'text',
          left: '16%',
          top: '80%',
          style: {
            text: '收缩压力型',
            fill: 'rgba(37,99,235,0.74)',
            fontSize: 15,
            fontWeight: 700
          }
        },
        {
          type: 'text',
          left: '71%',
          top: '80%',
          style: {
            text: '人口承接型',
            fill: 'rgba(47,133,90,0.74)',
            fontSize: 15,
            fontWeight: 700
          }
        }
      ],
      series
    },
    true
  )

  scatterChart.off('click')
  scatterChart.on('click', (params) => {
    if (params.data?.row?.city) {
      selectedCity.value = params.data.row.city
    }
  })
}

function updateTrendChart() {
  if (!trendChart || !selectedRow.value) return

  const years = availableYears.value
  const populationMap = new Map(selectedPopulationSeries.value.map((item) => [item.year, item]))
  const houseMap = new Map(selectedHouseSeries.value.map((item) => [item.year, item]))
  const houseValues = years.map((year) => houseMap.get(year)?.index ?? null)
  const growthValues = years.map((year) => populationMap.get(year)?.population_growth ?? null)

  trendChart.setOption(
    {
      animationDuration: 500,
      tooltip: {
        trigger: 'axis',
        borderWidth: 0,
        backgroundColor: 'rgba(18, 24, 38, 0.94)',
        textStyle: { color: '#fff' },
        formatter(params) {
          const year = Number(params[0].axisValue)
          const house = houseMap.get(year)
          const population = populationMap.get(year)
          return [
            `<strong>${selectedCity.value} · ${year}</strong>`,
            `${metricLabel.value}指数：${house ? formatNumber(house.index, 1) : '-'}`,
            `房价涨幅：${house ? formatPct(house.annual_growth) : '-'}`,
            `人口增量：${population ? formatSigned(population.population_growth, '万') : '-'}`,
            `人口增长率：${population ? formatPct(population.growth_rate, 2) : '-'}`
          ].join('<br/>')
        }
      },
      legend: {
        top: 8,
        right: 10,
        textStyle: {
          color: '#596374'
        }
      },
      grid: {
        left: 54,
        right: 54,
        top: 58,
        bottom: 38
      },
      xAxis: {
        type: 'category',
        data: years,
        axisLabel: { color: '#596374' }
      },
      yAxis: [
        {
          type: 'value',
          name: '房价指数',
          scale: true,
          axisLabel: { color: '#596374' },
          splitLine: {
            lineStyle: {
              type: 'dashed',
              color: '#e4e8ef'
            }
          }
        },
        {
          type: 'value',
          name: '增量/万',
          axisLabel: { color: '#596374' },
          splitLine: { show: false }
        }
      ],
      series: [
        {
          name: `${metricLabel.value}指数`,
          type: 'line',
          smooth: true,
          data: houseValues,
          symbolSize: 8,
          itemStyle: { color: '#15616d' },
          lineStyle: { width: 3.2 },
          markPoint: {
            symbol: 'pin',
            symbolSize: 42,
            data: [{ name: String(selectedYear.value), xAxis: selectedYear.value, yAxis: selectedRow.value.house_index }],
            itemStyle: { color: '#d97706' },
            label: { formatter: String(selectedYear.value), color: '#fff', fontSize: 10, fontWeight: 700 }
          }
        },
        {
          name: '人口增量',
          type: 'bar',
          yAxisIndex: 1,
          data: growthValues.map((value, index) => ({
            value,
            itemStyle: {
              color:
                years[index] === selectedYear.value ? '#d97706' : value >= 0 ? 'rgba(194,65,12,0.82)' : 'rgba(37,99,235,0.82)',
              borderRadius: value >= 0 ? [5, 5, 0, 0] : [0, 0, 5, 5]
            }
          })),
          markLine: {
            symbol: 'none',
            silent: true,
            lineStyle: {
              color: '#94a3b8',
              type: 'dashed'
            },
            data: [{ yAxis: 0 }]
          }
        }
      ]
    },
    true
  )
}

function updateCharts() {
  nextTick(() => {
    updateScatterChart()
    updateTrendChart()
  })
}

function resizeCharts() {
  scatterChart?.resize()
  trendChart?.resize()
}

watch(selectedRegion, () => {
  if (!filteredRows.value.some((item) => item.city === selectedCity.value)) {
    selectedCity.value = filteredRows.value[0]?.city || selectedCity.value
  }
})

watch([selectedRegion, selectedMetric, selectedYear, selectedCity], updateCharts)

onMounted(() => {
  selectedYear.value = availableYears.value[availableYears.value.length - 1] || selectedYear.value
  scatterChart = echarts.init(scatterChartRef.value)
  trendChart = echarts.init(trendChartRef.value)
  updateCharts()
  window.addEventListener('resize', resizeCharts)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', resizeCharts)
  scatterChart?.dispose()
  trendChart?.dispose()
})
</script>

<template>
  <main class="relation-page">
    <header class="relation-header">
      <div class="title-block">
        <span class="eyebrow">Page 04</span>
        <h1>房价-人口耦合关系分析</h1>
        <p>{{ availableYears[0] }} 至 {{ availableYears[availableYears.length - 1] }} · 重点城市 · {{ metricLabel }}</p>
      </div>

      <div class="relation-toolbar" aria-label="图表筛选">
        <div class="relation-segmented" role="tablist" aria-label="住宅类型">
          <button
            v-for="option in metricOptions"
            :key="option.value"
            type="button"
            :class="{ active: selectedMetric === option.value }"
            @click="selectedMetric = option.value"
          >
            {{ option.label }}
          </button>
        </div>

        <label class="relation-select">
          <span>年份</span>
          <select v-model.number="selectedYear">
            <option v-for="year in availableYears" :key="year" :value="year">{{ year }}</option>
          </select>
        </label>

        <div class="region-filter" aria-label="区域筛选">
          <button
            v-for="region in regions"
            :key="region"
            type="button"
            :class="{ active: selectedRegion === region }"
            @click="selectedRegion = region"
          >
            {{ region }}
          </button>
        </div>
      </div>
    </header>

    <section class="relation-grid">
      <section class="relation-panel scatter-panel">
        <div class="relation-panel-head">
          <div>
            <h2>房价-人口四象限耦合散点图</h2>
            <p>{{ selectedYear }}年 · 点大小按人口规模编码</p>
          </div>
          <span v-if="selectedRow" class="relation-chip" :style="{ color: typeColors[selectedRow.type] }">
            {{ selectedRow.type }}
          </span>
        </div>
        <div ref="scatterChartRef" class="relation-chart scatter-chart" aria-label="房价人口四象限耦合散点图"></div>
      </section>

      <aside class="relation-side">
        <section class="relation-panel trend-panel">
          <div class="relation-panel-head compact">
            <div>
              <h2>城市房价-人口双轴趋势图</h2>
              <p>{{ selectedCity }} · {{ periodLabel }}</p>
            </div>
          </div>
          <div ref="trendChartRef" class="relation-chart relation-trend-chart" aria-label="城市房价人口双轴趋势图"></div>
        </section>

        <section v-if="selectedRow" class="relation-panel profile-panel">
          <div class="relation-profile-head">
            <div>
              <span class="eyebrow">{{ selectedRow.region }}</span>
              <h2>{{ selectedRow.city }}</h2>
            </div>
            <span class="type-badge" :style="{ backgroundColor: `${typeColors[selectedRow.type]}18`, color: typeColors[selectedRow.type] }">
              {{ selectedRow.type }}
            </span>
          </div>

          <div class="profile-rings">
            <div v-for="metric in profileMetrics" :key="metric.label" class="profile-ring-item">
              <div class="profile-ring" :style="ringStyle(metric)">
                <span>{{ metric.score }}</span>
              </div>
              <div class="profile-ring-info">
                <span>{{ metric.label }}</span>
                <strong :class="metric.label.includes('涨幅') || metric.label.includes('增量') ? barClass(Number(metric.value.replace('%', '').replace('万', ''))) : ''">
                  {{ metric.value }}
                </strong>
              </div>
            </div>
          </div>

          <p class="relation-summary">{{ relationInsight }}</p>
          <p class="data-source-note">人口口径：WUP 城市/城市群人口估计；单位已换算为万人。</p>
        </section>
      </aside>
    </section>
  </main>
</template>

<style scoped>
.relation-page {
  width: min(1440px, calc(100vw - 32px));
  min-height: calc(100vh - 72px);
  margin: 0 auto;
  padding: 22px 0 28px;
}

.relation-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 20px;
  margin-bottom: 16px;
}

.title-block h1,
.relation-panel h2 {
  margin: 0;
  letter-spacing: 0;
}

.title-block h1 {
  font-size: clamp(28px, 3vw, 42px);
  line-height: 1.08;
}

.title-block p,
.relation-panel-head p,
.data-source-note,
.relation-summary {
  margin: 8px 0 0;
  color: #647084;
  font-size: 13px;
  line-height: 1.45;
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

.relation-toolbar {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  flex-wrap: wrap;
  gap: 10px;
}

.relation-segmented {
  display: inline-grid;
  grid-template-columns: repeat(2, minmax(76px, 1fr));
  padding: 3px;
  border: 1px solid #d6dde8;
  border-radius: 8px;
  background: #ffffff;
}

.relation-segmented button,
.region-filter button {
  border: 0;
  color: #4b5563;
  background: transparent;
  transition:
    color 0.2s ease,
    background 0.2s ease,
    border-color 0.2s ease;
}

.relation-segmented button {
  min-height: 34px;
  padding: 0 12px;
  border-radius: 6px;
  white-space: nowrap;
}

.relation-segmented button.active {
  color: #ffffff;
  background: #15616d;
}

.relation-select {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  height: 42px;
  padding: 0 10px;
  border: 1px solid #d6dde8;
  border-radius: 8px;
  background: #ffffff;
  color: #647084;
  font-size: 13px;
}

.relation-select select {
  min-width: 72px;
  border: 0;
  outline: 0;
  color: #172033;
  background: transparent;
}

.region-filter {
  display: flex;
  gap: 6px;
  overflow-x: auto;
  padding: 2px;
}

.region-filter button {
  min-width: 50px;
  min-height: 38px;
  padding: 0 11px;
  border: 1px solid #d6dde8;
  border-radius: 8px;
  background: #ffffff;
  white-space: nowrap;
}

.region-filter button.active {
  color: #ffffff;
  border-color: #15616d;
  background: #15616d;
}

.relation-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.58fr) minmax(360px, 0.92fr);
  gap: 16px;
  min-width: 0;
}

.relation-panel {
  border: 1px solid #dfe5ee;
  border-radius: 8px;
  background: #ffffff;
  box-shadow: 0 14px 30px rgba(23, 32, 51, 0.07);
  min-width: 0;
}

.scatter-panel,
.trend-panel,
.profile-panel {
  padding: 18px;
}

.relation-panel-head,
.relation-profile-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 14px;
}

.relation-panel-head {
  min-height: 54px;
}

.relation-panel-head.compact {
  min-height: 48px;
}

.relation-panel h2,
.relation-profile-head h2 {
  font-size: 18px;
  line-height: 1.2;
}

.relation-chip,
.type-badge {
  flex: 0 0 auto;
  padding: 7px 10px;
  border-radius: 999px;
  background: #f8fafc;
  font-size: 12px;
  font-weight: 800;
  white-space: nowrap;
}

.relation-chart {
  width: 100%;
  min-width: 0;
}

.scatter-chart {
  height: min(68vh, 710px);
  min-height: 620px;
}

.relation-side {
  display: grid;
  grid-template-rows: minmax(320px, 0.92fr) minmax(360px, auto);
  gap: 16px;
  min-width: 0;
}

.relation-trend-chart {
  height: 300px;
}

.profile-rings {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
  margin-top: 16px;
}

.profile-ring-item {
  display: grid;
  grid-template-columns: 58px minmax(0, 1fr);
  align-items: center;
  gap: 10px;
  min-height: 78px;
  padding: 10px;
  border: 1px solid #e4e8ef;
  border-radius: 8px;
  background: #fbfcfe;
}

.profile-ring {
  display: grid;
  width: 54px;
  height: 54px;
  place-items: center;
  border-radius: 50%;
  background:
    radial-gradient(circle at center, #ffffff 55%, transparent 56%),
    conic-gradient(var(--ring-color) var(--ring-degree), #e2e8f0 var(--ring-degree));
}

.profile-ring span {
  color: #172033;
  font-size: 12px;
  font-weight: 800;
}

.profile-ring-info {
  min-width: 0;
}

.profile-ring-info span {
  display: block;
  color: #667085;
  font-size: 12px;
  line-height: 1.35;
}

.profile-ring-info strong {
  display: block;
  margin-top: 6px;
  color: #172033;
  font-size: 19px;
  line-height: 1.12;
  word-break: break-word;
}

.relation-summary {
  margin-top: 14px;
  padding-top: 14px;
  border-top: 1px solid #e4e8ef;
  color: #344054;
}

.is-positive {
  color: #c2410c;
}

.is-negative {
  color: #2563eb;
}

.is-flat {
  color: #6b7280;
}

@media (max-width: 1180px) {
  .relation-header {
    flex-direction: column;
  }

  .relation-toolbar {
    width: 100%;
    justify-content: flex-start;
  }

  .relation-grid {
    grid-template-columns: 1fr;
  }

  .relation-side {
    grid-template-columns: minmax(0, 1fr) minmax(360px, 0.95fr);
    grid-template-rows: auto;
  }
}

@media (max-width: 820px) {
  .relation-page {
    width: min(100vw - 20px, 760px);
    padding-top: 16px;
  }

  .relation-toolbar,
  .relation-panel-head,
  .relation-profile-head {
    align-items: stretch;
    flex-direction: column;
  }

  .relation-segmented,
  .relation-select {
    width: 100%;
  }

  .relation-select select {
    flex: 1;
  }

  .relation-side {
    grid-template-columns: 1fr;
  }

  .scatter-chart {
    height: 540px;
    min-height: 540px;
  }

  .profile-rings {
    grid-template-columns: 1fr;
  }
}
</style>
