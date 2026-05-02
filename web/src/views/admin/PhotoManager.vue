<template>
  <div>
    <div class="page-header">
      <h2>照片管理</h2>
      <div></div>
    </div>
    <a-spin :spinning="loading">
      <a-empty v-if="!loading && activities.length === 0" description="暂无已同步照片的活动" />
      <a-row :gutter="[16, 16]" v-else>
        <a-col :xs="24" :sm="12" :lg="6" v-for="item in activities" :key="item.id">
          <a-card hoverable class="activity-card" @click="$router.push(`/admin/photo-manager/activity/${item.id}`)">
            <template #cover>
              <div class="card-cover">
                <PictureOutlined class="cover-icon" />
                <span class="cover-date">{{ item.event_date || '未设定日期' }}</span>
              </div>
            </template>
            <a-card-meta :title="item.name" :description="item.venue || ''">
              <template #avatar>
                <a-avatar style="backgroundColor: #52c41a">
                  {{ item.photo_count }}
                </a-avatar>
              </template>
            </a-card-meta>
            <div class="card-footer">
              <a-tag color="green">{{ item.photo_count }} 张照片</a-tag>
              <a-button type="link" size="small" @click.stop="$router.push(`/admin/photo-manager/activity/${item.id}`)">
                查看照片
              </a-button>
            </div>
          </a-card>
        </a-col>
      </a-row>
    </a-spin>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { PictureOutlined } from '@ant-design/icons-vue'
import { message } from 'ant-design-vue'
import { photoApi, type PhotoActivity } from '@/api/admin'

const activities = ref<PhotoActivity[]>([])
const loading = ref(false)

const fetchActivities = async () => {
  loading.value = true
  try {
    const res = await photoApi.getPhotoActivities()
    activities.value = res.data
  } catch {
    message.error('加载活动列表失败')
  } finally {
    loading.value = false
  }
}

onMounted(fetchActivities)
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

.activity-card {
  border-radius: 8px;
  overflow: hidden;
  transition: box-shadow 0.3s, transform 0.2s;
}

.activity-card :deep(.ant-card-body) {
  padding: 12px;
}

.activity-card:hover {
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.12);
  transform: translateY(-2px);
}

.card-cover {
  height: 80px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #f6ffed 0%, #b7eb8f 100%);
}

.cover-icon {
  font-size: 24px;
  color: #52c41a;
  margin-bottom: 4px;
}

.cover-date {
  color: #52c41a;
  font-size: 12px;
  font-weight: 500;
}

.card-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px solid #f0f0f0;
}
</style>
