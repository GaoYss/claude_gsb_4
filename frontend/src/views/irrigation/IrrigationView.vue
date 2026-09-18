<template>
  <div class="page">
    <PageHeader
      title="灌溉用水"
      description="维护水源点与取水方式，登记每次灌溉的用水量或时长，按行政区与月份汇总用水量并标记异常偏高的单次用水"
    />

    <el-tabs v-model="activeTab" class="module-tabs">
      <el-tab-pane label="灌溉记录" name="records">
        <IrrigationRecordList v-if="activeTab === 'records'" />
      </el-tab-pane>
      <el-tab-pane label="用水汇总" name="summary">
        <IrrigationSummaryPanel v-if="activeTab === 'summary'" />
      </el-tab-pane>
      <el-tab-pane label="水源点管理" name="sources">
        <WaterSourcePanel v-if="activeTab === 'sources'" />
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { ref } from 'vue'

import PageHeader from '@/components/common/PageHeader.vue'

import IrrigationRecordList from './IrrigationRecordList.vue'
import IrrigationSummaryPanel from './IrrigationSummaryPanel.vue'
import WaterSourcePanel from './WaterSourcePanel.vue'

const activeTab = ref('records')
</script>

<style scoped>
.module-tabs :deep(.el-tabs__item) {
  font-size: 15px;
}
</style>
