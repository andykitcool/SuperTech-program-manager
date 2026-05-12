<template>
  <div class="lobby-player" :class="{ 'is-idle': isIdle }" @mousemove="onMouseMove" @click="onMouseMove">
    <!-- Ambient background -->
    <div class="ambient-bg">
      <div class="ambient-orb orb-1" />
      <div class="ambient-orb orb-2" />
      <div class="ambient-orb orb-3" />
    </div>

    <!-- Video layer -->
    <transition name="video-fade" mode="out-in">
      <video
        v-if="currentVideo"
        ref="videoRef"
        :key="playbackKey"
        :src="currentVideo.short_video_url"
        class="lobby-video"
        autoplay
        :muted="isMuted"
        playsinline
        @ended="onVideoEnded"
        @error="onVideoError"
        @canplay="onVideoCanPlay"
      />
    </transition>

    <!-- Overlay gradient -->
    <div class="video-overlay" />

    <!-- Top bar: activity info -->
    <transition name="slide-down">
      <header v-show="showOverlay" class="top-bar">
        <div class="top-bar-inner">
          <div class="activity-badge">
            <span class="badge-dot" />
            <span class="badge-text">LIVE</span>
          </div>
          <div class="activity-info">
            <h1 class="activity-name">{{ activityInfo?.name || '' }}</h1>
            <p v-if="activityInfo?.venue" class="activity-venue">{{ activityInfo.venue }}</p>
          </div>
        </div>
      </header>
    </transition>

    <!-- Bottom bar: now playing -->
    <transition name="slide-up">
      <footer v-show="showOverlay" class="bottom-bar">
        <div class="bottom-bar-inner">
          <div class="now-playing">
            <div class="now-playing-label">正在播放</div>
            <div class="now-playing-title">
              <span class="seq-num">{{ formatSeq(currentVideo?.sequence_number) }}</span>
              <span class="prog-name">{{ currentVideo?.program_name || '' }}</span>
            </div>
          </div>
          <div class="playback-stats">
            <div class="stat">
              <span class="stat-value">{{ allVideos.length }}</span>
              <span class="stat-label">视频总数</span>
            </div>
            <div class="stat-divider" />
            <div class="stat">
              <span class="stat-value">{{ currentVideoIndex + 1 }}</span>
              <span class="stat-label">当前序号</span>
            </div>
          </div>
        </div>
        <!-- Progress bar -->
        <div class="progress-track">
          <div class="progress-fill" :style="{ width: progressPercent + '%' }" />
        </div>
      </footer>
    </transition>

    <!-- Mute toggle (always visible, auto-hides with overlay) -->
    <transition name="fade">
      <button
        v-show="showOverlay"
        class="mute-toggle"
        :title="isMuted ? '取消静音' : '静音'"
        @click.stop="toggleMute"
      >
        <!-- Volume on icon -->
        <svg v-if="!isMuted" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5" />
          <path d="M19.07 4.93a10 10 0 0 1 0 14.14" />
          <path d="M15.54 8.46a5 5 0 0 1 0 7.07" />
        </svg>
        <!-- Volume off icon -->
        <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5" />
          <line x1="23" y1="9" x2="17" y2="15" />
          <line x1="17" y1="9" x2="23" y2="15" />
        </svg>
      </button>
    </transition>

    <!-- Idle / loading screen -->
    <div v-if="isIdle" class="idle-screen">
      <div class="idle-content">
        <div class="idle-icon">
          <svg viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg">
            <rect x="4" y="10" width="28" height="28" rx="4" stroke="currentColor" stroke-width="2.5" />
            <path d="M40 16v16a4 4 0 004-4v-8a4 4 0 00-4-4z" stroke="currentColor" stroke-width="2.5" />
            <circle cx="18" cy="24" r="4" fill="currentColor" />
          </svg>
        </div>
        <h2 class="idle-title">{{ idleMessage }}</h2>
        <p class="idle-subtitle">等待短视频就绪后自动播放</p>
        <div v-if="isChecking" class="idle-spinner">
          <span class="spinner-dot" />
          <span class="spinner-dot" />
          <span class="spinner-dot" />
        </div>
      </div>
    </div>

    <!-- New video notification -->
    <transition name="toast-slide">
      <div v-if="showNewVideoToast" class="new-video-toast">
        <span class="toast-icon">✦</span>
        <span>检测到新短视频，即将优先播放</span>
      </div>
    </transition>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'

interface ActivityInfo {
  id: number
  name: string
  venue: string | null
  event_date: string | null
}

interface VideoItem {
  program_id: number
  program_name: string
  sequence_number: number
  short_video_url: string
  updated_at: string | null
}

const route = useRoute()
const activityId = computed(() => Number(route.params.activityId))

const API_BASE = import.meta.env.VITE_API_BASE || ''

// State
const activityInfo = ref<ActivityInfo | null>(null)
const playlist = ref<VideoItem[]>([])
const playedList = ref<VideoItem[]>([])
const currentVideo = ref<VideoItem | null>(null)
const playedIndex = ref(0)
const isIdle = ref(true)
const isChecking = ref(false)
const showOverlay = ref(true)
const showNewVideoToast = ref(false)
const progressPercent = ref(0)
const videoRef = ref<HTMLVideoElement | null>(null)
const isMuted = ref(true)
const playbackKey = ref(0)

let overlayTimer: number | null = null
let progressTimer: number | null = null
let wakeLock: any = null
let totalVideosLoaded = 0

const idleMessage = computed(() => {
  if (!activityInfo.value) return '加载中...'
  return `${activityInfo.value.name} · 等待播放`
})

const currentVideoIndex = computed(() => {
  if (!currentVideo.value) return 0
  return allVideos.value.findIndex(v => v.program_id === currentVideo.value!.program_id)
})

// Formatting
const formatSeq = (n?: number | null) => n != null ? String(n).padStart(3, '0') : ''

// Fetch videos from lobby API
const fetchVideos = async (): Promise<VideoItem[]> => {
  try {
    const res = await fetch(`${API_BASE}/api/public/lobby/${activityId.value}/short-videos`)
    if (!res.ok) throw new Error('Failed to fetch')
    const data = await res.json()
    activityInfo.value = data.activity
    return data.videos || []
  } catch {
    return []
  }
}

// All known videos (deduplicated by program_id)
const allVideos = ref<VideoItem[]>([])

// Check for new videos from server
const checkForNewVideos = async () => {
  isChecking.value = true
  try {
    const latestVideos = await fetchVideos()
    const existingIds = new Set(allVideos.value.map(v => v.program_id))
    const newVideos = latestVideos.filter(v => !existingIds.has(v.program_id))
    if (newVideos.length > 0) {
      showNewVideoToast.value = true
      setTimeout(() => { showNewVideoToast.value = false }, 3000)
      // Add new videos to the front of playlist and to allVideos
      playlist.value = [...newVideos, ...playlist.value]
      allVideos.value = [...newVideos, ...allVideos.value]
    }
    return newVideos.length
  } finally {
    isChecking.value = false
  }
}

// Play next video
const playNext = async () => {
  if (playlist.value.length > 0) {
    // Play next from playlist (new or unseen videos first)
    currentVideo.value = playlist.value.shift()!
    playedList.value.push(currentVideo.value)
    playedIndex.value = playedList.value.length - 1
    isIdle.value = false
    playbackKey.value++
  } else if (allVideos.value.length > 0) {
    // Playlist exhausted — pick a random video from all known videos (loop forever)
    const randomIndex = Math.floor(Math.random() * allVideos.value.length)
    currentVideo.value = allVideos.value[randomIndex]
    playedList.value.push(currentVideo.value)
    playedIndex.value = playedList.value.length - 1
    isIdle.value = false
    playbackKey.value++
  } else {
    // No videos at all — wait and retry
    isIdle.value = true
    await checkForNewVideos()
    if (playlist.value.length > 0) {
      playNext()
    } else {
      setTimeout(async () => {
        await checkForNewVideos()
        if (playlist.value.length > 0) playNext()
      }, 10000)
    }
  }
}

// Initialize
const init = async () => {
  const videos = await fetchVideos()
  totalVideosLoaded = videos.length
  if (videos.length > 0) {
    playlist.value = [...videos]
    allVideos.value = [...videos]
    playNext()
  } else {
    isIdle.value = true
    // Poll for videos
    setTimeout(async () => {
      const retry = await fetchVideos()
      if (retry.length > 0) {
        playlist.value = [...retry]
        allVideos.value = [...retry]
        totalVideosLoaded = retry.length
        playNext()
      }
    }, 8000)
  }
}

// Video event handlers
const onVideoEnded = async () => {
  await checkForNewVideos()
  await playNext()
}

const onVideoError = async () => {
  console.warn('Video playback error, skipping...')
  await checkForNewVideos()
  await playNext()
}

const onVideoCanPlay = async () => {
  const video = videoRef.value
  if (video) {
    try {
      await video.play()
    } catch (e: any) {
      if (e.name === 'NotAllowedError') {
        // Autoplay blocked — ensure muted and retry
        isMuted.value = true
        video.muted = true
        try { await video.play() } catch {}
      }
    }
  }
}

const toggleMute = () => {
  isMuted.value = !isMuted.value
  if (videoRef.value) {
    videoRef.value.muted = isMuted.value
  }
}

// Progress tracking
const startProgressTracking = () => {
  stopProgressTracking()
  const update = () => {
    const video = videoRef.value
    if (video && video.duration && !video.paused) {
      progressPercent.value = (video.currentTime / video.duration) * 100
    }
    progressTimer = requestAnimationFrame(update)
  }
  progressTimer = requestAnimationFrame(update)
}

const stopProgressTracking = () => {
  if (progressTimer) {
    cancelAnimationFrame(progressTimer)
    progressTimer = null
  }
}

// Overlay auto-hide
const showOverlayTemporarily = () => {
  showOverlay.value = true
  if (overlayTimer) clearTimeout(overlayTimer)
  overlayTimer = window.setTimeout(() => {
    showOverlay.value = false
  }, 5000)
}

const onMouseMove = () => {
  showOverlayTemporarily()
}

// Wake Lock — keep screen awake
const requestWakeLock = async () => {
  try {
    if ('wakeLock' in navigator) {
      wakeLock = await (navigator as any).wakeLock.request('screen')
      wakeLock.addEventListener('release', () => { wakeLock = null })
    }
  } catch {
    // Wake Lock not supported or denied
  }
}

// Periodic wake lock re-request (for when tab regains focus)
const handleVisibilityChange = () => {
  if (document.visibilityState === 'visible') {
    requestWakeLock()
  }
}

// Watch video ref for progress tracking
watch(videoRef, (el) => {
  if (el) {
    startProgressTracking()
  } else {
    stopProgressTracking()
  }
})

watch(currentVideo, () => {
  progressPercent.value = 0
})

onMounted(async () => {
  document.body.style.overflow = 'hidden'
  document.documentElement.style.overflow = 'hidden'
  await init()
  await requestWakeLock()
  document.addEventListener('visibilitychange', handleVisibilityChange)
  showOverlayTemporarily()
})

onUnmounted(() => {
  document.body.style.overflow = ''
  document.documentElement.style.overflow = ''
  stopProgressTracking()
  if (overlayTimer) clearTimeout(overlayTimer)
  document.removeEventListener('visibilitychange', handleVisibilityChange)
  if (wakeLock) {
    try { wakeLock.release() } catch {}
  }
})
</script>

<style scoped>
/* ── Reset & Base ─────────────────────────────────────── */
.lobby-player {
  position: fixed;
  inset: 0;
  background: #0a0a0f;
  color: #fff;
  font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display', 'PingFang SC',
    'Noto Sans SC', 'Helvetica Neue', Arial, sans-serif;
  overflow: hidden;
  user-select: none;
  cursor: none;
  z-index: 9999;
}

.lobby-player:hover,
.lobby-player.is-idle {
  cursor: default;
}

/* ── Ambient Background ──────────────────────────────── */
.ambient-bg {
  position: absolute;
  inset: 0;
  overflow: hidden;
  pointer-events: none;
}

.ambient-orb {
  position: absolute;
  border-radius: 50%;
  filter: blur(120px);
  opacity: 0.15;
  animation: orbFloat 20s ease-in-out infinite;
}

.orb-1 {
  width: 60vw;
  height: 60vw;
  top: -20%;
  left: -10%;
  background: radial-gradient(circle, #6366f1 0%, transparent 70%);
  animation-delay: 0s;
}

.orb-2 {
  width: 50vw;
  height: 50vw;
  bottom: -20%;
  right: -10%;
  background: radial-gradient(circle, #a855f7 0%, transparent 70%);
  animation-delay: -7s;
}

.orb-3 {
  width: 40vw;
  height: 40vw;
  top: 30%;
  left: 50%;
  background: radial-gradient(circle, #3b82f6 0%, transparent 70%);
  animation-delay: -14s;
  opacity: 0.08;
}

@keyframes orbFloat {
  0%, 100% { transform: translate(0, 0) scale(1); }
  25% { transform: translate(30px, -20px) scale(1.05); }
  50% { transform: translate(-20px, 30px) scale(0.95); }
  75% { transform: translate(20px, 20px) scale(1.02); }
}

/* ── Video ───────────────────────────────────────────── */
.lobby-video {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: contain;
  background: #000;
}

/* ── Video fade transition ───────────────────────────── */
.video-fade-enter-active,
.video-fade-leave-active {
  transition: opacity 0.8s cubic-bezier(0.4, 0, 0.2, 1);
}

.video-fade-enter-from,
.video-fade-leave-to {
  opacity: 0;
}

/* ── Overlay gradient ────────────────────────────────── */
.video-overlay {
  position: absolute;
  inset: 0;
  pointer-events: none;
  background:
    linear-gradient(to bottom, rgba(0, 0, 0, 0.5) 0%, transparent 18%),
    linear-gradient(to top, rgba(0, 0, 0, 0.6) 0%, transparent 22%);
  z-index: 1;
}

/* ── Top Bar ─────────────────────────────────────────── */
.top-bar {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  z-index: 10;
  padding: 28px 40px 40px;
  background: linear-gradient(to bottom, rgba(0, 0, 0, 0.5) 0%, transparent 100%);
}

.top-bar-inner {
  display: flex;
  align-items: center;
  gap: 20px;
}

.activity-badge {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 16px;
  background: rgba(239, 68, 68, 0.9);
  border-radius: 6px;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.1em;
  backdrop-filter: blur(8px);
}

.badge-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #fff;
  animation: pulse-dot 2s ease-in-out infinite;
}

@keyframes pulse-dot {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.3; }
}

.badge-text {
  color: #fff;
}

.activity-info {
  min-width: 0;
}

.activity-name {
  margin: 0;
  font-size: 22px;
  font-weight: 600;
  letter-spacing: -0.01em;
  color: rgba(255, 255, 255, 0.95);
  line-height: 1.3;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.activity-venue {
  margin: 4px 0 0;
  font-size: 13px;
  color: rgba(255, 255, 255, 0.55);
  font-weight: 400;
}

/* ── Bottom Bar ──────────────────────────────────────── */
.bottom-bar {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  z-index: 10;
  background: linear-gradient(to top, rgba(0, 0, 0, 0.6) 0%, transparent 100%);
}

.bottom-bar-inner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 40px 40px 20px;
}

.now-playing {
  min-width: 0;
}

.now-playing-label {
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: rgba(255, 255, 255, 0.45);
  margin-bottom: 6px;
}

.now-playing-title {
  display: flex;
  align-items: baseline;
  gap: 12px;
}

.seq-num {
  font-size: 28px;
  font-weight: 700;
  color: rgba(167, 139, 250, 0.9);
  font-variant-numeric: tabular-nums;
  letter-spacing: -0.02em;
  line-height: 1;
}

.prog-name {
  font-size: 20px;
  font-weight: 500;
  color: rgba(255, 255, 255, 0.9);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.playback-stats {
  display: flex;
  align-items: center;
  gap: 20px;
}

.stat {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
}

.stat-value {
  font-size: 20px;
  font-weight: 700;
  color: rgba(255, 255, 255, 0.9);
  font-variant-numeric: tabular-nums;
}

.stat-label {
  font-size: 11px;
  color: rgba(255, 255, 255, 0.4);
  font-weight: 500;
  letter-spacing: 0.04em;
}

.stat-divider {
  width: 1px;
  height: 28px;
  background: rgba(255, 255, 255, 0.15);
}

/* ── Progress Bar ────────────────────────────────────── */
.progress-track {
  height: 3px;
  background: rgba(255, 255, 255, 0.1);
  position: relative;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #818cf8 0%, #a78bfa 50%, #c084fc 100%);
  border-radius: 0 2px 2px 0;
  transition: width 0.3s linear;
}

/* ── Slide transitions ───────────────────────────────── */
.slide-down-enter-active,
.slide-down-leave-active {
  transition: transform 0.5s cubic-bezier(0.4, 0, 0.2, 1), opacity 0.5s ease;
}

.slide-down-enter-from,
.slide-down-leave-to {
  transform: translateY(-100%);
  opacity: 0;
}

.slide-up-enter-active,
.slide-up-leave-active {
  transition: transform 0.5s cubic-bezier(0.4, 0, 0.2, 1), opacity 0.5s ease;
}

.slide-up-enter-from,
.slide-up-leave-to {
  transform: translateY(100%);
  opacity: 0;
}

/* ── Mute Toggle ─────────────────────────────────────── */
.mute-toggle {
  position: absolute;
  bottom: 100px;
  right: 40px;
  z-index: 15;
  width: 48px;
  height: 48px;
  border: none;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.12);
  backdrop-filter: blur(12px);
  color: rgba(255, 255, 255, 0.85);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.25s ease, transform 0.2s ease;
  padding: 0;
}

.mute-toggle:hover {
  background: rgba(255, 255, 255, 0.22);
  transform: scale(1.08);
}

.mute-toggle:active {
  transform: scale(0.95);
}

.mute-toggle svg {
  width: 22px;
  height: 22px;
}

/* ── Fade transition ─────────────────────────────────── */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.5s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

/* ── Idle Screen ─────────────────────────────────────── */
.idle-screen {
  position: absolute;
  inset: 0;
  z-index: 5;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(10, 10, 15, 0.85);
  backdrop-filter: blur(40px);
}

.idle-content {
  text-align: center;
  animation: fadeInUp 1s cubic-bezier(0.4, 0, 0.2, 1);
}

@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.idle-icon {
  margin: 0 auto 24px;
  width: 64px;
  height: 64px;
  color: rgba(167, 139, 250, 0.7);
}

.idle-title {
  margin: 0 0 8px;
  font-size: 28px;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.9);
  letter-spacing: -0.01em;
}

.idle-subtitle {
  margin: 0;
  font-size: 15px;
  color: rgba(255, 255, 255, 0.4);
  font-weight: 400;
}

.idle-spinner {
  display: flex;
  justify-content: center;
  gap: 8px;
  margin-top: 32px;
}

.spinner-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: rgba(167, 139, 250, 0.6);
  animation: spinPulse 1.4s ease-in-out infinite;
}

.spinner-dot:nth-child(2) {
  animation-delay: 0.2s;
}

.spinner-dot:nth-child(3) {
  animation-delay: 0.4s;
}

@keyframes spinPulse {
  0%, 80%, 100% {
    opacity: 0.3;
    transform: scale(0.8);
  }
  40% {
    opacity: 1;
    transform: scale(1.2);
  }
}

/* ── New Video Toast ─────────────────────────────────── */
.new-video-toast {
  position: absolute;
  top: 100px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 20;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 24px;
  background: rgba(99, 102, 241, 0.85);
  border: 1px solid rgba(129, 140, 248, 0.5);
  border-radius: 12px;
  backdrop-filter: blur(16px);
  font-size: 14px;
  font-weight: 500;
  color: #fff;
  box-shadow: 0 8px 32px rgba(99, 102, 241, 0.3);
}

.toast-icon {
  font-size: 16px;
  animation: sparkle 1.5s ease-in-out infinite;
}

@keyframes sparkle {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.6; transform: scale(1.2); }
}

.toast-slide-enter-active,
.toast-slide-leave-active {
  transition: transform 0.5s cubic-bezier(0.4, 0, 0.2, 1), opacity 0.5s ease;
}

.toast-slide-enter-from,
.toast-slide-leave-to {
  transform: translateX(-50%) translateY(-30px);
  opacity: 0;
}

/* ── Responsive ──────────────────────────────────────── */
@media (max-width: 768px) {
  .top-bar {
    padding: 16px 20px 24px;
  }

  .bottom-bar-inner {
    padding: 24px 20px 14px;
  }

  .activity-name {
    font-size: 17px;
  }

  .seq-num {
    font-size: 22px;
  }

  .prog-name {
    font-size: 16px;
  }

  .idle-title {
    font-size: 22px;
  }

  .mute-toggle {
    bottom: 80px;
    right: 20px;
    width: 42px;
    height: 42px;
  }

  .mute-toggle svg {
    width: 18px;
    height: 18px;
  }
}
</style>
