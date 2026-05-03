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
      <a-row :gutter="[18, 18]" v-else>
        <a-col :xs="24" :sm="12" :lg="8" :xl="6" v-for="item in activities" :key="item.id">
          <article class="activity-card" @click="$router.push(`/admin/activity/${item.id}/programs`)">
            <div class="cover-frame">
              <img :src="item.cover_image || defaultCoverImage" :alt="item.name" />
              <a-tag :class="['status-tag', `status-${getActivityStatus(item).key}`]">
                {{ getActivityStatus(item).text }}
              </a-tag>
              <div class="card-stats">
                <div>
                  <strong>{{ item.program_count }}</strong>
                  <span>节目</span>
                </div>
                <div>
                  <strong>{{ item.ready_program_count }}</strong>
                  <span>已就绪</span>
                </div>
              </div>
              <div class="cover-time">
                <CalendarOutlined />
                <span>{{ formatActivityRange(item) }}</span>
              </div>
            </div>

            <div class="card-body">
              <h3>{{ item.name }}</h3>
              <div class="bottom-line">
                <span class="venue-text">{{ item.venue || '未设置地点' }}</span>
                <div class="card-actions">
                  <a-button type="link" size="small" @click.stop="$router.push(`/admin/activity/${item.id}/programs`)">节目</a-button>
                  <a-button type="link" size="small" @click.stop="$router.push(`/admin/activity/${item.id}/edit`)">编辑</a-button>
                  <a-popconfirm title="确定删除此活动？" @confirm.stop="handleDelete(item.id)">
                    <a-button type="link" size="small" danger @click.stop>删除</a-button>
                  </a-popconfirm>
                </div>
              </div>
            </div>
          </article>
        </a-col>
      </a-row>
    </a-spin>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { CalendarOutlined, PlusOutlined } from '@ant-design/icons-vue'
import { message } from 'ant-design-vue'
import dayjs from 'dayjs'
import { adminApi, type Activity } from '@/api/admin'

const defaultCoverImage = 'https://images.unsplash.com/photo-1511795409834-ef04bbd61622?auto=format&fit=crop&w=900&q=80'
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

const getActivityStatus = (activity: Activity) => {
  const now = dayjs()
  const start = activity.start_time ? dayjs(activity.start_time) : (activity.event_date ? dayjs(activity.event_date).startOf('day') : null)
  const end = activity.end_time ? dayjs(activity.end_time) : (activity.event_date ? dayjs(activity.event_date).endOf('day') : null)

  if (start && now.isBefore(start)) return { text: '未开始', key: 'pending' }
  if (end && now.isAfter(end)) return { text: '已结束', key: 'ended' }
  if (start && end) return { text: '进行中', key: 'active' }
  return { text: '时间未设置', key: 'unset' }
}

const formatActivityRange = (activity: Activity) => {
  const start = activity.start_time ? dayjs(activity.start_time) : (activity.event_date ? dayjs(activity.event_date).startOf('day') : null)
  const end = activity.end_time ? dayjs(activity.end_time) : (activity.event_date ? dayjs(activity.event_date).endOf('day') : null)
  if (start && end) {
    return `${start.format('MM-DD HH:mm')} - ${end.format('MM-DD HH:mm')}`
  }
  return '未设置时间'
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
  aspect-ratio: 4 / 3;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  border: 1px solid #eef1f5;
  border-radius: 8px;
  background: #fff;
  box-shadow: 0 8px 22px rgba(18, 31, 53, 0.08);
  cursor: pointer;
  transition: border-color 0.22s ease, box-shadow 0.22s ease, transform 0.22s ease;
}

.activity-card:hover {
  border-color: #d6e4ff;
  box-shadow: 0 14px 34px rgba(18, 31, 53, 0.13);
  transform: translateY(-2px);
}

.cover-frame {
  position: relative;
  aspect-ratio: 16 / 9;
  overflow: hidden;
  background: #edf2f7;
}

.cover-frame::after {
  position: absolute;
  right: 0;
  bottom: 0;
  left: 0;
  height: 52%;
  content: "";
  background: linear-gradient(180deg, rgba(15, 23, 42, 0), rgba(15, 23, 42, 0.62));
  pointer-events: none;
}

.cover-frame img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
  transition: transform 0.28s ease;
}

.activity-card:hover .cover-frame img {
  transform: scale(1.035);
}

.status-tag {
  position: absolute;
  top: 10px;
  right: 10px;
  z-index: 2;
  display: inline-flex;
  align-items: center;
  gap: 5px;
  height: 24px;
  margin: 0;
  padding: 0 9px;
  border: 1px solid rgba(255, 255, 255, 0.82);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.94);
  box-shadow: 0 8px 22px rgba(15, 23, 42, 0.2);
  color: #172033;
  font-size: 12px;
  font-weight: 700;
  line-height: 22px;
  backdrop-filter: blur(10px);
}

.status-tag::before {
  width: 6px;
  height: 6px;
  border-radius: 999px;
  background: var(--status-color, #8c96a8);
  box-shadow: 0 0 0 3px var(--status-halo, rgba(140, 150, 168, 0.16));
  content: "";
}

.status-active {
  --status-color: #1677ff;
  --status-halo: rgba(22, 119, 255, 0.18);
}

.status-pending {
  --status-color: #d48806;
  --status-halo: rgba(212, 136, 6, 0.18);
}

.status-ended {
  --status-color: #8c96a8;
  --status-halo: rgba(140, 150, 168, 0.18);
}

.status-unset {
  --status-color: #b36b00;
  --status-halo: rgba(179, 107, 0, 0.16);
}

.card-stats {
  position: absolute;
  left: 12px;
  bottom: 10px;
  z-index: 2;
  display: flex;
  gap: 6px;
}

.card-stats div {
  min-width: 54px;
  padding: 4px 7px;
  border: 1px solid rgba(255, 255, 255, 0.18);
  border-radius: 6px;
  background: rgba(15, 23, 42, 0.52);
  color: #fff;
  backdrop-filter: blur(8px);
}

.card-stats strong {
  margin-right: 4px;
  color: #fff;
  font-size: 16px;
  line-height: 1;
}

.card-stats span {
  color: rgba(255, 255, 255, 0.82);
  font-size: 12px;
}

.cover-time {
  position: absolute;
  right: 12px;
  bottom: 12px;
  z-index: 2;
  display: inline-flex;
  align-items: center;
  max-width: 48%;
  min-width: 0;
  gap: 4px;
  padding: 4px 7px;
  overflow: hidden;
  border-radius: 6px;
  background: rgba(255, 255, 255, 0.88);
  color: #243047;
  font-size: 11px;
  line-height: 1;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.cover-time span {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.card-body {
  min-height: 48px;
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  padding: 7px 10px 8px;
}

.card-body h3 {
  display: block;
  margin: 0;
  overflow: hidden;
  color: #172033;
  font-size: 15px;
  font-weight: 700;
  line-height: 19px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.bottom-line {
  min-height: 20px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.venue-text {
  min-width: 0;
  overflow: hidden;
  color: #6b7688;
  font-size: 12px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.card-actions {
  flex: 0 0 auto;
  display: inline-flex;
  align-items: center;
  gap: 2px;
}

.card-actions :deep(.ant-btn) {
  height: 20px;
  padding: 0 3px;
  font-size: 11px;
  line-height: 18px;
}
</style>
