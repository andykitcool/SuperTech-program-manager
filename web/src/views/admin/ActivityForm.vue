<template>
  <div class="activity-form-page">
    <div class="page-header">
      <a-button @click="$router.back()">
        <template #icon><ArrowLeftOutlined /></template>
        返回
      </a-button>
      <h2>{{ isEdit ? '编辑活动' : '创建活动' }}</h2>
      <div></div>
    </div>

    <a-form :model="form" layout="vertical" @finish="handleSubmit" class="activity-form">
      <a-form-item label="活动名称" name="name" :rules="[{ required: true, message: '请输入活动名称' }]">
        <a-input v-model:value="form.name" placeholder="例如：2026 春季少儿舞蹈展演" />
      </a-form-item>

      <a-form-item label="活动主图">
        <a-upload-dragger
          accept="image/png,image/jpeg,image/webp"
          :show-upload-list="false"
          :before-upload="handleCoverUpload"
        >
          <div class="cover-uploader">
            <img v-if="form.cover_image" :src="form.cover_image" alt="活动主图" />
            <template v-else>
              <PictureOutlined class="cover-upload-icon" />
              <p>点击或拖拽上传活动主图</p>
              <span>建议使用 16:9 图片，支持 JPG、PNG、WEBP</span>
            </template>
          </div>
        </a-upload-dragger>
      </a-form-item>

      <a-row :gutter="16">
        <a-col :xs="24" :md="12">
          <a-form-item label="活动开始日期、时间" name="start_time" :rules="[{ required: true, message: '请选择活动开始时间' }]">
            <a-date-picker
              v-model:value="form.start_time"
              show-time
              format="YYYY-MM-DD HH:mm"
              style="width: 100%"
              placeholder="选择开始日期和时间"
            />
          </a-form-item>
        </a-col>
        <a-col :xs="24" :md="12">
          <a-form-item label="活动结束日期、时间" name="end_time" :rules="[{ required: true, message: '请选择活动结束时间' }]">
            <a-date-picker
              v-model:value="form.end_time"
              show-time
              format="YYYY-MM-DD HH:mm"
              style="width: 100%"
              placeholder="选择结束日期和时间"
            />
          </a-form-item>
        </a-col>
      </a-row>

      <a-form-item label="活动地点" name="venue">
        <a-input v-model:value="form.venue" placeholder="演出场地" />
      </a-form-item>

      <a-form-item label="喔图相册 URL" name="wotu_album_url">
        <a-input v-model:value="form.wotu_album_url" placeholder="https://m.alltuu.com/album/xxx/" />
      </a-form-item>

      <a-form-item label="存储路径前缀" name="storage_path_prefix">
        <a-input v-model:value="form.storage_path_prefix" placeholder="留空则自动生成" />
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
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowLeftOutlined, PictureOutlined } from '@ant-design/icons-vue'
import { message } from 'ant-design-vue'
import dayjs, { type Dayjs } from 'dayjs'
import { adminApi } from '@/api/admin'

const route = useRoute()
const router = useRouter()
const submitting = ref(false)
const uploadingCover = ref(false)
const activityId = computed(() => Number(route.params.id))
const isEdit = computed(() => !Number.isNaN(activityId.value))

const form = reactive({
  name: '',
  start_time: null as Dayjs | null,
  end_time: null as Dayjs | null,
  venue: '',
  wotu_album_url: '',
  storage_path_prefix: '',
  cover_image: '',
})

onMounted(async () => {
  if (!isEdit.value) return
  try {
    const res = await adminApi.getActivity(activityId.value)
    const data = res.data
    form.name = data.name
    form.start_time = data.start_time ? dayjs(data.start_time) : (data.event_date ? dayjs(data.event_date).startOf('day') : null)
    form.end_time = data.end_time ? dayjs(data.end_time) : (data.event_date ? dayjs(data.event_date).endOf('day') : null)
    form.venue = data.venue || ''
    form.wotu_album_url = data.wotu_album_url || ''
    form.storage_path_prefix = data.storage_path_prefix || ''
    form.cover_image = data.cover_image || ''
  } catch {
    message.error('加载活动信息失败')
  }
})

const handleCoverUpload = async (file: File) => {
  if (!file.type.startsWith('image/')) {
    message.warning('请选择图片文件')
    return false
  }
  if (file.size > 5 * 1024 * 1024) {
    message.warning('图片大小不能超过 5MB')
    return false
  }

  uploadingCover.value = true
  try {
    const res = await adminApi.uploadActivityCover(file)
    form.cover_image = res.data.url
    message.success('活动主图已上传')
  } catch {
    message.error('上传活动主图失败')
  } finally {
    uploadingCover.value = false
  }
  return false
}

const handleSubmit = async () => {
  if (form.start_time && form.end_time && form.end_time.isBefore(form.start_time)) {
    message.warning('活动结束时间不能早于开始时间')
    return
  }

  submitting.value = true
  try {
    const payload = {
      name: form.name,
      description: '',
      venue: form.venue,
      wotu_album_url: form.wotu_album_url,
      storage_path_prefix: form.storage_path_prefix,
      cover_image: form.cover_image,
      start_time: form.start_time ? form.start_time.toISOString() : null,
      end_time: form.end_time ? form.end_time.toISOString() : null,
      event_date: form.start_time ? form.start_time.format('YYYY-MM-DD') : null,
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
.activity-form-page {
  max-width: 760px;
}

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

.activity-form {
  max-width: 720px;
}

.cover-uploader {
  width: 100%;
  aspect-ratio: 16 / 9;
  display: grid;
  place-items: center;
  overflow: hidden;
  color: #5b6b82;
}

.cover-uploader img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.cover-upload-icon {
  color: #2563eb;
  font-size: 34px;
}

.cover-uploader p {
  margin: 8px 0 2px;
  color: #1f2937;
  font-weight: 600;
}

.cover-uploader span {
  color: #7b8796;
  font-size: 13px;
}
</style>
