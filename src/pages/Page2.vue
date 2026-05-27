<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import * as echarts from 'echarts'
import housePriceData from '../static/house_price_monthly.json'

const metricOptions = [
  {
    value: 'new',
    label: '新建住宅',
    indexField: 'new_house_index',
    yAxisName: '新建住宅价格指数'
  },
  {
    value: 'second',
    label: '二手住宅',
    indexField: 'second_hand_index',
    yAxisName: '二手住宅价格指数'
  }
]

const provinceRegion = {
  北京: '东部',
  天津: '东部',
  河北: '东部',
  上海: '东部',
  江苏: '东部',
  浙江: '东部',
  福建: '东部',
  山东: '东部',
  广东: '东部',
  海南: '东部',
  山西: '中部',
  安徽: '中部',
  江西: '中部',
  河南: '中部',
  湖北: '中部',
  湖南: '中部',
  内蒙古: '西部',
  广西: '西部',
  重庆: '西部',
  四川: '西部',
  贵州: '西部',
  云南: '西部',
  陕西: '西部',
  甘肃: '西部',
  青海: '西部',
  宁夏: '西部',
  新疆: '西部',
  辽宁: '东北',
  吉林: '东北',
  黑龙江: '东北'
}

const palette = ['#15616d', '#c2410c', '#2563eb', '#d97706', '#2f855a', '#7c3aed']
const keyCities = ['北京', '上海', '广州', '深圳', '成都', '武汉', '重庆', '西安', '杭州', '南京']
const maxSelectedCities = 6

const metric = ref('new')
const selectedCities = ref(['北京', '上海', '广州', '深圳', '成都', '武汉'])
const focusCity = ref('北京')
const lineChartRef = ref(null)
const ringChartRef = ref(null)
const focusYear = ref(2026)

let lineChart
let ringChart

const cityNames = computed(() => housePriceData.map((item) => item.city))
const cityMetaMap = computed(() => {
  const map = new Map()
  housePriceData.forEach((item) => {
    map.set(item.city, {
      province: item.province,
      region: provinceRegion[item.province] || '其他'
    })
  })
  return map
})

const metricConfig = computed(() => metricOptions.find((item) => item.value === metric.value))

const dateRange = computed(() => {
  const firstCity = housePriceData[0]
  const first = firstCity?.series?.[0]?.date || ''
  const last = firstCity?.series?.[firstCity.series.length - 1]?.date || ''
  return { first, last }
})

const annualSeries = computed(() => {
  const field = metricConfig.value.indexField
  const result = new Map()
  const years = new Set()

  housePriceData.forEach((cityItem) => {
    let cumulativeIndex = 100
    const yearEndMap = new Map()

    cityItem.series.forEach((row, rowIndex) => {
      if (rowIndex > 0) {
        cumulativeIndex *= Number(row[field]) / 100
      }

      yearEndMap.set(row.year, {
        city: cityItem.city,
        province: cityItem.province,
        region: provinceRegion[cityItem.province] || '其他',
        year: row.year,
        month: row.month,
        date: row.date,
        index: cumulativeIndex
      })
      years.add(row.year)
    })

    const cityYears = [...yearEndMap.keys()].sort((a, b) => a - b)
    const cityAnnual = cityYears.map((year, index) => {
      const current = yearEndMap.get(year)
      const previous = index === 0 ? { index: 100 } : yearEndMap.get(cityYears[index - 1])
      const annualGrowth = ((current.index - previous.index) / previous.index) * 100
      return {
        ...current,
        annualGrowth,
        cumulativeGrowth: current.index - 100
      }
    })

    result.set(cityItem.city, cityAnnual)
  })

  return {
    years: [...years].sort((a, b) => a - b),
    byCity: result
  }
})

const availableYears = computed(() => annualSeries.value.years)

const rankingByYear = computed(() => {
  const rankMap = new Map()
  availableYears.value.forEach((year) => {
    const sorted = cityNames.value
      .map((city) => annualSeries.value.byCity.get(city)?.find((item) => item.year === year))
      .filter(Boolean)
      .sort((a, b) => b.annualGrowth - a.annualGrowth)

    const yearRanks = new Map()
    sorted.forEach((item, index) => {
      yearRanks.set(item.city, index + 1)
    })
    rankMap.set(year, yearRanks)
  })
  return rankMap
})

const focusRecord = computed(() => {
  const citySeries = annualSeries.value.byCity.get(focusCity.value) || []
  return citySeries.find((item) => item.year === focusYear.value) || citySeries[citySeries.length - 1]
})

const detailRows = computed(() => {
  const record = focusRecord.value
  if (!record) return []

  const sameYearRecords = cityNames.value
    .map((city) => annualSeries.value.byCity.get(city)?.find((item) => item.year === record.year))
    .filter(Boolean)
  const regionRecords = sameYearRecords.filter((item) => item.region === record.region)
  const nationalAvg = average(sameYearRecords.map((item) => item.annualGrowth))
  const regionAvg = average(regionRecords.map((item) => item.annualGrowth))
  const maxAbs = Math.max(Math.abs(record.annualGrowth), Math.abs(regionAvg), Math.abs(nationalAvg), 1)

  return [
    {
      label: '本城市',
      value: record.annualGrowth,
      width: (Math.abs(record.annualGrowth) / maxAbs) * 100
    },
    {
      label: `${record.region}均值`,
      value: regionAvg,
      width: (Math.abs(regionAvg) / maxAbs) * 100
    },
    {
      label: '70城均值',
      value: nationalAvg,
      width: (Math.abs(nationalAvg) / maxAbs) * 100
    }
  ]
})

const rankInfo = computed(() => {
  const record = focusRecord.value
  if (!record) return { current: '-', change: '—', changeClass: '' }

  const currentRank = rankingByYear.value.get(record.year)?.get(record.city)
  const prevYear = previousYear(record.year)
  const previousRank = prevYear ? rankingByYear.value.get(prevYear)?.get(record.city) : undefined

  if (!currentRank || !previousRank) {
    return { current: currentRank ? `第 ${currentRank}` : '-', change: '—', changeClass: '' }
  }

  const delta = previousRank - currentRank
  if (delta > 0) return { current: `第 ${currentRank}`, change: `上升 ${delta}`, changeClass: 'positive' }
  if (delta < 0) return { current: `第 ${currentRank}`, change: `下降 ${Math.abs(delta)}`, changeClass: 'negative' }
  return { current: `第 ${currentRank}`, change: '持平', changeClass: '' }
})

const rangeLabel = computed(() => `${dateRange.value.first} 至 ${dateRange.value.last}`)
const selectedMetricLabel = computed(() => metricConfig.value.label)
const lineSubtitle = computed(() => `指数基准：${dateRange.value.first}=100；当前数据截至 ${dateRange.value.last}`)

const periodLabel = computed(() => {
  const record = focusRecord.value
  if (!record) return ''
  return record.month === 12 ? `${record.year} 年` : `${record.year} 年截至 ${record.month} 月`
})

const insightText = computed(() => {
  const record = focusRecord.value
  const national = detailRows.value.find((row) => row.label === '70城均值')
  if (!record || !national) return ''

  const gap = record.annualGrowth - national.value
  const direction = gap >= 0 ? '高于' : '低于'
  return `${record.city}${periodLabel.value}${selectedMetricLabel.value}涨幅${formatPct(record.annualGrowth)}，${direction}70城均值 ${Math.abs(gap).toFixed(1)} 个百分点。`
})

function average(values) {
  if (!values.length) return 0
  return values.reduce((sum, item) => sum + item, 0) / values.length
}

function previousYear(year) {
  const index = availableYears.value.indexOf(year)
  return index > 0 ? availableYears.value[index - 1] : undefined
}

function formatNumber(value, digits = 1) {
  if (value === undefined || Number.isNaN(value)) return '-'
  return Number(value).toFixed(digits)
}

function formatPct(value) {
  if (value === undefined || Number.isNaN(value)) return '-'
  return `${value > 0 ? '+' : ''}${value.toFixed(1)}%`
}

function barClass(value) {
  if (value > 0) return 'is-positive'
  if (value < 0) return 'is-negative'
  return 'is-flat'
}

function ensureCitySelected(city) {
  if (!selectedCities.value.includes(city)) {
    const next = [...selectedCities.value, city]
    selectedCities.value = next.slice(Math.max(0, next.length - maxSelectedCities))
  }
}

function toggleCity(city) {
  if (selectedCities.value.includes(city)) {
    if (selectedCities.value.length === 1) return
    selectedCities.value = selectedCities.value.filter((item) => item !== city)
    if (focusCity.value === city) {
      focusCity.value = selectedCities.value[0]
    }
    return
  }

  const next = [...selectedCities.value, city]
  selectedCities.value = next.slice(Math.max(0, next.length - maxSelectedCities))
  focusCity.value = city
}

function renderLineChart() {
  if (!lineChart) return

  const selectedSeries = selectedCities.value
    .map((city, cityIndex) => {
      const citySeries = annualSeries.value.byCity.get(city) || []
      const data = citySeries.map((item) => ({
        value: Number(item.index.toFixed(2)),
        city: item.city,
        year: item.year,
        month: item.month,
        annualGrowth: item.annualGrowth,
        cumulativeGrowth: item.cumulativeGrowth,
        symbol: 'triangle',
        symbolRotate: item.annualGrowth >= 0 ? 0 : 180,
        symbolSize: Math.min(18, 7 + Math.abs(item.annualGrowth) * 0.7)
      }))

      return {
        name: city,
        type: 'line',
        smooth: true,
        showSymbol: true,
        symbol: 'triangle',
        lineStyle: {
          width: city === focusCity.value ? 3.5 : 2,
          opacity: city === focusCity.value ? 1 : 0.68
        },
        itemStyle: {
          color: palette[cityIndex % palette.length]
        },
        emphasis: {
          focus: 'series',
          scale: 1.2
        },
        data
      }
    })

  const values = selectedSeries.flatMap((series) => series.data.map((item) => item.value))
  const minValue = Math.floor((Math.min(...values) - 3) / 5) * 5
  const maxValue = Math.ceil((Math.max(...values) + 3) / 5) * 5

  lineChart.setOption(
    {
      color: palette,
      animationDuration: 500,
      tooltip: {
        trigger: 'item',
        borderWidth: 0,
        backgroundColor: 'rgba(18, 24, 38, 0.94)',
        textStyle: {
          color: '#fff'
        },
        formatter(params) {
          const item = params.data
          const label = item.month === 12 ? `${item.year}` : `${item.year} 截至 ${item.month} 月`
          return [
            `<strong>${item.city} · ${label}</strong>`,
            `${metricConfig.value.yAxisName}：${formatNumber(item.value)}`,
            `当期涨幅：${formatPct(item.annualGrowth)}`,
            `累计涨幅：${formatPct(item.cumulativeGrowth)}`
          ].join('<br/>')
        }
      },
      legend: {
        top: 4,
        right: 8,
        itemGap: 16,
        textStyle: {
          color: '#4b5563',
          fontSize: 12
        }
      },
      grid: {
        left: 58,
        right: 28,
        top: 68,
        bottom: 48
      },
      xAxis: {
        type: 'category',
        data: availableYears.value,
        boundaryGap: false,
        axisTick: {
          alignWithLabel: true
        },
        axisLine: {
          lineStyle: {
            color: '#d5dbe5'
          }
        },
        axisLabel: {
          color: '#5d6676'
        }
      },
      yAxis: {
        type: 'value',
        name: '价格指数',
        min: minValue,
        max: maxValue,
        nameTextStyle: {
          color: '#5d6676',
          padding: [0, 0, 8, 0]
        },
        splitLine: {
          lineStyle: {
            color: '#e4e8ef',
            type: 'dashed'
          }
        },
        axisLabel: {
          color: '#5d6676'
        }
      },
      series: selectedSeries
    },
    true
  )

  lineChart.off('click')
  lineChart.on('click', (params) => {
    if (!params.data?.city) return
    focusCity.value = params.data.city
    focusYear.value = params.data.year
    ensureCitySelected(params.data.city)
  })
}

function renderRingChart() {
  if (!ringChart || !focusRecord.value) return

  const citySeries = annualSeries.value.byCity.get(focusCity.value) || []
  const data = citySeries.map((item) => {
    const active = item.year === focusRecord.value.year
    return {
      name: String(item.year),
      value: Math.max(Math.abs(item.annualGrowth), 0.3),
      annualGrowth: item.annualGrowth,
      cumulativeGrowth: item.cumulativeGrowth,
      selected: active,
      itemStyle: {
        color: active ? '#d97706' : item.annualGrowth >= 0 ? 'rgba(194,65,12,0.78)' : 'rgba(37,99,235,0.72)',
        borderColor: active ? '#111827' : '#ffffff',
        borderWidth: active ? 2 : 1
      }
    }
  })

  ringChart.setOption(
    {
      animationDuration: 500,
      tooltip: {
        trigger: 'item',
        borderWidth: 0,
        backgroundColor: 'rgba(18, 24, 38, 0.94)',
        textStyle: {
          color: '#fff'
        },
        formatter(params) {
          return [
            `<strong>${focusCity.value} · ${params.name}</strong>`,
            `当期涨幅：${formatPct(params.data.annualGrowth)}`,
            `累计涨幅：${formatPct(params.data.cumulativeGrowth)}`
          ].join('<br/>')
        }
      },
      graphic: [
        {
          type: 'text',
          left: 'center',
          top: '41%',
          style: {
            text: focusCity.value,
            fill: '#172033',
            fontSize: 24,
            fontWeight: 700,
            textAlign: 'center'
          }
        },
        {
          type: 'text',
          left: 'center',
          top: '53%',
          style: {
            text: `${focusRecord.value.year} ${formatPct(focusRecord.value.annualGrowth)}`,
            fill: focusRecord.value.annualGrowth >= 0 ? '#c2410c' : '#2563eb',
            fontSize: 15,
            fontWeight: 700,
            textAlign: 'center'
          }
        }
      ],
      series: [
        {
          name: '涨幅年轮',
          type: 'pie',
          radius: ['47%', '78%'],
          center: ['50%', '51%'],
          roseType: 'area',
          selectedMode: 'single',
          selectedOffset: 8,
          avoidLabelOverlap: true,
          label: {
            color: '#596374',
            fontSize: 11,
            formatter: '{b}'
          },
          labelLine: {
            length: 8,
            length2: 5
          },
          data
        }
      ]
    },
    true
  )

  ringChart.off('click')
  ringChart.on('click', (params) => {
    focusYear.value = Number(params.name)
  })
}

function renderCharts() {
  nextTick(() => {
    renderLineChart()
    renderRingChart()
  })
}

function resizeCharts() {
  lineChart?.resize()
  ringChart?.resize()
}

watch(focusCity, (city) => ensureCitySelected(city))
watch([metric, selectedCities, focusCity, focusYear], renderCharts, { deep: true })

onMounted(() => {
  focusYear.value = availableYears.value[availableYears.value.length - 1]
  lineChart = echarts.init(lineChartRef.value)
  ringChart = echarts.init(ringChartRef.value)
  renderCharts()
  window.addEventListener('resize', resizeCharts)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', resizeCharts)
  lineChart?.dispose()
  ringChart?.dispose()
})
</script>

<template>
  <main class="page-shell">
    <header class="topbar">
      <div class="title-block">
        <span class="eyebrow">Page 02</span>
        <h1>房价变化分析</h1>
        <p>{{ rangeLabel }} · 70 城 · {{ selectedMetricLabel }}</p>
      </div>

      <div class="toolbar" aria-label="图表筛选">
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

        <label class="select-field">
          <span>城市</span>
          <select v-model="focusCity">
            <option v-for="city in cityNames" :key="city" :value="city">{{ city }}</option>
          </select>
        </label>

        <label class="select-field">
          <span>年份</span>
          <select v-model.number="focusYear">
            <option v-for="year in availableYears" :key="year" :value="year">{{ year }}</option>
          </select>
        </label>
      </div>
    </header>

    <nav class="city-strip" aria-label="对比城市">
      <button
        v-for="city in keyCities"
        :key="city"
        type="button"
        :class="{ active: selectedCities.includes(city) }"
        @click="toggleCity(city)"
      >
        {{ city }}
      </button>
    </nav>

    <section class="dashboard-grid">
      <section class="panel trajectory-panel">
        <div class="panel-head">
          <div>
            <h2>城市房价演化轨迹</h2>
            <p>{{ lineSubtitle }}</p>
          </div>
          <div class="node-legend" aria-label="节点图例">
            <span class="legend-up">▲ 上涨</span>
            <span class="legend-down">▼ 下降</span>
          </div>
        </div>
        <div ref="lineChartRef" class="chart line-chart" aria-label="城市房价演化轨迹图"></div>
      </section>

      <aside class="side-column">
        <section class="panel ring-panel">
          <div class="panel-head compact">
            <div>
              <h2>城市房价涨幅年轮</h2>
              <p>{{ focusCity }} · {{ periodLabel }}</p>
            </div>
          </div>
          <div ref="ringChartRef" class="chart ring-chart" aria-label="城市房价涨幅年轮图"></div>
        </section>

        <section v-if="focusRecord" class="panel detail-panel">
          <div class="detail-head">
            <div>
              <span class="eyebrow">{{ cityMetaMap.get(focusCity)?.region }}</span>
              <h2>{{ focusCity }}</h2>
            </div>
            <span class="year-pill">{{ periodLabel }}</span>
          </div>

          <div class="metric-grid">
            <div class="metric-card">
              <span>{{ selectedMetricLabel }}指数</span>
              <strong>{{ formatNumber(focusRecord.index) }}</strong>
            </div>
            <div class="metric-card">
              <span>当期涨幅</span>
              <strong :class="barClass(focusRecord.annualGrowth)">{{ formatPct(focusRecord.annualGrowth) }}</strong>
            </div>
            <div class="metric-card">
              <span>累计涨幅</span>
              <strong :class="barClass(focusRecord.cumulativeGrowth)">{{ formatPct(focusRecord.cumulativeGrowth) }}</strong>
            </div>
            <div class="metric-card">
              <span>涨幅排名</span>
              <strong>{{ rankInfo.current }}</strong>
              <small :class="rankInfo.changeClass">{{ rankInfo.change }}</small>
            </div>
          </div>

          <div class="compare-block">
            <div class="compare-title">区域对比</div>
            <div v-for="row in detailRows" :key="row.label" class="bar-row">
              <span>{{ row.label }}</span>
              <div class="bar-track">
                <div class="bar-fill" :class="barClass(row.value)" :style="{ width: `${row.width}%` }"></div>
              </div>
              <strong :class="barClass(row.value)">{{ formatPct(row.value) }}</strong>
            </div>
          </div>

          <p class="insight">{{ insightText }}</p>
        </section>
      </aside>
    </section>
  </main>
</template>

<style>
:root {
  color: #172033;
  background: #f5f7fa;
  font-family:
    Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI",
    "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif;
  font-synthesis: none;
  text-rendering: optimizeLegibility;
}

* {
  box-sizing: border-box;
}

body {
  margin: 0;
  min-width: 320px;
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.86), rgba(245, 247, 250, 0.95)),
    #f5f7fa;
}

button,
select {
  font: inherit;
}

button {
  cursor: pointer;
}

.page-shell {
  width: min(1440px, calc(100vw - 32px));
  min-height: 100vh;
  margin: 0 auto;
  padding: 24px 0 28px;
}

.topbar {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 20px;
  margin-bottom: 14px;
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

.title-block p {
  margin: 8px 0 0;
  color: #647084;
  font-size: 14px;
}

.eyebrow {
  display: inline-flex;
  margin-bottom: 6px;
  color: #15616d;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0;
  text-transform: uppercase;
}

.toolbar {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  flex-wrap: wrap;
  gap: 10px;
}

.segmented {
  display: inline-grid;
  grid-template-columns: repeat(2, minmax(76px, 1fr));
  padding: 3px;
  border: 1px solid #d6dde8;
  border-radius: 8px;
  background: #ffffff;
}

.segmented button,
.city-strip button {
  border: 0;
  color: #4b5563;
  background: transparent;
  transition:
    color 0.2s ease,
    background 0.2s ease,
    border-color 0.2s ease;
}

.segmented button {
  min-height: 34px;
  padding: 0 12px;
  border-radius: 6px;
  white-space: nowrap;
}

.segmented button.active {
  color: #ffffff;
  background: #15616d;
}

.select-field {
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

.select-field select {
  min-width: 86px;
  border: 0;
  outline: 0;
  color: #172033;
  background: transparent;
}

.city-strip {
  display: flex;
  gap: 8px;
  overflow-x: auto;
  padding: 8px 0 16px;
}

.city-strip button {
  min-width: 58px;
  height: 34px;
  padding: 0 14px;
  border: 1px solid #d6dde8;
  border-radius: 999px;
  background: #ffffff;
  white-space: nowrap;
}

.city-strip button.active {
  color: #ffffff;
  border-color: #15616d;
  background: #15616d;
}

.dashboard-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(340px, 390px);
  gap: 16px;
  align-items: stretch;
  min-width: 0;
}

.panel {
  border: 1px solid #dfe5ee;
  border-radius: 8px;
  background: #ffffff;
  box-shadow: 0 14px 30px rgba(23, 32, 51, 0.07);
  min-width: 0;
}

.trajectory-panel,
.ring-panel,
.detail-panel {
  padding: 18px;
}

.panel-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  min-height: 50px;
}

.panel-head h2,
.detail-head h2 {
  font-size: 18px;
  line-height: 1.2;
}

.panel-head p {
  margin: 7px 0 0;
  color: #647084;
  font-size: 13px;
  line-height: 1.45;
}

.panel-head.compact {
  min-height: 42px;
}

.node-legend {
  display: inline-flex;
  align-items: center;
  gap: 12px;
  flex: 0 0 auto;
  color: #647084;
  font-size: 12px;
}

.legend-up,
.is-positive,
.positive {
  color: #c2410c;
}

.legend-down,
.is-negative,
.negative {
  color: #2563eb;
}

.is-flat {
  color: #6b7280;
}

.chart {
  width: 100%;
  min-width: 0;
}

.line-chart {
  height: min(66vh, 620px);
  min-height: 520px;
}

.side-column {
  display: grid;
  grid-template-rows: minmax(300px, 0.9fr) auto;
  gap: 16px;
  min-width: 0;
}

.ring-chart {
  height: 300px;
}

.detail-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.year-pill {
  flex: 0 0 auto;
  max-width: 154px;
  padding: 7px 10px;
  border-radius: 999px;
  background: #eef6f7;
  color: #15616d;
  font-size: 12px;
  font-weight: 700;
  text-align: center;
}

.metric-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
  margin-top: 16px;
}

.metric-card {
  min-height: 84px;
  padding: 12px;
  border: 1px solid #e4e8ef;
  border-radius: 8px;
  background: #fbfcfe;
}

.metric-card span,
.metric-card small {
  display: block;
  color: #667085;
  font-size: 12px;
  line-height: 1.35;
}

.metric-card strong {
  display: block;
  margin-top: 8px;
  color: #172033;
  font-size: 24px;
  line-height: 1.05;
}

.metric-card small {
  margin-top: 7px;
  font-weight: 700;
}

.compare-block {
  margin-top: 16px;
  padding-top: 14px;
  border-top: 1px solid #e4e8ef;
}

.compare-title {
  margin-bottom: 10px;
  color: #172033;
  font-size: 14px;
  font-weight: 700;
}

.bar-row {
  display: grid;
  grid-template-columns: 68px minmax(90px, 1fr) 58px;
  align-items: center;
  gap: 10px;
  min-height: 30px;
  color: #667085;
  font-size: 12px;
}

.bar-track {
  height: 8px;
  overflow: hidden;
  border-radius: 999px;
  background: #edf1f6;
}

.bar-fill {
  height: 100%;
  min-width: 3px;
  border-radius: inherit;
}

.bar-fill.is-positive {
  background: linear-gradient(90deg, #f59e0b, #c2410c);
}

.bar-fill.is-negative {
  background: linear-gradient(90deg, #38bdf8, #2563eb);
}

.bar-fill.is-flat {
  background: #94a3b8;
}

.bar-row strong {
  text-align: right;
}

.insight {
  margin: 14px 0 0;
  padding: 11px 12px;
  border-left: 3px solid #15616d;
  border-radius: 6px;
  background: #f1f7f7;
  color: #394557;
  font-size: 13px;
  line-height: 1.5;
}

@media (max-width: 1080px) {
  .topbar {
    flex-direction: column;
  }

  .toolbar {
    width: 100%;
    justify-content: flex-start;
  }

  .dashboard-grid {
    grid-template-columns: 1fr;
  }

  .side-column {
    grid-template-columns: minmax(0, 1fr) minmax(320px, 380px);
    grid-template-rows: auto;
  }

  .line-chart {
    height: 520px;
  }
}

@media (max-width: 760px) {
  .page-shell {
    width: min(100vw - 20px, 720px);
    padding-top: 16px;
  }

  .toolbar,
  .select-field,
  .segmented {
    width: 100%;
  }

  .select-field {
    justify-content: space-between;
  }

  .select-field select {
    flex: 1;
  }

  .city-strip {
    flex-wrap: wrap;
    overflow-x: visible;
  }

  .city-strip button {
    flex: 1 1 calc(20% - 8px);
    min-width: 58px;
  }

  .side-column {
    grid-template-columns: 1fr;
  }

  .panel-head {
    flex-direction: column;
  }

  .line-chart {
    height: 460px;
    min-height: 460px;
  }

  .metric-grid {
    grid-template-columns: 1fr;
  }
}
</style>
