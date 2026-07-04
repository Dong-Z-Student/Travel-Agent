import { getSupabaseUserHttp, signInHttp, signOutHttp, signUpHttp } from '@/api/authApi'

const TOKEN_KEY = 'travel_agent_access_token'
const REFRESH_TOKEN_KEY = 'travel_agent_refresh_token'

export const persistSession = session => {
  if (!session?.access_token) return
  window.localStorage.setItem(TOKEN_KEY, session.access_token)
  if (session.refresh_token) {
    window.localStorage.setItem(REFRESH_TOKEN_KEY, session.refresh_token)
  }
}

export const clearPersistedSession = () => {
  window.localStorage.removeItem(TOKEN_KEY)
  window.localStorage.removeItem(REFRESH_TOKEN_KEY)
}

export const getAccessToken = () => window.localStorage.getItem(TOKEN_KEY)

export const signIn = async payload => {
  const result = await signInHttp(payload)
  persistSession(result.session)
  return result
}

export const signUp = async payload => {
  const result = await signUpHttp(payload)
  persistSession(result.session)
  return result
}

export const signOut = async () => {
  const accessToken = getAccessToken()
  const result = await signOutHttp(accessToken)
  clearPersistedSession()
  return result
}

export const restoreSession = async () => {
  const accessToken = getAccessToken()
  if (!accessToken) return { user: null, session: null }
  try {
    const user = await getSupabaseUserHttp(accessToken)
    return {
      user,
      session: { access_token: accessToken, refresh_token: window.localStorage.getItem(REFRESH_TOKEN_KEY) }
    }
  } catch {
    clearPersistedSession()
    return { user: null, session: null }
  }
}
