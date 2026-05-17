<template>
  <div class="activity-print-settings">
    <div class="panel-toolbar">
      <div>
        <h3>打印设置</h3>
        <p>配置当前活动的打印额度、价格和派发方式。打印图片由前端或本地打印客户端合成。</p>
      </div>
      <a-space>
        <a-button @click="loadData" :loading="loading">重载</a-button>
        <a-button type="primary" @click="saveData" :loading="saving">
          <template #icon><SaveOutlined /></template>
          保存
        </a-button>
      </a-space>
    </div>

    <a-spin :spinning="loading">
      <div class="settings-grid">
        <section class="settings-card">
          <div class="card-title">额度与价格</div>
          <div class="setting-row">
            <div>
              <strong>免费打印额度</strong>
              <span>每个微信用户在当前活动下可免费打印的张数。</span>
            </div>
            <a-input-number v-model:value="form.print_free_quota" :min="0" :max="100" style="width: 130px" />
          </div>
          <div class="setting-row">
            <div>
              <strong>超额打印价格</strong>
              <span>用户超过免费额度后，每张照片的打印价格。</span>
            </div>
            <a-input-number
              v-model:value="form.print_price"
              :min="0"
              :max="10000"
              :precision="2"
              :step="0.1"
              addon-after="元"
              style="width: 150px"
            />
          </div>
        </section>

        <section class="settings-card">
          <div class="card-title">打印派发</div>
          <div class="setting-row">
            <div>
              <strong>派发方式</strong>
              <span>选择订单提交到蓝阔云打印，或由本地 Windows 打印客户端领取处理。</span>
            </div>
            <a-select v-model:value="form.print_dispatch_mode" style="width: 180px">
              <a-select-option value="lankuo">蓝阔云打印</a-select-option>
              <a-select-option value="local_client">本地打印客户端</a-select-option>
              <a-select-option value="disabled">暂停派发</a-select-option>
            </a-select>
          </div>
          <div class="setting-row">
            <div>
              <strong>图片合成</strong>
              <span>服务端不再使用浏览器内核合成打印图片，避免大体积运行依赖。</span>
            </div>
            <a-tag color="green">前端/本地客户端合成</a-tag>
          </div>
        </section>
      </div>
    </a-spin>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { SaveOutlined } from '@ant-design/icons-vue'
import { message } from 'ant-design-vue'
import { activityPrintSettingsApi } from '@/api/admin'

const props = defineProps<{
  activityId: number
}>()

const loading = ref(false)
const saving = ref(false)

const form = reactive({
  print_free_quota: 2,
  print_price: 1,
  print_dispatch_mode: 'lankuo' as 'lankuo' | 'local_client' | 'disabled',
})

async function loadData() {
  loading.value = true
  try {
    const settings = (await activityPrintSettingsApi.get(props.activityId) as any)?.data || {}
    form.print_free_quota = settings.print_free_quota ?? 2
    form.print_price = (settings.print_price ?? 100) / 100
    form.print_dispatch_mode = settings.print_dispatch_mode || 'lankuo'
  } catch (error: any) {
    message.error(error?.response?.data?.detail || '加载打印设置失败')
  } finally {
    loading.value = false
  }
}

async function saveData() {
  saving.value = true
  try {
    await activityPrintSettingsApi.update(props.activityId, {
      print_free_quota: form.print_free_quota,
      print_price: Math.round(form.print_price * 100),
      print_dispatch_mode: form.print_dispatch_mode,
    })
    message.success('打印设置已保存')
  } catch (error: any) {
    message.error(error?.response?.data?.detail || '保存打印设置失败')
  } finally {
    saving.value = false
  }
}

onMounted(loadData)
</script>

<style scoped>
.activity-print-settings {
  background: #f7f8fb;
  border: 1px solid #edf0f5;
  border-radius: 8px;
  padding: 18px;
}

.panel-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 16px;
}

.panel-toolbar h3 {
  margin: 0;
  font-size: 16px;
}

.panel-toolbar p {
  margin: 4px 0 0;
  color: #8c8c8c;
  font-size: 13px;
}

.settings-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}

.settings-card {
  background: #fff;
  border: 1px solid #edf0f5;
  border-radius: 8px;
  padding: 16px;
}

.card-title {
  margin-bottom: 12px;
  font-size: 15px;
  font-weight: 700;
  color: #1f2937;
}

.setting-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  padding: 12px 0;
  border-top: 1px solid #f3f4f6;
}

.setting-row:first-of-type {
  border-top: 0;
}

.setting-row strong,
.setting-row span {
  display: block;
}

.setting-row strong {
  color: #1f2937;
  font-size: 14px;
}

.setting-row span {
  margin-top: 3px;
  color: #8c8c8c;
  font-size: 12px;
}

@media (max-width: 900px) {
  .settings-grid {
    grid-template-columns: 1fr;
  }

  .setting-row,
  .panel-toolbar {
    align-items: flex-start;
    flex-direction: column;
  }
}
</style>
