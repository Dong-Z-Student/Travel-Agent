import axios from 'axios'

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY

const ensureSupabaseConfig = () => {
  if (!supabaseUrl || !supabaseAnonKey) {
    throw new Error('Supabase 前端配置缺失，请检查 VITE_SUPABASE_URL 和 VITE_SUPABASE_ANON_KEY')
  }
}

const authClient = axios.create({
  baseURL: supabaseUrl ? `${supabaseUrl}/auth/v1` : '',
  timeout: 15000
})

authClient.interceptors.request.use(config => {
  ensureSupabaseConfig()
  config.headers.apikey = supabaseAnonKey
  if (!config.headers.Authorization) {
    config.headers.Authorization = `Bearer ${supabaseAnonKey}`
  }
  return config
})

const normalizeAuthResponse = data => ({
  user: data?.user || null,
  session: data?.access_token ? {
    access_token: data.access_token,
    refresh_token: data.refresh_token,
    token_type: data.token_type,
    expires_in: data.expires_in,
    expires_at: data.expires_at
  } : null,
  raw: data
})

export const signInHttp = async payload => {
  const { data } = await authClient.post('/token?grant_type=password', {
    email: payload.email,
    password: payload.password
  })
  return normalizeAuthResponse(data)
}

export const signUpHttp = async payload => {
  const { data } = await authClient.post('/signup', {
    email: payload.email,
    password: payload.password
  })
  return normalizeAuthResponse(data)
}

export const signOutHttp = async accessToken => {
  if (!accessToken) return { success: true }
  await authClient.post('/logout', null, {
    headers: {
      Authorization: `Bearer ${accessToken}`
    }
  })
  return { success: true }
}

export const getSupabaseUserHttp = async accessToken => {
  if (!accessToken) return null
  const { data } = await authClient.get('/user', {
    headers: {
      Authorization: `Bearer ${accessToken}`
    }
  })
  return data
}
