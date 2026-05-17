<template>
  <div>
    <div class="page-header">
      <a-button @click="$router.push('/admin')">
        <template #icon><ArrowLeftOutlined /></template>
        返回
      </a-button>
      <h2>{{ activity?.name || '节目管理' }}</h2>
      <a-space v-if="activeWorkspaceTab === 'programs'">
        <div class="program-photo-category-picker">
          <span class="ready-mode-label">照片分类</span>
          <a-checkbox v-if="!programPhotoMatchCategories.length" checked disabled>全部</a-checkbox>
          <a-checkbox-group
            v-else
            v-model:value="programPhotoMatchSelectedIds"
            :options="programPhotoMatchCategoryOptions"
            :disabled="savingProgramPhotoMatchCategories"
            @change="handleProgramPhotoMatchCategoryChange"
          />
        </div>
        <div class="ready-mode-switch">
          <span class="ready-mode-label">就绪模式</span>
          <a-switch
            :checked="activity?.ready_mode !== 'manual'"
            @change="handleToggleActivityReadyMode"
            checked-children="自动"
            un-checked-children="手动"
          />
        </div>
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
          <a-segmented
            v-model:value="sequenceNumberPad"
            :options="sequenceNumberPadOptions"
            size="small"
          />
          <a-input-search
            v-model:value="programSearchKeyword"
            allow-clear
            placeholder="搜索节目号或节目名"
            style="max-width: 320px"
          />
        </div>
      </template>

      <a-tab-pane v-if="!isPrintAdmin" key="programs" tab="节目管理">
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
            :pagination="{
              current: programPage,
              pageSize: programPageSize,
              pageSizeOptions: ['20', '50', '100'],
              showSizeChanger: true,
              showTotal: (total: number) => `共 ${total} 条`,
              onChange: handleProgramPageChange,
              onShowSizeChange: handleProgramPageSizeChange,
            }"
            row-key="id"
            size="middle"
            table-layout="fixed"
            :scroll="{ x: 1410 }"
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
                <span v-else class="sequence-number-text">{{ formatSequenceNumber(record.sequence_number) }}</span>
              </template>

              <template v-if="column.dataIndex === 'name'">
                <div class="program-name-cell">
                  <a-input
                    v-if="record._isNew || editableData[record.id] || programNameDrafts[record.id] !== undefined"
                    :ref="(el: any) => setProgramNameInputRef(record.id, el)"
                    class="program-name-editor"
                    :value="getProgramNameValue(record)"
                    @change="(e: any) => setProgramNameValue(record, e.target.value)"
                    @pressEnter="handleProgramNameEnter(record)"
                    @keydown.esc="handleProgramNameEsc(record)"
                    @blur="handleProgramNameBlur(record)"
                    size="small"
                    placeholder="节目名称"
                  />
                  <a-tooltip v-else title="双击修改节目名称">
                    <span class="program-name-text" @dblclick.stop="handleEditProgramName(record)">
                      {{ record.name }}
                    </span>
                  </a-tooltip>
                </div>
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

              <template v-if="column.dataIndex === 'video_status'">
                <template v-if="getProgramVideos(record).length > 0">
                  <div class="video-stack-cell">
                    <a-tooltip title="点击预览节目">
                      <div class="video-thumb" @click="handlePreviewVideo(record)">
                        <img
                          v-if="record.video_thumbnail_url && !failedThumbnails[record.id]"
                          :src="record.video_thumbnail_url"
                          class="video-thumb-img"
                          @error="failedThumbnails[record.id] = true"
                        />
                        <PlayCircleOutlined v-else class="video-thumb-icon" />
                        <div class="video-thumb-play"><PlayCircleOutlined /></div>
                      </div>
                    </a-tooltip>
                    <a-popover trigger="click" placement="leftTop">
                      <template #content>
                        <div class="recording-list">
                          <div v-for="video in getProgramVideos(record)" :key="video.id" class="recording-item">
                            <button class="recording-main" @click="handleOpenVideo(video.storage_url)">
                              <strong>{{ formatRecordingTime(video) }}</strong>
                              <span>{{ video.filename }}</span>
                            </button>
                            <a-popconfirm title="确定删除这条录制视频？" @confirm="handleDeleteRecording(video.id)" placement="topRight">
                              <a-button type="text" size="small" danger>
                                <template #icon><DeleteOutlined /></template>
                              </a-button>
                            </a-popconfirm>
                          </div>
                        </div>
                      </template>
                      <a-button size="small" class="recording-count-btn">{{ getProgramVideos(record).length }} 条录制</a-button>
                    </a-popover>
                    <a-popconfirm v-if="editableData[record.id]" title="确定删除当前节目视频？视频将移至临时文件夹" @confirm="handleDeleteVideo(record.id)" placement="top">
                      <a-tooltip title="删除当前视频">
                        <a-button type="text" size="small" danger class="video-delete-btn">
                          <template #icon><DeleteOutlined /></template>
                        </a-button>
                      </a-tooltip>
                    </a-popconfirm>
                  </div>
                </template>
                <template v-else-if="record.video_status === 'uploading'">
                  <a-progress :percent="uploadProgress[record.id] || 0" size="small" :stroke-width="4" style="width: 80px" />
                </template>
                <a-tag v-else :color="videoStatusColor(record.video_status)">
                  {{ videoStatusText(record.video_status) }}
                </a-tag>
              </template>

              <template v-if="column.dataIndex === 'short_video'">
                <div class="sv-cell">
                  <template v-if="record.short_video_status === 'ready' && record.short_video_url">
                    <a-tooltip title="点击查看短视频">
                      <div class="sv-thumb" @click="handleOpenVideo(record.short_video_url)">
                        <PlayCircleOutlined class="sv-thumb-icon" />
                        <div class="sv-thumb-play"><PlayCircleOutlined /></div>
                      </div>
                    </a-tooltip>
                  </template>
                  <template v-else-if="record.short_video_status === 'generating'">
                    <div class="sv-status generating">
                      <LoadingOutlined spin />
                      <span>生成中</span>
                    </div>
                  </template>
                  <template v-else-if="record.short_video_status === 'failed'">
                    <a-tooltip title="生成失败，可在短视频管理中重试">
                      <div class="sv-status failed">
                        <WarningOutlined />
                        <span>失败</span>
                      </div>
                    </a-tooltip>
                  </template>
                  <template v-else>
                    <a-tooltip title="点击生成短视频">
                      <div class="sv-status none clickable" @click="handleGenerateSingleShortVideo(record)">
                        <VideoCameraOutlined />
                        <span>未生成</span>
                      </div>
                    </a-tooltip>
                  </template>
                </div>
              </template>

              <template v-if="column.dataIndex === 'photo_count'">
                <span style="font-size: 13px">{{ record.photo_count ?? 0 }}</span>
              </template>

              <template v-if="column.dataIndex === 'ready_status'">
                <a-switch
                  :checked="record.ready_status === 'ready'"
                  @change="(checked: boolean) => handleToggleReady(record, checked)"
                  :disabled="activity?.ready_mode !== 'manual'"
                />
                <span v-if="activity?.ready_mode !== 'manual'" class="muted-inline">自动</span>
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

      <a-tab-pane v-if="!isPrintAdmin" key="photo-sync" tab="照片同步">
        <ActivityPhotoSync
          v-if="activity"
          :activity-id="activityId"
          :activity="activity"
        />
      </a-tab-pane>

      <a-tab-pane v-if="!isPrintAdmin" key="photo-manager" tab="照片管理">
        <div class="activity-photo-panel">
          <div class="panel-toolbar">
            <div>
              <h3>已同步照片</h3>
              <p>展示当前活动下已同步入库的照片，可直接提交打印任务。</p>
            </div>
            <a-space>
              <a-button danger :disabled="photoSelectedIds.size === 0" :loading="photoDeleting" @click="handleDeleteSelectedPhotos">
                <template #icon><DeleteOutlined /></template>
                删除{{ photoSelectedIds.size > 0 ? ` (${photoSelectedIds.size})` : '' }}
              </a-button>
              <a-button @click="fetchActivityPhotos" :loading="activityPhotosLoading">
                <template #icon><ReloadOutlined /></template>
                刷新
              </a-button>
            </a-space>
          </div>

          <div v-if="activityPhotoCategories.length > 0" class="photo-category-filter">
            <a-radio-group
              v-model:value="activityPhotoCategoryId"
              button-style="solid"
              @change="handleActivityPhotoCategoryChange"
            >
              <a-radio-button value="">全部 {{ activityPhotoCategories.reduce((sum, item) => sum + item.count, 0) }}</a-radio-button>
              <a-radio-button
                v-for="category in activityPhotoCategories"
                :key="category.category_id || category.category_name"
                :value="category.category_id"
                :disabled="!category.category_id"
              >
                {{ category.category_name || '未分类' }} {{ category.count }}
              </a-radio-button>
            </a-radio-group>
          </div>

          <a-spin :spinning="activityPhotosLoading">
            <div v-if="activityPhotos.length > 0" class="activity-photo-grid">
              <div v-for="photo in activityPhotos" :key="photo.id" class="activity-photo-card" :class="{ 'activity-photo-card-selected': photoSelectedIds.has(photo.id) }">
                <div class="activity-photo-thumb">
                  <div class="photo-checkbox" @click.stop>
                    <a-checkbox
                      :checked="photoSelectedIds.has(photo.id)"
                      @change="(e: any) => togglePhotoSelect(photo.id, e.target.checked)"
                    />
                  </div>
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
                  <a-tag v-if="photo.wotu_category_name" class="activity-photo-category">
                    {{ photo.wotu_category_name }}
                  </a-tag>
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
              @change="(page: number) => { activityPhotoPage = page; photoSelectedIds = new Set(); fetchActivityPhotos() }"
            />
          </div>
        </div>
      </a-tab-pane>

      <a-tab-pane v-if="!isPrintAdmin" key="short-video" tab="短视频管理">
        <div class="sv-auto-config-bar">
          <div class="sv-auto-config-left">
            <a-switch
              :checked="shortVideoAutoConfig.enabled"
              @change="handleToggleAutoGenerate"
              checked-children="开"
              un-checked-children="关"
            />
            <span class="sv-auto-config-label">视频上传后自动生成短视频</span>
            <a-tooltip title="开启后，每当有节目视频上传完成，系统会按照下方配置自动触发短视频生成工作流">
              <QuestionCircleOutlined style="color: #8c8c8c; cursor: help" />
            </a-tooltip>
          </div>
          <div style="display: flex; align-items: center; gap: 16px;">
            <div v-if="shortVideoAutoConfig.enabled" class="sv-auto-config-summary">
              <a-tag color="blue">{{ shortVideoAutoConfig.duration }}秒</a-tag>
              <a-tag color="purple">{{ { 1: '每拍切换', 2: '每2拍', 4: '每4拍', 8: '每8拍' }[shortVideoAutoConfig.cut_intensity] || '每2拍' }}</a-tag>
              <a-tag>{{ { random: '随机', forward: '正向', backward: '反向' }[shortVideoAutoConfig.direction] || '随机' }}</a-tag>
              <a-tag v-if="shortVideoAutoConfig.music_id" color="green">{{ musicOptions.find(m => m.id === shortVideoAutoConfig.music_id)?.name || '指定音乐' }}</a-tag>
              <a-tag v-else>随机音乐</a-tag>
            </div>
            <a-button type="primary" ghost @click="handleOpenLobbyPlayer">
              <template #icon><DesktopOutlined /></template>
              前厅播放
            </a-button>
          </div>
        </div>

        <a-tabs v-model:activeKey="shortVideoInnerTab" size="small" @change="handleShortVideoInnerChange">
          <a-tab-pane key="sv-generate" tab="短视频生成">
            <div class="short-video-panel">
              <div class="panel-toolbar">
                <div>
                  <h3>短视频生成</h3>
                  <p>从热门曲库中随机选择音乐，自动将节目视频剪辑为短视频（默认15秒），配乐卡点。</p>
                </div>
                <a-button @click="fetchShortVideoStatus" :loading="shortVideoLoading">
                  <template #icon><ReloadOutlined /></template>
                  刷新
                </a-button>
              </div>

              <a-form layout="inline" class="short-video-config" style="margin-bottom: 16px">
                <a-form-item label="短视频时长">
                  <a-input-number v-model:value="shortVideoDuration" :min="5" :max="60" :step="5" addon-after="秒" style="width: 120px" />
                </a-form-item>
                <a-form-item label="卡点强度">
                  <a-select v-model:value="shortVideoCutIntensity" style="width: 120px">
                    <a-select-option :value="1">每拍切换</a-select-option>
                    <a-select-option :value="2">每2拍切换</a-select-option>
                    <a-select-option :value="4">每4拍切换</a-select-option>
                    <a-select-option :value="8">每8拍切换</a-select-option>
                  </a-select>
                </a-form-item>
                <a-form-item label="播放方向">
                  <a-select v-model:value="shortVideoDirection" style="width: 120px">
                    <a-select-option value="random">随机</a-select-option>
                    <a-select-option value="forward">正向</a-select-option>
                    <a-select-option value="backward">反向</a-select-option>
                  </a-select>
                </a-form-item>
                <a-form-item label="指定音乐">
                  <a-select v-model:value="shortVideoMusicId" style="width: 180px" allow-clear placeholder="随机选择">
                    <a-select-option v-for="m in musicOptions" :key="m.id" :value="m.id">
                      {{ m.name }}{{ m.duration ? ` (${Math.floor(m.duration / 60)}:${String(Math.floor(m.duration % 60)).padStart(2, '0')})` : '' }}
                    </a-select-option>
                  </a-select>
                </a-form-item>
                <a-form-item>
                  <a-button type="primary" ghost :loading="shortVideoAutoConfigLoading" @click="handleSaveShortVideoConfig">
                    <template #icon><SaveOutlined /></template>
                    保存配置
                  </a-button>
                </a-form-item>
              </a-form>
              <a-alert
                v-if="shortVideoAutoConfig.enabled"
                type="info"
                show-icon
                message="自动生成已开启"
                style="margin-bottom: 16px"
              >
                <template #description>
                  视频上传后会自动按照当前配置生成短视频。修改上方配置后点击「生成短视频」按钮会同步更新自动生成配置。
                </template>
              </a-alert>

              <a-spin :spinning="shortVideoLoading">
                <a-table
                  :columns="shortVideoColumns"
                  :data-source="shortVideoPrograms"
                  :pagination="false"
                  row-key="id"
                  size="small"
                  :row-selection="{ selectedRowKeys: shortVideoSelectedIds, onChange: onShortVideoSelectChange }"
                >
                  <template #bodyCell="{ column, record }">
                    <template v-if="column.dataIndex === 'sequence_number'">
                      {{ record.sequence_number }}
                    </template>
                    <template v-if="column.dataIndex === 'short_video_status'">
                      <a-tag :color="shortVideoStatusColor(record.short_video_status)">
                        {{ shortVideoStatusText(record.short_video_status) }}
                      </a-tag>
                    </template>
                    <template v-if="column.dataIndex === 'actions'">
                      <a-space>
                        <a-button
                          v-if="record.short_video_status === 'ready' && record.short_video_url"
                          type="link"
                          size="small"
                          @click="handleOpenVideo(record.short_video_url)"
                        >查看</a-button>
                        <a-popconfirm
                          v-if="record.short_video_status === 'ready'"
                          title="确定删除短视频？"
                          @confirm="handleDeleteShortVideo(record.id)"
                        >
                          <a-button type="link" size="small" danger>删除</a-button>
                        </a-popconfirm>
                      </a-space>
                    </template>
                  </template>
                </a-table>
              </a-spin>

              <div style="margin-top: 16px; text-align: center">
                <a-button
                  type="primary"
                  :disabled="shortVideoSelectedIds.length === 0"
                  :loading="shortVideoGenerating"
                  @click="handleGenerateShortVideos"
                >
                  <template #icon><ScissorOutlined /></template>
                  生成短视频（{{ shortVideoSelectedIds.length }} 个节目）
                </a-button>
                <a-button
                  style="margin-left: 12px"
                  :disabled="shortVideoPrograms.length === 0"
                  @click="shortVideoSelectedIds = shortVideoPrograms.filter(p => p.video_url).map(p => p.id)"
                >全选有视频的节目</a-button>
              </div>
            </div>
          </a-tab-pane>

          <a-tab-pane key="sv-list" tab="短视频列表">
            <div class="short-video-panel">
              <div class="panel-toolbar">
                <div>
                  <h3>短视频列表</h3>
                  <p>展示当前活动下所有已生成的短视频。</p>
                </div>
                <a-button @click="fetchShortVideoList" :loading="shortVideoListLoading">
                  <template #icon><ReloadOutlined /></template>
                  刷新
                </a-button>
              </div>

              <a-spin :spinning="shortVideoListLoading">
                <div v-if="shortVideoReadyList.length > 0" class="short-video-grid">
                  <div v-for="item in shortVideoReadyList" :key="item.id" class="short-video-card">
                    <div class="short-video-card-thumb" @click="handleOpenVideo(item.short_video_url)">
                      <PlayCircleOutlined class="short-video-card-icon" />
                      <div class="short-video-card-play"><PlayCircleOutlined /></div>
                    </div>
                    <div class="short-video-card-info">
                      <div class="short-video-card-title">{{ item.name }}</div>
                      <div class="short-video-card-meta">
                        <span>节目号: {{ item.sequence_number }}</span>
                        <a-tag :color="shortVideoStatusColor(item.short_video_status)" size="small">
                          {{ shortVideoStatusText(item.short_video_status) }}
                        </a-tag>
                      </div>
                    </div>
                    <div class="short-video-card-actions">
                      <a-button type="link" size="small" @click="handleOpenVideo(item.short_video_url)">
                        <template #icon><PlayCircleOutlined /></template>
                        播放
                      </a-button>
                      <a-popconfirm title="确定删除短视频？" @confirm="handleDeleteShortVideo(item.id)">
                        <a-button type="link" size="small" danger>
                          <template #icon><DeleteOutlined /></template>
                          删除
                        </a-button>
                      </a-popconfirm>
                    </div>
                  </div>
                </div>
                <a-empty v-else description="暂无已生成的短视频" style="padding: 42px 0" />
              </a-spin>
            </div>
          </a-tab-pane>
        </a-tabs>
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
                  <button
                    v-if="getPrintImageUrl(record)"
                    class="print-photo-thumb-button"
                    type="button"
                    @click="openPrintPhotoPreview(record)"
                  >
                    <img :src="getThumbUrl(getPrintImageUrl(record))" :alt="record.photo_filename || '送印图'" />
                  </button>
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
                <a-space size="small">
                  <a-button type="primary" size="small" @click="handleReprint(record)" :loading="reprintingId === record.id">
                    <template #icon><PrinterOutlined /></template>
                    重打
                  </a-button>
                  <a-popconfirm
                    v-if="canDeletePrintRecord(record)"
                    title="确定删除这条打印记录吗？"
                    ok-text="删除"
                    ok-type="danger"
                    cancel-text="取消"
                    @confirm="handleDeletePrintRecord(record)"
                  >
                    <a-button danger size="small" :loading="deletingPrintRecordId === record.id">
                      <template #icon><DeleteOutlined /></template>
                      删除
                    </a-button>
                  </a-popconfirm>
                </a-space>
              </template>
            </template>
          </a-table>
        </div>
      </a-tab-pane>

      <a-tab-pane key="print-settings" tab="打印设置">
        <ActivityPrintSettings :activity-id="activityId" />
      </a-tab-pane>

      <a-tab-pane key="print-template" tab="打印模版">
        <PrintTemplateManager :activity-id="activityId" />
      </a-tab-pane>

      <a-tab-pane v-if="!isPrintAdmin" key="custom-share" tab="定制分享">
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

      <a-tab-pane v-if="!isPrintAdmin" key="audiences" tab="观众管理">
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

    <a-modal
      v-model:open="printPhotoPreviewOpen"
      title="被打印照片预览"
      width="860px"
      centered
      class="print-photo-preview-modal"
    >
      <div v-if="previewPrintImageUrl" class="print-photo-preview">
        <img :src="getPreviewUrl(previewPrintImageUrl)" :alt="previewPrintRecord?.photo_filename || '送印图'" />
        <div class="print-photo-preview-meta">
          <strong>{{ previewPrintRecord?.photo_filename || `照片 #${previewPrintRecord?.photo_id || '-'}` }}</strong>
          <span>{{ previewPrintRecord?.program_sequence_number ? `节目号 ${previewPrintRecord?.program_sequence_number}` : '未关联节目' }}</span>
        </div>
      </div>
      <a-empty v-else description="暂无可预览送印图" />
      <template #footer>
        <a-space>
          <a-button @click="printPhotoPreviewOpen = false">关闭</a-button>
          <a-button type="primary" :disabled="!previewPrintImageUrl" @click="downloadPrintPhotoOriginal">
            下载送印图
          </a-button>
        </a-space>
      </template>
    </a-modal>

    <input ref="fileInputRef" type="file" accept="video/*" style="display: none" @change="handleFileSelected" />
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  ArrowLeftOutlined,
  DeleteOutlined,
  DesktopOutlined,
  DownOutlined,
  InboxOutlined,
  LoadingOutlined,
  PictureOutlined,
  PlayCircleOutlined,
  PlusOutlined,
  EditOutlined,
  PrinterOutlined,
  QuestionCircleOutlined,
  ReloadOutlined,
  SaveOutlined,
  ScissorOutlined,
  UndoOutlined,
  UploadOutlined,
  UserOutlined,
  VideoCameraOutlined,
  WarningOutlined,
} from '@ant-design/icons-vue'
import { message, Modal } from 'ant-design-vue'
import dayjs from 'dayjs'
import request from '@/api/request'
import { useAuthStore } from '@/stores/auth'
import {
  adminApi,
  audienceApi,
  materialApi,
  photoApi,
  printApi,
  shortVideoApi,
  uploadApi,
  type Activity,
  type AudienceItem,
  type MusicOption,
  type PhotoCategoryInfo,
  type PhotoItemFull,
  type PrintRecordItem,
  type Program,
  type ProgramPhotoMatchCategory,
  type ProgramVideo,
  type ShortVideoAutoConfig,
} from '@/api/admin'
import { getPreviewUrl, getThumbUrl } from '@/utils/image'
import ActivityPhotoSync from './ActivityPhotoSync.vue'
import ActivityPrintSettings from './ActivityPrintSettings.vue'
import PrintTemplateManager from './PrintTemplateManager.vue'

interface PrintTemplate {
  templateName: string
  freePrintLimit: number
  printConfigMode: 'global' | 'activity'
  paperKey: string
  dmPaperSize: string
  paperWidthMm: number
  paperHeightMm: number
  // 画布编辑器配置
  canvasWidth: number
  canvasHeight: number
  photoInitX: number
  photoInitY: number
  photoInitScale: number
  photoMargin: number
}

interface CustomShareConfig {
  coverUrl: string
  title: string
  showInvite: boolean
  description: string
}

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const printAdminWorkspaceTabs = new Set(['print-records', 'print-settings', 'print-template'])
const isPrintAdmin = computed(() => auth.isPrintAdmin())
const defaultWorkspaceTab = computed(() => isPrintAdmin.value ? 'print-records' : 'programs')
const activityId = computed(() => Number(route.params.id))
const activity = ref<Activity | null>(null)
const programs = ref<Program[]>([])
const loading = ref(false)
const programPage = ref(1)
const programPageSize = ref(20)
const saving = ref(false)
const activeWorkspaceTab = ref(defaultWorkspaceTab.value)
const programSearchKeyword = ref('')
const sequenceNumberPad = ref<1 | 2 | 3>(
  ([1, 2, 3].includes(Number(localStorage.getItem('programSequencePad')))
    ? Number(localStorage.getItem('programSequencePad'))
    : 3) as 1 | 2 | 3
)
const sequenceNumberPadOptions = [
  { label: '001', value: 3 },
  { label: '01', value: 2 },
  { label: '1', value: 1 },
]
const showExcelModal = ref(false)
const fileInputRef = ref<HTMLInputElement | null>(null)
const uploadingProgramId = ref<number | null>(null)
const uploadProgress = ref<Record<number, number>>({})
const failedThumbnails = reactive<Record<number, boolean>>({})
const editableData = ref<Record<number, any>>({})
const programNameInputRefs = ref<Record<number, any>>({})
const programNameDrafts = ref<Record<number, string>>({})
const savingProgramNameIds = ref<Record<number, boolean>>({})
const newRows = ref<any[]>([])
let newIdCounter = -1

const printRecords = ref<PrintRecordItem[]>([])
const printRecordsLoading = ref(false)
const printRecordPage = ref(1)
const printRecordPageSize = ref(20)
const printRecordTotal = ref(0)
const reprintingId = ref<number | null>(null)
const deletingPrintRecordId = ref<number | null>(null)
const printPhotoPreviewOpen = ref(false)
const previewPrintRecord = ref<PrintRecordItem | null>(null)
const savingPrintTemplate = ref(false)
const savingCustomShare = ref(false)
const activityPhotos = ref<PhotoItemFull[]>([])
const activityPhotosLoading = ref(false)
const activityPhotoPage = ref(1)
const activityPhotoPageSize = ref(30)
const activityPhotoTotal = ref(0)
const activityPhotoCategories = ref<PhotoCategoryInfo[]>([])
const activityPhotoCategoryId = ref('')
const programPhotoMatchCategories = ref<ProgramPhotoMatchCategory[]>([])
const programPhotoMatchSelectedIds = ref<string[]>([])
const savingProgramPhotoMatchCategories = ref(false)
const printingPhotoId = ref<number | null>(null)
const photoSelectedIds = ref<Set<number>>(new Set())
const photoDeleting = ref(false)
const showMaterialModal = ref(false)

// Short video state
const shortVideoInnerTab = ref('sv-generate')
const shortVideoPrograms = ref<any[]>([])
const shortVideoLoading = ref(false)
const shortVideoGenerating = ref(false)
const shortVideoSelectedIds = ref<number[]>([])
const shortVideoDuration = ref(15)
const shortVideoCutIntensity = ref(2)
const shortVideoDirection = ref('random')
const shortVideoMusicId = ref<number | null>(null)
const musicOptions = ref<MusicOption[]>([])
const shortVideoListLoading = ref(false)
const shortVideoReadyList = ref<any[]>([])
const shortVideoAutoConfig = ref<ShortVideoAutoConfig>({
  enabled: false,
  duration: 15,
  cut_intensity: 2,
  direction: 'random',
  music_id: null,
})
const shortVideoAutoConfigLoading = ref(false)

const shortVideoColumns = [
  { title: '节目号', dataIndex: 'sequence_number', width: 80, align: 'center' as const },
  { title: '节目名称', dataIndex: 'name', width: 200 },
  { title: '短视频状态', dataIndex: 'short_video_status', width: 120, align: 'center' as const },
  { title: '操作', dataIndex: 'actions', width: 120, align: 'center' as const },
]
const audiences = ref<AudienceItem[]>([])
const audienceLoading = ref(false)
const audiencePage = ref(1)
const audiencePageSize = ref(20)
const audienceTotal = ref(0)
let printRecordTimer: number | null = null
let programRefreshTimer: number | null = null

const defaultPrintTemplate: PrintTemplate = {
  templateName: '活动照片贴纸',
  freePrintLimit: 2,
  printConfigMode: 'global',
  paperKey: 'a4',
  dmPaperSize: '9',
  paperWidthMm: 210,
  paperHeightMm: 297,
  // 画布编辑器配置
  canvasWidth: 800,
  canvasHeight: 600,
  photoInitX: 50,
  photoInitY: 50,
  photoInitScale: 100,
  photoMargin: 20,
}

const printTemplate = reactive<PrintTemplate>({ ...defaultPrintTemplate })
const globalPrintSettings = reactive({
  print_free_quota: defaultPrintTemplate.freePrintLimit,
  lankuo_print_config: {} as Record<string, any>,
})

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
    const displayNumber = formatSequenceNumber(program.sequence_number).toLowerCase()
    const programName = (program.name || '').toLowerCase()
    return programNumber.includes(keyword) || displayNumber.includes(keyword) || programName.includes(keyword)
  })
})

const tableData = computed(() => [...newRows.value, ...filteredPrograms.value])
const programPhotoMatchCategoryOptions = computed(() =>
  programPhotoMatchCategories.value.map(category => ({
    label: `${category.category_name || '未分类'} ${category.count}`,
    value: category.category_id,
  })),
)

function handleProgramPageChange(page: number) {
  programPage.value = page
}

function handleProgramPageSizeChange(_current: number, size: number) {
  programPageSize.value = size
  programPage.value = 1
}

const paperSizeMap: Record<string, { width: number; height: number }> = {
  '1': { width: 216, height: 279 },
  '5': { width: 216, height: 356 },
  '9': { width: 210, height: 297 },
  '11': { width: 148, height: 210 },
  '70': { width: 105, height: 148 },
}

const toPositiveNumber = (value: unknown) => {
  const parsed = Number(value)
  return Number.isFinite(parsed) && parsed > 0 ? parsed : 0
}

const effectivePrintPreview = computed(() => {
  if (printTemplate.printConfigMode === 'activity') {
    return {
      source: '活动设置',
      freePrintLimit: printTemplate.freePrintLimit,
      dmPaperSize: printTemplate.dmPaperSize,
      paperWidthMm: printTemplate.paperWidthMm,
      paperHeightMm: printTemplate.paperHeightMm,
    }
  }

  const config = globalPrintSettings.lankuo_print_config || {}
  const dmPaperSize = String(config.dmPaperSize || defaultPrintTemplate.dmPaperSize)
  const preset = paperSizeMap[dmPaperSize]
  let paperWidthMm = preset?.width || defaultPrintTemplate.paperWidthMm
  let paperHeightMm = preset?.height || defaultPrintTemplate.paperHeightMm
  if (dmPaperSize === '0') {
    paperWidthMm = Math.round((toPositiveNumber(config.dmPaperWidth) / 10 || defaultPrintTemplate.paperWidthMm) * 10) / 10
    paperHeightMm = Math.round((toPositiveNumber(config.dmPaperLength) / 10 || defaultPrintTemplate.paperHeightMm) * 10) / 10
  }

  return {
    source: '全局设置',
    freePrintLimit: Number(globalPrintSettings.print_free_quota ?? defaultPrintTemplate.freePrintLimit),
    dmPaperSize,
    paperWidthMm,
    paperHeightMm,
  }
})

const paperPreviewStyle = computed(() => {
  const width = 220
  const paperWidth = effectivePrintPreview.value.paperWidthMm || defaultPrintTemplate.paperWidthMm
  const paperHeight = effectivePrintPreview.value.paperHeightMm || defaultPrintTemplate.paperHeightMm
  const height = Math.min(340, Math.max(190, width * (paperHeight / paperWidth)))
  return {
    width: `${width}px`,
    height: `${height}px`,
    backgroundColor: '#f8fafc',
    border: '1px solid #e5e7eb',
  }
})

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
]

const editableColumns = [
  { title: '节目号', dataIndex: 'sequence_number', key: 'sequence_number', width: 90, align: 'center' as const },
  { title: '节目名称', dataIndex: 'name', key: 'name', width: 280, align: 'center' as const },
  { title: '录制时间', dataIndex: 'time_range', key: 'time_range', width: 230, align: 'center' as const },
  { title: '时长', dataIndex: 'duration', key: 'duration', width: 90, align: 'center' as const },
  { title: '视频', dataIndex: 'video_status', key: 'video_status', width: 230, align: 'center' as const },
  { title: '短视频', dataIndex: 'short_video', key: 'short_video', width: 140, align: 'center' as const },
  { title: '照片', dataIndex: 'photo_count', key: 'photo_count', width: 80, align: 'center' as const },
  { title: '就绪', dataIndex: 'ready_status', key: 'ready_status', width: 90, align: 'center' as const },
  { title: '操作', key: 'actions', width: 180, align: 'center' as const },
]

const printRecordColumns = [
  { title: '照片', key: 'photo', width: 280 },
  { title: '用户', key: 'user', width: 180 },
  { title: '打印任务', key: 'job', width: 180 },
  { title: '状态', key: 'status', width: 140 },
  { title: '提交时间', key: 'created_at', width: 180 },
  { title: '操作', key: 'actions', width: 180, align: 'center' as const },
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

const formatTime = (time: string) => dayjs(time).format('YYYY-MM-DD HH:mm:ss')
const formatNullableTime = (time?: string | null) => time ? dayjs(time).format('YYYY-MM-DD HH:mm:ss') : '--'
const formatSequenceNumber = (value?: number | null) => String(value ?? '').padStart(sequenceNumberPad.value, '0')

const formatDuration = (seconds: number) => {
  const minutes = Math.floor(seconds / 60)
  const rest = Math.round(seconds % 60)
  return `${minutes}:${String(rest).padStart(2, '0')}`
}

const videoStatusColor = (status: string) => ({ none: 'default', uploading: 'processing', ready: 'success' }[status] || 'default')
const videoStatusText = (status: string) => ({ none: '未上传', uploading: '上传中', ready: '已就绪' }[status] || status)
const getProgramVideos = (record: Program) => record.videos ?? []

const formatRecordingTime = (video: ProgramVideo) => {
  if (video.recorded_at) return formatTime(video.recorded_at)
  return formatTime(video.created_at)
}

watch(sequenceNumberPad, value => {
  localStorage.setItem('programSequencePad', String(value))
})

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

const getPrintImageUrl = (record?: PrintRecordItem | null) => record?.print_image_url || record?.photo_url || ''
const previewPrintImageUrl = computed(() => getPrintImageUrl(previewPrintRecord.value))

const canDeletePrintRecord = (record: PrintRecordItem) => ['failed', 'queued'].includes(record.status)

const maskOpenid = (openid?: string | null) => {
  if (!openid) return '-'
  return openid.length <= 6 ? openid : openid.slice(-6)
}

const fetchActivity = async () => {
  const res = await adminApi.getActivity(activityId.value)
  activity.value = res.data
}

const fetchProgramPhotoMatchCategories = async () => {
  try {
    const res = await adminApi.getPhotoMatchCategories(activityId.value)
    programPhotoMatchCategories.value = res.data.categories || []
    programPhotoMatchSelectedIds.value = res.data.selected_category_ids || []
  } catch {
    programPhotoMatchCategories.value = []
    programPhotoMatchSelectedIds.value = []
  }
}

const fetchData = async () => {
  loading.value = true
  try {
    if (isPrintAdmin.value) {
      await fetchActivity()
      return
    }
    const [actRes, progRes] = await Promise.all([
      adminApi.getActivity(activityId.value),
      adminApi.listPrograms(activityId.value),
      fetchProgramPhotoMatchCategories(),
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

const refreshProgramsSilently = async () => {
  if (activeWorkspaceTab.value !== 'programs') return
  if (Object.keys(editableData.value).length > 0 || newRows.value.length > 0) return
  try {
    const res = await adminApi.listPrograms(activityId.value)
    programs.value = res.data
    Object.keys(failedThumbnails).forEach(key => {
      const id = Number(key)
      if (!programs.value.some(program => program.id === id)) {
        delete failedThumbnails[id]
      }
    })
  } catch {
    // keep live refresh quiet; manual refresh still reports errors
  }
}

const handleProgramPhotoMatchCategoryChange = async (values: any[]) => {
  savingProgramPhotoMatchCategories.value = true
  try {
    const categoryIds = values.map(value => String(value))
    const res = await adminApi.updatePhotoMatchCategories(activityId.value, categoryIds)
    programPhotoMatchCategories.value = res.data.categories || []
    programPhotoMatchSelectedIds.value = res.data.selected_category_ids || []
    const progRes = await adminApi.listPrograms(activityId.value)
    programs.value = progRes.data
    message.success('照片关联分类已更新')
  } catch (error: any) {
    message.error(error?.response?.data?.detail || '更新照片关联分类失败')
    await fetchProgramPhotoMatchCategories()
  } finally {
    savingProgramPhotoMatchCategories.value = false
  }
}

const startProgramRefreshPolling = () => {
  stopProgramRefreshPolling()
  programRefreshTimer = window.setInterval(refreshProgramsSilently, 3000)
}

const stopProgramRefreshPolling = () => {
  if (programRefreshTimer) {
    window.clearInterval(programRefreshTimer)
    programRefreshTimer = null
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
    const res = await photoApi.getActivityPhotos(
      activityId.value,
      activityPhotoPage.value,
      activityPhotoPageSize.value,
      activityPhotoCategoryId.value || undefined,
    )
    activityPhotos.value = res.data.photos
    activityPhotoCategories.value = res.data.categories || []
    activityPhotoTotal.value = res.data.total
  } catch {
    message.error('加载照片失败')
  } finally {
    activityPhotosLoading.value = false
  }
}

const handleActivityPhotoCategoryChange = () => {
  activityPhotoPage.value = 1
  photoSelectedIds.value = new Set()
  fetchActivityPhotos()
}

function togglePhotoSelect(photoId: number, checked: boolean) {
  const newSet = new Set(photoSelectedIds.value)
  if (checked) {
    newSet.add(photoId)
  } else {
    newSet.delete(photoId)
  }
  photoSelectedIds.value = newSet
}

function handleDeleteSelectedPhotos() {
  const ids = Array.from(photoSelectedIds.value)
  if (ids.length === 0) return
  Modal.confirm({
    title: '确认删除',
    content: `确定要删除选中的 ${ids.length} 张照片吗？此操作不可恢复。`,
    okText: '确认删除',
    okType: 'danger',
    cancelText: '取消',
    onOk: async () => {
      photoDeleting.value = true
      try {
        await photoApi.batchDeletePhotos(ids)
        message.success(`已删除 ${ids.length} 张照片`)
        photoSelectedIds.value = new Set()
        await fetchActivityPhotos()
      } catch {
        message.error('删除照片失败')
      } finally {
        photoDeleting.value = false
      }
    },
  })
}

// ── Short video functions ──────────────────────────────────────────

const fetchShortVideoStatus = async () => {
  shortVideoLoading.value = true
  try {
    const [statusRes, musicRes] = await Promise.all([
      shortVideoApi.getPrograms(activityId.value),
      shortVideoApi.getMusicOptions(),
    ])
    shortVideoPrograms.value = statusRes.data.items
    musicOptions.value = musicRes.data
  } catch {
    message.error('加载短视频状态失败')
  } finally {
    shortVideoLoading.value = false
  }
}

const onShortVideoSelectChange = (selectedKeys: number[]) => {
  shortVideoSelectedIds.value = selectedKeys
}

const shortVideoStatusColor = (status: string) => ({
  none: 'default', generating: 'processing', ready: 'success', failed: 'error',
}[status] || 'default')

const shortVideoStatusText = (status: string) => ({
  none: '未生成', generating: '生成中', ready: '已生成', failed: '失败',
}[status] || status)

const handleGenerateShortVideos = async () => {
  if (shortVideoSelectedIds.value.length === 0) return
  Modal.confirm({
    title: '确认生成短视频',
    content: `将为选中的 ${shortVideoSelectedIds.value.length} 个节目生成短视频（${shortVideoDuration.value}秒），这可能需要几分钟时间。`,
    okText: '开始生成',
    okType: 'primary',
    cancelText: '取消',
    onOk: async () => {
      shortVideoGenerating.value = true
      try {
        const res = await shortVideoApi.generate({
          program_ids: shortVideoSelectedIds.value,
          duration: shortVideoDuration.value,
          cut_intensity: shortVideoCutIntensity.value,
          direction: shortVideoDirection.value,
          music_id: shortVideoMusicId.value,
        })
        message.success(`已开始生成 ${res.data.count} 个短视频${res.data.skipped > 0 ? `，跳过 ${res.data.skipped} 个无视频节目` : ''}`)
        shortVideoSelectedIds.value = []
        setTimeout(() => fetchShortVideoStatus(), 5000)

        // Sync auto-config with current generation settings
        if (shortVideoAutoConfig.value.enabled) {
          await saveAutoConfig()
        }
      } catch {
        message.error('生成短视频失败')
      } finally {
        shortVideoGenerating.value = false
      }
    },
  })
}

const fetchShortVideoList = async () => {
  shortVideoListLoading.value = true
  try {
    const res = await shortVideoApi.getPrograms(activityId.value)
    shortVideoReadyList.value = res.data.items.filter(
      (p: any) => p.short_video_status === 'ready' || p.short_video_status === 'generating' || p.short_video_status === 'failed'
    )
  } catch {
    message.error('加载短视频列表失败')
  } finally {
    shortVideoListLoading.value = false
  }
}

const handleShortVideoInnerChange = (key: string) => {
  if (key === 'sv-list') {
    fetchShortVideoList()
  }
}

const loadAutoConfig = async () => {
  try {
    const res = await shortVideoApi.getAutoConfig(activityId.value)
    shortVideoAutoConfig.value = res.data
    // Sync generation form with auto-config values
    shortVideoDuration.value = res.data.duration
    shortVideoCutIntensity.value = res.data.cut_intensity
    shortVideoDirection.value = res.data.direction
    shortVideoMusicId.value = res.data.music_id
  } catch {
    // use defaults
  }
}

const saveAutoConfig = async () => {
  shortVideoAutoConfigLoading.value = true
  try {
    const config: ShortVideoAutoConfig = {
      enabled: shortVideoAutoConfig.value.enabled,
      duration: shortVideoDuration.value,
      cut_intensity: shortVideoCutIntensity.value,
      direction: shortVideoDirection.value,
      music_id: shortVideoMusicId.value,
    }
    const res = await shortVideoApi.updateAutoConfig(activityId.value, config)
    shortVideoAutoConfig.value = res.data
  } catch {
    message.error('保存自动生成配置失败')
  } finally {
    shortVideoAutoConfigLoading.value = false
  }
}

const handleToggleAutoGenerate = async (checked: boolean) => {
  const prevEnabled = shortVideoAutoConfig.value.enabled
  shortVideoAutoConfig.value.enabled = checked
  try {
    await saveAutoConfig()
    message.success(checked ? '已开启自动生成短视频' : '已关闭自动生成短视频')
  } catch {
    shortVideoAutoConfig.value.enabled = prevEnabled
  }
}

const loadPrintTemplate = async () => {
  await loadGlobalPrintSettings()
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

const loadGlobalPrintSettings = async () => {
  try {
    const settings = (await materialApi.getPrintSettings() as any)?.data || {}
    globalPrintSettings.print_free_quota = Number(settings.print_free_quota ?? defaultPrintTemplate.freePrintLimit)
    globalPrintSettings.lankuo_print_config = settings.lankuo_print_config || {}
  } catch {
    globalPrintSettings.print_free_quota = defaultPrintTemplate.freePrintLimit
    globalPrintSettings.lankuo_print_config = {}
  }
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

const handlePrintConfigModeChange = (checked: boolean | string | number) => {
  printTemplate.printConfigMode = checked ? 'activity' : 'global'
}

const applyPaperPreset = (key: string) => {
  const preset = paperPresets[key]
  if (!preset) return
  printTemplate.dmPaperSize = preset.dmPaperSize
  printTemplate.paperWidthMm = preset.width
  printTemplate.paperHeightMm = preset.height
}

const handleWorkspaceChange = (key: string) => {
  if (isPrintAdmin.value && !printAdminWorkspaceTabs.has(key)) {
    activeWorkspaceTab.value = 'print-records'
    fetchPrintRecords()
    startPrintRecordPolling()
    return
  }
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
  if (key === 'short-video') {
    fetchShortVideoStatus()
    loadAutoConfig()
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

const openPrintPhotoPreview = (record: PrintRecordItem) => {
  previewPrintRecord.value = record
  printPhotoPreviewOpen.value = true
}

const downloadPrintPhotoOriginal = () => {
  const url = previewPrintImageUrl.value
  if (!url) return
  const link = document.createElement('a')
  link.href = url
  link.download = previewPrintRecord.value?.photo_filename || `print-image-${previewPrintRecord.value?.photo_id || 'sent'}`
  link.target = '_blank'
  link.rel = 'noopener'
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
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

const handleDeletePrintRecord = async (record: PrintRecordItem) => {
  if (!canDeletePrintRecord(record)) {
    message.warning('只有失败或排队中的打印记录可以删除')
    return
  }
  deletingPrintRecordId.value = record.id
  try {
    await printApi.deleteRecord(record.id)
    message.success('已删除打印记录')
    if (printRecords.value.length === 1 && printRecordPage.value > 1) {
      printRecordPage.value -= 1
    }
    await fetchPrintRecords()
  } catch (error: any) {
    message.error(error?.response?.data?.detail || '删除打印记录失败')
  } finally {
    deletingPrintRecordId.value = null
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
    start_time: record.start_time ? new Date(record.start_time) : null,
  }
}

const setProgramNameInputRef = (id: number, el: any) => {
  if (el) {
    programNameInputRefs.value[id] = el
  } else {
    delete programNameInputRefs.value[id]
  }
}

const focusProgramNameInput = async (id: number) => {
  await nextTick()
  programNameInputRefs.value[id]?.focus?.()
}

const handleEditProgramName = (record: Program) => {
  programNameDrafts.value[record.id] = record.name
  focusProgramNameInput(record.id)
}

const getProgramNameValue = (record: any) => {
  if (record._isNew) return record.name
  if (editableData.value[record.id]) return editableData.value[record.id].name
  return programNameDrafts.value[record.id] ?? record.name
}

const setProgramNameValue = (record: any, value: string) => {
  if (record._isNew) {
    record.name = value
  } else if (editableData.value[record.id]) {
    editableData.value[record.id].name = value
  } else {
    programNameDrafts.value[record.id] = value
  }
}

const handleProgramNameEnter = (record: any) => {
  if (record._isNew) {
    handleSaveNew(record)
  } else if (editableData.value[record.id]) {
    handleSaveInline(record)
  } else {
    handleSaveProgramName(record)
  }
}

const handleProgramNameEsc = (record: any) => {
  if (record._isNew) {
    handleCancelNew(record.id)
  } else if (editableData.value[record.id]) {
    handleCancelInline(record.id)
  } else {
    delete programNameDrafts.value[record.id]
  }
}

const handleProgramNameBlur = (record: any) => {
  if (record._isNew || editableData.value[record.id] || programNameDrafts.value[record.id] === undefined) return
  handleSaveProgramName(record)
}

const handleCancelInline = (id: number) => {
  delete editableData.value[id]
}

const handleSaveProgramName = async (record: Program) => {
  if (savingProgramNameIds.value[record.id]) return

  const nextName = programNameDrafts.value[record.id]?.trim()
  if (!nextName) {
    message.warning('节目名称不能为空')
    focusProgramNameInput(record.id)
    return
  }
  if (nextName === record.name) {
    delete programNameDrafts.value[record.id]
    return
  }

  savingProgramNameIds.value[record.id] = true
  try {
    await adminApi.updateProgram(record.id, { name: nextName })
    record.name = nextName
    delete programNameDrafts.value[record.id]
    message.success('保存成功')
  } catch {
    message.error('保存失败')
  } finally {
    savingProgramNameIds.value[record.id] = false
  }
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

const handleOpenVideo = (url?: string | null) => {
  if (!url) {
    message.warning('这条录制没有可打开的视频链接')
    return
  }
  window.open(url, '_blank')
}

const handleDeleteRecording = async (videoId: number) => {
  try {
    await uploadApi.deleteDesktopVideo(videoId)
    message.success('录制视频已删除')
    fetchData()
  } catch {
    message.error('删除录制视频失败')
  }
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

const handleGenerateSingleShortVideo = async (record: Program) => {
  if (!record.video_url && getProgramVideos(record).length === 0) {
    message.warning('该节目没有原视频，无法生成短视频')
    return
  }
  try {
    await shortVideoApi.generate({
      program_ids: [record.id],
      duration: shortVideoAutoConfig.value.duration,
      cut_intensity: shortVideoAutoConfig.value.cut_intensity,
      direction: shortVideoAutoConfig.value.direction,
      music_id: shortVideoAutoConfig.value.music_id,
    })
    message.success(`已开始为节目「${record.name}」生成短视频`)
    record.short_video_status = 'generating'
    setTimeout(() => fetchData(), 5000)
  } catch (e: any) {
    const detail = e.response?.data?.detail || '生成短视频失败'
    message.error(detail)
  }
}

const handleDeleteShortVideo = async (programId: number) => {
  try {
    await shortVideoApi.delete(programId)
    message.success('短视频已删除')
    fetchData()
  } catch {
    message.error('删除短视频失败')
  }
}

const handleOpenLobbyPlayer = () => {
  const url = `${window.location.origin}/lobby/${activityId.value}`
  window.open(url, '_blank', 'noopener,noreferrer')
}

const handleSaveShortVideoConfig = async () => {
  shortVideoAutoConfigLoading.value = true
  try {
    const config: ShortVideoAutoConfig = {
      enabled: shortVideoAutoConfig.value.enabled,
      duration: shortVideoDuration.value,
      cut_intensity: shortVideoCutIntensity.value,
      direction: shortVideoDirection.value,
      music_id: shortVideoMusicId.value,
    }
    const res = await shortVideoApi.updateAutoConfig(activityId.value, config)
    shortVideoAutoConfig.value = res.data
    message.success('短视频配置已保存')
  } catch {
    message.error('保存短视频配置失败')
  } finally {
    shortVideoAutoConfigLoading.value = false
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

const handleToggleActivityReadyMode = async (checked: boolean) => {
  if (!activity.value) return
  try {
    const newMode = checked ? 'auto' : 'manual'
    const res = await adminApi.updateActivity(activityId.value, { ready_mode: newMode })
    activity.value = res.data
    // Refresh programs to reflect cascaded ready_mode changes
    await fetchData()
    message.success(checked ? '已切换为自动就绪模式' : '已切换为手动就绪模式')
  } catch {
    message.error('切换就绪模式失败')
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
  if (isPrintAdmin.value) {
    activeWorkspaceTab.value = 'print-records'
    await fetchPrintRecords()
    startPrintRecordPolling()
    return
  }
  await loadAutoConfig()
  await loadPrintTemplate()
  startProgramRefreshPolling()
})

onUnmounted(() => {
  stopProgramRefreshPolling()
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

.ready-mode-switch {
  display: flex;
  align-items: center;
  gap: 8px;
}

.program-photo-category-picker {
  display: flex;
  align-items: center;
  gap: 8px;
  max-width: 520px;
  padding-right: 4px;
  overflow-x: auto;
}

.program-photo-category-picker :deep(.ant-checkbox-group) {
  display: flex;
  flex-wrap: nowrap;
  gap: 8px;
  white-space: nowrap;
}

.program-photo-category-picker :deep(.ant-checkbox-wrapper) {
  margin-inline-start: 0;
  white-space: nowrap;
}

.ready-mode-label {
  font-size: 14px;
  color: #595959;
  white-space: nowrap;
}

.workspace-tabs :deep(.ant-tabs-nav) {
  margin-bottom: 18px;
}

.program-tab-search {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 520px;
  max-width: 48vw;
}

.sequence-number-text {
  display: inline-block;
  min-width: 34px;
  color: #111827;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
  text-align: center;
}

.muted-inline {
  margin-left: 8px;
  font-size: 12px;
  color: #8c8c8c;
}

.program-name-cell {
  display: flex;
  align-items: center;
  justify-content: center;
  width: min(240px, 100%);
  min-height: 32px;
  margin: 0 auto;
}

.program-name-text,
.program-name-editor {
  width: 100%;
  height: 28px;
  box-sizing: border-box;
}

.program-name-text {
  display: block;
  padding: 2px 6px;
  overflow: hidden;
  border-radius: 4px;
  color: #111827;
  cursor: text;
  line-height: 24px;
  text-align: center;
  text-overflow: ellipsis;
  transition: background-color 0.18s, color 0.18s;
  white-space: nowrap;
}

.program-name-text:hover {
  background-color: #f0f7ff;
  color: #1677ff;
}

.program-name-editor {
  text-align: center;
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

.video-stack-cell {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
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

.sv-cell {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 36px;
}

.sv-thumb {
  width: 64px;
  height: 36px;
  border-radius: 4px;
  overflow: hidden;
  position: relative;
  cursor: pointer;
  background: linear-gradient(135deg, #722ed1 0%, #b37feb 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  transition: box-shadow 0.2s;
}

.sv-thumb:hover {
  box-shadow: 0 2px 8px rgba(114, 46, 209, 0.35);
}

.sv-thumb-icon {
  font-size: 18px;
  color: rgba(255, 255, 255, 0.9);
}

.sv-thumb-play {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0);
  transition: background 0.2s;
}

.sv-thumb-play :deep(.anticon) {
  font-size: 18px;
  color: #fff;
  opacity: 0;
  transition: opacity 0.2s;
  filter: drop-shadow(0 1px 3px rgba(0, 0, 0, 0.5));
}

.sv-thumb:hover .sv-thumb-play {
  background: rgba(0, 0, 0, 0.35);
}

.sv-thumb:hover .sv-thumb-play :deep(.anticon) {
  opacity: 1;
}

.sv-status {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 5px;
  padding: 3px 10px;
  border-radius: 4px;
  font-size: 12px;
  line-height: 1;
  white-space: nowrap;
}

.sv-status.generating {
  color: #1677ff;
  background: #e6f4ff;
  border: 1px solid #91caff;
}

.sv-status.failed {
  color: #cf1322;
  background: #fff1f0;
  border: 1px solid #ffa39e;
  cursor: default;
}

.sv-status.none {
  color: #8c8c8c;
  background: #fafafa;
  border: 1px solid #d9d9d9;
}

.sv-status.clickable {
  cursor: pointer;
  transition: all 0.2s;
}

.sv-status.clickable:hover {
  color: #1677ff;
  background: #e6f4ff;
  border-color: #91caff;
}

.recording-count-btn {
  min-width: 70px;
  padding: 0 8px;
  color: #0f766e;
  border-color: #99f6e4;
  background: #f0fdfa;
  font-size: 12px;
}

.recording-list {
  width: 360px;
  max-height: 320px;
  overflow-y: auto;
}

.recording-item {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 32px;
  align-items: center;
  gap: 8px;
  padding: 8px 0;
  border-bottom: 1px solid #eef2f7;
}

.recording-item:last-child {
  border-bottom: 0;
}

.recording-main {
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: 3px;
  padding: 0;
  border: 0;
  background: transparent;
  color: #111827;
  text-align: left;
  cursor: pointer;
}

.recording-main strong {
  color: #0f766e;
  font-size: 12px;
  font-weight: 700;
}

.recording-main span {
  overflow: hidden;
  color: #64748b;
  font-size: 12px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.activity-photo-panel,
.short-video-panel,
.print-records-panel,
.print-template-panel {
  background: #f7f8fb;
  border: 1px solid #edf0f5;
  border-radius: 8px;
  padding: 18px;
}

/* ── 打印模版新版样式 ── */
.pt-panel {
  min-height: 100%;
}

.pt-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  background: #fff;
  border-radius: 12px;
  margin-bottom: 16px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.04);
}

.pt-header-left {}

.pt-header-title {
  font-size: 18px;
  font-weight: 700;
  color: #1f2937;
}

.pt-header-desc {
  font-size: 13px;
  color: #9ca3af;
  margin-top: 2px;
}

.pt-header-right {
  display: flex;
  gap: 8px;
}

.pt-body {
  display: grid;
  grid-template-columns: 1fr 320px;
  gap: 16px;
  align-items: start;
}

.pt-config {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.pt-section {
  background: #fff;
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 1px 3px rgba(0,0,0,0.04);
}

.pt-section-head {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 18px;
  border-bottom: 1px solid #f3f4f6;
}

.pt-section-icon {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.pt-section-title {
  font-size: 15px;
  font-weight: 600;
  color: #1f2937;
}

.pt-section-desc {
  font-size: 12px;
  color: #9ca3af;
  margin-top: 1px;
}

.pt-section-body {
  padding: 14px 18px 16px;
}

.pt-mode-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 12px 14px;
  margin-bottom: 14px;
  background: #f8fafc;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
}

.pt-mode-title {
  font-size: 13px;
  font-weight: 600;
  color: #111827;
}

.pt-mode-desc {
  margin-top: 3px;
  font-size: 12px;
  color: #6b7280;
}

.pt-field-row {
  display: flex;
  gap: 12px;
  margin-bottom: 12px;
}

.pt-field-row:last-child {
  margin-bottom: 0;
}

.pt-field label {
  display: block;
  font-size: 12px;
  font-weight: 500;
  color: #6b7280;
  margin-bottom: 4px;
}

.pt-slider-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.pt-slider-row .ant-slider {
  flex: 1;
}

.pt-slider-val {
  font-size: 12px;
  color: #6b7280;
  min-width: 40px;
  text-align: right;
  font-variant-numeric: tabular-nums;
}

.pt-switch-row {
  display: flex;
  align-items: center;
  gap: 10px;
}

.pt-color-input {
  width: 32px;
  height: 28px;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  padding: 2px;
  cursor: pointer;
  background: #fff;
}

.pt-color-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.pt-color-hex {
  font-size: 12px;
  color: #6b7280;
  font-family: monospace;
}

.pt-divider {
  height: 1px;
  background: #f3f4f6;
  margin: 12px 0;
}

.pt-canvas-hint {
  font-size: 11px;
  color: #9ca3af;
  background: #f9fafb;
  padding: 6px 10px;
  border-radius: 6px;
  margin-bottom: 12px;
  line-height: 1.5;
}

/* 右侧预览 */
.pt-preview {
  position: relative;
}

.pt-preview-sticky {
  position: sticky;
  top: 16px;
  background: #fff;
  border-radius: 12px;
  padding: 18px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.04);
}

.pt-preview-title {
  font-size: 14px;
  font-weight: 600;
  color: #1f2937;
  margin-bottom: 14px;
  text-align: center;
}

.pt-preview-canvas {
  margin-bottom: 16px;
}

.pt-preview-tags {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.pt-tag {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 12px;
  color: #4b5563;
  padding: 6px 10px;
  background: #f9fafb;
  border-radius: 6px;
}

.pt-tag-label {
  font-weight: 500;
  color: #9ca3af;
  margin-right: 8px;
}

@media (max-width: 900px) {
  .pt-body {
    grid-template-columns: 1fr;
  }
  .pt-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 12px;
  }
}

.sv-auto-config-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 16px;
  padding: 12px 16px;
  background: #fafafa;
  border: 1px solid #f0f0f0;
  border-radius: 8px;
}

.sv-auto-config-left {
  display: flex;
  align-items: center;
  gap: 10px;
}

.sv-auto-config-label {
  font-size: 14px;
  font-weight: 500;
  color: #1f2937;
}

.sv-auto-config-summary {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}

.short-video-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 14px;
}

.short-video-card {
  border: 1px solid #eef1f5;
  border-radius: 8px;
  background: #fff;
  overflow: hidden;
  transition: box-shadow 0.2s;
}

.short-video-card:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
}

.short-video-card-thumb {
  position: relative;
  aspect-ratio: 16 / 9;
  background: linear-gradient(135deg, #722ed1 0%, #1890ff 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  overflow: hidden;
}

.short-video-card-icon {
  font-size: 36px;
  color: rgba(255, 255, 255, 0.85);
}

.short-video-card-play {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0);
  transition: background 0.2s;
}

.short-video-card-play :deep(.anticon) {
  font-size: 28px;
  color: #fff;
  opacity: 0;
  transition: opacity 0.2s;
  filter: drop-shadow(0 1px 3px rgba(0, 0, 0, 0.5));
}

.short-video-card-thumb:hover .short-video-card-play {
  background: rgba(0, 0, 0, 0.3);
}

.short-video-card-thumb:hover .short-video-card-play :deep(.anticon) {
  opacity: 1;
}

.short-video-card-info {
  padding: 10px 12px;
}

.short-video-card-title {
  font-size: 14px;
  font-weight: 600;
  color: #1f2937;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.short-video-card-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 6px;
  font-size: 12px;
  color: #6b7280;
}

.short-video-card-actions {
  display: flex;
  justify-content: flex-end;
  gap: 4px;
  padding: 4px 8px 8px;
  border-top: 1px solid #f5f5f5;
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

.print-photo-thumb-button {
  width: 64px;
  height: 64px;
  padding: 0;
  flex: none;
  overflow: hidden;
  cursor: zoom-in;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  background: #eef1f6;
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

.print-photo-preview {
  display: grid;
  gap: 14px;
}

.print-photo-preview img {
  width: 100%;
  max-height: 68vh;
  object-fit: contain;
  border-radius: 8px;
  background: #f5f7fb;
}

.print-photo-preview-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  color: #4b5563;
}

.print-photo-preview-meta strong {
  color: #111827;
}

.record-error {
  margin-top: 4px;
  color: #cf1322;
  font-size: 12px;
}

.photo-category-filter {
  margin: 0 0 14px;
  padding: 10px 12px;
  border: 1px solid #edf0f5;
  border-radius: 8px;
  background: #fafbfc;
  overflow-x: auto;
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
  position: relative;
  transition: border-color 0.2s;
}

.activity-photo-card-selected {
  border-color: #1890ff;
  box-shadow: 0 0 0 2px rgba(24, 144, 255, 0.2);
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

.photo-checkbox {
  position: absolute;
  top: 4px;
  left: 4px;
  z-index: 2;
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

.activity-photo-category {
  margin: 6px 0 0;
  max-width: 100%;
}

.photo-pagination {
  display: flex;
  justify-content: center;
  padding-top: 18px;
}

.template-layout {
  display: grid;
  grid-template-columns: 1fr;
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

  .share-cover-block {
    grid-template-columns: 1fr;
  }
}
</style>
