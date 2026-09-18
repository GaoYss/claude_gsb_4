<template>
  <div class="page">
    <PageHeader title="灌溉用水记录" description="每次灌溉登记用水量或灌溉时长、覆盖绿地与执行班组，按行政区与月份汇总并标记异常偏高用水">
      <template #actions>
        <el-button type="primary" :icon="'Plus'" @click="formDialog.open()">登记灌溉用水</el-button>
      </template>
    </PageHeader>

    <div class="panel">
      <div class="filter-bar">
        <el-input v-model="filters.keyword" placeholder="记录编号 / 班组 / 登记人" clearable
                  :prefix-icon="'Search'" @keyup.enter="search" @clear="search" />
        <div style="width: 220px">
          <GreenSpaceSelect v-model="filters.green_space_id" placeholder="按覆盖绿地筛选" @update:model-value="search" />
        </div>
        <el-select v-model="filters.district" placeholder="行政区" clearable @change="search">
          <el-option v-for="item in districts" :key="item.district" :label="item.district" :value="item.district" />
        </el-select>
        <el-select v-model="filters.method" placeholder="灌溉方式" clearable @change="search">
          <el-option v-for="item in methodOptions" :key="item.value" :label="item.label" :value="item.value" />
        </el-select>
        <el-date-picker v-model="dateRange" type="daterange" unlink-panels value-format="YYYY-MM-DD"
                        start-placeholder="灌溉日期起" end-placeholder="灌溉日期止" @change="onDateChange" />
        <el-checkbox v-model="filters.abnormal_only" @change="search">仅看异常偏高</el-checkbox>
        <el-button type="primary" :icon="'Search'" @click="search">查询</el-button>
        <el-button :icon="'RefreshLeft'" @click="reset">重置</el-button>
      </div>
    </div>

    <div class="stat-grid">
      <StatCard label="用水总量" :value="formatNumber(summary?.total_volume ?? 0)" unit="吨"
                :hint="`共 ${formatNumber(summary?.total_count ?? 0)} 次灌溉`" icon="Coffee" />
      <StatCard label="灌溉总时长" :value="formatMinutes(summary?.total_duration_minutes ?? 0)"
                hint="按登记的灌溉时长累计" tone="info" icon="Timer" />
      <StatCard label="异常偏高" :value="formatNumber(summary?.abnormal_count ?? 0)" unit="次"
                hint="同行政区同月份用水量离群偏高"
                :tone="(summary?.abnormal_count ?? 0) ? 'danger' : 'default'" icon="Warning" />
      <StatCard label="覆盖行政区·月" :value="formatNumber(summary?.monthly_by_district?.length ?? 0)" unit="组"
                hint="按行政区 × 自然月汇总" icon="MapLocation" />
    </div>

    <div class="panel">
      <div class="table-toolbar">
        <span class="summary-text">
          共 <strong>{{ meta.total }}</strong> 条灌溉记录，
          用水量合计 <strong>{{ formatNumber(summary?.total_volume ?? 0) }}</strong> 吨，
          异常偏高 <strong>{{ formatNumber(summary?.abnormal_count ?? 0) }}</strong> 次
        </span>
        <el-button :icon="'Refresh'" text @click="load">刷新</el-button>
      </div>

      <el-table :data="items" v-loading="loading" border stripe :row-class-name="rowClassName"
                @sort-change="onSortChange">
        <el-table-column type="expand">
          <template #default="{ row }">
            <div class="expand-detail">
              <span><b>水源点：</b>{{ row.water_source ? `${row.water_source.source_no} ${row.water_source.name}` : '-' }}</span>
              <span><b>覆盖面积：</b>{{ formatArea(row.covered_area_sqm) }}</span>
              <span><b>执行班组：</b>{{ row.worker_team || '-' }}</span>
              <span><b>登记人：</b>{{ row.operator || '-' }}</span>
              <span><b>关联养护记录：</b>{{ row.record ? `${row.record.record_no}（${formatDate(row.record.record_date)}）` : '未关联' }}</span>
              <span><b>登记时间：</b>{{ formatDateTime(row.created_at) }}</span>
              <span v-if="row.remark"><b>备注：</b>{{ row.remark }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="record_no" label="编号" width="150" />
        <el-table-column label="覆盖绿地" min-width="160" show-overflow-tooltip>
          <template #default="{ row }">
            <div class="cell-main">{{ row.green_space?.name || '-' }}</div>
            <div class="cell-sub">{{ row.green_space?.district || '-' }}</div>
          </template>
        </el-table-column>
        <el-table-column label="灌溉日期" width="105">
          <template #default="{ row }">{{ formatDate(row.irrigation_date) }}</template>
        </el-table-column>
        <el-table-column label="灌溉方式" width="100">
          <template #default="{ row }">
            <EnumTag group="irrigation_method" :value="row.method" :label="row.method_label" />
          </template>
        </el-table-column>
        <el-table-column label="用水量（吨）" width="130" align="right" sortable="custom" prop="water_volume">
          <template #default="{ row }">
            <span :class="{ 'volume-abnormal': row.is_abnormal }">
              {{ row.water_volume === null ? '仅登记时长' : formatNumber(row.water_volume) }}
            </span>
            <el-tag v-if="row.is_abnormal" type="danger" size="small" effect="dark" class="abnormal-tag">
              异常偏高
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="灌溉时长" width="105" align="right">
          <template #default="{ row }">{{ row.duration_minutes ? formatMinutes(row.duration_minutes) : '-' }}</template>
        </el-table-column>
        <el-table-column label="执行班组" width="110">
          <template #default="{ row }">{{ row.worker_team || '-' }}</template>
        </el-table-column>
        <el-table-column label="操作" width="130" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="formDialog.open(row)">编辑</el-button>
            <el-button link type="danger" @click="remove(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-pagination
        class="pager"
        background
        layout="total, sizes, prev, pager, next, jumper"
        :total="meta.total"
        :current-page="meta.page"
        :page-size="meta.page_size"
        :page-sizes="[10, 20, 50]"
        @current-change="handlePageChange"
        @size-change="handleSizeChange"
      />
    </div>

    <div class="summary-grid">
      <div class="panel">
        <div class="table-toolbar">
          <span class="panel-title">行政区 × 月份用水量汇总</span>
          <span class="summary-text">按当前筛选条件统计</span>
        </div>
        <el-table :data="summary?.monthly_by_district || []" size="small" border stripe empty-text="暂无数据">
          <el-table-column prop="district" label="行政区" width="100" />
          <el-table-column prop="month" label="月份" width="100" />
          <el-table-column prop="count" label="灌溉次数" width="90" align="right" />
          <el-table-column label="用水量（吨）" width="130" align="right">
            <template #default="{ row }">
              <span :class="{ 'volume-abnormal': row.abnormal_count > 0 }">
                {{ formatNumber(row.total_volume) }}
              </span>
            </template>
          </el-table-column>
          <el-table-column label="灌溉时长" width="110" align="right">
            <template #default="{ row }">{{ formatMinutes(row.total_duration_minutes) }}</template>
          </el-table-column>
          <el-table-column label="异常偏高" width="100" align="center">
            <template #default="{ row }">
              <el-tag v-if="row.abnormal_count > 0" type="danger" size="small">{{ row.abnormal_count }} 次</el-tag>
              <span v-else>-</span>
            </template>
          </el-table-column>
        </el-table>
      </div>

      <div class="panel">
        <div class="table-toolbar">
          <span class="panel-title">异常偏高用水明细</span>
          <el-button link type="primary" @click="viewAbnormal">查看全部</el-button>
        </div>
        <el-table :data="summary?.abnormal_records || []" size="small" border empty-text="当前筛选下无异常记录">
          <el-table-column prop="record_no" label="编号" width="150" />
          <el-table-column label="绿地" min-width="130" show-overflow-tooltip>
            <template #default="{ row }">{{ row.green_space?.name || '-' }}</template>
          </el-table-column>
          <el-table-column label="行政区" width="90">
            <template #default="{ row }">{{ row.green_space?.district || '-' }}</template>
          </el-table-column>
          <el-table-column label="日期" width="100">
            <template #default="{ row }">{{ formatDate(row.irrigation_date) }}</template>
          </el-table-column>
          <el-table-column label="用水量（吨）" width="110" align="right">
            <template #default="{ row }">
              <span class="volume-abnormal">{{ formatNumber(row.water_volume) }}</span>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </div>

    <IrrigationFormDialog ref="formDialog" @saved="load" />
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'

import { greenSpaceApi, irrigationRecordApi } from '@/api'
import EnumTag from '@/components/common/EnumTag.vue'
import GreenSpaceSelect from '@/components/common/GreenSpaceSelect.vue'
import PageHeader from '@/components/common/PageHeader.vue'
import StatCard from '@/components/common/StatCard.vue'
import { useEnumOptions } from '@/composables/useEnumOptions'
import { useListQuery } from '@/composables/useListQuery'
import { formatArea, formatDate, formatDateTime, formatNumber } from '@/utils/format'

import IrrigationFormDialog from './IrrigationFormDialog.vue'

const route = useRoute()
const formDialog = ref(null)
const dateRange = ref([])
const districts = ref([])

const { options: methodOptions } = useEnumOptions('irrigation_method')

const { filters, meta, items, summary, loading, load, search, resetFilters, handlePageChange, handleSizeChange } =
  useListQuery(irrigationRecordApi.list, {
    initialFilters: {
      keyword: '',
      green_space_id: route.query.green_space_id ? Number(route.query.green_space_id) : null,
      district: '',
      method: '',
      date_from: '',
      date_to: '',
      abnormal_only: false,
      sort: '',
      order: 'desc',
    },
  })

function onDateChange(value) {
  filters.date_from = value?.[0] || ''
  filters.date_to = value?.[1] || ''
  search()
}

function reset() {
  dateRange.value = []
  resetFilters()
}

function rowClassName({ row }) {
  return row.is_abnormal ? 'abnormal-row' : ''
}

function onSortChange({ prop, order }) {
  filters.sort = order ? prop : ''
  filters.order = order === 'ascending' ? 'asc' : 'desc'
  search()
}

function formatMinutes(value) {
  const total = Number(value || 0)
  if (!total) return '0 分钟'
  const hours = Math.floor(total / 60)
  const minutes = total % 60
  return hours ? `${hours} 小时${minutes ? ` ${minutes} 分` : ''}` : `${minutes} 分钟`
}

function viewAbnormal() {
  filters.abnormal_only = true
  search()
}

async function remove(row) {
  try {
    await ElMessageBox.confirm(`确认删除灌溉用水记录「${row.record_no}」吗？`, '删除确认', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消',
    })
    await irrigationRecordApi.remove(row.id)
    ElMessage.success('灌溉用水记录已删除')
    await load()
  } catch (error) {
    if (error === 'cancel' || error === 'close') return
  }
}

onMounted(async () => {
  const data = await greenSpaceApi.districts().catch(() => null)
  districts.value = data?.items || []
})
</script>

<style scoped>
.pager {
  margin-top: 16px;
  justify-content: flex-end;
}

.panel-title {
  font-weight: 600;
}

.summary-grid {
  display: grid;
  grid-template-columns: 1.2fr 1fr;
  gap: 16px;
}

.expand-detail {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 6px 16px;
  padding: 4px 12px;
  color: #606266;
  font-size: 13px;
}

.cell-main {
  font-weight: 500;
}

.cell-sub {
  color: #909399;
  font-size: 12px;
}

.volume-abnormal {
  color: #f56c6c;
  font-weight: 600;
}

.abnormal-tag {
  margin-left: 6px;
}

:deep(.abnormal-row) {
  background-color: #fef0f0;
}

:deep(.abnormal-row:hover > td.el-table__cell) {
  background-color: #fde2e2;
}
</style>
