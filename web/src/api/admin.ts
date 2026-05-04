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
}

export interface WechatProfile {
  openid: string
  unionid?: string | null
  nickname?: string | null
  avatar_url?: string | null
  province?: string | null
  city?: string | null
  country?: string | null
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
  shoot_time: string | null
  width: number | null
  height: number | null
}

// Admin APIs
export const adminApi = {
  login: (username: string, password: string) =>
    request.post('/admin/login', { username, password }),

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
}

export interface PrintRecordItem {
  id: number
  activity_id: number
  program_id: number | null
  program_name: string | null
  program_sequence_number: number | null
  photo_id: number | null
  photo_url: string | null
  photo_filename: string | null
  user_identifier: string | null
  user_name: string | null
  template_name: string | null
  paper_size: string | null
  copies: number
  status: string
  task_id: string | null
  error_msg: string | null
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
}

export const audienceApi = {
  getActivityAudiences: (activityId: number, page = 1, pageSize = 20) =>
    request.get<AudienceResponse>(`/admin/activities/${activityId}/audiences`, {
      params: { page, page_size: pageSize },
    }),

  updateBlacklist: (audienceId: number, blacklisted: boolean) =>
    request.post(`/admin/audiences/${audienceId}/blacklist`, { blacklisted }),
}
