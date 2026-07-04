import { createPreferenceHttp, deletePreferenceHttp, getMeHttp, listPreferencesHttp } from '@/api/userApi'

export const getMe = () => getMeHttp()
export const listPreferences = () => listPreferencesHttp()
export const createPreference = payload => createPreferenceHttp(payload)
export const deletePreference = preferenceId => deletePreferenceHttp(preferenceId)
