import request from './request'

export interface Activity {
  id: number
  name: string
  description: string | null
  event_date: string | null
  start_time: string | null
  end_time: string | null
  venue: string | null
  status: string
  wotu_album_id: string | null
  wotu_album_url: string | null
  storage_path_prefix: string | null
  cover_image: string | null
  ready_mode: string
  program_count: number
  ready_program_count: number
  created_at: string
  updated_at: string
}

export interface PublicActivity {
  id: number
  name: string
  description: string | null
  event_date: string | null
  start_time?: string | null
  end_time?: string | null
  venue: string | null
  cover_image: string | null
  program_count: number
  photo_count: number
  share_config?: Record<string, any>
}

export interface PublicProgramSearchItem {
  id: number
  name: string
  sequence_number: number
  access_token: string
  photo_count: number
  video_status: string
  ready_status: string
  recorded_at: string | null
  program_url?: string | null
}

export interface WechatProfile {
  appid?: string | null
  openid: string
  unionid?: string | null
  nickname?: string | null
  avatar_url?: string | null
  province?: string | null
  city?: string | null
  country?: string | null
}

export interface AdminRole {
  id: number
  name: string
  code: string
  description: string | null
  permissions: string[]
  is_system: boolean
  created_at?: string | null
}

export interface AdminPermission {
  key: string
  label: string
}

export interface AdminUserAssignment {
  id: number
  role_id: number
  role_name: string
  role_code: string
  permissions: string[]
  activity_id: number | null
  activity_name: string | null
}

export interface AdminUser {
  id: number
  openid: string
  source: 'self' | 'wechat' | string
  username: string | null
  unionid: string | null
  nickname: string | null
  avatar_url: string | null
  phone: string | null
  province: string | null
  city: string | null
  country: string | null
  is_blacklisted: boolean
  is_deleted: boolean
  last_seen_at: string | null
  created_at: string | null
  role_codes: string[]
  permissions: string[]
  activity_ids: number[]
  assignments: AdminUserAssignment[]
}

export interface AdminUserResponse {
  items: AdminUser[]
  total: number
  page: number
  page_size: number
}

export interface Program {
  id: number
  access_token: string
  activity_id: number
  name: string
  sequence_number: number
  start_time: string | null
  end_time: string | null
  duration: number | null
  video_url: string | null
  video_thumbnail_url: string | null
  video_status: string
  short_video_url: string | null
  short_video_status: string
  videos?: ProgramVideo[]
  photo_count: number
  ready_mode: string
  ready_status: string
  created_at: string
  updated_at: string
}

export interface ProgramVideo {
  id: number
  filename: string
  file_size: number | null
  duration: number | null
  recorded_at: string | null
  storage_url: string | null
  storage_provider: string
  upload_type: string
  upload_source: string | null
  status: string
  created_at: string
  updated_at: string
}

export interface ProgramListItem {
  id: number
  name: string
  sequence_number: number
  video_status: string
  photo_count: number
  ready_status: string
}

export interface PhotoItem {
  id: number
  storage_url: string | null
  wotu_url?: string | null
  shoot_time: string | null
  width: number | null
  height: number | null
}

// Admin APIs
export const adminApi = {
  login: (username: string, password: string) =>
    request.post('/admin/login', { username, password }),

  register: (data: { username: string; password: string; nickname?: string }) =>
    request.post('/admin/register', data),

  changePassword: (oldPassword: string, newPassword: string) =>
    request.put('/admin/password', { old_password: oldPassword, new_password: newPassword }),

  listActivities: () =>
    request.get<Activity[]>('/admin/activities'),

  getActivity: (id: number) =>
    request.get<Activity>(`/admin/activities/${id}`),

  createActivity: (data: Partial<Activity>) =>
    request.post<Activity>('/admin/activities', data),

  updateActivity: (id: number, data: Partial<Activity>) =>
    request.put<Activity>(`/admin/activities/${id}`, data),

  deleteActivity: (id: number) =>
    request.delete(`/admin/activities/${id}`),

  uploadActivityCover: (file: File) => {
    const formData = new FormData()
    formData.append('file', file)
    return request.post<{ url: string; filename: string }>('/admin/activities/cover/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },

  listPrograms: (activityId: number) =>
    request.get<Program[]>(`/admin/activities/${activityId}/programs`),

  createProgram: (activityId: number, data: Partial<Program>) =>
    request.post<Program>(`/admin/activities/${activityId}/programs`, data),

  updateProgram: (id: number, data: Partial<Program>) =>
    request.put<Program>(`/admin/programs/${id}`, data),

  deleteProgram: (id: number) =>
    request.delete(`/admin/programs/${id}`),

  batchCreatePrograms: (activityId: number, programs: Partial<Program>[]) =>
    request.post<Program[]>(`/admin/activities/${activityId}/programs/batch`, { programs }),

  listPermissions: () =>
    request.get<AdminPermission[]>('/admin/permissions'),

  listRoles: () =>
    request.get<AdminRole[]>('/admin/roles'),

  createRole: (data: { name: string; code: string; description?: string | null; permissions: string[] }) =>
    request.post<AdminRole>('/admin/roles', data),

  updateRole: (roleId: number, data: { name: string; code: string; description?: string | null; permissions: string[] }) =>
    request.put<AdminRole>(`/admin/roles/${roleId}`, data),

  deleteRole: (roleId: number) =>
    request.delete(`/admin/roles/${roleId}`),

  listUsers: (keyword?: string, page = 1, pageSize = 20, source?: 'self' | 'wechat') =>
    request.get<AdminUserResponse>('/admin/users', {
      params: { keyword, page, page_size: pageSize, source },
    }),

  updateUserBlacklist: (userId: number, blacklisted: boolean) =>
    request.put<AdminUser>(`/admin/users/${userId}/blacklist`, { blacklisted }),

  deleteUser: (userId: number) =>
    request.delete(`/admin/users/${userId}`),

  updateUserRoles: (userId: number, assignments: { role_id: number; activity_ids?: number[] }[]) =>
    request.put<AdminUser>(`/admin/users/${userId}/roles`, { assignments }),
}

// Public APIs
export const publicApi = {
  getProgram: (token: string) =>
    request.get<Program>(`/public/programs/${token}`),

  listPhotos: (token: string, page = 1, pageSize = 30) =>
    request.get<PhotoItem[]>(`/public/programs/${token}/photos`, {
      params: { page, page_size: pageSize },
    }),

  printPhoto: (token: string, photoId: number, copies = 1, profile?: WechatProfile | null) =>
    request.post(`/public/programs/${token}/photos/${photoId}/print`, {
      copies,
      user_identifier: profile?.openid,
      user_name: profile?.nickname,
    }),

  listActivities: () =>
    request.get<PublicActivity[]>('/public/activities'),

  getActivity: (activityId: number) =>
    request.get<PublicActivity>(`/public/activities/${activityId}`),

  searchPrograms: (activityId: number, keyword: string) =>
    request.get<PublicProgramSearchItem[]>(`/public/activities/${activityId}/programs/search`, {
      params: { q: keyword },
    }),

  getWechatConfig: () =>
    request.get<{ enabled: boolean; appid: string; scope: string }>('/public/wechat/config'),

  getWechatOAuthUrl: (redirectUri: string) =>
    request.get<{ url: string }>('/public/wechat/oauth-url', {
      params: { redirect_uri: redirectUri },
    }),

  resolveWechatProfile: (code: string, activityId?: number) =>
    request.get<WechatProfile>('/public/wechat/oauth-profile', {
      params: { code, activity_id: activityId },
    }),

  trackWechatUser: (profile: WechatProfile & { activity_id: number }) =>
    request.post('/public/wechat/track', profile),
}

// Upload API
export interface VideoTokenResponse {
  token: string
  key: string
  upload_url: string
}

export const uploadApi = {
  /** Get Qiniu upload token for client-side direct upload */
  getVideoUploadToken: (programId: number, filename: string) =>
    request.post<VideoTokenResponse>('/upload/video/token', { program_id: programId, filename }),

  /** Confirm video upload completion after client-side direct upload */
  confirmVideoUpload: (programId: number, key: string, filename: string, fileSize: number) =>
    request.post('/upload/video/confirm', {
      program_id: programId,
      key,
      filename,
      file_size: fileSize,
    }),

  /** Delete a program's video (move cloud file to TEMP) */
  deleteVideo: (programId: number) =>
    request.delete(`/upload/video/${programId}`),

  deleteDesktopVideo: (videoId: number) =>
    request.delete(`/upload/desktop/videos/${videoId}`),

  importProgramsExcel: (activityId: number, file: File) => {
    const formData = new FormData()
    formData.append('file', file)
    return request.post<Program[]>(`/admin/activities/${activityId}/programs/import`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 30000,
    })
  },
}

// Wotu Sync API
export interface SyncHistoryItem {
  id: number
  activity_id: number | null
  activity_name: string | null
  wotu_album_url: string | null
  status: string
  config: {
    concurrency?: number
    scroll_delay?: number
    tab_mode?: string
    tab_subdir?: boolean
    storage_path_prefix?: string
  }
  total_found: number
  total_downloaded: number
  total_uploaded: number
  total_failed: number
  total_skipped: number
  total_bytes: number
  error_msg: string | null
  duration: string | null
  started_at: string
  finished_at: string | null
}

export interface SyncHistoryResponse {
  items: SyncHistoryItem[]
  total: number
  page: number
  page_size: number
}

export const wotuApi = {
  startSync: (data: {
    activity_id: number
    url: string
    concurrency?: number
    scroll_delay?: number
    tab_mode?: string
    tab_subdir?: boolean
  }) => request.post('/admin/sync/start', data),

  stopSync: () => request.post('/admin/sync/stop'),

  getStatus: () => request.get('/admin/sync/status'),

  getPhotos: () => request.get('/admin/sync/photos'),

  getLogs: () => request.get('/admin/sync/logs'),

  getActivities: () => request.get('/admin/sync/activities'),

  getSyncHistory: (page = 1, pageSize = 20) =>
    request.get<SyncHistoryResponse>('/admin/sync/history', {
      params: { page, page_size: pageSize },
    }),
}

// Photo Manager API
export interface PhotoActivity {
  id: number
  name: string
  event_date: string | null
  venue: string | null
  cover_image: string | null
  photo_count: number
}

export interface PhotoItemFull {
  id: number
  filename: string
  storage_url: string | null
  wotu_url: string | null
  shoot_time: string | null
  width: number | null
  height: number | null
  file_size: number | null
  sync_status: string | null
  created_at: string | null
}

export interface PhotoListResponse {
  activity: { id: number; name: string; event_date: string | null }
  photos: PhotoItemFull[]
  total: number
  page: number
  page_size: number
}

export const photoApi = {
  getPhotoActivities: () =>
    request.get<PhotoActivity[]>('/admin/photos/activities'),

  getActivityPhotos: (activityId: number, page = 1, pageSize = 30) =>
    request.get<PhotoListResponse>(`/admin/photos/activity/${activityId}`, {
      params: { page, page_size: pageSize },
    }),

  deletePhoto: (photoId: number) =>
    request.delete<{ message: string; id: number }>(`/admin/photos/${photoId}`),

  batchDeletePhotos: (photoIds: number[]) =>
    request.post<{ message: string; count: number }>('/admin/photos/batch-delete', { photo_ids: photoIds }),

  deleteAllActivityPhotos: (activityId: number) =>
    request.delete<{ message: string; count: number }>(`/admin/photos/activity/${activityId}/all`),
}

export interface PrintRecordItem {
  id: number
  order_no?: string | null
  activity_id: number
  activity_name?: string | null
  program_id: number | null
  program_name: string | null
  program_sequence_number: number | null
  photo_id: number | null
  photo_url: string | null
  original_photo_url?: string | null
  print_image_url?: string | null
  photo_filename: string | null
  user_identifier: string | null
  user_name: string | null
  nickname?: string | null
  avatar_url?: string | null
  template_name: string | null
  paper_size: string | null
  copies: number
  status: string
  task_id: string | null
  error_msg: string | null
  payment_status?: string | null
  payment_order_id?: string | null
  payment_amount?: number | null
  paid_at?: string | null
  printed_at: string | null
  created_at: string | null
}

export interface PrintRecordResponse {
  items: PrintRecordItem[]
  total: number
  page: number
  page_size: number
}

export interface AudienceItem {
  id: number
  activity_id: number
  openid: string
  unionid: string | null
  nickname: string | null
  avatar_url: string | null
  phone: string | null
  province: string | null
  city: string | null
  country: string | null
  first_ip: string | null
  last_ip: string | null
  first_client: string | null
  last_client: string | null
  is_online: boolean
  is_blacklisted: boolean
  first_seen_at: string | null
  last_seen_at: string | null
}

export interface AudienceResponse {
  items: AudienceItem[]
  total: number
  page: number
  page_size: number
}

export const printApi = {
  getPrintRecords: (params?: {
    page?: number
    page_size?: number
    activity_id?: number
    status?: string
    keyword?: string
  }) =>
    request.get<PrintRecordResponse>('/admin/print-records', { params }),

  getActivityPrintRecords: (activityId: number, page = 1, pageSize = 20) =>
    request.get<PrintRecordResponse>(`/admin/activities/${activityId}/print-records`, {
      params: { page, page_size: pageSize },
    }),

  createActivityPrintRecord: (activityId: number, photoId: number, copies = 1) =>
    request.post(`/admin/activities/${activityId}/print-records`, {
      photo_id: photoId,
      copies,
    }),

  reprintRecord: (recordId: number) =>
    request.post(`/admin/print-records/${recordId}/reprint`),

  deleteRecord: (recordId: number) =>
    request.delete<{ message: string; id: number }>(`/admin/print-records/${recordId}`),
}

export const audienceApi = {
  getActivityAudiences: (activityId: number, page = 1, pageSize = 20) =>
    request.get<AudienceResponse>(`/admin/activities/${activityId}/audiences`, {
      params: { page, page_size: pageSize },
    }),

  updateBlacklist: (audienceId: number, blacklisted: boolean) =>
    request.post(`/admin/audiences/${audienceId}/blacklist`, { blacklisted }),
}

// Music API
export interface MusicItem {
  id: number
  name: string
  duration: number | null
  filename: string
  file_size: number | null
  storage_url: string | null
  created_at: string
}

export interface MusicListResponse {
  items: MusicItem[]
  total: number
  page: number
  page_size: number
}

export const musicApi = {
  list: (page = 1, pageSize = 20) =>
    request.get<MusicListResponse>('/admin/musics', {
      params: { page, page_size: pageSize },
    }),

  upload: (file: File, name?: string) => {
    const formData = new FormData()
    formData.append('file', file)
    if (name) formData.append('name', name)
    return request.post<MusicItem>('/admin/musics/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 120000,
    })
  },

  delete: (musicId: number) =>
    request.delete<{ message: string; id: number }>(`/admin/musics/${musicId}`),
}

// Short Video API
export interface ShortVideoProgram {
  id: number
  name: string
  sequence_number: number
  video_url: string | null
  short_video_url: string | null
  short_video_status: string
}

export interface ShortVideoBatchStatus {
  items: ShortVideoProgram[]
  total: number
}

export interface MusicOption {
  id: number
  name: string
  duration: number | null
}

export interface ShortVideoAutoConfig {
  enabled: boolean
  duration: number
  cut_intensity: number
  direction: string
  music_id: number | null
}

export const shortVideoApi = {
  getPrograms: (activityId: number) =>
    request.get<ShortVideoBatchStatus>(`/admin/short-video/programs/${activityId}`),

  getMusicOptions: () =>
    request.get<MusicOption[]>('/admin/short-video/musics'),

  generate: (data: {
    program_ids: number[]
    duration?: number
    cut_intensity?: number
    direction?: string
    music_id?: number | null
  }) => request.post<{ message: string; count: number; skipped: number }>('/admin/short-video/generate', data),

  delete: (programId: number) =>
    request.delete<{ message: string }>(`/admin/short-video/programs/${programId}`),

  getAutoConfig: (activityId: number) =>
    request.get<ShortVideoAutoConfig>(`/admin/short-video/auto-config/${activityId}`),

  updateAutoConfig: (activityId: number, config: ShortVideoAutoConfig) =>
    request.put<ShortVideoAutoConfig>(`/admin/short-video/auto-config/${activityId}`, config),
}

// Decoration Material API
export interface DecorationMaterialItem {
  id: number
  type: string
  name: string
  storage_url: string
  thumbnail_url?: string
  category?: string
  sort_order: number
  is_active: boolean
  created_at?: string
}

export interface MaterialListResponse {
  items: DecorationMaterialItem[]
  total: number
  page: number
  page_size: number
}

export const materialApi = {
  listDecorationMaterials: (type?: string, isActive?: boolean, page = 1, pageSize = 50, category?: string) =>
    request.get<MaterialListResponse>('/admin/decoration-materials', {
      params: { type, is_active: isActive, page, page_size: pageSize, category },
    }),

  createDecorationMaterial: (data: {
    type: string
    name: string
    storage_url: string
    thumbnail_url?: string
    category?: string
    sort_order?: number
    is_active?: boolean
  }) => request.post('/admin/decoration-materials', data),

  updateDecorationMaterial: (id: number, data: Partial<DecorationMaterialItem>) =>
    request.put(`/admin/decoration-materials/${id}`, data),

  deleteDecorationMaterial: (id: number) =>
    request.delete(`/admin/decoration-materials/${id}`),

  uploadDecorationMaterial: (file: File) => {
    const formData = new FormData()
    formData.append('file', file)
    return request.post('/admin/materials/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },

  // Print Settings (uses material.py router at /api/admin/materials)
  getPrintSettings: () =>
    request.get('/admin/materials/settings'),

  updatePrintSettings: (data: {
    print_free_quota?: number
    print_price?: number
    wechat_pay_enabled?: boolean
    wechat_pay_mchid?: string
    wechat_pay_api_key?: string
    wechat_pay_notify_url?: string
    print_render_mode?: 'frontend' | 'server'
    print_render_multiplier?: 1 | 2 | 3
    print_dispatch_mode?: 'lankuo' | 'local_client'
    lankuo_print_config?: Record<string, any>
  }) => request.put('/admin/materials/settings', data),

  getPrintStats: (activityId?: number) =>
    request.get('/admin/materials/stats', { params: { activity_id: activityId } }),
}

export const activityPrintSettingsApi = {
  get: (activityId: number) =>
    request.get(`/admin/activities/${activityId}/print-settings`),

  update: (activityId: number, data: {
    print_free_quota?: number
    print_price?: number
    print_render_mode?: 'frontend' | 'server'
    print_render_multiplier?: 1 | 2 | 3
    print_dispatch_mode?: 'lankuo' | 'local_client'
  }) => request.put(`/admin/activities/${activityId}/print-settings`, data),
}

export interface WechatPayParams {
  appId: string
  timeStamp: string
  nonceStr: string
  package: string
  signType: string
  paySign: string
}

export interface CanvasPrintResponse {
  message: string
  record_id: number
  payment_status: 'free' | 'pending' | 'paid' | 'refunded'
  payment_status_display?: string
  out_trade_no?: string
  amount?: number
  pay_params?: WechatPayParams
}

// Public APIs extension
export const publicApi2 = {
  // Materials
  listMaterials: (type: string, page = 1, pageSize = 20, category?: string) =>
    request.get('/public/materials', { params: { type, page, page_size: pageSize, category } }),

  // Fonts
  listFonts: () =>
    request.get<{ fonts: { name: string; family: string; weight: string }[] }>('/public/fonts'),

  // Canvas config
  getCanvasConfig: (activityId: number) =>
    request.get<{
      templateName?: string
      paperSize?: string | null
      canvasWidth: number
      canvasHeight: number
      photoInitX: number
      photoInitY: number
      photoInitScale: number
      photoMargin: number
      photoSlots?: { id: string; x: number; y: number; width: number; height: number }[]
      canvasJson?: any
    }>(`/public/canvas-config/${activityId}`),

  // Canvas print
  canvasPrint: (
    token: string,
    photoId: number,
    data: {
      copies?: number
      openid?: string
      nickname?: string
      canvas_json?: string
      canvas_image?: string
      canvas_width?: number
      canvas_height?: number
      template_name?: string
      paper_size?: string
    }
  ) =>
    request.post<CanvasPrintResponse>(`/public/programs/${token}/photos/${photoId}/canvas-print`, {
      copies: 1,
      ...data,
    }),

  // User records
  getUserRecords: (openid: string, recordType?: string, page = 1, pageSize = 10) =>
    request.get('/public/user/records', {
      params: { openid, record_type: recordType, page, page_size: pageSize },
    }),

  getUserAdminEntry: (openid: string) =>
    request.get('/public/user/admin-entry', { params: { openid } }),

  // Delete print record
  deletePrintRecord: (recordId: number, openid: string) =>
    request.delete(`/public/user/print-records/${recordId}`, {
      params: { openid },
    }),

  // Download record
  createDownloadRecord: (photoId: number, openid?: string, nickname?: string) =>
    request.post('/public/download/records', {
      photo_id: photoId,
      openid,
      nickname,
    }),

  deleteDownloadRecord: (recordId: number, openid: string) =>
    request.delete(`/public/download/records/${recordId}`, {
      params: { openid },
    }),

  // Check print quota
  checkPrintQuota: (activityId: number, openid: string) =>
    request.get('/public/print/quota', { params: { activity_id: activityId, openid } }),
}
