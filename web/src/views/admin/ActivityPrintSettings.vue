<template>
  <div class="activity-print-settings">
    <div class="panel-toolbar">
      <div>
        <h3>打印设置</h3>
        <p>配置当前打印流程的额度、价格与图片合成位置。纸张尺寸由「打印模版」中选中的模版决定。</p>
      </div>
      <a-space>
        <a-button @click="loadData" :loading="loading">重置</a-button>
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
              <span>每个微信用户在每个活动下可享受的免费打印张数。</span>
            </div>
            <a-input-number v-model:value="form.print_free_quota" :min="0" :max="100" style="width: 130px" />
          </div>
          <div class="setting-row">
            <div>
              <strong>超额打印价格</strong>
              <span>用户超出免费额度后，每张照片的打印价格。</span>
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
          <div class="card-title">图片合成位置</div>
          <div class="setting-row">
            <div>
              <strong>服务端合成打印图片</strong>
              <span>开启后，服务端用 Fabric/Playwright 合成图片并继续走云打印派发。</span>
            </div>
            <a-switch
              v-model:checked="form.server_render_enabled"
              checked-children="服务端"
              un-checked-children="本地"
            />
          </div>
          <div class="setting-row">
            <div>
              <strong>本地电脑合成打印图片</strong>
              <span>关闭上方开关后，订单保持排队状态，由 supertech-PhotoPrinter 本地领取、合成并打印。</span>
            </div>
            <a-tag :color="form.server_render_enabled ? 'default' : 'green'">
              {{ form.server_render_enabled ? '未启用' : 'print_dispatch_mode=local_client' }}
            </a-tag>
          </div>
          <div class="setting-row">
            <div>
              <strong>服务端合成图倍率</strong>
              <span>仅服务端合成模式使用；本地电脑合成固定使用最终打印像素与 PNG 母版。</span>
            </div>
            <a-segmented
              v-model:value="form.print_render_multiplier"
              :options="renderMultiplierOptions"
              :disabled="!form.server_render_enabled"
            />
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
  server_render_enabled: true,
  print_render_multiplier: 1 as 1 | 2 | 3,
})

const renderMultiplierOptions = [
  { label: '1倍', value: 1 },
  { label: '2倍', value: 2 },
  { label: '3倍', value: 3 },
]

async function loadData() {
  loading.value = true
  try {
    const settings = (await activityPrintSettingsApi.get(props.activityId) as any)?.data || {}
    form.print_free_quota = settings.print_free_quota ?? 2
    form.print_price = (settings.print_price ?? 100) / 100
    form.server_render_enabled = (settings.print_dispatch_mode || 'lankuo') !== 'local_client'
    form.print_render_multiplier = ([1, 2, 3].includes(settings.print_render_multiplier)
      ? settings.print_render_multiplier
      : 1) as 1 | 2 | 3
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
      print_dispatch_mode: form.server_render_enabled ? 'lankuo' : 'local_client',
      print_render_mode: form.server_render_enabled ? 'server' : 'frontend',
      print_render_multiplier: form.print_render_multiplier,
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
