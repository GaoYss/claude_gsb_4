<template>
  <div>
    <div class="panel">
      <div class="filter-bar">
        <el-input v-model="filters.keyword" placeholder="名称 / 编号 / 计量表" clearable
                  :prefix-icon="'Search'" @keyup.enter="search" @clear="search" />
        <el-select v-model="filters.source_type" placeholder="水源类型" clearable @change="search">
          <el-option v-for="item in typeOptions" :key="item.value" :label="item.label" :value="item.value" />
        </el-select>
        <el-select v-model="filters.intake_method" placeholder="取水方式" clearable @change="search">
          <el-option v-for="item in methodOptions" :key="item.value" :label="item.label" :value="item.value" />
        </el-select>
        <el-select v-model="filters.status" placeholder="状态" clearable @change="search">
          <el-option v-for="item in statusOptions" :key="item.value" :label="item.label" :value="item.value" />
        </el-select>
        <el-button type="primary" :icon="'Search'" @click="search">查询</el-button>
        <el-button :icon="'RefreshLeft'" @click="reset">重置</el-button>
        <div class="filter-bar__spacer" />
        <el-button type="primary" :icon="'Plus'" @click="formDialog.open()">新增水源点</el-button>
      </div>
    </div>

    <div class="stat-grid">
      <StatCard label="水源点" :value="formatNumber(summary?.total ?? 0)" unit="处"
                :hint="`正常使用 ${summary?.by_status?.normal ?? 0} 处`" icon="OfficeBuilding" />
      <StatCard label="维护检修" :value="formatNumber(summary?.by_status?.maintenance ?? 0)" unit="处"
                hint="检修期间取水需关注" tone="warning" icon="Tools" />
      <StatCard label="合计额定流量" :value="formatNumber(summary?.total_flow_rate ?? 0)" unit="m³/h"
                hint="时长折算用水量的依据" tone="info" icon="Odometer" />
      <StatCard label="停用" :value="formatNumber(summary?.by_status?.disabled ?? 0)" unit="处"
                hint="停用后不再出现在下拉选项" icon="CircleClose" />
    </div>

    <div class="panel">
      <div class="table-toolbar">
        <span class="summary-text">共 <strong>{{ meta.total }}</strong> 处水源点</span>
        <el-button :icon="'Refresh'" text @click="load">刷新</el-button>
      </div>

      <el-table :data="items" v-loading="loading" border stripe>
        <el-table-column prop="code" label="编号" width="140" />
        <el-table-column prop="name" label="水源点名称" min-width="150" show-overflow-tooltip />
        <el-table-column prop="district" label="行政区" width="100" />
        <el-table-column label="水源类型" width="110">
          <template #default="{ row }">
            <EnumTag group="water_source_type" :value="row.source_type" :label="row.source_type_label" />
          </template>
        </el-table-column>
        <el-table-column label="取水方式" width="105">
          <template #default="{ row }">
            <EnumTag group="intake_method" :value="row.intake_method" :label="row.intake_method_label" />
          </template>
        </el-table-column>
        <el-table-column label="额定流量" width="110" align="right">
          <template #default="{ row }">{{ row.flow_rate ? `${formatNumber(row.flow_rate)} m³/h` : '未维护' }}</template>
        </el-table-column>
        <el-table-column prop="meter_no" label="计量表编号" width="120">
          <template #default="{ row }">{{ row.meter_no || '-' }}</template>
        </el-table-column>
        <el-table-column label="灌溉记录" width="90" align="right">
          <template #default="{ row }">{{ formatNumber(row.irrigation_count ?? 0) }}</template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <EnumTag group="water_source_status" :value="row.status" :label="row.status_label" />
          </template>
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

    <WaterSourceFormDialog ref="formDialog" @saved="load" />
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'

import { waterSourceApi } from '@/api'
import EnumTag from '@/components/common/EnumTag.vue'
import StatCard from '@/components/common/StatCard.vue'
import { useEnumOptions } from '@/composables/useEnumOptions'
import { useListQuery } from '@/composables/useListQuery'
import { formatNumber } from '@/utils/format'

import WaterSourceFormDialog from './WaterSourceFormDialog.vue'

const formDialog = ref(null)

const { options: typeOptions } = useEnumOptions('water_source_type')
const { options: methodOptions } = useEnumOptions('intake_method')
const { options: statusOptions } = useEnumOptions('water_source_status')

const { filters, meta, items, summary, loading, load, search, resetFilters, handlePageChange, handleSizeChange } =
  useListQuery(waterSourceApi.list, {
    initialFilters: { keyword: '', source_type: '', intake_method: '', status: '' },
  })

function reset() {
  resetFilters()
}

async function remove(row) {
  const hasRecords = (row.irrigation_count ?? 0) > 0
  try {
    if (hasRecords) {
      await ElMessageBox.confirm(
        `该水源点已关联 ${row.irrigation_count} 条灌溉记录，删除后记录将保留但解除关联，是否继续？`,
        '存在关联数据',
        { type: 'warning', confirmButtonText: '确认删除', cancelButtonText: '取消' },
      )
    } else {
      await ElMessageBox.confirm(`确认删除水源点「${row.name}」吗？`, '删除确认', {
        type: 'warning',
        confirmButtonText: '删除',
        cancelButtonText: '取消',
      })
    }
    await waterSourceApi.remove(row.id, hasRecords ? { force: true } : undefined)
    ElMessage.success('水源点已删除')
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
</style>
