<script setup>
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { restoreSession, signIn, signOut, signUp } from '@/services/authService'
import { useUserStore } from '@/stores/userStore'
import AuthDialog from './AuthDialog.vue'
import ToolbarButton from '@/components/toolbar/ToolbarButton.vue'

const emit = defineEmits(['click-tool'])
const userStore = useUserStore()
const dialogOpen = ref(false)
const loading = ref(false)

const getAuthErrorMessage = error => error?.response?.data?.msg
  || error?.response?.data?.error_description
  || error?.response?.data?.message
  || error.message
  || '认证失败'

const handleLogin = async payload => {
  loading.value = true
  try {
    const result = await signIn(payload)
    userStore.setSession(result)
    dialogOpen.value = false
    ElMessage.success('登录成功')
  } catch (error) {
    ElMessage.error(getAuthErrorMessage(error))
  } finally {
    loading.value = false
  }
}

const handleRegister = async payload => {
  loading.value = true
  try {
    const result = await signUp(payload)
    if (result.session) {
      userStore.setSession(result)
      dialogOpen.value = false
      ElMessage.success('注册并登录成功')
    } else {
      ElMessage.success('注册成功，请完成邮箱确认后再登录')
    }
  } catch (error) {
    ElMessage.error(getAuthErrorMessage(error))
  } finally {
    loading.value = false
  }
}

const handleClick = async () => {
  emit('click-tool')
  if (userStore.isLoggedIn) {
    await signOut()
    userStore.clearSession()
    ElMessage.success('已退出登录')
  } else {
    dialogOpen.value = true
  }
}

onMounted(async () => {
  const result = await restoreSession()
  if (result.user) userStore.setSession(result)
})
</script>

<template>
  <div class="user-entry">
    <ToolbarButton
      :label="userStore.isLoggedIn ? '退' : '我'"
      round
      :active="userStore.isLoggedIn"
      :disabled="loading"
      @click="handleClick"
    />
    <AuthDialog v-if="dialogOpen" @close="dialogOpen = false" @login="handleLogin" @register="handleRegister" />
  </div>
</template>

<style scoped>
.user-entry { position: relative; }
</style>
