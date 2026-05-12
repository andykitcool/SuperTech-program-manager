<template>
  <div class="music-library">
    <div class="page-header">
      <h2>热门曲库</h2>
      <a-space>
        <a-upload
          :before-upload="handleBeforeUpload"
          :show-upload-list="false"
          accept=".mp3,.wav,.flac,.aac,.ogg,.m4a,.wma"
        >
          <a-button type="primary" :loading="uploading">
            <template #icon><UploadOutlined /></template>
            上传音乐
          </a-button>
        </a-upload>
        <a-button @click="fetchMusics" :loading="loading">
          <template #icon><ReloadOutlined /></template>
          刷新
        </a-button>
      </a-space>
    </div>

    <a-spin :spinning="loading">
      <div v-if="musics.length > 0" class="music-grid">
        <div v-for="music in musics" :key="music.id" class="music-card">
          <div class="music-card-icon" :class="{ playing: playingId === music.id }">
            <CustomerServiceOutlined />
          </div>
          <div class="music-card-info">
            <div class="music-card-name" :title="music.name">{{ music.name }}</div>
            <div class="music-card-meta">
              <span v-if="music.duration != null">{{ formatDuration(music.duration) }}</span>
              <span v-else>未知时长</span>
              <span class="music-card-size" v-if="music.file_size">{{ formatFileSize(music.file_size) }}</span>
            </div>
          </div>
          <div class="music-card-actions">
            <a-button
              type="text"
              size="small"
              :class="{ 'playing-btn': playingId === music.id }"
              @click="togglePlay(music)"
            >
              <template #icon>
                <PauseCircleOutlined v-if="playingId === music.id" />
                <PlayCircleOutlined v-else />
              </template>
            </a-button>
            <a-popconfirm
              title="确定要删除这首音乐吗？"
              ok-text="确定"
              cancel-text="取消"
              @confirm="handleDelete(music.id)"
            >
              <a-button type="text" size="small" danger>
                <template #icon><DeleteOutlined /></template>
              </a-button>
            </a-popconfirm>
          </div>
        </div>
      </div>
      <a-empty v-else description="暂无音乐，请点击上方按钮上传" style="padding: 60px 0" />
    </a-spin>

    <div class="music-pagination" v-if="total > pageSize">
      <a-pagination
        v-model:current="page"
        :page-size="pageSize"
        :total="total"
        show-less-items
        @change="handlePageChange"
      />
    </div>

    <!-- Hidden audio element -->
    <audio ref="audioRef" @ended="onAudioEnded" @error="onAudioError" />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { message, Modal } from 'ant-design-vue'
import {
  CustomerServiceOutlined,
  DeleteOutlined,
  PauseCircleOutlined,
  PlayCircleOutlined,
  ReloadOutlined,
  UploadOutlined,
} from '@ant-design/icons-vue'
import { musicApi, type MusicItem } from '@/api/admin'

const musics = ref<MusicItem[]>([])
const loading = ref(false)
const uploading = ref(false)
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)

const playingId = ref<number | null>(null)
const audioRef = ref<HTMLAudioElement | null>(null)

const fetchMusics = async () => {
  loading.value = true
  try {
    const res = await musicApi.list(page.value, pageSize.value)
    musics.value = res.data.items
    total.value = res.data.total
  } catch {
    message.error('加载音乐列表失败')
  } finally {
    loading.value = false
  }
}

const handleBeforeUpload = async (file: File) => {
  const ext = file.name.substring(file.name.lastIndexOf('.')).toLowerCase()
  const allowed = ['.mp3', '.wav', '.flac', '.aac', '.ogg', '.m4a', '.wma']
  if (!allowed.includes(ext)) {
    message.error(`不支持的文件格式: ${ext}`)
    return false
  }

  uploading.value = true
  try {
    await musicApi.upload(file)
    message.success('上传成功')
    await fetchMusics()
  } catch {
    message.error('上传失败')
  } finally {
    uploading.value = false
  }
  return false
}

const togglePlay = (music: MusicItem) => {
  const audio = audioRef.value
  if (!audio) return

  if (playingId.value === music.id) {
    audio.pause()
    playingId.value = null
    return
  }

  if (!music.storage_url) {
    message.error('该音乐暂无可播放的文件地址')
    return
  }

  audio.src = music.storage_url
  audio.play().catch(() => {
    message.error('播放失败，请稍后重试')
    playingId.value = null
  })
  playingId.value = music.id
}

const onAudioEnded = () => {
  playingId.value = null
}

const onAudioError = () => {
  if (playingId.value !== null) {
    message.error('播放出错')
    playingId.value = null
  }
}

const handleDelete = async (musicId: number) => {
  if (playingId.value === musicId) {
    audioRef.value?.pause()
    playingId.value = null
  }
  try {
    await musicApi.delete(musicId)
    message.success('已删除')
    await fetchMusics()
  } catch {
    message.error('删除失败')
  }
}

const handlePageChange = (p: number) => {
  page.value = p
  fetchMusics()
}

function formatDuration(seconds: number): string {
  const m = Math.floor(seconds / 60)
  const s = Math.floor(seconds % 60)
  return `${m}:${s.toString().padStart(2, '0')}`
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes}B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)}KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)}MB`
}

onMounted(() => {
  fetchMusics()
})

onUnmounted(() => {
  if (audioRef.value) {
    audioRef.value.pause()
    audioRef.value.src = ''
  }
})
</script>

<style scoped>
.music-library {
  min-height: 400px;
}

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 24px;
}

.page-header h2 {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
}

.music-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 16px;
}

.music-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px;
  border: 1px solid #f0f0f0;
  border-radius: 10px;
  background: #fafafa;
  transition: all 0.2s;
}

.music-card:hover {
  border-color: #d9d9d9;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}

.music-card-icon {
  flex-shrink: 0;
  width: 44px;
  height: 44px;
  border-radius: 50%;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  transition: transform 0.3s;
}

.music-card-icon.playing {
  animation: pulse 1.5s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { transform: scale(1); }
  50% { transform: scale(1.1); }
}

.music-card-info {
  flex: 1;
  min-width: 0;
}

.music-card-name {
  font-size: 14px;
  font-weight: 500;
  color: rgba(0, 0, 0, 0.85);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.music-card-meta {
  margin-top: 4px;
  font-size: 12px;
  color: rgba(0, 0, 0, 0.45);
  display: flex;
  gap: 8px;
}

.music-card-actions {
  flex-shrink: 0;
  display: flex;
  gap: 2px;
}

.playing-btn {
  color: #764ba2 !important;
}

.music-pagination {
  margin-top: 24px;
  text-align: center;
}
</style>
