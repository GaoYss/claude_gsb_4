<template>
  <el-dialog :model-value="visible"
             :title="isEdit ? `编辑水源点 · ${form.source_no}` : '新增灌溉水源点'"
             width="720px" top="6vh" destroy-on-close @update:model-value="close">
    <el-form ref="formRef" :model="form" :rules="rules" label-width="110px">
      <el-row :gutter="16">
        <el-col :span="12">
          <el-form-item label="水源点名称" prop="name" :error="fieldErrors.name">
            <el-input v-model="form.name" placeholder="如：运河文化公园中河水口" maxlength="128" />
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
          <el-form-item label="所属行政区" prop="district" :error="fieldErrors.district">
            <el-input v-model="form.district" placeholder="如：拱墅区" maxlength="64" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="水源点状态" :error="fieldErrors.status">
            <el-select v-model="form.status" style="width: 100%">
              <el-option v-for="item in statusOptions" :key="item.value" :label="item.label" :value="item.value" />
            </el-select>
          </el-form-item>
        </el-col>
        <el-col :span="24">
          <el-form-item label="取水位置" :error="fieldErrors.address">
            <el-input v-model="form.address" placeholder="如：运河东路 128 号沿河取水口" maxlength="255" />
          </el-form-item>
        </el-col>
        <el-col :span="24">
          <el-form-item label="关联绿地" :error="fieldErrors.green_space_id">
            <GreenSpaceSelect v-model="form.green_space_id" :preset="spacePreset"
                              @update:model-value="onGreenSpaceChange" />
            <div class="form-hint">不关联绿地时为公共取水点，可被同行政区各绿地灌溉登记引用。</div>
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="管护人" :error="fieldErrors.manager">
            <el-input v-model="form.manager" maxlength="64" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="联系电话" :error="fieldErrors.contact_phone">
            <el-input v-model="form.contact_phone" maxlength="32" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="启用日期" :error="fieldErrors.installed_date">
            <el-date-picker v-model="form.installed_date" type="date" value-format="YYYY-MM-DD"
                            placeholder="选择日期" style="width: 100%" />
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

import { greenSpaceApi, waterSourceApi } from '@/api'
import GreenSpaceSelect from '@/components/common/GreenSpaceSelect.vue'
import { useEnumOptions } from '@/composables/useEnumOptions'

const emit = defineEmits(['saved'])

const { options: typeOptions } = useEnumOptions('water_source_type')
const { options: statusOptions } = useEnumOptions('water_source_status')

const formRef = ref(null)
const visible = ref(false)
const submitting = ref(false)
const editingId = ref(null)
const fieldErrors = ref({})
const spacePreset = ref(null)
const form = reactive(emptyForm())

const isEdit = computed(() => editingId.value !== null)

const rules = {
  name: [{ required: true, message: '请输入水源点名称', trigger: 'blur' }],
  source_type: [{ required: true, message: '请选择水源类型', trigger: 'change' }],
  district: [{ required: true, message: '请输入所属行政区', trigger: 'blur' }],
}

function emptyForm() {
  return {
    source_no: '',
    name: '',
    source_type: 'municipal',
    district: '',
    address: '',
    green_space_id: null,
    status: 'active',
    manager: '',
    contact_phone: '',
    installed_date: '',
    remark: '',
  }
}

function open(row = null) {
  Object.assign(form, emptyForm())
  fieldErrors.value = {}
  spacePreset.value = null
  editingId.value = row?.id ?? null
  if (row) {
    Object.keys(form).forEach((key) => {
      if (row[key] !== undefined && row[key] !== null) form[key] = row[key]
    })
    spacePreset.value = row.green_space || null
  }
  visible.value = true
}

function close() {
  visible.value = false
}

async function onGreenSpaceChange(value) {
  if (!value) return
  try {
    const detail = await greenSpaceApi.detail(value)
    if (detail?.district && !form.district) form.district = detail.district
  } catch {
    /* 保留手填行政区 */
  }
}

async function submit() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  submitting.value = true
  fieldErrors.value = {}
  const payload = { ...form }
  if (!payload.source_no) delete payload.source_no
  if (!payload.green_space_id) payload.green_space_id = null
  if (!payload.installed_date) payload.installed_date = null
  try {
    if (isEdit.value) {
      await waterSourceApi.update(editingId.value, payload)
      ElMessage.success('灌溉水源点已更新')
    } else {
      await waterSourceApi.create(payload)
      ElMessage.success('灌溉水源点创建成功')
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
