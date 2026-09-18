<template>
  <el-dialog :model-value="visible"
             :title="isEdit ? `编辑灌溉用水记录 · ${form.record_no}` : '登记灌溉用水'"
             width="760px" top="6vh" destroy-on-close @update:model-value="close">
    <el-form ref="formRef" :model="form" :rules="rules" label-width="110px">
      <el-form-item label="覆盖绿地" prop="green_space_id" :error="fieldErrors.green_space_id">
        <GreenSpaceSelect v-model="form.green_space_id" :preset="spacePreset"
                          @update:model-value="onGreenSpaceChange" />
      </el-form-item>
      <el-form-item label="水源点" prop="water_source_id" :error="fieldErrors.water_source_id">
        <WaterSourceSelect v-model="form.water_source_id" :preset="sourcePreset"
                           :green-space-id="form.green_space_id" />
        <div class="form-hint">水源点按覆盖绿地所属行政区过滤；停用的水源点不可选择。</div>
      </el-form-item>
      <el-row :gutter="16">
        <el-col :span="12">
          <el-form-item label="灌溉日期" prop="irrigation_date" :error="fieldErrors.irrigation_date">
            <el-date-picker v-model="form.irrigation_date" type="date" value-format="YYYY-MM-DD"
                            placeholder="选择日期" style="width: 100%" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="灌溉方式" prop="method" :error="fieldErrors.method">
            <el-select v-model="form.method" placeholder="请选择" style="width: 100%">
              <el-option v-for="item in methodOptions" :key="item.value" :label="item.label" :value="item.value" />
            </el-select>
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="用水量（吨）" :error="fieldErrors.water_volume">
            <el-input-number v-model="form.water_volume" :min="0.01" :max="999999" :precision="2"
                             :controls="false" placeholder="与时长至少填一项" style="width: 100%" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="灌溉时长（分钟）" :error="fieldErrors.duration_minutes">
            <el-input-number v-model="form.duration_minutes" :min="1" :max="100000" :precision="0"
                             :controls="false" placeholder="与用水量至少填一项" style="width: 100%" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="覆盖面积（㎡）" :error="fieldErrors.covered_area_sqm">
            <el-input-number v-model="form.covered_area_sqm" :min="0.01" :max="99999999" :precision="2"
                             :controls="false" placeholder="本次实际浇灌面积" style="width: 100%" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="执行班组" :error="fieldErrors.worker_team">
            <el-input v-model="form.worker_team" placeholder="如：浇水一班" maxlength="64" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="登记人" :error="fieldErrors.operator">
            <el-input v-model="form.operator" maxlength="64" />
          </el-form-item>
        </el-col>
      </el-row>
      <el-form-item label="关联养护记录" :error="fieldErrors.maintenance_record_id">
        <RecordSelect v-model="form.maintenance_record_id" :green-space-id="form.green_space_id"
                      :preset="recordPreset" />
      </el-form-item>
      <el-form-item label="备注" :error="fieldErrors.remark">
        <el-input v-model="form.remark" type="textarea" :rows="2" maxlength="2000"
                  placeholder="如：连续高温应急浇灌" />
      </el-form-item>
    </el-form>

    <template #footer>
      <el-button @click="close">取消</el-button>
      <el-button type="primary" :loading="submitting" @click="submit">保存</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { computed, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'

import { irrigationRecordApi } from '@/api'
import GreenSpaceSelect from '@/components/common/GreenSpaceSelect.vue'
import RecordSelect from '@/components/common/RecordSelect.vue'
import WaterSourceSelect from '@/components/common/WaterSourceSelect.vue'
import { useEnumOptions } from '@/composables/useEnumOptions'
import { today } from '@/utils/format'

const emit = defineEmits(['saved'])

const { options: methodOptions } = useEnumOptions('irrigation_method')

const formRef = ref(null)
const visible = ref(false)
const submitting = ref(false)
const editingId = ref(null)
const fieldErrors = ref({})
const spacePreset = ref(null)
const sourcePreset = ref(null)
const recordPreset = ref(null)
const form = reactive(emptyForm())

const isEdit = computed(() => editingId.value !== null)

const rules = {
  green_space_id: [{ required: true, message: '请选择覆盖绿地', trigger: 'change' }],
  water_source_id: [{ required: true, message: '请选择水源点', trigger: 'change' }],
  irrigation_date: [{ required: true, message: '请选择灌溉日期', trigger: 'change' }],
  method: [{ required: true, message: '请选择灌溉方式', trigger: 'change' }],
}

function emptyForm() {
  return {
    record_no: '',
    green_space_id: null,
    water_source_id: null,
    maintenance_record_id: null,
    irrigation_date: today(),
    method: 'sprinkler',
    water_volume: null,
    duration_minutes: null,
    covered_area_sqm: null,
    worker_team: '',
    operator: '',
    remark: '',
  }
}

function open(row = null) {
  Object.assign(form, emptyForm())
  fieldErrors.value = {}
  spacePreset.value = null
  sourcePreset.value = null
  recordPreset.value = null
  editingId.value = row?.id ?? null
  if (row) {
    Object.keys(form).forEach((key) => {
      if (row[key] !== undefined && row[key] !== null) form[key] = row[key]
    })
    spacePreset.value = row.green_space || null
    sourcePreset.value = row.water_source || null
    recordPreset.value = row.record ? { ...row.record, id: row.maintenance_record_id } : null
  }
  visible.value = true
}

function close() {
  visible.value = false
}

function onGreenSpaceChange() {
  form.water_source_id = null
  form.maintenance_record_id = null
  sourcePreset.value = null
  recordPreset.value = null
}

async function submit() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  if (!form.water_volume && !form.duration_minutes) {
    fieldErrors.value = { water_volume: '用水量与灌溉时长至少填写一项' }
    return
  }
  submitting.value = true
  fieldErrors.value = {}
  const payload = { ...form }
  delete payload.record_no
  payload.maintenance_record_id = payload.maintenance_record_id || null
  try {
    if (isEdit.value) {
      await irrigationRecordApi.update(editingId.value, payload)
      ElMessage.success('灌溉用水记录已更新')
    } else {
      await irrigationRecordApi.create(payload)
      ElMessage.success('灌溉用水记录登记成功')
    }
    emit('saved')
    close()
  } catch (error) {
    fieldErrors.value = error?.details || {}
  } finally {
    submitting.value = false
  }
}

defineExpose({ open })
</script>
