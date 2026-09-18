<template>
  <div class="page">
    <PageHeader title="灌溉水源点" description="维护灌溉取水位置与取水方式，作为每次灌溉用水登记的取水来源">
      <template #actions>
        <el-button type="primary" :icon="'Plus'" @click="formDialog.open()">新增水源点</el-button>
      </template>
    </PageHeader>

    <div class="panel">
      <div class="filter-bar">
        <el-input v-model="filters.keyword" placeholder="编号 / 名称 / 取水位置 / 管护人" clearable
                  :prefix-icon="'Search'" @keyup.enter="search" @clear="search" />
        <el-select v-model="filters.district" placeholder="所属行政区" clearable @change="search">
          <el-option v-for="item in districts" :key="item.district" :label="item.district" :value="item.district" />
        </el-select>
        <el-select v-model="filters.source_type" placeholder="水源类型" clearable @change="search">
          <el-option v-for="item in typeOptions" :key="item.value" :label="item.label" :value="item.value" />
        </el-select>
        <el-select v-model="filters.status" placeholder="状态" clearable @change="search">
          <el-option v-for="item in statusOptions" :key="item.value" :label="item.label" :value="item.value" />
        </el-select>
        <div style="width: 220px">
          <GreenSpaceSelect v-model="filters.green_space_id" placeholder="按关联绿地筛选" @update:model-value="search" />
        </div>
        <el-button type="primary" :icon="'Search'" @click="search">查询</el-button>
        <el-button :icon="'RefreshLeft'" @click="reset">重置</el-button>
      </div>
    </div>

    <div class="stat-grid">
      <StatCard label="水源点" :value="formatNumber(summary?.total ?? 0)" unit="个"
                hint="含在用、备用与停用" icon="Coffee" />
      <StatCard label="在用" :value="formatNumber(summary?.by_status?.active ?? 0)" unit="个"
                hint="可直接用于灌溉登记" tone="info" icon="CircleCheck" />
      <StatCard label="备用" :value="formatNumber(summary?.by_status?.standby ?? 0)" unit="个"
                hint="暂不主用，可应急取水" icon="Clock" />
      <StatCard label="停用" :value="formatNumber(summary?.by_status?.disabled ?? 0)" unit="个"
                hint="停用后不再出现在取水点选择中" icon="CircleClose" />
    </div>

    <div class="panel">
      <div class="table-toolbar">
        <span class="summary-text">共 <strong>{{ meta.total }}</strong> 个水源点</span>
        <el-button :icon="'Refresh'" text @click="load">刷新</el-button>
      </div>

      <el-table :data="items" v-loading="loading" border stripe>
        <el-table-column prop="source_no" label="编号" width="140" />
        <el-table-column label="水源点名称" min-width="180" show-overflow-tooltip>
          <template #default="{ row }">
            <div class="cell-main">{{ row.name }}</div>
            <div class="cell-sub">{{ row.address || '未填写取水位置' }}</div>
          </template>
        </el-table-column>
        <el-table-column label="水源类型" width="115">
          <template #default="{ row }">
            <EnumTag group="water_source_type" :value="row.source_type" :label="row.source_type_label" />
          </template>
        </el-table-column>
        <el-table-column prop="district" label="行政区" width="90" />
        <el-table-column label="关联绿地" min-width="150" show-overflow-tooltip>
          <template #default="{ row }">{{ row.green_space?.name || '公共取水点' }}</template>
        </el-table-column>
        <el-table-column label="状态" width="90">
          <template #default="{ row }">
            <EnumTag group="water_source_status" :value="row.status" :label="row.status_label" />
          </template>
        </el-table-column>
        <el-table-column label="取用次数" width="90" align="right">
          <template #default="{ row }">{{ formatNumber(row.statistics?.usage_count ?? 0) }}</template>
        </el-table-column>
        <el-table-column label="最近取用" width="110">
          <template #default="{ row }">{{ row.statistics?.last_used_date || '-' }}</template>
        </el-table-column>
        <el-table-column label="管护人" width="100">
          <template #default="{ row }">{{ row.manager || '-' }}</template>
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
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'

import { greenSpaceApi, waterSourceApi } from '@/api'
import EnumTag from '@/components/common/EnumTag.vue'
import GreenSpaceSelect from '@/components/common/GreenSpaceSelect.vue'
import PageHeader from '@/components/common/PageHeader.vue'
import StatCard from '@/components/common/StatCard.vue'
import { useEnumOptions } from '@/composables/useEnumOptions'
import { useListQuery } from '@/composables/useListQuery'
import { formatNumber } from '@/utils/format'

import WaterSourceFormDialog from './WaterSourceFormDialog.vue'

const route = useRoute()
const formDialog = ref(null)
const districts = ref([])

const { options: typeOptions } = useEnumOptions('water_source_type')
const { options: statusOptions } = useEnumOptions('water_source_status')

const { filters, meta, items, summary, loading, load, search, resetFilters, handlePageChange, handleSizeChange } =
  useListQuery(waterSourceApi.list, {
    initialFilters: {
      keyword: '',
      district: '',
      source_type: '',
      status: '',
      green_space_id: route.query.green_space_id ? Number(route.query.green_space_id) : null,
    },
  })

function reset() {
  resetFilters()
}

async function remove(row) {
  try {
    await ElMessageBox.confirm(`确认删除水源点「${row.name}」吗？已有灌溉记录的水源点不可删除。`, '删除确认', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消',
    })
    await waterSourceApi.remove(row.id)
    ElMessage.success('灌溉水源点已删除')
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

.cell-main {
  font-weight: 500;
}

.cell-sub {
  color: #909399;
  font-size: 12px;
}
</style>
