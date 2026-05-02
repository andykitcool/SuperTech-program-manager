/**
 * 图片 URL 工具函数 - 七牛云图片处理
 */

/** 七牛云存储域名白名单 */
const QINIU_DOMAINS = [
  'autorecord.vidiu.cn',
  'vidiu.cn',
  'clouddn.com',
  'qiniucdn.com',
  'qncdn.com',
]

/** 缩略图默认参数 */
const THUMB_PARAMS = 'imageView2/2/w/320/h/320/q/75'
/** 预览大图参数（限制宽度，减少传输） */
const PREVIEW_PARAMS = 'imageView2/2/w/1200/q/85'

function isQiniuUrl(url: string): boolean {
  if (!url) return false
  try {
    const hostname = new URL(url).hostname
    return QINIU_DOMAINS.some(d => hostname === d || hostname.endsWith('.' + d))
  } catch {
    return QINIU_DOMAINS.some(d => url.includes(d))
  }
}

function appendQiniuParam(url: string, params: string): string {
  if (!url || !isQiniuUrl(url)) return url
  const separator = url.includes('?') ? '|' : '?'
  return `${url}${separator}${params}`
}

/**
 * 获取缩略图 URL（用于列表/网格展示）
 * 宽高限制 320px，质量 75%
 */
export function getThumbUrl(url: string | null): string {
  if (!url) return ''
  return appendQiniuParam(url, THUMB_PARAMS)
}

/**
 * 获取预览大图 URL（用于弹窗预览）
 * 宽度限制 1200px，质量 85%，比原图小很多但画质仍然很好
 */
export function getPreviewUrl(url: string | null): string {
  if (!url) return ''
  return appendQiniuParam(url, PREVIEW_PARAMS)
}

/**
 * 获取照片最佳 URL，支持 storage_url 和 wotu_url 双源 fallback
 */
export function getPhotoUrl(
  storageUrl: string | null,
  wotuUrl?: string | null
): string {
  return storageUrl || wotuUrl || ''
}
