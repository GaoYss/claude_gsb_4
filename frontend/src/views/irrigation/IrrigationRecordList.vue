<template>
  <div>
    <div class="panel">
      <div class="filter-bar">
        <el-input v-model="filters.keyword" placeholder="编号 / 班组 / 登记人" clearable
                  :prefix-icon="'Search'" @keyup.enter="search" @clear="search" />
        <div style="width: 220px">
          <GreenSpaceSelect v-model="filters.green_space_id" placeholder="按绿地筛选" @update:model-value="search" />
        </div>
        <div style="width: 220px">
          <WaterSourceSelect v-model="filters.water_source_id" placeholder="按水源点筛选" @update:model-value="search" />
        </div>
        <el-date-picker v-model="dateRange" type="daterange" unlink-panels value-format="YYYY-MM-DD"
                        start-placeholder="灌溉日期起" end-placeholder="灌溉日期止" @change="onDateChange" />
        <el-checkbox v-model="onlyEstimated" label="仅看折算" @change="onEstimatedChange" />
        <el-button type="primary" :icon="'Search'" @click="search">查询</el-button>
        <el-button :icon="'RefreshLeft'" @click="reset">重置</el-button>
        <div class="filter-bar__spacer" />
        <el-button type="primary" :icon="'Plus'" @click="formDialog.open()">登记灌溉记录</el-button>
      </div>
    </div>

    <div class="stat-grid">
      <StatCard label="灌溉记录" :value="formatNumber(summary?.total_count ?? 0)" unit="条"
                :hint="`灌溉时长合计 ${formatNumber(summary?.total_duration_hours ?? 0)} 小时`" icon="Pouring" />
      <StatCard label="总用水量" :value="formatNumber(summary?.total_water_amount ?? 0)" unit="m³"
                hint="含实际登记与按时长折算" tone="info" icon="Odometer" />
      <StatCard label="其中折算水量" :value="formatNumber(summary?.estimated_amount ?? 0)" unit="m³"
                :hint="`${formatNumber(summary?.estimated_count ?? 0)} 条按额定流量折算`" icon="MagicStick" />
      <StatCard label="实际登记水量" :value="formatNumber(actualAmount)" unit="m³"
                hint="直接登记的计量水量" icon="CircleCheck" />
    </div>

    <div class="panel">
      <div class="table-toolbar">
        <span class="summary-text">
          共 <strong>{{ meta.total }}</strong> 条灌溉记录，
          用水量合计 <strong>{{ formatNumber(summary?.total_water_amount ?? 0) }}</strong> m³
        </span>
        <el-button :icon="'Refresh'" text @click="load">刷新</el-button>
      </div>

      <el-table :data="items" v-loading="loading" border stripe>
        <el-table-column type="expand">
          <template #default="{ row }">
            <div class="expand-detail">
              <span><b>水源点：</b>{{ row.water_source ? `${row.water_source.code} ${row.water_source.name}` : '已解除关联' }}</span>
              <span><b>取水方式：</b>{{ row.water_source?.intake_method_label || '-' }}</span>
              <span><b>登记人：</b>{{ row.operator || '-' }}</span>
              <span><b>登记时间：</b>{{ formatDateTime(row.created_at) }}</span>
              <span v-if="row.remark"><b>备注：</b>{{ row.remark }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="record_no" label="编号" width="150" />
        <el-table-column prop="irrigation_date" label="灌溉日期" width="105" />
        <el-table-column label="覆盖绿地" min-width="150" show-overflow-tooltip>
          <template #default="{ row }">{{ row.green_space?.name || '-' }}</template>
        </el-table-column>
        <el-table-column label="水源点" min-width="140" show-overflow-tooltip>
          <template #default="{ row }">{{ row.water_source?.name || '-' }}</template>
        </el-table-column>
        <el-table-column label="用水量" width="130" align="right">
          <template #default="{ row }">
            <span>{{ formatNumber(row.water_amount) }} m³</span>
            <el-tag v-if="row.is_estimated" type="warning" size="small" effect="plain" class="estimate-tag">折算</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="灌溉时长" width="100" align="right">
          <template #default="{ row }">{{ row.duration_hours ? `${formatNumber(row.duration_hours)} h` : '-' }}</template>
        </el-table-column>
        <el-table-column prop="team" label="执行班组" width="110" />
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

    <IrrigationRecordFormDialog ref="formDialog" @saved="load" />
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'

import { irrigationRecordApi } from '@/api'
import GreenSpaceSelect from '@/components/common/GreenSpaceSelect.vue'
import StatCard from '@/components/common/StatCard.vue'
import WaterSourceSelect from '@/components/common/WaterSourceSelect.vue'
import { useListQuery } from '@/composables/useListQuery'
import { formatDateTime, formatNumber } from '@/utils/format'

import IrrigationRecordFormDialog from './IrrigationRecordFormDialog.vue'

const formDialog = ref(null)
const dateRange = ref([])
const onlyEstimated = ref(false)

const { filters, meta, items, summary, loading, load, search, resetFilters, handlePageChange, handleSizeChange } =
  useListQuery(irrigationRecordApi.list, {
    initialFilters: {
      keyword: '',
      green_space_id: null,
      water_source_id: null,
      estimated: '',
      date_from: '',
      date_to: '',
    },
  })

const actualAmount = computed(() => {
  const total = Number(summary.value?.total_water_amount ?? 0)
  const estimated = Number(summary.value?.estimated_amount ?? 0)
  return Math.round((total - estimated) * 100) / 100
})

function onDateChange(value) {
  filters.date_from = value?.[0] || ''
  filters.date_to = value?.[1] || ''
  search()
}

function onEstimatedChange(value) {
  filters.estimated = value ? 'true' : ''
  search()
}

function reset() {
  dateRange.value = []
  onlyEstimated.value = false
  resetFilters()
}

async function remove(row) {
  try {
    await ElMessageBox.confirm(`确认删除灌溉记录「${row.record_no}」吗？`, '删除确认', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消',
    })
    await irrigationRecordApi.remove(row.id)
    ElMessage.success('灌溉记录已删除')
    await load()
  } catch (error) {
    if (error === 'cancel' || error === 'close') return
  }
}
</script>

<style scoped>
.pager {
  margin-top: 16px;
  justify-content: flex-end;
}

.estimate-tag {
  margin-left: 6px;
}

.expand-detail {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 6px 16px;
  padding: 4px 12px;
  color: #606266;
  font-size: 13px;
}
</style>
