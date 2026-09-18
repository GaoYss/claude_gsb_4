<template>
  <el-dialog :model-value="visible"
             :title="isEdit ? `编辑水源点 · ${form.code}` : '新增水源点'"
             width="680px" top="8vh" destroy-on-close @update:model-value="close">
    <el-form ref="formRef" :model="form" :rules="rules" label-width="120px">
      <el-row :gutter="16">
        <el-col :span="12">
          <el-form-item label="水源点名称" prop="name" :error="fieldErrors.name">
            <el-input v-model="form.name" placeholder="如：运河取水泵站" maxlength="96" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="所在行政区" prop="district" :error="fieldErrors.district">
            <el-input v-model="form.district" placeholder="如：拱墅区" maxlength="64" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="水源类型" prop="source_type" :error="fieldErrors.source_type">
            <el-select v-model="form.source_type" placeholder="请选择" style="width: 100%">
              <el-option v-for="item in typeOptions" :key="item.value" :label="item.label" :value="item.value" />
            </el-select>
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="取水方式" prop="intake_method" :error="fieldErrors.intake_method">
            <el-select v-model="form.intake_method" placeholder="请选择" style="width: 100%">
              <el-option v-for="item in methodOptions" :key="item.value" :label="item.label" :value="item.value" />
            </el-select>
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="计量表编号" :error="fieldErrors.meter_no">
            <el-input v-model="form.meter_no" placeholder="如：SB-GS-001" maxlength="64" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="额定流量" :error="fieldErrors.flow_rate">
            <el-input-number v-model="form.flow_rate" :min="0.01" :max="99999" :precision="2"
                             :controls="false" placeholder="m³/h，用于时长折算" style="width: 100%" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="状态" :error="fieldErrors.status">
            <el-select v-model="form.status" style="width: 100%">
              <el-option v-for="item in statusOptions" :key="item.value" :label="item.label" :value="item.value" />
            </el-select>
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="位置说明" :error="fieldErrors.address">
            <el-input v-model="form.address" maxlength="255" />
          </el-form-item>
        </el-col>
      </el-row>
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

import { waterSourceApi } from '@/api'
import { useEnumOptions } from '@/composables/useEnumOptions'

const emit = defineEmits(['saved'])

const { options: typeOptions } = useEnumOptions('water_source_type')
const { options: methodOptions } = useEnumOptions('intake_method')
const { options: statusOptions } = useEnumOptions('water_source_status')

const formRef = ref(null)
const visible = ref(false)
const submitting = ref(false)
const editingId = ref(null)
const fieldErrors = ref({})
const form = reactive(emptyForm())

const isEdit = computed(() => editingId.value !== null)

const rules = {
  name: [{ required: true, message: '请输入水源点名称', trigger: 'blur' }],
  district: [{ required: true, message: '请输入所在行政区', trigger: 'blur' }],
  source_type: [{ required: true, message: '请选择水源类型', trigger: 'change' }],
  intake_method: [{ required: true, message: '请选择取水方式', trigger: 'change' }],
}

function emptyForm() {
  return {
    code: '',
    name: '',
    district: '',
    address: '',
    source_type: 'municipal',
    intake_method: 'pipeline',
    meter_no: '',
    flow_rate: null,
    status: 'normal',
    remark: '',
  }
}

function open(row = null) {
  Object.assign(form, emptyForm())
  fieldErrors.value = {}
  editingId.value = row?.id ?? null
  if (row) {
    Object.keys(form).forEach((key) => {
      if (row[key] !== undefined && row[key] !== null) form[key] = row[key]
    })
  }
  visible.value = true
}

function close() {
  visible.value = false
}

async function submit() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  submitting.value = true
  fieldErrors.value = {}
  const payload = { ...form }
  if (!payload.code) delete payload.code
  try {
    if (isEdit.value) {
      await waterSourceApi.update(editingId.value, payload)
      ElMessage.success('水源点已更新')
    } else {
      await waterSourceApi.create(payload)
      ElMessage.success('水源点登记成功')
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
