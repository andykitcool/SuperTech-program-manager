<template>
  <main class="wx-page">
    <section class="index-hero">
      <div>
        <p>SuperTech 快速交付系统</p>
        <h1>活动素材中心</h1>
        <span>请选择活动，输入节目号或节目名称即可查看专属照片与视频。</span>
      </div>
    </section>

    <section class="activity-list">
      <a-spin :spinning="loading">
        <div v-if="activities.length" class="activity-grid">
          <button
            v-for="activity in activities"
            :key="activity.id"
            class="activity-card"
            type="button"
            @click="goActivity(activity.id)"
          >
            <div class="activity-cover">
              <img v-if="activity.cover_image" :src="activity.cover_image" :alt="activity.name" />
              <div v-else class="activity-cover-fallback">{{ activity.name.slice(0, 2) }}</div>
            </div>
            <div class="activity-body">
              <h2>{{ activity.name }}</h2>
              <p>{{ activity.description || '活动照片与节目视频交付入口' }}</p>
              <div class="activity-meta">
                <span><CalendarOutlined />{{ activity.event_date || '日期待定' }}</span>
                <span>{{ activity.program_count }} 个节目</span>
              </div>
            </div>
          </button>
        </div>
        <a-empty v-else description="暂无活动" />
      </a-spin>
    </section>
  </main>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { CalendarOutlined } from '@ant-design/icons-vue'
import { message } from 'ant-design-vue'
import { publicApi, type PublicActivity } from '@/api/admin'
import { ensureWechatProfile } from '@/utils/wechat'

const router = useRouter()
const activities = ref<PublicActivity[]>([])
const loading = ref(false)

const fetchActivities = async () => {
  loading.value = true
  try {
    const res = await publicApi.listActivities()
    activities.value = res.data
  } catch {
    message.error('活动加载失败')
  } finally {
    loading.value = false
  }
}

const goActivity = (id: number) => {
  router.push(`/p/${id}`)
}

onMounted(async () => {
  await ensureWechatProfile()
  await fetchActivities()
})
</script>

<style scoped>
.wx-page {
  min-height: 100vh;
  background: #f5f7fb;
  color: #172033;
}

.index-hero {
  min-height: 210px;
  display: flex;
  align-items: flex-end;
  padding: 28px 20px;
  background:
    linear-gradient(135deg, rgba(15, 91, 255, 0.92), rgba(4, 191, 149, 0.82)),
    url('https://images.unsplash.com/photo-1511795409834-ef04bbd61622?auto=format&fit=crop&w=1200&q=80') center/cover;
  color: #fff;
}

.index-hero p {
  margin: 0 0 6px;
  font-size: 13px;
  opacity: 0.86;
}

.index-hero h1 {
  margin: 0 0 8px;
  font-size: 30px;
  letter-spacing: 0;
}

.index-hero span {
  display: block;
  max-width: 340px;
  line-height: 1.6;
  opacity: 0.9;
}

.activity-list {
  padding: 16px;
}

.activity-grid {
  display: grid;
  gap: 14px;
}

.activity-card {
  width: 100%;
  display: grid;
  grid-template-columns: 108px 1fr;
  gap: 14px;
  padding: 12px;
  border: 0;
  border-radius: 8px;
  background: #fff;
  box-shadow: 0 10px 28px rgba(22, 32, 54, 0.08);
  text-align: left;
}

.activity-cover {
  aspect-ratio: 1;
  overflow: hidden;
  border-radius: 8px;
  background: #e9eef8;
}

.activity-cover img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.activity-cover-fallback {
  height: 100%;
  display: grid;
  place-items: center;
  color: #2563eb;
  font-size: 24px;
  font-weight: 700;
}

.activity-body h2 {
  margin: 4px 0 8px;
  color: #172033;
  font-size: 17px;
}

.activity-body p {
  min-height: 40px;
  margin: 0 0 10px;
  color: #637083;
  font-size: 13px;
  line-height: 1.55;
}

.activity-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  color: #486078;
  font-size: 12px;
}

.activity-meta span {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}
</style>
