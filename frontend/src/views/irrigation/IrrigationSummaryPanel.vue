<template>
  <div>
    <div class="panel">
      <div class="filter-bar">
        <el-select v-model="query.district" placeholder="按行政区筛选" clearable @change="load">
          <el-option v-for="item in districtOptions" :key="item.district"
                     :label="item.district" :value="item.district" />
        </el-select>
        <el-date-picker v-model="monthRange" type="monthrange" unlink-panels value-format="YYYY-MM"
                        start-placeholder="起始月份" end-placeholder="截止月份" @change="onMonthChange" />
        <el-button type="primary" :icon="'Search'" @click="load">查询</el-button>
        <el-button :icon="'RefreshLeft'" @click="reset">重置</el-button>
        <span class="summary-text" v-if="data?.params">
          异常判定：单次用水量超过同区同月其他记录均值 {{ data.params.anomaly_multiplier }} 倍
        </span>
      </div>
    </div>

    <div class="stat-grid">
      <StatCard label="总用水量" :value="formatNumber(data?.totals?.total_water_amount ?? 0)" unit="m³"
                :hint="`${data?.params?.month_from || ''} 至 ${data?.params?.month_to || ''}`"
                tone="info" icon="Odometer" />
      <StatCard label="灌溉记录" :value="formatNumber(data?.totals?.record_count ?? 0)" unit="条"
                hint="按行政区与月份分组统计" icon="Pouring" />
      <StatCard label="其中折算水量" :value="formatNumber(data?.totals?.estimated_amount ?? 0)" unit="m³"
                hint="按水源点额定流量折算" icon="MagicStick" />
      <StatCard label="异常单次用水" :value="formatNumber(data?.totals?.anomaly_count ?? 0)" unit="条"
                hint="超过同区同月均值倍数的单次用水" tone="warning" icon="Warning" />
    </div>

    <ChartPanel title="各行政区月度用水量" hint="单位：m³，按灌溉日期所在月份汇总"
                :option="chartOption" height="300px" />

    <div class="panel">
      <div class="table-toolbar">
        <span class="panel-title">行政区 × 月份 用水汇总</span>
        <el-button :icon="'Refresh'" text @click="load">刷新</el-button>
      </div>
      <el-table :data="data?.groups || []" v-loading="loading" border stripe
                :row-class-name="rowClassName">
        <el-table-column type="expand">
          <template #default="{ row }">
            <div v-if="row.anomalies.length" class="anomaly-block">
              <div class="anomaly-title">异常偏高的单次用水（{{ row.anomalies.length }} 条）</div>
              <el-table :data="row.anomalies" size="small" border>
                <el-table-column prop="record_no" label="记录编号" width="150" />
                <el-table-column prop="irrigation_date" label="灌溉日期" width="105" />
                <el-table-column prop="green_space_name" label="覆盖绿地" min-width="150"
                                 show-overflow-tooltip />
                <el-table-column prop="team" label="执行班组" width="110" />
                <el-table-column label="单次用水量" width="120" align="right">
                  <template #default="{ row: anomaly }">
                    <span class="anomaly-amount">{{ formatNumber(anomaly.water_amount) }} m³</span>
                    <el-tag v-if="anomaly.is_estimated" type="warning" size="small" effect="plain">折算</el-tag>
                  </template>
                </el-table-column>
                <el-table-column label="同区同月其他均值" width="150" align="right">
                  <template #default="{ row: anomaly }">{{ formatNumber(anomaly.others_avg) }} m³</template>
                </el-table-column>
                <el-table-column label="超出倍数" width="100" align="right">
                  <template #default="{ row: anomaly }">
                    <el-tag type="danger" size="small">{{ anomaly.ratio }} 倍</el-tag>
                  </template>
                </el-table-column>
              </el-table>
            </div>
            <div v-else class="anomaly-empty">该组无异常用水记录</div>
          </template>
        </el-table-column>
        <el-table-column prop="month" label="月份" width="100" />
        <el-table-column prop="district" label="行政区" width="120" />
        <el-table-column prop="record_count" label="灌溉次数" width="100" align="right" />
        <el-table-column label="用水量合计" width="130" align="right">
          <template #default="{ row }">{{ formatNumber(row.total_water_amount) }} m³</template>
        </el-table-column>
        <el-table-column label="其中折算" width="110" align="right">
          <template #default="{ row }">{{ formatNumber(row.estimated_amount) }} m³</template>
        </el-table-column>
        <el-table-column label="平均单次" width="110" align="right">
          <template #default="{ row }">{{ formatNumber(row.avg_amount) }} m³</template>
        </el-table-column>
        <el-table-column label="灌溉时长" width="100" align="right">
          <template #default="{ row }">{{ formatNumber(row.total_duration_hours) }} h</template>
        </el-table-column>
        <el-table-column label="异常用水" width="100" align="center">
          <template #default="{ row }">
            <el-tag v-if="row.anomaly_count" type="danger" size="small">{{ row.anomaly_count }} 条</el-tag>
            <span v-else class="no-anomaly">-</span>
          </template>
        </el-table-column>
      </el-table>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'

import { greenSpaceApi, irrigationRecordApi } from '@/api'
import ChartPanel from '@/components/common/ChartPanel.vue'
import StatCard from '@/components/common/StatCard.vue'
import { formatNumber } from '@/utils/format'
import { PALETTE } from '@/views/dashboard/chartOptions'

const loading = ref(false)
const data = ref(null)
const districtOptions = ref([])

function defaultMonthRange() {
  const end = new Date()
  const start = new Date(end.getFullYear(), end.getMonth() - 5, 1)
  const fmt = (d) => `${d.getFullYear()}-${`${d.getMonth() + 1}`.padStart(2, '0')}`
  return [fmt(start), fmt(end)]
}

const monthRange = ref(defaultMonthRange())
const query = ref({ district: '', month_from: '', month_to: '' })

const chartOption = computed(() => {
  const groups = data.value?.groups || []
  const months = [...new Set(groups.map((g) => g.month))].sort()
  const districts = [...new Set(groups.map((g) => g.district))].sort()
  return {
    color: PALETTE,
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' }, valueFormatter: (v) => `${v} m³` },
    legend: { bottom: 0, icon: 'circle', itemWidth: 8, itemHeight: 8, textStyle: { fontSize: 12, color: '#606266' } },
    grid: { left: 12, right: 12, top: 24, bottom: 40, containLabel: true },
    xAxis: {
      type: 'category',
      data: months,
      axisLabel: { color: '#606266', fontSize: 12 },
    },
    yAxis: {
      type: 'value',
      name: 'm³',
      nameTextStyle: { color: '#909399', fontSize: 12 },
      axisLabel: { color: '#909399', fontSize: 12 },
      splitLine: { lineStyle: { color: '#eef2ef' } },
    },
    series: districts.map((district) => ({
      name: district,
      type: 'bar',
      stack: 'total',
      barMaxWidth: 36,
      data: months.map((month) => {
        const group = groups.find((g) => g.month === month && g.district === district)
        return group ? group.total_water_amount : 0
      }),
    })),
  }
})

function rowClassName({ row }) {
  return row.anomaly_count ? 'row-has-anomaly' : ''
}

function buildParams() {
  const params = {}
  if (query.value.district) params.district = query.value.district
  if (query.value.month_from) params.month_from = query.value.month_from
  if (query.value.month_to) params.month_to = query.value.month_to
  return params
}

async function load() {
  loading.value = true
  try {
    data.value = await irrigationRecordApi.monthlySummary(buildParams())
  } finally {
    loading.value = false
  }
}

function onMonthChange(value) {
  query.value.month_from = value?.[0] || ''
  query.value.month_to = value?.[1] || ''
  load()
}

function reset() {
  query.value = { district: '', month_from: '', month_to: '' }
  monthRange.value = defaultMonthRange()
  onMonthChange(monthRange.value)
}

onMounted(async () => {
  query.value.month_from = monthRange.value[0]
  query.value.month_to = monthRange.value[1]
  load()
  const districts = await greenSpaceApi.districts().catch(() => [])
  districtOptions.value = districts || []
})
</script>

<style scoped>
.panel-title {
  font-weight: 600;
}

.anomaly-block {
  padding: 8px 16px;
}

.anomaly-title {
  margin-bottom: 8px;
  color: #c0653b;
  font-size: 13px;
  font-weight: 600;
}

.anomaly-empty {
  padding: 8px 16px;
  color: #909399;
  font-size: 13px;
}

.anomaly-amount {
  margin-right: 6px;
  color: #c0653b;
  font-weight: 600;
}

.no-anomaly {
  color: #c0c4cc;
}

:deep(.row-has-anomaly) {
  --el-table-tr-bg-color: #fdf6ec;
}
</style>
