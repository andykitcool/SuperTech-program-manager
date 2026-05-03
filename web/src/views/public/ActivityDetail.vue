<template>
  <main class="wx-activity-page">
    <section class="activity-hero">
      <img v-if="activity?.cover_image" :src="activity.cover_image" :alt="activity.name" />
      <div class="activity-hero-overlay">
        <button class="back-button" type="button" @click="router.push('/p/index')">
          <ArrowLeftOutlined />
        </button>
        <div>
          <h1>{{ activity?.name || '活动详情' }}</h1>
          <p>{{ activity?.description || '输入节目号或节目名称，快速查找节目素材。' }}</p>
          <div class="hero-stats">
            <span>{{ activity?.program_count || 0 }} 个节目</span>
            <span>{{ activity?.photo_count || 0 }} 张照片</span>
          </div>
        </div>
      </div>
    </section>

    <section class="search-panel">
      <a-input-search
        v-model:value="keyword"
        size="large"
        allow-clear
        placeholder="输入节目号或节目名称"
        enter-button="搜索"
        @search="searchPrograms"
      />
    </section>

    <section class="result-panel">
      <a-spin :spinning="loading || searching">
        <div v-if="programs.length" class="program-results">
          <button
            v-for="program in programs"
            :key="program.id"
            type="button"
            class="program-card"
            @click="goProgram(program.access_token)"
          >
            <div class="program-number">{{ program.sequence_number }}</div>
            <div>
              <h2>{{ program.name }}</h2>
              <p>{{ program.photo_count }} 张照片 · {{ program.video_status === 'ready' ? '视频已就绪' : '视频待就绪' }}</p>
            </div>
          </button>
        </div>
        <a-empty v-else :description="searched ? '未找到匹配节目' : '请输入节目号或节目名称搜索'" />
      </a-spin>
    </section>
  </main>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowLeftOutlined } from '@ant-design/icons-vue'
import { message } from 'ant-design-vue'
import { publicApi, type PublicActivity, type PublicProgramSearchItem } from '@/api/admin'
import { ensureWechatProfile } from '@/utils/wechat'

const route = useRoute()
const router = useRouter()
const activityId = Number(route.params.activityId)
const activity = ref<PublicActivity | null>(null)
const keyword = ref('')
const programs = ref<PublicProgramSearchItem[]>([])
const loading = ref(false)
const searching = ref(false)
const searched = ref(false)

const fetchActivity = async () => {
  loading.value = true
  try {
    const res = await publicApi.getActivity(activityId)
    activity.value = res.data
  } catch {
    message.error('活动加载失败')
  } finally {
    loading.value = false
  }
}

const searchPrograms = async () => {
  searched.value = true
  searching.value = true
  try {
    const res = await publicApi.searchPrograms(activityId, keyword.value)
    programs.value = res.data
  } catch {
    message.error('节目搜索失败')
  } finally {
    searching.value = false
  }
}

const goProgram = (token: string) => {
  router.push(`/p/${token}`)
}

onMounted(async () => {
  await ensureWechatProfile(activityId)
  await fetchActivity()
})
</script>

<style scoped>
.wx-activity-page {
  min-height: 100vh;
  background: #f6f8fc;
}

.activity-hero {
  position: relative;
  min-height: 260px;
  overflow: hidden;
  background: linear-gradient(135deg, #1d4ed8, #0f766e);
}

.activity-hero > img {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.activity-hero-overlay {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  padding: 18px 18px 24px;
  background: linear-gradient(180deg, rgba(6, 12, 24, 0.26), rgba(6, 12, 24, 0.72));
  color: #fff;
}

.back-button {
  width: 38px;
  height: 38px;
  border: 0;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.2);
  color: #fff;
}

.activity-hero h1 {
  margin: 0 0 8px;
  font-size: 28px;
  letter-spacing: 0;
}

.activity-hero p {
  margin: 0 0 14px;
  line-height: 1.6;
  opacity: 0.92;
}

.hero-stats {
  display: flex;
  gap: 10px;
}

.hero-stats span {
  padding: 5px 10px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.18);
  font-size: 12px;
}

.search-panel {
  position: sticky;
  top: 0;
  z-index: 3;
  padding: 14px 16px;
  background: rgba(246, 248, 252, 0.94);
  backdrop-filter: blur(12px);
}

.result-panel {
  padding: 0 16px 28px;
}

.program-results {
  display: grid;
  gap: 12px;
}

.program-card {
  width: 100%;
  display: grid;
  grid-template-columns: 52px 1fr;
  gap: 14px;
  align-items: center;
  padding: 14px;
  border: 0;
  border-radius: 8px;
  background: #fff;
  box-shadow: 0 8px 24px rgba(22, 32, 54, 0.08);
  text-align: left;
}

.program-number {
  width: 52px;
  height: 52px;
  display: grid;
  place-items: center;
  border-radius: 8px;
  background: #eaf2ff;
  color: #1d4ed8;
  font-size: 20px;
  font-weight: 760;
}

.program-card h2 {
  margin: 0 0 6px;
  color: #172033;
  font-size: 16px;
}

.program-card p {
  margin: 0;
  color: #6b7688;
  font-size: 13px;
}
</style>
