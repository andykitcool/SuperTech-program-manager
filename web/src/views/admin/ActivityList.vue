<template>
  <div>
    <div class="page-header">
      <h2>活动管理</h2>
      <a-button type="primary" @click="$router.push('/admin/activity/create')">
        <template #icon><PlusOutlined /></template>
        创建活动
      </a-button>
    </div>
    <a-spin :spinning="loading">
      <a-empty v-if="!loading && activities.length === 0" description="暂无活动" />
      <a-row :gutter="[16, 16]" v-else>
        <a-col :xs="24" :sm="12" :lg="6" v-for="item in activities" :key="item.id">
          <a-card hoverable class="activity-card" @click="$router.push(`/admin/activity/${item.id}/programs`)">
            <template #cover>
              <div class="card-cover">
                <CalendarOutlined class="cover-icon" />
                <span class="cover-date">{{ item.event_date || '未设定日期' }}</span>
              </div>
            </template>
            <a-card-meta :title="item.name" :description="item.venue || ''">
              <template #avatar>
                <a-avatar :style="{ backgroundColor: item.status === 'active' ? '#1890ff' : '#d9d9d9' }">
                  {{ item.program_count }}
                </a-avatar>
              </template>
            </a-card-meta>
            <div class="card-footer">
              <a-space>
                <a-tag :color="item.status === 'active' ? 'blue' : 'default'">
                  {{ item.status === 'active' ? '进行中' : '已结束' }}
                </a-tag>
                <span class="ready-count">{{ item.ready_program_count }}/{{ item.program_count }} 节目就绪</span>
              </a-space>
              <a-space>
                <a-button type="link" size="small" @click.stop="$router.push(`/admin/activity/${item.id}/programs`)">
                  节目
                </a-button>
                <a-button type="link" size="small" @click.stop="$router.push(`/admin/activity/${item.id}/edit`)">
                  编辑
                </a-button>
                <a-popconfirm title="确定删除此活动？" @confirm.stop="handleDelete(item.id)">
                  <a-button type="link" size="small" danger @click.stop>删除</a-button>
                </a-popconfirm>
              </a-space>
            </div>
          </a-card>
        </a-col>
      </a-row>
    </a-spin>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { PlusOutlined, CalendarOutlined } from '@ant-design/icons-vue'
import { message } from 'ant-design-vue'
import { adminApi, type Activity } from '@/api/admin'

const activities = ref<Activity[]>([])
const loading = ref(false)

const fetchActivities = async () => {
  loading.value = true
  try {
    const res = await adminApi.listActivities()
    activities.value = res.data
  } catch {
    message.error('加载活动列表失败')
  } finally {
    loading.value = false
  }
}

const handleDelete = async (id: number) => {
  try {
    await adminApi.deleteActivity(id)
    message.success('删除成功')
    fetchActivities()
  } catch {
    message.error('删除失败')
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
  background: linear-gradient(135deg, #e6f7ff 0%, #bae7ff 100%);
}

.cover-icon {
  font-size: 24px;
  color: #1890ff;
  margin-bottom: 4px;
}

.cover-date {
  color: #1890ff;
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

.ready-count {
  font-size: 12px;
  color: #8c8c8c;
}
</style>
