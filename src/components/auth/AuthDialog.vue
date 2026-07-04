<script setup>
import { reactive, ref } from 'vue'

const emit = defineEmits(['login', 'register', 'close'])
const mode = ref('login')
const form = reactive({ email: '', password: '' })

const submit = () => {
  const payload = { email: form.email, password: form.password }
  emit(mode.value === 'login' ? 'login' : 'register', payload)
}
</script>

<template>
  <div class="auth-mask" @click.self="$emit('close')">
    <section class="auth-dialog">
      <button class="auth-close" type="button" @click="$emit('close')">×</button>
      <h3>{{ mode === 'login' ? '登录' : '注册' }}</h3>
      <label>
        <span>账号</span>
        <input v-model="form.email" type="email" placeholder="邮箱" />
      </label>
      <label>
        <span>密码</span>
        <input v-model="form.password" type="password" placeholder="密码" @keyup.enter="submit" />
      </label>
      <button class="submit" type="button" @click="submit">{{ mode === 'login' ? '登录' : '注册' }}</button>
      <button class="switch" type="button" @click="mode = mode === 'login' ? 'register' : 'login'">
        {{ mode === 'login' ? '没有账号，现在去注册' : '已有账号，返回登录' }}
      </button>
    </section>
  </div>
</template>

<style scoped>
.auth-mask {
  position: fixed;
  inset: 0;
  z-index: 40;
  display: grid;
  place-items: center;
  background: rgba(15, 23, 42, 0.20);
}
.auth-dialog {
  position: relative;
  display: grid;
  gap: 12px;
  width: 320px;
  padding: 20px;
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 20px 48px rgba(15, 23, 42, 0.24);
}
h3 { margin: 0; font-size: 18px; font-weight: 700; }
label { display: grid; gap: 5px; font-size: 13px; color: #475569; }
input { height: 36px; padding: 0 10px; border: 1px solid #cbd5e1; border-radius: 7px; }
.auth-close { position: absolute; top: 8px; right: 8px; width: 28px; height: 28px; border: 0; background: transparent; cursor: pointer; }
.submit { height: 36px; color: #fff; cursor: pointer; background: #0f766e; border: 0; border-radius: 7px; }
.switch { height: 28px; color: #0f766e; cursor: pointer; background: transparent; border: 0; }
</style>
