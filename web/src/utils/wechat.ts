import { publicApi, type WechatProfile } from '@/api/admin'

const PROFILE_KEY = 'supertech_wechat_profile'

const isWechatBrowser = () => /micromessenger/i.test(window.navigator.userAgent)

const cleanOAuthQuery = () => {
  const url = new URL(window.location.href)
  if (!url.searchParams.has('code')) return
  url.searchParams.delete('code')
  url.searchParams.delete('state')
  window.history.replaceState({}, document.title, `${url.pathname}${url.search}${url.hash}`)
}

export function getStoredWechatProfile(): WechatProfile | null {
  try {
    const raw = window.localStorage.getItem(PROFILE_KEY)
    return raw ? JSON.parse(raw) : null
  } catch {
    return null
  }
}

export async function ensureWechatProfile(activityId?: number): Promise<WechatProfile | null> {
  const url = new URL(window.location.href)
  const code = url.searchParams.get('code')

  if (code) {
    const res = await publicApi.resolveWechatProfile(code, activityId)
    window.localStorage.setItem(PROFILE_KEY, JSON.stringify(res.data))
    cleanOAuthQuery()
    return res.data
  }

  const stored = getStoredWechatProfile()
  if (stored?.openid) {
    if (activityId) {
      await publicApi.trackWechatUser({ ...stored, activity_id: activityId }).catch(() => undefined)
    }
    return stored
  }

  if (isWechatBrowser()) {
    const config = await publicApi.getWechatConfig()
    if (config.data.enabled) {
      const oauth = await publicApi.getWechatOAuthUrl(window.location.href)
      window.location.href = oauth.data.url
    }
  }

  return null
}
