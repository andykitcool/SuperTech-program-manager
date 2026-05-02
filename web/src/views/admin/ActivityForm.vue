<template>
  <div>
    <div class="page-header">
      <a-button @click="$router.back()">
        <template #icon><ArrowLeftOutlined /></template>
        返回
      </a-button>
      <h2>{{ isEdit ? '编辑活动' : '创建活动' }}</h2>
      <div></div>
    </div>
    <a-form :model="form" layout="vertical" @finish="handleSubmit" class="activity-form" style="max-width: 600px">
      <a-form-item label="活动名称" name="name" :rules="[{ required: true, message: '请输入活动名称' }]">
        <a-input v-model:value="form.name" placeholder="例如：2026春季少儿舞蹈展演" />
      </a-form-item>
      <a-form-item label="活动描述" name="description">
        <a-textarea v-model:value="form.description" :rows="3" placeholder="活动简介" />
      </a-form-item>
      <a-row :gutter="16">
        <a-col :span="12">
          <a-form-item label="活动日期" name="event_date">
            <a-date-picker v-model:value="form.event_date" style="width: 100%" placeholder="选择日期" />
          </a-form-item>
        </a-col>
        <a-col :span="12">
          <a-form-item label="活动地点" name="venue">
            <a-input v-model:value="form.venue" placeholder="演出场地" />
          </a-form-item>
        </a-col>
      </a-row>
      <a-form-item label="喔图相册URL" name="wotu_album_url">
        <a-input v-model:value="form.wotu_album_url" placeholder="https://m.alltuu.com/album/xxx/" />
      </a-form-item>
      <a-form-item label="存储路径前缀" name="storage_path_prefix">
        <a-input v-model:value="form.storage_path_prefix" placeholder="留空则自动生成" />
      </a-form-item>
      <a-form-item label="封面图URL" name="cover_image">
        <a-input v-model:value="form.cover_image" placeholder="留空使用默认封面，可后续编辑" />
      </a-form-item>
      <a-form-item>
        <a-space>
          <a-button type="primary" html-type="submit" :loading="submitting">
            {{ isEdit ? '保存修改' : '创建活动' }}
          </a-button>
          <a-button @click="$router.back()">取消</a-button>
        </a-space>
      </a-form-item>
    </a-form>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowLeftOutlined } from '@ant-design/icons-vue'
import { message } from 'ant-design-vue'
import { adminApi } from '@/api/admin'
import dayjs, { type Dayjs } from 'dayjs'

const route = useRoute()
const router = useRouter()
const submitting = ref(false)
const activityId = computed(() => Number(route.params.id))
const isEdit = computed(() => !isNaN(activityId.value))

const form = reactive({
  name: '',
  description: '',
  event_date: null as Dayjs | null,
  venue: '',
  wotu_album_url: '',
  storage_path_prefix: '',
  cover_image: '',
})

onMounted(async () => {
  if (isEdit.value) {
    try {
      const res = await adminApi.getActivity(activityId.value)
      const data = res.data
      form.name = data.name
      form.description = data.description || ''
      form.event_date = data.event_date ? dayjs(data.event_date) : null
      form.venue = data.venue || ''
      form.wotu_album_url = data.wotu_album_url || ''
      form.storage_path_prefix = data.storage_path_prefix || ''
      form.cover_image = data.cover_image || ''
    } catch {
      message.error('加载活动信息失败')
    }
  }
})

const handleSubmit = async () => {
  submitting.value = true
  try {
    const payload: any = {
      name: form.name,
      description: form.description,
      venue: form.venue,
      wotu_album_url: form.wotu_album_url,
      storage_path_prefix: form.storage_path_prefix,
      cover_image: form.cover_image,
      event_date: form.event_date ? form.event_date.format('YYYY-MM-DD') : null,
    }
    if (isEdit.value) {
      await adminApi.updateActivity(activityId.value, payload)
      message.success('修改成功')
    } else {
      await adminApi.createActivity(payload)
      message.success('创建成功')
    }
    router.push('/admin')
  } catch {
    message.error(isEdit.value ? '修改失败' : '创建失败')
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.page-header h2 {
  margin: 0;
  font-size: 20px;
}
</style>
