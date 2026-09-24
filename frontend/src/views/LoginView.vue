<template>
  <main class="login-screen">
    <form class="login-card" @submit.prevent="submit">
      <p class="login-kicker">HOME ANALYTICS PLATFORM</p>
      <h1>登录 HAP</h1>
      <p class="login-note">使用管理员密码访问你的数据和设置。</p>
      <label for="username">用户名</label>
      <input id="username" v-model="username" autocomplete="username" required />
      <label for="password">密码</label>
      <input id="password" v-model="password" type="password" autocomplete="current-password" required />
      <p v-if="error" class="login-error" role="alert">{{ error }}</p>
      <button type="submit" :disabled="busy">{{ busy ? '正在登录…' : '登录' }}</button>
    </form>
  </main>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { postApiData, setCsrfToken } from '@/api/client';

const route = useRoute();
const router = useRouter();
const username = ref('admin');
const password = ref('');
const error = ref('');
const busy = ref(false);

async function submit(): Promise<void> {
  busy.value = true;
  error.value = '';
  try {
    const session = await postApiData<{ csrf_token: string }, { username: string; password: string }>(
      '/auth/login', { username: username.value, password: password.value },
    );
    setCsrfToken(session.csrf_token);
    const requested = route.query.redirect;
    const destination = typeof requested === 'string' && requested.startsWith('/') && !requested.startsWith('//')
      ? requested : '/';
    await router.replace(destination);
  } catch {
    error.value = '登录失败，请检查密码后重试。';
    password.value = '';
  } finally {
    busy.value = false;
  }
}
</script>

<style scoped>
.login-screen { min-height: 100vh; display: grid; place-items: center; padding: 24px; background: #0b1220; color: #e9f0fa; }
.login-card { width: min(100%, 400px); display: grid; gap: 12px; padding: 36px; border: 1px solid #29425d; border-radius: 18px; background: #122036; box-shadow: 0 24px 70px #0006; }
.login-kicker { margin: 0; color: #6eb9ed; font-size: 12px; letter-spacing: .18em; }
h1 { margin: 0; font-size: 28px; }
.login-note { margin: 0 0 12px; color: #aebfd2; }
label { font-size: 14px; }
input { width: 100%; box-sizing: border-box; padding: 12px; border: 1px solid #44617d; border-radius: 8px; background: #0d192b; color: inherit; font: inherit; }
input:focus-visible, button:focus-visible { outline: 2px solid #67c4ff; outline-offset: 2px; }
button { margin-top: 8px; padding: 12px; border: 0; border-radius: 8px; background: #56b6ed; color: #071423; font: inherit; font-weight: 700; cursor: pointer; }
button:disabled { opacity: .6; cursor: wait; }
.login-error { margin: 0; color: #ff9a9a; }
</style>
