<template>
  <el-dialog :model-value="visible"
             :title="isEdit ? `编辑灌溉记录 · ${form.record_no}` : '登记灌溉记录'"
             width="680px" top="8vh" destroy-on-close @update:model-value="close">
    <el-form ref="formRef" :model="form" :rules="rules" label-width="120px">
      <el-form-item label="覆盖绿地" prop="green_space_id" :error="fieldErrors.green_space_id">
        <GreenSpaceSelect v-model="form.green_space_id" :preset="spacePreset" />
      </el-form-item>
      <el-form-item label="水源点" :error="fieldErrors.water_source_id">
        <WaterSourceSelect v-model="form.water_source_id" :preset="sourcePreset" @change="onSourceChange" />
        <div class="form-hint" v-if="selectedSource">
          取水方式：{{ selectedSource.intake_method_label }}；
          额定流量：{{ selectedSource.flow_rate ? `${selectedSource.flow_rate} m³/h` : '未维护' }}
        </div>
      </el-form-item>
      <el-row :gutter="16">
        <el-col :span="12">
          <el-form-item label="灌溉日期" prop="irrigation_date" :error="fieldErrors.irrigation_date">
            <el-date-picker v-model="form.irrigation_date" type="date" value-format="YYYY-MM-DD"
                            placeholder="选择日期" style="width: 100%" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="执行班组" prop="team" :error="fieldErrors.team">
            <el-input v-model="form.team" placeholder="如：浇水一班" maxlength="64" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="用水量（m³）" :error="fieldErrors.water_amount">
            <el-input-number v-model="form.water_amount" :min="0.01" :max="999999" :precision="2"
                             :controls="false" placeholder="实际计量水量" style="width: 100%" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="灌溉时长（h）" :error="fieldErrors.duration_hours">
            <el-input-number v-model="form.duration_hours" :min="0.1" :max="200" :precision="2"
                             :controls="false" placeholder="无计量时填时长" style="width: 100%" />
          </el-form-item>
        </el-col>
      </el-row>
      <div class="form-hint amount-hint">
        用水量与灌溉时长至少填写一项；只填时长时按水源点额定流量折算用水量并标记「折算」。
        <template v-if="estimatedPreview">当前将折算为 <b>{{ estimatedPreview }} m³</b>。</template>
      </div>
      <el-form-item label="登记人" :error="fieldErrors.operator">
        <el-input v-model="form.operator" maxlength="64" />
      </el-form-item>
      <el-form-item label="备注" :error="fieldErrors.remark">
        <el-input v-model="form.remark" type="textarea" :rows="2" maxlength="2000" />
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
import WaterSourceSelect from '@/components/common/WaterSourceSelect.vue'
import { formatNumber, today } from '@/utils/format'

const emit = defineEmits(['saved'])

const formRef = ref(null)
const visible = ref(false)
const submitting = ref(false)
const editingId = ref(null)
const fieldErrors = ref({})
const spacePreset = ref(null)
const sourcePreset = ref(null)
const selectedSource = ref(null)
const form = reactive(emptyForm())

const isEdit = computed(() => editingId.value !== null)

// 只填时长且水源点有额定流量时，实时提示折算结果
const estimatedPreview = computed(() => {
  if (form.water_amount !== null && form.water_amount !== undefined && form.water_amount !== '') return ''
  const flow = Number(selectedSource.value?.flow_rate || 0)
  const hours = Number(form.duration_hours || 0)
  if (!flow || !hours) return ''
  return formatNumber(Math.round(flow * hours * 100) / 100)
})

const rules = {
  green_space_id: [{ required: true, message: '请选择覆盖绿地', trigger: 'change' }],
  irrigation_date: [{ required: true, message: '请选择灌溉日期', trigger: 'change' }],
  team: [{ required: true, message: '请输入执行班组', trigger: 'blur' }],
}

function emptyForm() {
  return {
    record_no: '',
    green_space_id: null,
    water_source_id: null,
    irrigation_date: today(),
    water_amount: null,
    duration_hours: null,
    team: '',
    operator: '',
    remark: '',
  }
}

function open(row = null) {
  Object.assign(form, emptyForm())
  fieldErrors.value = {}
  spacePreset.value = null
  sourcePreset.value = null
  selectedSource.value = null
  editingId.value = row?.id ?? null
  if (row) {
    Object.keys(form).forEach((key) => {
      if (row[key] !== undefined && row[key] !== null) form[key] = row[key]
    })
    // 折算记录不回填折算水量，避免估算值被固化为实际登记
    if (row.is_estimated) form.water_amount = null
    spacePreset.value = row.green_space || null
    sourcePreset.value = row.water_source || null
    selectedSource.value = row.water_source || null
  }
  visible.value = true
}

function close() {
  visible.value = false
}

function onSourceChange(item) {
  selectedSource.value = item
}

async function submit() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  fieldErrors.value = {}
  if (!form.water_amount && !form.duration_hours) {
    fieldErrors.value = { water_amount: '用水量与灌溉时长至少填写一项' }
    return
  }
  submitting.value = true
  const payload = { ...form }
  if (!payload.record_no) delete payload.record_no
  if (!payload.water_source_id) payload.water_source_id = null
  try {
    if (isEdit.value) {
      await irrigationRecordApi.update(editingId.value, payload)
      ElMessage.success('灌溉记录已更新')
    } else {
      await irrigationRecordApi.create(payload)
      ElMessage.success('灌溉记录登记成功')
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

<style scoped>
.form-hint {
  color: #909399;
  font-size: 12px;
  line-height: 1.5;
}

.amount-hint {
  margin: -8px 0 12px 120px;
}
</style>
