<template>
  <div>
    <div class="page-header">
      <a-button @click="$router.push('/admin')">
        <template #icon><ArrowLeftOutlined /></template>
        返回
      </a-button>
      <h2>{{ activity?.name || '节目管理' }}</h2>
      <a-space v-if="activeWorkspaceTab === 'programs'">
        <a-dropdown>
          <a-button>
            <template #icon><PlusOutlined /></template>
            添加节目
            <DownOutlined />
          </a-button>
          <template #overlay>
            <a-menu @click="handleAddMenuClick">
              <a-menu-item key="single">手动添加</a-menu-item>
              <a-menu-item key="excel">Excel 导入</a-menu-item>
            </a-menu>
          </template>
        </a-dropdown>
      </a-space>
    </div>

    <a-tabs v-model:activeKey="activeWorkspaceTab" class="workspace-tabs" @change="handleWorkspaceChange">
      <template #rightExtra>
        <div v-if="activeWorkspaceTab === 'programs'" class="program-tab-search">
          <a-input-search
            v-model:value="programSearchKeyword"
            allow-clear
            placeholder="搜索节目号或节目名"
            style="max-width: 320px"
          />
        </div>
      </template>

      <a-tab-pane key="programs" tab="节目管理">
        <a-spin :spinning="loading">
          <a-alert
            v-if="programs.length === 0 && !loading"
            message="暂无节目，请通过上方按钮添加节目"
            type="info"
            show-icon
            style="margin-bottom: 16px"
          />
          <a-alert
            v-else-if="filteredPrograms.length === 0 && newRows.length === 0 && !loading"
            message="未找到匹配的节目"
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
            <template #bodyCell="{ column, record }">
              <template v-if="column.dataIndex === 'sequence_number'">
                <a-input-number
                  v-if="record._isNew || editableData[record.id]"
                  :value="record._isNew ? record.sequence_number : editableData[record.id]?.sequence_number"
                  @change="(val: number) => record._isNew ? (record.sequence_number = val) : (editableData[record.id].sequence_number = val)"
                  :min="1"
                  size="small"
                  style="width: 76px"
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
                <span v-else-if="record.start_time">{{ formatTime(record.start_time) }}</span>
                <span v-else style="color: #bfbfbf">未设置</span>
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
                <a-tag v-else :color="record.ready_mode === 'auto' ? 'blue' : 'orange'">
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
                  <div class="video-ready-cell">
                    <a-tooltip title="点击预览节目">
                      <div class="video-thumb video-thumb-fallback" @click="handlePreviewVideo(record)">
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
                <span v-if="record.ready_mode === 'auto'" class="muted-inline">自动</span>
              </template>

              <template v-if="column.key === 'actions'">
                <template v-if="record._isNew">
                  <a-space>
                    <a-button type="link" size="small" @click="handleSaveNew(record)" style="color: #52c41a">保存</a-button>
                    <a-button type="link" size="small" @click="handleCancelNew(record.id)">取消</a-button>
                  </a-space>
                </template>
                <template v-else-if="editableData[record.id]">
                  <a-space>
                    <a-button type="link" size="small" @click="handleSaveInline(record)" style="color: #52c41a">保存</a-button>
                    <a-button type="link" size="small" @click="handleCancelInline(record.id)">取消</a-button>
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
      </a-tab-pane>

      <a-tab-pane key="photo-sync" tab="照片同步">
        <ActivityPhotoSync
          v-if="activity"
          :activity-id="activityId"
          :activity="activity"
        />
      </a-tab-pane>

      <a-tab-pane key="photo-manager" tab="照片管理">
        <div class="activity-photo-panel">
          <div class="panel-toolbar">
            <div>
              <h3>已同步照片</h3>
              <p>展示当前活动下已同步入库的照片，可直接提交打印任务。</p>
            </div>
            <a-button @click="fetchActivityPhotos" :loading="activityPhotosLoading">
              <template #icon><ReloadOutlined /></template>
              刷新
            </a-button>
          </div>

          <a-spin :spinning="activityPhotosLoading">
            <div v-if="activityPhotos.length > 0" class="activity-photo-grid">
              <div v-for="photo in activityPhotos" :key="photo.id" class="activity-photo-card">
                <div class="activity-photo-thumb">
                  <img :src="getThumbUrl(photo.storage_url || photo.wotu_url || '')" :alt="photo.filename" loading="lazy" />
                  <a-button
                    type="primary"
                    shape="circle"
                    class="photo-print-button"
                    :loading="printingPhotoId === photo.id"
                    @click="handlePrintPhoto(photo)"
                  >
                    <template #icon><PrinterOutlined /></template>
                  </a-button>
                </div>
                <div class="activity-photo-meta">
                  <strong>{{ photo.filename || `照片 #${photo.id}` }}</strong>
                  <span>{{ formatNullableTime(photo.shoot_time) }}</span>
                </div>
              </div>
            </div>
            <a-empty v-else description="暂无已同步照片" style="padding: 42px 0" />
          </a-spin>

          <div class="photo-pagination" v-if="activityPhotoTotal > activityPhotoPageSize">
            <a-pagination
              v-model:current="activityPhotoPage"
              :page-size="activityPhotoPageSize"
              :total="activityPhotoTotal"
              show-less-items
              @change="fetchActivityPhotos"
            />
          </div>
        </div>
      </a-tab-pane>

      <a-tab-pane key="print-records" tab="打印记录">
        <div class="print-records-panel">
          <div class="panel-toolbar">
            <div>
              <h3>用户打印记录</h3>
              <p>记录家长提交的照片打印任务，管理员可对指定照片执行重打。</p>
            </div>
            <a-button @click="fetchPrintRecords" :loading="printRecordsLoading">
              <template #icon><ReloadOutlined /></template>
              刷新
            </a-button>
          </div>

          <a-table
            :columns="printRecordColumns"
            :data-source="printRecords"
            :loading="printRecordsLoading"
            :pagination="{
              current: printRecordPage,
              pageSize: printRecordPageSize,
              total: printRecordTotal,
              showSizeChanger: false,
              onChange: handlePrintRecordPageChange,
            }"
            row-key="id"
            size="middle"
          >
            <template #bodyCell="{ column, record }">
              <template v-if="column.key === 'photo'">
                <div class="print-photo-cell">
                  <img v-if="record.photo_url" :src="getThumbUrl(record.photo_url)" :alt="record.photo_filename || '照片'" />
                  <div v-else class="empty-thumb">无图</div>
                  <div>
                    <strong>{{ record.photo_filename || `照片 #${record.photo_id || '-'}` }}</strong>
                    <span>{{ record.program_sequence_number ? `节目号 ${record.program_sequence_number}` : '未关联节目' }}</span>
                  </div>
                </div>
              </template>
              <template v-if="column.key === 'user'">
                <div class="stack-text">
                  <strong>{{ record.user_name || '匿名用户' }}</strong>
                  <span>{{ record.user_identifier || '无用户标识' }}</span>
                </div>
              </template>
              <template v-if="column.key === 'job'">
                <div class="stack-text">
                  <strong>{{ record.template_name || '默认模版' }}</strong>
                  <span>{{ record.paper_size || '跟随模版' }} / {{ record.copies }} 份</span>
                </div>
              </template>
              <template v-if="column.key === 'status'">
                <a-tag :color="printStatusColor(record.status)">{{ printStatusText(record.status) }}</a-tag>
                <div v-if="record.error_msg" class="record-error">{{ record.error_msg }}</div>
              </template>
              <template v-if="column.key === 'created_at'">
                {{ formatNullableTime(record.created_at) }}
              </template>
              <template v-if="column.key === 'actions'">
                <a-button type="primary" size="small" @click="handleReprint(record)" :loading="reprintingId === record.id">
                  <template #icon><PrinterOutlined /></template>
                  重打
                </a-button>
              </template>
            </template>
          </a-table>
        </div>
      </a-tab-pane>

      <a-tab-pane key="print-template" tab="打印模版">
        <div class="print-template-panel">
          <a-alert
            type="info"
            show-icon
            message="此处纸张尺寸会覆盖系统设置中的打印机默认纸张尺寸"
            description="打印照片时优先读取当前活动的打印模版；若这里设置了纸张尺寸，将覆盖系统设置里蓝阔云打印配置的 dmPaperSize。"
            style="margin-bottom: 16px"
          />

          <div class="template-layout">
            <a-card title="打印规则" :bordered="false" class="template-card">
              <a-form layout="vertical">
                <a-row :gutter="16">
                  <a-col :xs="24" :md="12">
                    <a-form-item label="每用户可免费打印次数">
                      <a-input-number v-model:value="printTemplate.freePrintLimit" :min="0" :max="99" style="width: 100%" />
                    </a-form-item>
                  </a-col>
                  <a-col :xs="24" :md="12">
                    <a-form-item label="模版名称">
                      <a-input v-model:value="printTemplate.templateName" placeholder="例如：活动照片贴纸" />
                    </a-form-item>
                  </a-col>
                  <a-col :xs="24" :md="12">
                    <a-form-item label="纸张大小">
                      <a-select v-model:value="printTemplate.paperKey" :options="paperOptions" @change="applyPaperPreset" />
                    </a-form-item>
                  </a-col>
                  <a-col :xs="24" :md="12">
                    <a-form-item label="打印纸张参数 dmPaperSize">
                      <a-input v-model:value="printTemplate.dmPaperSize" placeholder="蓝阔任务参数，如 9 / 11 / 70 / 0" />
                    </a-form-item>
                  </a-col>
                  <a-col :xs="24" :md="12">
                    <a-form-item label="纸张宽度（mm）">
                      <a-input-number v-model:value="printTemplate.paperWidthMm" :min="1" style="width: 100%" />
                    </a-form-item>
                  </a-col>
                  <a-col :xs="24" :md="12">
                    <a-form-item label="纸张高度（mm）">
                      <a-input-number v-model:value="printTemplate.paperHeightMm" :min="1" style="width: 100%" />
                    </a-form-item>
                  </a-col>
                </a-row>
              </a-form>
            </a-card>

            <a-card title="视觉模版" :bordered="false" class="template-card">
              <a-form layout="vertical">
                <a-row :gutter="16">
                  <a-col :xs="24" :md="12">
                    <a-form-item label="照片适配">
                      <a-radio-group v-model:value="printTemplate.photoFit" button-style="solid">
                        <a-radio-button value="cover">铺满裁切</a-radio-button>
                        <a-radio-button value="contain">完整留白</a-radio-button>
                      </a-radio-group>
                    </a-form-item>
                  </a-col>
                  <a-col :xs="24" :md="12">
                    <a-form-item label="照片圆角">
                      <a-slider v-model:value="printTemplate.cornerRadius" :min="0" :max="28" />
                    </a-form-item>
                  </a-col>
                  <a-col :xs="24" :md="12">
                    <a-form-item label="贴纸">
                      <a-switch v-model:checked="printTemplate.stickerEnabled" checked-children="开启" un-checked-children="关闭" />
                    </a-form-item>
                    <a-form-item v-if="printTemplate.stickerEnabled" label="贴纸样式">
                      <a-select v-model:value="printTemplate.stickerShape" :options="stickerOptions" />
                    </a-form-item>
                  </a-col>
                  <a-col :xs="24" :md="12">
                    <a-form-item label="边框">
                      <a-switch v-model:checked="printTemplate.borderEnabled" checked-children="开启" un-checked-children="关闭" />
                    </a-form-item>
                    <a-space v-if="printTemplate.borderEnabled" compact>
                      <a-select v-model:value="printTemplate.borderStyle" :options="borderStyleOptions" style="width: 120px" />
                      <a-input-number v-model:value="printTemplate.borderWidth" :min="1" :max="24" style="width: 90px" />
                      <input v-model="printTemplate.borderColor" type="color" class="color-input" />
                    </a-space>
                  </a-col>
                  <a-col :xs="24" :md="12">
                    <a-form-item label="文字">
                      <a-switch v-model:checked="printTemplate.textEnabled" checked-children="开启" un-checked-children="关闭" />
                    </a-form-item>
                    <template v-if="printTemplate.textEnabled">
                      <a-form-item label="文字内容">
                        <a-input v-model:value="printTemplate.textContent" placeholder="支持活动名、节目名等后续替换" />
                      </a-form-item>
                      <a-form-item label="文字位置">
                        <a-select v-model:value="printTemplate.textPosition" :options="textPositionOptions" />
                      </a-form-item>
                      <a-space compact>
                        <a-input-number v-model:value="printTemplate.textSize" :min="8" :max="48" style="width: 110px" />
                        <input v-model="printTemplate.textColor" type="color" class="color-input" />
                      </a-space>
                    </template>
                  </a-col>
                  <a-col :xs="24" :md="12">
                    <a-form-item label="底图">
                      <a-radio-group v-model:value="printTemplate.backgroundMode" button-style="solid">
                        <a-radio-button value="color">纯色</a-radio-button>
                        <a-radio-button value="image">图片</a-radio-button>
                      </a-radio-group>
                    </a-form-item>
                    <a-form-item v-if="printTemplate.backgroundMode === 'color'" label="底色">
                      <input v-model="printTemplate.backgroundColor" type="color" class="color-input wide" />
                    </a-form-item>
                    <a-form-item v-else label="底图 URL">
                      <a-input v-model:value="printTemplate.backgroundImageUrl" placeholder="https://..." />
                    </a-form-item>
                  </a-col>
                </a-row>
              </a-form>
            </a-card>

            <a-card title="模版预览" :bordered="false" class="template-preview-card">
              <div class="paper-preview-wrap">
                <div class="paper-preview" :style="paperPreviewStyle">
                  <div class="photo-slot" :style="photoSlotStyle">
                    <PictureOutlined />
                    <span>照片区域</span>
                  </div>
                  <div v-if="printTemplate.stickerEnabled" class="preview-sticker" :class="printTemplate.stickerShape">贴纸</div>
                  <div v-if="printTemplate.textEnabled" class="preview-text" :class="printTemplate.textPosition" :style="previewTextStyle">
                    {{ printTemplate.textContent || activity?.name || 'SuperTech' }}
                  </div>
                </div>
              </div>
              <div class="template-summary">
                <a-tag>{{ printTemplate.paperWidthMm }} x {{ printTemplate.paperHeightMm }} mm</a-tag>
                <a-tag color="blue">dmPaperSize: {{ printTemplate.dmPaperSize }}</a-tag>
                <a-tag color="green">免费 {{ printTemplate.freePrintLimit }} 次/用户</a-tag>
              </div>
              <a-space class="template-actions">
                <a-button type="primary" @click="savePrintTemplate" :loading="savingPrintTemplate">
                  <template #icon><SaveOutlined /></template>
                  保存打印模版
                </a-button>
                <a-button @click="resetPrintTemplate">恢复默认</a-button>
              </a-space>
            </a-card>
          </div>
        </div>
      </a-tab-pane>

      <a-tab-pane key="custom-share" tab="定制分享">
        <div class="custom-share-panel">
          <div class="share-cover-block">
            <div>
              <div class="field-title">分享封面 <span>建议尺寸：200*200px，支持 PNG、JPG，文件小于 1MB</span></div>
              <div class="share-cover-row">
                <div class="share-cover-preview">
                  <img v-if="customShare.coverUrl" :src="customShare.coverUrl" alt="分享封面" />
                  <div v-else class="share-cover-empty">封面</div>
                </div>
                <a-space>
                  <a-upload :show-upload-list="false" accept="image/png,image/jpeg" :before-upload="handleShareCoverUpload">
                    <a-button>
                      <template #icon><UploadOutlined /></template>
                      本地上传
                    </a-button>
                  </a-upload>
                  <a-button @click="openMaterialPicker">
                    <template #icon><PictureOutlined /></template>
                    从素材库中选择
                  </a-button>
                </a-space>
              </div>
            </div>
            <a-alert
              type="info"
              show-icon
              message="温馨提示"
              description="上传的图片将作为此活动分享封面；如果未设置，会使用活动封面或默认样式。"
            />
          </div>

          <a-form layout="vertical" class="share-form">
            <a-form-item label="分享标题（40个字符）">
              <div class="inline-setting">
                <a-input v-model:value="customShare.title" :maxlength="40" placeholder="请输入分享标题" />
                <span>标题前显示邀请人</span>
                <a-switch v-model:checked="customShare.showInvite" />
              </div>
            </a-form-item>
            <a-form-item label="分享描述（120个字符）">
              <a-textarea v-model:value="customShare.description" :maxlength="120" :rows="5" placeholder="请输入分享描述" />
            </a-form-item>
          </a-form>

          <div class="tab-footer-actions">
            <a-button type="primary" @click="saveCustomShare" :loading="savingCustomShare">
              <template #icon><SaveOutlined /></template>
              保存
            </a-button>
          </div>
        </div>
      </a-tab-pane>

      <a-tab-pane key="audiences" tab="观众管理">
        <div class="audience-panel">
          <div class="panel-toolbar">
            <div>
              <h3>观众管理</h3>
              <p>记录微信端访问活动页面的观众 openid、头像、昵称、访问时间和终端信息。</p>
            </div>
            <a-button @click="fetchAudiences" :loading="audienceLoading">
              <template #icon><ReloadOutlined /></template>
              刷新
            </a-button>
          </div>

          <a-table
            :columns="audienceColumns"
            :data-source="audiences"
            :loading="audienceLoading"
            :pagination="{
              current: audiencePage,
              pageSize: audiencePageSize,
              total: audienceTotal,
              showSizeChanger: false,
              onChange: handleAudiencePageChange,
            }"
            row-key="id"
            size="middle"
          >
            <template #bodyCell="{ column, record }">
              <template v-if="column.key === 'avatar'">
                <a-avatar :src="record.avatar_url || undefined" :size="42">
                  <UserOutlined />
                </a-avatar>
              </template>
              <template v-if="column.key === 'openid'">
                {{ maskOpenid(record.openid) }}
              </template>
              <template v-if="column.key === 'status'">
                <a-tag :color="record.is_online ? 'green' : 'default'">
                  {{ record.is_online ? '在线' : '离线' }}
                </a-tag>
              </template>
              <template v-if="column.key === 'location'">
                <div class="stack-text">
                  <strong>{{ [record.province, record.city].filter(Boolean).join('') || '-' }}</strong>
                  <span>{{ record.last_ip || record.first_ip || '-' }}</span>
                </div>
              </template>
              <template v-if="column.key === 'last_seen_at'">
                {{ formatNullableTime(record.last_seen_at) }}
              </template>
              <template v-if="column.key === 'actions'">
                <a-button type="link" size="small" @click="toggleAudienceBlacklist(record)">
                  {{ record.is_blacklisted ? '恢复' : '拉黑' }}
                </a-button>
              </template>
            </template>
          </a-table>
        </div>
      </a-tab-pane>
    </a-tabs>

    <a-modal v-model:open="showMaterialModal" title="从素材库中选择封面" :footer="null" width="720px">
      <a-spin :spinning="activityPhotosLoading">
        <div v-if="activityPhotos.length" class="material-grid">
          <button
            v-for="photo in activityPhotos"
            :key="photo.id"
            class="material-item"
            type="button"
            @click="chooseMaterialCover(photo)"
          >
            <img :src="getThumbUrl(photo.storage_url || photo.wotu_url || '')" :alt="photo.filename" />
          </button>
        </div>
        <a-empty v-else description="暂无可选择素材" />
      </a-spin>
    </a-modal>

    <a-modal
      v-model:open="showExcelModal"
      title="Excel 导入节目"
      :footer="null"
      @cancel="resetExcelForm"
    >
      <div class="excel-import">
        <a-alert
          message="Excel 格式要求"
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
          <p class="ant-upload-text">点击或拖拽 Excel 文件到此处</p>
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

    <input ref="fileInputRef" type="file" accept="video/*" style="display: none" @change="handleFileSelected" />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  ArrowLeftOutlined,
  DeleteOutlined,
  DownOutlined,
  InboxOutlined,
  PictureOutlined,
  PlayCircleOutlined,
  PlusOutlined,
  PrinterOutlined,
  ReloadOutlined,
  SaveOutlined,
  UploadOutlined,
  UserOutlined,
} from '@ant-design/icons-vue'
import { message } from 'ant-design-vue'
import dayjs from 'dayjs'
import request from '@/api/request'
import {
  adminApi,
  audienceApi,
  photoApi,
  printApi,
  uploadApi,
  type Activity,
  type AudienceItem,
  type PhotoItemFull,
  type PrintRecordItem,
  type Program,
} from '@/api/admin'
import { getThumbUrl } from '@/utils/image'
import ActivityPhotoSync from './ActivityPhotoSync.vue'

interface PrintTemplate {
  templateName: string
  freePrintLimit: number
  paperKey: string
  dmPaperSize: string
  paperWidthMm: number
  paperHeightMm: number
  photoFit: 'cover' | 'contain'
  cornerRadius: number
  stickerEnabled: boolean
  stickerShape: string
  borderEnabled: boolean
  borderStyle: string
  borderColor: string
  borderWidth: number
  textEnabled: boolean
  textContent: string
  textPosition: string
  textColor: string
  textSize: number
  backgroundMode: 'color' | 'image'
  backgroundColor: string
  backgroundImageUrl: string
}

interface CustomShareConfig {
  coverUrl: string
  title: string
  showInvite: boolean
  description: string
}

const route = useRoute()
const router = useRouter()
const activityId = computed(() => Number(route.params.id))
const activity = ref<Activity | null>(null)
const programs = ref<Program[]>([])
const loading = ref(false)
const saving = ref(false)
const activeWorkspaceTab = ref('programs')
const programSearchKeyword = ref('')
const showExcelModal = ref(false)
const fileInputRef = ref<HTMLInputElement | null>(null)
const uploadingProgramId = ref<number | null>(null)
const uploadProgress = ref<Record<number, number>>({})
const failedThumbnails = reactive<Record<number, boolean>>({})
const editableData = ref<Record<number, any>>({})
const newRows = ref<any[]>([])
let newIdCounter = -1

const printRecords = ref<PrintRecordItem[]>([])
const printRecordsLoading = ref(false)
const printRecordPage = ref(1)
const printRecordPageSize = ref(20)
const printRecordTotal = ref(0)
const reprintingId = ref<number | null>(null)
const savingPrintTemplate = ref(false)
const savingCustomShare = ref(false)
const activityPhotos = ref<PhotoItemFull[]>([])
const activityPhotosLoading = ref(false)
const activityPhotoPage = ref(1)
const activityPhotoPageSize = ref(30)
const activityPhotoTotal = ref(0)
const printingPhotoId = ref<number | null>(null)
const showMaterialModal = ref(false)
const audiences = ref<AudienceItem[]>([])
const audienceLoading = ref(false)
const audiencePage = ref(1)
const audiencePageSize = ref(20)
const audienceTotal = ref(0)
let printRecordTimer: number | null = null

const defaultPrintTemplate: PrintTemplate = {
  templateName: '活动照片贴纸',
  freePrintLimit: 2,
  paperKey: 'a4',
  dmPaperSize: '9',
  paperWidthMm: 210,
  paperHeightMm: 297,
  photoFit: 'cover',
  cornerRadius: 8,
  stickerEnabled: true,
  stickerShape: 'ribbon',
  borderEnabled: true,
  borderStyle: 'solid',
  borderColor: '#111827',
  borderWidth: 4,
  textEnabled: true,
  textContent: 'SuperTech 快速交付',
  textPosition: 'bottom',
  textColor: '#111827',
  textSize: 16,
  backgroundMode: 'color',
  backgroundColor: '#f7f4ee',
  backgroundImageUrl: '',
}

const printTemplate = reactive<PrintTemplate>({ ...defaultPrintTemplate })

const defaultCustomShare: CustomShareConfig = {
  coverUrl: '',
  title: '',
  showInvite: false,
  description: '',
}

const customShare = reactive<CustomShareConfig>({ ...defaultCustomShare })

const printTemplateSettingKey = computed(() => `activity_${activityId.value}_print_template`)
const customShareSettingKey = computed(() => `activity_${activityId.value}_share_config`)

const filteredPrograms = computed(() => {
  const keyword = programSearchKeyword.value.trim().toLowerCase()
  if (!keyword) return programs.value

  return programs.value.filter(program => {
    const programNumber = String(program.sequence_number ?? '').toLowerCase()
    const programName = (program.name || '').toLowerCase()
    return programNumber.includes(keyword) || programName.includes(keyword)
  })
})

const tableData = computed(() => [...newRows.value, ...filteredPrograms.value])

const paperPreviewStyle = computed(() => {
  const width = 220
  const height = Math.min(340, Math.max(190, width * (printTemplate.paperHeightMm / printTemplate.paperWidthMm)))
  return {
    width: `${width}px`,
    height: `${height}px`,
    backgroundColor: printTemplate.backgroundMode === 'color' ? printTemplate.backgroundColor : '#f8fafc',
    backgroundImage: printTemplate.backgroundMode === 'image' && printTemplate.backgroundImageUrl ? `url(${printTemplate.backgroundImageUrl})` : '',
    border: printTemplate.borderEnabled ? `${printTemplate.borderWidth}px ${printTemplate.borderStyle} ${printTemplate.borderColor}` : '1px solid #e5e7eb',
  }
})

const photoSlotStyle = computed(() => ({
  objectFit: printTemplate.photoFit,
  borderRadius: `${printTemplate.cornerRadius}px`,
}))

const previewTextStyle = computed(() => ({
  color: printTemplate.textColor,
  fontSize: `${printTemplate.textSize}px`,
}))

const excelResult = ref<{ success: number; failed: number } | null>(null)

const excelHintColumns = [
  { title: '列名', dataIndex: 'column', width: 120 },
  { title: '说明', dataIndex: 'desc' },
  { title: '必填', dataIndex: 'required', width: 60 },
]

const excelHintData = [
  { key: '1', column: '节目名称', desc: '节目名称（支持：节目名称、名称、name、节目）', required: '是' },
  { key: '2', column: '节目号', desc: '节目号（支持：节目号、序号、编号、sequence、order）', required: '否' },
  { key: '3', column: '开始时间', desc: '录制开始时间（支持：开始时间、录制开始、start_time）', required: '否' },
  { key: '4', column: '结束时间', desc: '录制结束时间（支持：结束时间、录制结束、end_time）', required: '否' },
  { key: '5', column: '就绪模式', desc: '自动/手动（支持：就绪模式、ready_mode）', required: '否' },
]

const editableColumns = [
  { title: '节目号', dataIndex: 'sequence_number', key: 'sequence_number', align: 'center' as const },
  { title: '节目名称', dataIndex: 'name', key: 'name', align: 'center' as const },
  { title: '录制时间', dataIndex: 'time_range', key: 'time_range', align: 'center' as const },
  { title: '时长', dataIndex: 'duration', key: 'duration', align: 'center' as const },
  { title: '就绪模式', dataIndex: 'ready_mode', key: 'ready_mode', align: 'center' as const },
  { title: '视频', dataIndex: 'video_status', key: 'video_status', align: 'center' as const },
  { title: '照片', dataIndex: 'photo_count', key: 'photo_count', align: 'center' as const },
  { title: '就绪', dataIndex: 'ready_status', key: 'ready_status', align: 'center' as const },
  { title: '操作', key: 'actions', align: 'center' as const },
]

const printRecordColumns = [
  { title: '照片', key: 'photo', width: 280 },
  { title: '用户', key: 'user', width: 180 },
  { title: '打印任务', key: 'job', width: 180 },
  { title: '状态', key: 'status', width: 140 },
  { title: '提交时间', key: 'created_at', width: 180 },
  { title: '操作', key: 'actions', width: 120, align: 'center' as const },
]

const audienceColumns = [
  { title: '用户ID', key: 'openid', width: 110 },
  { title: '在线状态', key: 'status', width: 100 },
  { title: '用户头像', key: 'avatar', width: 100 },
  { title: '微信昵称', dataIndex: 'nickname', key: 'nickname', width: 160 },
  { title: '手机号', dataIndex: 'phone', key: 'phone', width: 120 },
  { title: '所在省市', key: 'location', width: 180 },
  { title: '最近观看时间', key: 'last_seen_at', width: 180 },
  { title: '操作', key: 'actions', width: 100, align: 'center' as const },
]

const paperOptions = [
  { label: 'A4 210 x 297mm（dmPaperSize 9）', value: 'a4' },
  { label: 'A5 148 x 210mm（dmPaperSize 11）', value: 'a5' },
  { label: 'A6 105 x 148mm（dmPaperSize 70）', value: 'a6' },
  { label: '自定义尺寸（dmPaperSize 0）', value: 'custom' },
]

const paperPresets: Record<string, { dmPaperSize: string; width: number; height: number }> = {
  a4: { dmPaperSize: '9', width: 210, height: 297 },
  a5: { dmPaperSize: '11', width: 148, height: 210 },
  a6: { dmPaperSize: '70', width: 105, height: 148 },
  custom: { dmPaperSize: '0', width: 100, height: 150 },
}

const stickerOptions = [
  { label: '角标丝带', value: 'ribbon' },
  { label: '圆形印章', value: 'stamp' },
  { label: '底部胶片', value: 'film' },
]

const borderStyleOptions = [
  { label: '实线', value: 'solid' },
  { label: '虚线', value: 'dashed' },
  { label: '点线', value: 'dotted' },
]

const textPositionOptions = [
  { label: '顶部', value: 'top' },
  { label: '底部', value: 'bottom' },
  { label: '左下角', value: 'left-bottom' },
  { label: '右下角', value: 'right-bottom' },
]

const formatTime = (time: string) => dayjs(time).format('YYYY-MM-DD HH:mm:ss')
const formatNullableTime = (time?: string | null) => time ? dayjs(time).format('YYYY-MM-DD HH:mm:ss') : '--'

const formatDuration = (seconds: number) => {
  const minutes = Math.floor(seconds / 60)
  const rest = Math.round(seconds % 60)
  return `${minutes}:${String(rest).padStart(2, '0')}`
}

const videoStatusColor = (status: string) => ({ none: 'default', uploading: 'processing', ready: 'success' }[status] || 'default')
const videoStatusText = (status: string) => ({ none: '未上传', uploading: '上传中', ready: '已就绪' }[status] || status)

const printStatusColor = (status: string) => ({
  queued: 'blue',
  printing: 'processing',
  success: 'green',
  failed: 'red',
  cancelled: 'default',
}[status] || 'default')

const printStatusText = (status: string) => ({
  queued: '排队中',
  printing: '打印中',
  success: '成功',
  failed: '失败',
  cancelled: '已取消',
}[status] || status)

const maskOpenid = (openid?: string | null) => {
  if (!openid) return '-'
  return openid.length <= 6 ? openid : openid.slice(-6)
}

const fetchData = async () => {
  loading.value = true
  try {
    const [actRes, progRes] = await Promise.all([
      adminApi.getActivity(activityId.value),
      adminApi.listPrograms(activityId.value),
    ])
    activity.value = actRes.data
    programs.value = progRes.data
    Object.keys(failedThumbnails).forEach(key => delete failedThumbnails[Number(key)])
  } catch {
    message.error('加载数据失败')
  } finally {
    loading.value = false
  }
}

const fetchPrintRecords = async () => {
  printRecordsLoading.value = true
  try {
    const res = await printApi.getActivityPrintRecords(activityId.value, printRecordPage.value, printRecordPageSize.value)
    printRecords.value = res.data.items
    printRecordTotal.value = res.data.total
  } catch {
    message.error('加载打印记录失败')
  } finally {
    printRecordsLoading.value = false
  }
}

const refreshPrintRecordsSilently = async () => {
  try {
    const res = await printApi.getActivityPrintRecords(activityId.value, printRecordPage.value, printRecordPageSize.value)
    printRecords.value = res.data.items
    printRecordTotal.value = res.data.total
  } catch {
    // keep polling quiet; manual refresh still reports errors
  }
}

const startPrintRecordPolling = () => {
  stopPrintRecordPolling()
  refreshPrintRecordsSilently()
  printRecordTimer = window.setInterval(refreshPrintRecordsSilently, 3000)
}

const stopPrintRecordPolling = () => {
  if (printRecordTimer) {
    window.clearInterval(printRecordTimer)
    printRecordTimer = null
  }
}

const fetchActivityPhotos = async () => {
  activityPhotosLoading.value = true
  try {
    const res = await photoApi.getActivityPhotos(activityId.value, activityPhotoPage.value, activityPhotoPageSize.value)
    activityPhotos.value = res.data.photos
    activityPhotoTotal.value = res.data.total
  } catch {
    message.error('加载照片失败')
  } finally {
    activityPhotosLoading.value = false
  }
}

const loadPrintTemplate = async () => {
  try {
    const res = await request.get(`/settings/${printTemplateSettingKey.value}`)
    if (res.data?.value) {
      Object.assign(printTemplate, defaultPrintTemplate, JSON.parse(res.data.value))
      return
    }
  } catch {
    // use default template
  }
  Object.assign(printTemplate, defaultPrintTemplate)
}

const savePrintTemplate = async () => {
  savingPrintTemplate.value = true
  try {
    await request.put(`/settings/${printTemplateSettingKey.value}`, {
      value: JSON.stringify({ ...printTemplate }),
    })
    message.success('打印模版已保存')
  } catch {
    message.error('保存打印模版失败')
  } finally {
    savingPrintTemplate.value = false
  }
}

const loadCustomShare = async () => {
  try {
    const res = await request.get(`/settings/${customShareSettingKey.value}`)
    if (res.data?.value) {
      Object.assign(customShare, defaultCustomShare, JSON.parse(res.data.value))
      return
    }
  } catch {
    // use defaults
  }
  Object.assign(customShare, {
    ...defaultCustomShare,
    title: activity.value?.name || '',
    description: activity.value?.description || '',
    coverUrl: activity.value?.cover_image || '',
  })
}

const saveCustomShare = async () => {
  savingCustomShare.value = true
  try {
    await request.put(`/settings/${customShareSettingKey.value}`, {
      value: JSON.stringify({ ...customShare }),
    })
    message.success('定制分享已保存')
  } catch {
    message.error('保存定制分享失败')
  } finally {
    savingCustomShare.value = false
  }
}

const handleShareCoverUpload = (file: File) => {
  if (!file.type.startsWith('image/')) {
    message.warning('请选择 PNG 或 JPG 图片')
    return false
  }
  if (file.size > 1024 * 1024) {
    message.warning('图片大小不能超过 1MB')
    return false
  }
  const reader = new FileReader()
  reader.onload = () => {
    const result = String(reader.result || '')
    if (result.length > 4500) {
      message.warning('图片数据过大，请从素材库选择或使用较小的封面图')
      return
    }
    customShare.coverUrl = result
  }
  reader.readAsDataURL(file)
  return false
}

const openMaterialPicker = async () => {
  showMaterialModal.value = true
  if (!activityPhotos.value.length) {
    await fetchActivityPhotos()
  }
}

const chooseMaterialCover = (photo: PhotoItemFull) => {
  customShare.coverUrl = photo.storage_url || photo.wotu_url || ''
  showMaterialModal.value = false
}

const fetchAudiences = async () => {
  audienceLoading.value = true
  try {
    const res = await audienceApi.getActivityAudiences(activityId.value, audiencePage.value, audiencePageSize.value)
    audiences.value = res.data.items
    audienceTotal.value = res.data.total
  } catch {
    message.error('加载观众数据失败')
  } finally {
    audienceLoading.value = false
  }
}

const handleAudiencePageChange = (page: number) => {
  audiencePage.value = page
  fetchAudiences()
}

const toggleAudienceBlacklist = async (record: AudienceItem) => {
  try {
    await audienceApi.updateBlacklist(record.id, !record.is_blacklisted)
    message.success(record.is_blacklisted ? '已恢复观众' : '已拉黑观众')
    fetchAudiences()
  } catch {
    message.error('更新观众状态失败')
  }
}

const resetPrintTemplate = () => {
  Object.assign(printTemplate, defaultPrintTemplate)
}

const applyPaperPreset = (key: string) => {
  const preset = paperPresets[key]
  if (!preset) return
  printTemplate.dmPaperSize = preset.dmPaperSize
  printTemplate.paperWidthMm = preset.width
  printTemplate.paperHeightMm = preset.height
}

const handleWorkspaceChange = (key: string) => {
  if (key !== 'print-records') {
    stopPrintRecordPolling()
  }
  if (key === 'photo-manager') {
    fetchActivityPhotos()
  }
  if (key === 'print-records') {
    fetchPrintRecords()
    startPrintRecordPolling()
  }
  if (key === 'print-template') {
    loadPrintTemplate()
  }
  if (key === 'custom-share') {
    loadCustomShare()
  }
  if (key === 'audiences') {
    fetchAudiences()
  }
}

const handlePrintRecordPageChange = (page: number) => {
  printRecordPage.value = page
  fetchPrintRecords()
}

const handleReprint = async (record: PrintRecordItem) => {
  reprintingId.value = record.id
  try {
    await printApi.reprintRecord(record.id)
    message.success('已提交重打任务')
    fetchPrintRecords()
  } catch {
    message.error('提交重打失败')
  } finally {
    reprintingId.value = null
  }
}

const handlePrintPhoto = async (photo: PhotoItemFull) => {
  printingPhotoId.value = photo.id
  try {
    await printApi.createActivityPrintRecord(activityId.value, photo.id)
    message.success('已提交打印任务')
    if (activeWorkspaceTab.value === 'print-records') {
      refreshPrintRecordsSilently()
    }
  } catch {
    message.error('提交打印失败')
  } finally {
    printingPhotoId.value = null
  }
}

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
    message.warning('节目号不能为空')
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

const handleAddMenuClick = ({ key }: { key: string }) => {
  if (key === 'single') {
    addNewRow()
  } else if (key === 'excel') {
    showExcelModal.value = true
    excelResult.value = null
  }
}

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
    message.warning('请输入节目号')
    return
  }
  saving.value = true
  try {
    await adminApi.createProgram(activityId.value, {
      name: record.name,
      sequence_number: record.sequence_number,
      ready_mode: record.ready_mode,
    })
    newRows.value = newRows.value.filter(row => row.id !== record.id)
    message.success('添加成功')
    fetchData()
  } catch {
    message.error('添加失败')
  } finally {
    saving.value = false
  }
}

const handleCancelNew = (id: number) => {
  newRows.value = newRows.value.filter(row => row.id !== id)
}

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
  return false
}

const resetExcelForm = () => {
  excelResult.value = null
}

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

const handleFileSelected = async (event: Event) => {
  const file = (event.target as HTMLInputElement).files?.[0]
  if (!file || !uploadingProgramId.value) return

  const programId = uploadingProgramId.value
  const uploadKey = `upload-${programId}`

  try {
    message.loading({ content: '正在获取上传凭证...', key: uploadKey, duration: 0 })
    const tokenRes = await uploadApi.getVideoUploadToken(programId, file.name)
    const { token, key, upload_url } = tokenRes.data

    const programIndex = programs.value.findIndex(program => program.id === programId)
    if (programIndex !== -1) {
      programs.value[programIndex].video_status = 'uploading'
    }
    uploadProgress.value[programId] = 0

    await new Promise<void>((resolve, reject) => {
      const xhr = new XMLHttpRequest()
      const formData = new FormData()
      formData.append('token', token)
      formData.append('key', key)
      formData.append('file', file)

      xhr.upload.addEventListener('progress', event => {
        if (event.lengthComputable) {
          const percent = Math.round((event.loaded / event.total) * 100)
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
      xhr.timeout = 600000
      xhr.send(formData)
    })

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

onMounted(async () => {
  await fetchData()
  await loadPrintTemplate()
})

onUnmounted(() => {
  stopPrintRecordPolling()
})
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

.workspace-tabs :deep(.ant-tabs-nav) {
  margin-bottom: 18px;
}

.program-tab-search {
  width: 320px;
  max-width: 38vw;
}

.muted-inline {
  margin-left: 8px;
  font-size: 12px;
  color: #8c8c8c;
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

.video-ready-cell {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
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

.video-thumb-fallback {
  display: flex;
  align-items: center;
  justify-content: center;
}

.video-thumb-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.video-thumb-play {
  position: absolute;
  inset: 0;
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

.activity-photo-panel,
.print-records-panel,
.print-template-panel {
  background: #f7f8fb;
  border: 1px solid #edf0f5;
  border-radius: 8px;
  padding: 18px;
}

.panel-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
  margin-bottom: 16px;
}

.panel-toolbar h3 {
  margin: 0 0 4px;
  font-size: 17px;
}

.panel-toolbar p {
  margin: 0;
  color: #6b7280;
}

.print-photo-cell {
  display: flex;
  align-items: center;
  gap: 12px;
}

.print-photo-cell img,
.empty-thumb {
  width: 64px;
  height: 64px;
  flex: none;
  border-radius: 6px;
  object-fit: cover;
  background: #eef1f6;
}

.empty-thumb {
  display: flex;
  align-items: center;
  justify-content: center;
  color: #8c8c8c;
  font-size: 12px;
}

.print-photo-cell strong,
.stack-text strong {
  display: block;
  color: #1f2937;
  font-size: 13px;
}

.print-photo-cell span,
.stack-text span {
  display: block;
  margin-top: 3px;
  color: #6b7280;
  font-size: 12px;
}

.record-error {
  margin-top: 4px;
  color: #cf1322;
  font-size: 12px;
}

.activity-photo-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(164px, 1fr));
  gap: 14px;
}

.activity-photo-card {
  overflow: hidden;
  border: 1px solid #eef1f5;
  border-radius: 8px;
  background: #fff;
}

.activity-photo-thumb {
  position: relative;
  aspect-ratio: 1;
  background: #eef1f6;
  overflow: hidden;
}

.activity-photo-thumb img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
  transition: transform 0.2s ease;
}

.activity-photo-card:hover .activity-photo-thumb img {
  transform: scale(1.035);
}

.photo-print-button {
  position: absolute;
  right: 10px;
  bottom: 10px;
  box-shadow: 0 8px 20px rgba(15, 23, 42, 0.28);
}

.activity-photo-meta {
  padding: 10px;
}

.activity-photo-meta strong {
  display: block;
  overflow: hidden;
  color: #1f2937;
  font-size: 13px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.activity-photo-meta span {
  display: block;
  margin-top: 3px;
  color: #6b7280;
  font-size: 12px;
}

.photo-pagination {
  display: flex;
  justify-content: center;
  padding-top: 18px;
}

.template-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr) 300px;
  gap: 16px;
  align-items: start;
}

.template-card,
.template-preview-card {
  border-radius: 8px;
  box-shadow: 0 10px 24px rgba(18, 31, 62, 0.06);
}

.color-input {
  width: 44px;
  height: 32px;
  border: 1px solid #d9d9d9;
  border-radius: 6px;
  background: #fff;
  padding: 2px;
}

.color-input.wide {
  width: 100%;
}

.paper-preview-wrap {
  display: flex;
  justify-content: center;
  padding: 8px 0 16px;
}

.paper-preview {
  position: relative;
  overflow: hidden;
  border-radius: 6px;
  background-size: cover;
  background-position: center;
  box-shadow: 0 18px 42px rgba(17, 24, 39, 0.18);
  padding: 18px;
}

.photo-slot {
  height: 72%;
  border: 1px dashed rgba(17, 24, 39, 0.35);
  background: rgba(255, 255, 255, 0.62);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  color: #6b7280;
  overflow: hidden;
}

.photo-slot :deep(.anticon) {
  font-size: 30px;
}

.preview-sticker {
  position: absolute;
  top: 18px;
  right: -30px;
  width: 110px;
  padding: 5px 0;
  background: #111827;
  color: #fff;
  text-align: center;
  font-size: 12px;
  transform: rotate(36deg);
}

.preview-sticker.stamp {
  right: 18px;
  width: 52px;
  height: 52px;
  border-radius: 50%;
  padding: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  transform: none;
  background: #c2410c;
}

.preview-sticker.film {
  top: auto;
  right: 18px;
  bottom: 18px;
  width: auto;
  padding: 5px 12px;
  border-radius: 999px;
  transform: none;
}

.preview-text {
  position: absolute;
  left: 18px;
  right: 18px;
  font-weight: 700;
  text-align: center;
}

.preview-text.top {
  top: 18px;
}

.preview-text.bottom {
  bottom: 20px;
}

.preview-text.left-bottom {
  right: auto;
  bottom: 20px;
  text-align: left;
}

.preview-text.right-bottom {
  left: auto;
  bottom: 20px;
  text-align: right;
}

.template-summary {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 16px;
}

.template-actions {
  width: 100%;
}

.custom-share-panel,
.audience-panel {
  background: #fff;
  border-radius: 8px;
  padding: 24px;
}

.share-cover-block {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(280px, 420px);
  gap: 28px;
  align-items: center;
  margin-bottom: 26px;
}

.field-title {
  margin-bottom: 12px;
  color: #24324b;
  font-size: 15px;
  font-weight: 650;
}

.field-title span {
  margin-left: 8px;
  color: #7c8798;
  font-size: 13px;
  font-weight: 400;
}

.share-cover-row {
  display: flex;
  gap: 28px;
  align-items: flex-start;
}

.share-cover-preview {
  width: 142px;
  height: 142px;
  overflow: hidden;
  border: 1px dashed #8fb4ff;
  background: #f4f8ff;
}

.share-cover-preview img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.share-cover-empty {
  height: 100%;
  display: grid;
  place-items: center;
  color: #8aa0c1;
}

.share-form {
  max-width: 820px;
}

.inline-setting {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto auto;
  gap: 12px;
  align-items: center;
}

.inline-setting span {
  color: #516070;
}

.tab-footer-actions {
  margin-top: 46px;
  padding: 18px 0 0 62px;
  border-top: 1px solid #eef1f5;
}

.material-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(116px, 1fr));
  gap: 12px;
}

.material-item {
  aspect-ratio: 1;
  padding: 0;
  overflow: hidden;
  border: 1px solid #e4e8f0;
  border-radius: 8px;
  background: #fff;
  cursor: pointer;
}

.material-item img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform 0.18s ease;
}

.material-item:hover img {
  transform: scale(1.05);
}

:deep(.ant-table) .ant-table-cell {
  text-align: center;
}

@media (max-width: 1280px) {
  .template-layout {
    grid-template-columns: 1fr;
  }

  .template-preview-card {
    max-width: 420px;
  }

  .share-cover-block {
    grid-template-columns: 1fr;
  }
}
</style>
