<template>
  <div>
    <div class="page-header">
      <a-button @click="$router.push('/admin')">
        <template #icon><ArrowLeftOutlined /></template>
        返回
      </a-button>
      <h2>{{ activity?.name || '节目管理' }}</h2>
      <a-space>
        <a-dropdown>
          <a-button>
            <template #icon><PlusOutlined /></template>
            添加节目
            <DownOutlined />
          </a-button>
          <template #overlay>
            <a-menu @click="handleAddMenuClick">
              <a-menu-item key="single">手动添加</a-menu-item>
              <a-menu-item key="excel">Excel导入</a-menu-item>
            </a-menu>
          </template>
        </a-dropdown>
      </a-space>
    </div>

    <a-spin :spinning="loading">
      <a-alert
        v-if="programs.length === 0 && !loading"
        message="暂无节目，请通过上方按钮添加节目"
        type="info"
        show-icon
        style="margin-bottom: 16px"
      />

      <a-table
        :columns="editableColumns"
        :data-source="tableData"
        :pagination="false"
        row-key="id"
        size="middle"
        :row-class-name="(record: any) => record._isNew ? 'new-row' : ''"
      >
        <template #bodyCell="{ column, record, index }">
          <template v-if="column.dataIndex === 'sequence_number'">
            <a-input-number
              v-if="record._isNew || editableData[record.id]"
              :value="record._isNew ? record.sequence_number : editableData[record.id]?.sequence_number"
              @change="(val: number) => record._isNew ? (record.sequence_number = val) : (editableData[record.id].sequence_number = val)"
              :min="1"
              size="small"
              style="width: 70px"
            />
            <span v-else style="font-weight: 500">{{ record.sequence_number }}</span>
          </template>

          <template v-if="column.dataIndex === 'name'">
            <a-input
              v-if="record._isNew || editableData[record.id]"
              :value="record._isNew ? record.name : editableData[record.id]?.name"
              @change="(e: any) => record._isNew ? (record.name = e.target.value) : (editableData[record.id].name = e.target.value)"
              size="small"
              placeholder="节目名称"
            />
            <span v-else>{{ record.name }}</span>
          </template>

          <template v-if="column.dataIndex === 'time_range'">
            <a-date-picker
              v-if="editableData[record.id]"
              :value="editableData[record.id].start_time ? dayjs(editableData[record.id].start_time) : null"
              :show-time="{ format: 'HH:mm:ss' }"
              format="YYYY-MM-DD HH:mm:ss"
              placeholder="选择录制时间"
              size="small"
              style="width: 210px"
              @change="(val: any) => { editableData[record.id].start_time = val ? val.toDate() : null }"
            />
            <span v-else-if="record.start_time">
              {{ formatTime(record.start_time) }}
            </span>
            <span v-else style="color: #bfbfbf">未设定</span>
          </template>

          <template v-if="column.dataIndex === 'duration'">
            <span v-if="record.duration">{{ formatDuration(record.duration) }}</span>
            <span v-else style="color: #bfbfbf">--</span>
          </template>

          <template v-if="column.dataIndex === 'ready_mode'">
            <a-select
              v-if="editableData[record.id]"
              v-model:value="editableData[record.id].ready_mode"
              size="small"
              style="width: 100px"
            >
              <a-select-option value="auto">自动</a-select-option>
              <a-select-option value="manual">手动</a-select-option>
            </a-select>
            <a-tag v-else :color="record.ready_mode === 'auto' ? 'blue' : 'orange'" size="small">
              {{ record.ready_mode === 'auto' ? '自动' : '手动' }}
            </a-tag>
          </template>

          <template v-if="column.dataIndex === 'video_status'">
            <template v-if="record.video_status === 'ready' && record.video_thumbnail_url && !failedThumbnails[record.id]">
              <a-tooltip title="点击预览节目">
                <div class="video-thumb" @click="handlePreviewVideo(record)">
                  <img :src="record.video_thumbnail_url" class="video-thumb-img" @error="failedThumbnails[record.id] = true" />
                  <div class="video-thumb-play"><PlayCircleOutlined /></div>
                </div>
              </a-tooltip>
              <a-popconfirm v-if="editableData[record.id]" title="确定删除此视频？视频将移至临时文件夹" @confirm="handleDeleteVideo(record.id)" placement="top">
                <a-tooltip title="删除视频">
                  <a-button type="text" size="small" danger class="video-delete-btn">
                    <template #icon><DeleteOutlined /></template>
                  </a-button>
                </a-tooltip>
              </a-popconfirm>
            </template>
            <template v-else-if="record.video_status === 'uploading'">
              <a-progress :percent="uploadProgress[record.id] || 0" size="small" :stroke-width="4" style="width: 80px" />
            </template>
            <template v-else-if="record.video_status === 'ready' && record.video_url">
              <div style="display: flex; align-items: center; justify-content: center; gap: 4px">
                <a-tooltip title="点击预览节目">
                  <div class="video-thumb" @click="handlePreviewVideo(record)">
                    <PlayCircleOutlined class="video-thumb-icon" />
                  </div>
                </a-tooltip>
                <a-popconfirm v-if="editableData[record.id]" title="确定删除此视频？视频将移至临时文件夹" @confirm="handleDeleteVideo(record.id)" placement="top">
                  <a-tooltip title="删除视频">
                    <a-button type="text" size="small" danger class="video-delete-btn">
                      <template #icon><DeleteOutlined /></template>
                    </a-button>
                  </a-tooltip>
                </a-popconfirm>
              </div>
            </template>
            <a-tag v-else :color="videoStatusColor(record.video_status)">
              {{ videoStatusText(record.video_status) }}
            </a-tag>
          </template>

          <template v-if="column.dataIndex === 'photo_count'">
            <span style="font-size: 13px">{{ record.photo_count ?? 0 }}</span>
          </template>

          <template v-if="column.dataIndex === 'ready_status'">
            <a-switch
              :checked="record.ready_status === 'ready'"
              @change="(checked: boolean) => handleToggleReady(record, checked)"
              :disabled="record.ready_mode === 'auto'"
            />
            <span v-if="record.ready_mode === 'auto'" style="margin-left: 8px; font-size: 12px; color: #8c8c8c">自动</span>
          </template>

          <template v-if="column.key === 'actions'">
            <template v-if="record._isNew">
              <a-space>
                <a-button type="link" size="small" @click="handleSaveNew(record)" style="color: #52c41a">
                  保存
                </a-button>
                <a-button type="link" size="small" @click="handleCancelNew(record.id)">
                  取消
                </a-button>
              </a-space>
            </template>
            <template v-else-if="editableData[record.id]">
              <a-space>
                <a-button type="link" size="small" @click="handleSaveInline(record)" style="color: #52c41a">
                  保存
                </a-button>
                <a-button type="link" size="small" @click="handleCancelInline(record.id)">
                  取消
                </a-button>
              </a-space>
            </template>
            <template v-else>
              <a-space>
                <a-button type="link" size="small" @click="handleEditInline(record)">编辑</a-button>
                <a-button v-if="record.video_status !== 'ready'" type="link" size="small" @click="handleUploadVideo(record)">上传视频</a-button>
                <a-popconfirm title="确定删除此节目？" @confirm="handleDelete(record.id)">
                  <a-button type="link" size="small" danger>删除</a-button>
                </a-popconfirm>
              </a-space>
            </template>
          </template>
        </template>
      </a-table>
    </a-spin>

    <!-- Excel导入 Modal -->
    <a-modal
      v-model:open="showExcelModal"
      title="Excel导入节目"
      :footer="null"
      @cancel="resetExcelForm"
    >
      <div class="excel-import">
        <a-alert
          message="Excel格式要求"
          type="info"
          show-icon
          style="margin-bottom: 16px"
        >
          <template #description>
            <div>第一行为表头，支持以下列名（不区分大小写）：</div>
            <a-table
              :columns="excelHintColumns"
              :data-source="excelHintData"
              :pagination="false"
              size="small"
              bordered
              style="margin-top: 8px"
            />
          </template>
        </a-alert>

        <a-upload-dragger
          :before-upload="handleExcelUpload"
          :show-upload-list="false"
          accept=".xlsx,.xls"
        >
          <p class="ant-upload-drag-icon"><InboxOutlined /></p>
          <p class="ant-upload-text">点击或拖拽Excel文件到此处</p>
          <p class="ant-upload-hint">支持 .xlsx / .xls 格式</p>
        </a-upload-dragger>

        <div v-if="excelResult" style="margin-top: 16px">
          <a-alert
            :message="`成功导入 ${excelResult.success} 个节目`"
            :type="excelResult.failed > 0 ? 'warning' : 'success'"
            show-icon
          />
        </div>
      </div>
    </a-modal>

    <!-- 隐藏的文件选择器（视频上传） -->
    <input ref="fileInputRef" type="file" accept="video/*" style="display: none" @change="handleFileSelected" />
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowLeftOutlined, PlusOutlined, DownOutlined, InboxOutlined, PlayCircleOutlined, DeleteOutlined } from '@ant-design/icons-vue'
import { message } from 'ant-design-vue'
import { adminApi, uploadApi, type Activity, type Program } from '@/api/admin'
import dayjs from 'dayjs'

const route = useRoute()
const router = useRouter()
const activityId = computed(() => Number(route.params.id))
const activity = ref<Activity | null>(null)
const programs = ref<Program[]>([])
const loading = ref(false)
const saving = ref(false)
const showExcelModal = ref(false)
const fileInputRef = ref<HTMLInputElement | null>(null)
const uploadingProgramId = ref<number | null>(null)
const uploadProgress = ref<Record<number, number>>({})
const failedThumbnails = reactive<Record<number, boolean>>({})

// 行内编辑
const editableData = ref<Record<number, any>>({})
let newIdCounter = -1

// 新增行列表
const newRows = ref<any[]>([])

const tableData = computed(() => {
  return [...newRows.value, ...programs.value]
})

// Excel导入结果
const excelResult = ref<{ success: number; failed: number } | null>(null)

const excelHintColumns = [
  { title: '列名', dataIndex: 'column', width: 120 },
  { title: '说明', dataIndex: 'desc' },
  { title: '必填', dataIndex: 'required', width: 60 },
]
const excelHintData = [
  { key: '1', column: '节目名称', desc: '节目名称（支持：节目名称、名称、name、节目）', required: '是' },
  { key: '2', column: '序号', desc: '演出顺序号（支持：序号、编号、sequence）', required: '否' },
  { key: '3', column: '开始时间', desc: '录制开始时间（支持：开始时间、录制开始、start_time）', required: '否' },
  { key: '4', column: '结束时间', desc: '录制结束时间（支持：结束时间、录制结束、end_time）', required: '否' },
  { key: '5', column: '就绪模式', desc: '自动/手动（支持：就绪模式、ready_mode）', required: '否' },
]

const editableColumns = [
  { title: '序号', dataIndex: 'sequence_number', key: 'sequence_number', align: 'center' as const },
  { title: '节目名称', dataIndex: 'name', key: 'name', align: 'center' as const },
  { title: '录制时间', dataIndex: 'time_range', key: 'time_range', align: 'center' as const },
  { title: '时长', dataIndex: 'duration', key: 'duration', align: 'center' as const },
  { title: '就绪模式', dataIndex: 'ready_mode', key: 'ready_mode', align: 'center' as const },
  { title: '视频', dataIndex: 'video_status', key: 'video_status', align: 'center' as const },
  { title: '照片', dataIndex: 'photo_count', key: 'photo_count', align: 'center' as const },
  { title: '就绪', dataIndex: 'ready_status', key: 'ready_status', align: 'center' as const },
  { title: '操作', key: 'actions', align: 'center' as const },
]

const formatTime = (t: string) => dayjs(t).format('YYYY-MM-DD HH:mm:ss')
const formatDuration = (seconds: number) => {
  const m = Math.floor(seconds / 60)
  const s = Math.round(seconds % 60)
  return `${m}:${String(s).padStart(2, '0')}`
}
const videoStatusColor = (s: string) => ({ none: 'default', uploading: 'processing', ready: 'success' }[s] || 'default')
const videoStatusText = (s: string) => ({ none: '未上传', uploading: '上传中', ready: '已就绪' }[s] || s)

const fetchData = async () => {
  loading.value = true
  try {
    const [actRes, progRes] = await Promise.all([
      adminApi.getActivity(activityId.value),
      adminApi.listPrograms(activityId.value),
    ])
    activity.value = actRes.data
    programs.value = progRes.data
    Object.keys(failedThumbnails).forEach(k => delete failedThumbnails[Number(k)])
  } catch {
    message.error('加载数据失败')
  } finally {
    loading.value = false
  }
}

// 行内编辑
const handleEditInline = (record: Program) => {
  editableData.value[record.id] = {
    name: record.name,
    sequence_number: record.sequence_number,
    ready_mode: record.ready_mode,
    start_time: record.start_time ? new Date(record.start_time) : null,
  }
}

const handleCancelInline = (id: number) => {
  delete editableData.value[id]
}

const handleSaveInline = async (record: Program) => {
  const data = editableData.value[record.id]
  if (!data || !data.name?.trim()) {
    message.warning('节目名称不能为空')
    return
  }
  if (!data.sequence_number || data.sequence_number < 1) {
    message.warning('节目序号不能为空')
    return
  }
  try {
    const payload: any = {
      name: data.name,
      sequence_number: data.sequence_number,
      ready_mode: data.ready_mode,
    }
    if (data.start_time !== undefined && data.start_time !== null) {
      payload.start_time = dayjs(data.start_time).format('YYYY-MM-DDTHH:mm:ss')
    } else if (data.start_time === null) {
      payload.start_time = null
    }
    await adminApi.updateProgram(record.id, payload)
    delete editableData.value[record.id]
    message.success('保存成功')
    fetchData()
  } catch {
    message.error('保存失败')
  }
}

// 添加菜单
const handleAddMenuClick = ({ key }: { key: string }) => {
  if (key === 'single') {
    addNewRow()
  } else if (key === 'excel') {
    showExcelModal.value = true
    excelResult.value = null
  }
}

// 行内新增
const addNewRow = () => {
  const newId = newIdCounter--
  newRows.value.push({
    id: newId,
    _isNew: true,
    sequence_number: programs.value.length + newRows.value.length + 1,
    name: '',
    ready_mode: 'auto',
    start_time: null,
    end_time: null,
    video_status: 'none',
    photo_count: 0,
    ready_status: 'pending',
  })
}

const handleSaveNew = async (record: any) => {
  if (!record.name?.trim()) {
    message.warning('请输入节目名称')
    return
  }
  if (!record.sequence_number || record.sequence_number < 1) {
    message.warning('请输入节目序号')
    return
  }
  saving.value = true
  try {
    await adminApi.createProgram(activityId.value, {
      name: record.name,
      sequence_number: record.sequence_number,
      ready_mode: record.ready_mode,
    })
    newRows.value = newRows.value.filter(r => r.id !== record.id)
    message.success('添加成功')
    fetchData()
  } catch {
    message.error('添加失败')
  } finally {
    saving.value = false
  }
}

const handleCancelNew = (id: number) => {
  newRows.value = newRows.value.filter(r => r.id !== id)
}

// Excel导入
const handleExcelUpload = async (file: File) => {
  try {
    const res = await uploadApi.importProgramsExcel(activityId.value, file)
    const imported = res.data
    excelResult.value = { success: imported.length, failed: 0 }
    message.success(`成功导入 ${imported.length} 个节目`)
    fetchData()
  } catch (e: any) {
    const detail = e.response?.data?.detail || '导入失败'
    message.error(detail)
    excelResult.value = { success: 0, failed: 1 }
  }
  return false // 阻止默认上传
}

const resetExcelForm = () => {
  excelResult.value = null
}

// 视频上传
const handleUploadVideo = (record: Program) => {
  uploadingProgramId.value = record.id
  fileInputRef.value?.click()
}

const handlePreviewVideo = (record: Program) => {
  window.open(`/p/${record.access_token}`, '_blank')
}

const handleDeleteVideo = async (programId: number) => {
  try {
    await uploadApi.deleteVideo(programId)
    delete editableData.value[programId]
    message.success('视频已删除')
    fetchData()
  } catch {
    message.error('删除视频失败')
  }
}

const handleFileSelected = async (e: Event) => {
  const file = (e.target as HTMLInputElement).files?.[0]
  if (!file || !uploadingProgramId.value) return

  const programId = uploadingProgramId.value
  const uploadKey = `upload-${programId}`

  try {
    // 1. Get upload token from server
    message.loading({ content: '正在获取上传凭证...', key: uploadKey, duration: 0 })
    const tokenRes = await uploadApi.getVideoUploadToken(programId, file.name)
    const { token, key, upload_url } = tokenRes.data

    // 2. Update local state to show uploading progress
    const progIndex = programs.value.findIndex(p => p.id === programId)
    if (progIndex !== -1) {
      programs.value[progIndex].video_status = 'uploading'
    }
    uploadProgress.value[programId] = 0

    // 3. Direct upload to Qiniu using XMLHttpRequest for progress tracking
    await new Promise<void>((resolve, reject) => {
      const xhr = new XMLHttpRequest()
      const formData = new FormData()
      formData.append('token', token)
      formData.append('key', key)
      formData.append('file', file)

      xhr.upload.addEventListener('progress', (e) => {
        if (e.lengthComputable) {
          const percent = Math.round((e.loaded / e.total) * 100)
          uploadProgress.value[programId] = percent
          message.loading({ content: `正在上传视频... ${percent}%`, key: uploadKey, duration: 0 })
        }
      })

      xhr.addEventListener('load', () => {
        if (xhr.status >= 200 && xhr.status < 300) {
          resolve()
        } else {
          reject(new Error(`Qiniu upload failed: ${xhr.status}`))
        }
      })

      xhr.addEventListener('error', () => reject(new Error('Network error during upload')))
      xhr.addEventListener('timeout', () => reject(new Error('Upload timed out')))

      xhr.open('POST', upload_url)
      xhr.timeout = 600000 // 10 minutes
      xhr.send(formData)
    })

    // 4. Confirm upload with server
    message.loading({ content: '正在确认上传...', key: uploadKey, duration: 0 })
    await uploadApi.confirmVideoUpload(programId, key, file.name, file.size)

    delete uploadProgress.value[programId]
    message.success({ content: '视频上传成功', key: uploadKey })
    fetchData()
  } catch (err: any) {
    delete uploadProgress.value[programId]
    const detail = err.response?.data?.detail || err.message || '视频上传失败'
    message.error({ content: detail, key: uploadKey })
  } finally {
    if (fileInputRef.value) fileInputRef.value.value = ''
    uploadingProgramId.value = null
  }
}

const handleToggleReady = async (record: Program, checked: boolean) => {
  try {
    await adminApi.updateProgram(record.id, { ready_status: checked ? 'ready' : 'pending' })
    record.ready_status = checked ? 'ready' : 'pending'
    message.success(checked ? '已标记为就绪' : '已取消就绪')
  } catch {
    message.error('操作失败')
  }
}

const handleDelete = async (id: number) => {
  try {
    await adminApi.deleteProgram(id)
    message.success('删除成功')
    fetchData()
  } catch {
    message.error('删除失败')
  }
}

onMounted(fetchData)
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

.excel-import {
  padding: 8px 0;
}

:deep(.new-row) {
  background-color: #f6ffed;
}

:deep(.new-row:hover > td) {
  background-color: #e6fffb !important;
}

.video-thumb {
  width: 80px;
  height: 45px;
  border-radius: 4px;
  overflow: hidden;
  position: relative;
  cursor: pointer;
  background: #f0f0f0;
}

.video-thumb-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.video-thumb-play {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0);
  transition: background 0.2s;
}

.video-thumb-play :deep(.anticon) {
  font-size: 20px;
  color: #fff;
  opacity: 0;
  transition: opacity 0.2s;
  filter: drop-shadow(0 1px 3px rgba(0, 0, 0, 0.5));
}

.video-thumb:hover .video-thumb-play {
  background: rgba(0, 0, 0, 0.3);
}

.video-thumb:hover .video-thumb-play :deep(.anticon) {
  opacity: 1;
}

.video-thumb:hover {
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
}

.video-thumb-icon {
  font-size: 22px;
  color: #1890ff;
}

.video-delete-btn {
  font-size: 14px;
}

::deep(.ant-table) .ant-table-cell {
  text-align: center;
}
</style>
