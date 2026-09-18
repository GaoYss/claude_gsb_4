<template>
  <el-select
    :model-value="modelValue"
    filterable
    remote
    clearable
    :remote-method="remoteSearch"
    :loading="loading"
    :placeholder="placeholder"
    :disabled="disabled"
    :style="{ width: '100%' }"
    @update:model-value="emit('update:modelValue', $event)"
  >
    <el-option
      v-for="item in options"
      :key="item.id"
      :label="`${item.source_no} ${item.name}`"
      :value="item.id"
    >
      <span>{{ item.source_no }} {{ item.name }}</span>
      <span class="source-option__type">{{ typeLabel(item.source_type) }}</span>
    </el-option>
  </el-select>
</template>

<script setup>
import { onMounted, ref, watch } from 'vue'

import { greenSpaceApi, waterSourceApi } from '@/api'
import { useMetaStore } from '@/stores/meta'

const props = defineProps({
  modelValue: { type: [Number, String], default: null },
  preset: { type: Object, default: null },
  greenSpaceId: { type: [Number, String], default: null },
  placeholder: { type: String, default: '请选择水源点' },
  disabled: { type: Boolean, default: false },
})

const emit = defineEmits(['update:modelValue'])

const meta = useMetaStore()
const options = ref([])
const loading = ref(false)
const district = ref(null)

function typeLabel(value) {
  return meta.label('water_source_type', value)
}

function merge(items) {
  const map = new Map()
  items.filter(Boolean).forEach((item) => map.set(item.id, item))
  if (props.preset) map.set(props.preset.id, props.preset)
  options.value = [...map.values()]
}

async function resolveDistrict() {
  if (!props.greenSpaceId) {
    district.value = null
    return
  }
  try {
    const detail = await greenSpaceApi.detail(props.greenSpaceId)
    district.value = detail?.district || null
  } catch {
    district.value = null
  }
}

async function load(keyword) {
  loading.value = true
  try {
    const data = await waterSourceApi.options({
      keyword: keyword || undefined,
      district: district.value || undefined,
      green_space_id: props.greenSpaceId || undefined,
    })
    merge(data?.items || [])
  } finally {
    loading.value = false
  }
}

function remoteSearch(keyword) {
  return load(keyword?.trim() || undefined)
}

watch(() => props.greenSpaceId, async () => {
  await resolveDistrict()
  await load()
}, { immediate: false })

watch(() => props.preset, () => load())

onMounted(async () => {
  await meta.ensureLoaded().catch(() => {})
  await resolveDistrict()
  await load()
})
</script>

<style scoped>
.source-option__type {
  float: right;
  color: #909399;
  font-size: 12px;
}
</style>
