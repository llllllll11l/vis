import housePriceData from '../static/house_price_monthly.json'
import populationFlowData from '../static/province_population_flow.json'

export const regionOrder = ['东部', '中部', '西部', '东北']

export const regionColors = {
  东部: '#c2410c',
  中部: '#d97706',
  西部: '#2f855a',
  东北: '#2563eb'
}

export const provinceFullNames = {
  北京: '北京市',
  天津: '天津市',
  河北: '河北省',
  山西: '山西省',
  内蒙古: '内蒙古自治区',
  辽宁: '辽宁省',
  吉林: '吉林省',
  黑龙江: '黑龙江省',
  上海: '上海市',
  江苏: '江苏省',
  浙江: '浙江省',
  安徽: '安徽省',
  福建: '福建省',
  江西: '江西省',
  山东: '山东省',
  河南: '河南省',
  湖北: '湖北省',
  湖南: '湖南省',
  广东: '广东省',
  广西: '广西壮族自治区',
  海南: '海南省',
  重庆: '重庆市',
  四川: '四川省',
  贵州: '贵州省',
  云南: '云南省',
  西藏: '西藏自治区',
  陕西: '陕西省',
  甘肃: '甘肃省',
  青海: '青海省',
  宁夏: '宁夏回族自治区',
  新疆: '新疆维吾尔自治区'
}

export const fullProvinceToShort = Object.fromEntries(
  Object.entries(provinceFullNames).map(([shortName, fullName]) => [fullName, shortName])
)

export { populationFlowData }

const houseCache = new Map()
const cityHouseCache = new Map()

export const provinceRegionMap = Object.fromEntries(
  populationFlowData.map((item) => [item.province, item.region])
)

export function formatPct(value, digits = 1) {
  if (value === null || value === undefined || Number.isNaN(value)) return '-'
  return `${value > 0 ? '+' : ''}${Number(value).toFixed(digits)}%`
}

export function formatSigned(value, unit = '') {
  if (value === null || value === undefined || Number.isNaN(value)) return '-'
  return `${value > 0 ? '+' : ''}${Number(value).toFixed(1).replace(/\\.0$/, '')}${unit}`
}

export function formatNumber(value, digits = 1) {
  if (value === null || value === undefined || Number.isNaN(value)) return '-'
  return Number(value).toFixed(digits)
}

export function getPopulationYears() {
  return populationFlowData[0]?.series.map((item) => item.year) || []
}

export function getPopulationRecord(province, year) {
  return populationFlowData.find((item) => item.province === province)?.series.find((item) => item.year === year)
}

export function getPopulationByYear(year) {
  return populationFlowData
    .map((province) => {
      const record = province.series.find((item) => item.year === year)
      if (!record) return null
      return {
        province: province.province,
        region: province.region,
        coordinate: province.coordinate,
        ...record
      }
    })
    .filter(Boolean)
}

export function getProvinceHouseAnnual(metric = 'new') {
  if (houseCache.has(metric)) return houseCache.get(metric)

  const field = metric === 'second' ? 'second_hand_index' : 'new_house_index'
  const cityAnnual = []

  housePriceData.forEach((cityItem) => {
    let cumulativeIndex = 100
    const yearEnd = new Map()

    cityItem.series.forEach((row, rowIndex) => {
      if (rowIndex > 0) {
        cumulativeIndex *= Number(row[field]) / 100
      }
      yearEnd.set(row.year, {
        year: row.year,
        month: row.month,
        date: row.date,
        index: cumulativeIndex
      })
    })

    cityAnnual.push({
      city: cityItem.city,
      province: cityItem.province,
      series: [...yearEnd.values()].sort((a, b) => a.year - b.year)
    })
  })

  const byProvinceRaw = new Map()
  cityAnnual.forEach((cityItem) => {
    if (!byProvinceRaw.has(cityItem.province)) {
      byProvinceRaw.set(cityItem.province, new Map())
    }

    const provinceMap = byProvinceRaw.get(cityItem.province)
    cityItem.series.forEach((record) => {
      if (!provinceMap.has(record.year)) {
        provinceMap.set(record.year, [])
      }
      provinceMap.get(record.year).push(record)
    })
  })

  const byProvince = new Map()
  byProvinceRaw.forEach((yearMap, province) => {
    const years = [...yearMap.keys()].sort((a, b) => a - b)
    const series = years.map((year, index) => {
      const records = yearMap.get(year)
      const currentIndex = average(records.map((item) => item.index))
      const previousIndex = index === 0 ? 100 : average(yearMap.get(years[index - 1]).map((item) => item.index))
      return {
        year,
        month: Math.max(...records.map((item) => item.month)),
        date: records[records.length - 1].date,
        index: Number(currentIndex.toFixed(2)),
        annual_growth: Number((((currentIndex - previousIndex) / previousIndex) * 100).toFixed(2)),
        city_count: records.length
      }
    })
    byProvince.set(province, series)
  })

  const allYears = [...new Set([...byProvince.values()].flatMap((series) => series.map((item) => item.year)))].sort(
    (a, b) => a - b
  )

  const result = {
    metric,
    years: allYears,
    byProvince
  }

  houseCache.set(metric, result)
  return result
}

export function getHouseRecord(province, year, metric = 'new') {
  return getProvinceHouseAnnual(metric).byProvince.get(province)?.find((item) => item.year === year)
}

export function getProvinceRegion(province) {
  return provinceRegionMap[province] || '其他'
}

export function getCityHouseAnnual(metric = 'new') {
  if (cityHouseCache.has(metric)) return cityHouseCache.get(metric)

  const field = metric === 'second' ? 'second_hand_index' : 'new_house_index'
  const byCity = new Map()
  const allYears = new Set()

  housePriceData.forEach((cityItem) => {
    let cumulativeIndex = 100
    const yearEnd = new Map()

    cityItem.series.forEach((row, rowIndex) => {
      if (rowIndex > 0) {
        cumulativeIndex *= Number(row[field]) / 100
      }

      yearEnd.set(row.year, {
        city: cityItem.city,
        province: cityItem.province,
        region: getProvinceRegion(cityItem.province),
        year: row.year,
        month: row.month,
        date: row.date,
        index: cumulativeIndex
      })
      allYears.add(row.year)
    })

    const years = [...yearEnd.keys()].sort((a, b) => a - b)
    const series = years.map((year, index) => {
      const current = yearEnd.get(year)
      const previous = index === 0 ? { index: 100 } : yearEnd.get(years[index - 1])
      return {
        ...current,
        index: Number(current.index.toFixed(2)),
        annual_growth: Number((((current.index - previous.index) / previous.index) * 100).toFixed(2)),
        cumulative_growth: Number((current.index - 100).toFixed(2))
      }
    })

    byCity.set(cityItem.city, series)
  })

  const result = {
    metric,
    years: [...allYears].sort((a, b) => a - b),
    byCity
  }

  cityHouseCache.set(metric, result)
  return result
}

export function getCityHouseRecord(city, year, metric = 'new') {
  return getCityHouseAnnual(metric).byCity.get(city)?.find((item) => item.year === year)
}

export function average(values) {
  const valid = values.filter((item) => item !== null && item !== undefined && !Number.isNaN(item))
  if (!valid.length) return 0
  return valid.reduce((sum, item) => sum + item, 0) / valid.length
}
