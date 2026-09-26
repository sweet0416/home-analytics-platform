<template>
  <main class="login-screen">
    <div class="login-shell">
      <header class="login-topbar">
        <div class="login-wordmark" aria-label="HAP Home Analytics Platform">H<span>A</span>P<i></i></div>
        <div class="login-topbar-copy" aria-hidden="true">
          <span>A smarter home</span><span>Deeper insights</span><span>A calmer tomorrow</span>
        </div>
        <span class="login-topbar-end">PRIVATE HOME INTELLIGENCE <i></i></span>
      </header>

      <section class="login-hero" aria-labelledby="login-hero-title">
        <div class="login-hero-copy">
          <h1 id="login-hero-title">Your Home<br /><span>Tells a Bigger Story</span></h1>
          <p>Turn everyday data into a smarter, safer,<br class="desktop-break" /> more comfortable home.</p>
          <div class="login-capabilities" aria-label="Platform values">
            <div class="login-capability">
              <svg viewBox="0 0 32 32" fill="none" aria-hidden="true"><path d="M4 24h4v-7H4v7Zm8 0h4V9h-4v15Zm8 0h4V4h-4v20Zm8 0h2V14h-2v10ZM3 27h27" stroke="currentColor" stroke-width="1.7"/></svg>
              <span>REAL-TIME<br />INSIGHTS</span>
            </div>
            <div class="login-capability">
              <svg viewBox="0 0 32 32" fill="none" aria-hidden="true"><path d="m3 15 13-11 13 11M7 13v15h18V13M13 28V18h6v10" stroke="currentColor" stroke-width="1.7" stroke-linejoin="round"/></svg>
              <span>A MORE<br />EFFICIENT HOME</span>
            </div>
            <div class="login-capability">
              <svg viewBox="0 0 32 32" fill="none" aria-hidden="true"><path d="m16 3 11 4v8c0 7-4.2 11.2-11 14-6.8-2.8-11-7-11-14V7l11-4Zm-5 13 3.2 3.2L21 12" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/></svg>
              <span>PRIVACY<br />FIRST</span>
            </div>
            <div class="login-capability">
              <svg viewBox="0 0 32 32" fill="none" aria-hidden="true"><path d="M27 5C14 5 5 10 5 19c0 5 3.2 8 8 8 9 0 14-9 14-22ZM5 28c4-8 10-13 19-17" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/></svg>
              <span>A HEALTHIER<br />TOMORROW</span>
            </div>
          </div>
        </div>

        <div class="login-telemetry" aria-hidden="true">
          <svg viewBox="0 0 840 430" preserveAspectRatio="none" fill="none">
            <defs>
              <linearGradient id="login-wave-cyan"><stop stop-color="#10DCEB" stop-opacity="0"/><stop offset=".27" stop-color="#33E5F2"/><stop offset=".7" stop-color="#38A8FF"/><stop offset="1" stop-color="#7652FF" stop-opacity=".3"/></linearGradient>
              <linearGradient id="login-wave-violet"><stop stop-color="#3AA7FF" stop-opacity="0"/><stop offset=".5" stop-color="#657FFF"/><stop offset="1" stop-color="#A748F8"/></linearGradient>
              <filter id="login-wave-glow"><feGaussianBlur stdDeviation="8"/></filter>
            </defs>
            <path class="login-wave-grid" d="M0 94h840M0 178h840M0 262h840M0 346h840M126 0v430M252 0v430M378 0v430M504 0v430M630 0v430M756 0v430"/>
            <path d="M0 336C92 367 111 269 182 282c67 12 94 91 170 2 56-65 90-168 177-141 85 26 84 132 175 60 63-50 81-158 136-165" stroke="url(#login-wave-cyan)" stroke-width="9" filter="url(#login-wave-glow)" opacity=".65"/>
            <path class="login-wave-flow" d="M0 336C92 367 111 269 182 282c67 12 94 91 170 2 56-65 90-168 177-141 85 26 84 132 175 60 63-50 81-158 136-165" stroke="url(#login-wave-cyan)" stroke-width="2.8"/>
            <path d="M0 391c105-20 134-135 224-113 62 14 91 85 162 18 62-58 102-129 167-86 96 65 102 170 188 105 53-40 72-120 99-131" stroke="url(#login-wave-violet)" stroke-width="1.8" opacity=".8"/>
            <path d="M0 413c126-36 163-139 248-115 81 23 102 103 183 43 72-53 108-102 175-60 102 64 134 79 234 7" stroke="#299EE9" opacity=".35"/>
            <path d="M0 308c120-27 159-112 227-97 84 18 91 96 171 30 68-57 105-136 178-96 97 53 112 91 178 45 44-30 67-97 86-104" stroke="#3FD4F7" opacity=".26"/>
            <circle cx="351" cy="284" r="5.5" fill="#48EDFA"/><circle cx="529" cy="143" r="5.5" fill="#48EDFA"/><circle cx="704" cy="203" r="4.5" fill="#A66AFF"/>
            <path d="M351 284v-77M529 143V67M704 203V119" stroke="#50BDFB" opacity=".47"/>
          </svg>
          <div class="login-readout login-readout--comfort"><strong>72°</strong><small>Comfort</small></div>
          <div class="login-readout login-readout--energy"><strong>436 <em>kWh</em></strong><small>Energy</small></div>
          <div class="login-readout login-readout--health"><strong>98%</strong><small>System health</small></div>
          <span class="login-telemetry-disclaimer">ILLUSTRATIVE TELEMETRY</span>
        </div>

        <svg class="login-architecture" viewBox="0 0 1000 490" preserveAspectRatio="xMidYMax slice" fill="none" aria-hidden="true">
          <defs>
            <linearGradient id="login-mountain" x1="0" y1="0" x2="0" y2="1"><stop stop-color="#183452"/><stop offset="1" stop-color="#071323"/></linearGradient>
            <linearGradient id="login-house" x1="0" y1="0" x2="0" y2="1"><stop stop-color="#1D374E"/><stop offset=".52" stop-color="#0B2032"/><stop offset="1" stop-color="#040C16"/></linearGradient>
            <linearGradient id="login-glass"><stop stop-color="#102E43" stop-opacity=".72"/><stop offset=".48" stop-color="#204B5D" stop-opacity=".5"/><stop offset="1" stop-color="#061522" stop-opacity=".86"/></linearGradient>
          </defs>
          <path d="M0 175 84 128l62 34 99-110 126 123 82-52 114 108 94-115 100 80 84-50 155 88v256H0Z" fill="url(#login-mountain)" opacity=".65"/>
          <path d="M0 243 117 178l82 56 111-84 153 112 111-57 127 62 143-92 156 84v231H0Z" fill="#0A1D36" opacity=".8"/>
          <path d="M0 348 164 316l244-48 333 50 46 35-35 38H0Z" fill="#030A14"/>
          <path d="M103 342 413 272l298 49-38 14-262-39-294 60Z" fill="#010711"/>
          <path d="M117 358 411 297l262 39v122H117Z" fill="url(#login-house)"/>
          <path d="M136 368 394 318v108H136ZM425 318l226 32v76H425Z" fill="url(#login-glass)"/>
          <path d="M118 355 410 297l262 39M130 432h532" stroke="#93C9D6" stroke-opacity=".18" stroke-width="2"/>
          <path d="M136 420h258m31-1h226" stroke="#DBA870" stroke-opacity=".56" stroke-width="2.5"/>
          <path d="M403 299v151M661 337v113" stroke="#7DB2C4" stroke-opacity=".14" stroke-width="2"/>
          <path d="M166 385h170m104-28h182" stroke="#E5BC91" stroke-opacity=".18" stroke-width="15"/>
          <path d="M0 451h788l131 39H0Z" fill="#050C16"/>
          <path d="M0 470c240-12 442-13 714-11 51 0 104 9 175 31H0Z" fill="#0D2E46" opacity=".68"/>
          <path d="M0 469c218-12 492-12 742-5" stroke="#2E9AC7" stroke-opacity=".32" stroke-width="2"/>
          <path d="m738 440 25-112 23 112m-11-51 39-86 25 137m-13-59 32-66 36 125" stroke="#04101B" stroke-width="16" stroke-linecap="round" stroke-linejoin="round"/>
          <path d="M757 444h173" stroke="#030A12" stroke-width="17"/>
          <path d="M705 305h2m31-3h2m31 16h2m53-33h2m30 22h2m64 19h2" stroke="#EFBF8B" stroke-width="3" opacity=".6"/>
        </svg>
        <div class="login-hero-footer">DATA TODAY.<br /><span>A BRIGHTER TOMORROW.</span></div>
      </section>

      <section class="login-panel" aria-label="Sign in">
        <form class="login-card" @submit.prevent="submit">
          <div class="login-card-top"><span class="login-card-status"><i></i> Private access</span></div>
          <div class="login-card-heading">
            <div class="login-card-logo" aria-hidden="true">H<span>A</span>P</div>
            <h2>Home Analytics Platform</h2>
            <p>Private intelligence for your household systems.</p>
          </div>
          <div class="login-fields">
            <div class="login-field">
              <label for="username">Username</label>
              <div class="login-input-wrap">
                <svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><circle cx="12" cy="7.5" r="3.5" stroke="currentColor" stroke-width="1.7"/><path d="M4.5 20v-1.5a7.5 7.5 0 0 1 15 0V20" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/></svg>
                <input id="username" v-model="username" name="username" type="text" autocomplete="username" placeholder="Enter your username" required />
              </div>
            </div>
            <div class="login-field">
              <label for="password">Password</label>
              <div class="login-input-wrap">
                <svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><rect x="4.5" y="10" width="15" height="11" rx="2" stroke="currentColor" stroke-width="1.7"/><path d="M8 10V7a4 4 0 0 1 8 0v3M12 14v3" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/></svg>
                <input id="password" v-model="password" name="password" :type="passwordVisible ? 'text' : 'password'" autocomplete="current-password" placeholder="Enter your password" required />
                <button class="login-visibility" type="button" :aria-label="passwordVisible ? 'Hide password' : 'Show password'" :aria-pressed="passwordVisible" @click="passwordVisible = !passwordVisible">
                  <svg v-if="passwordVisible" viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M2.5 12s3.5-6 9.5-6 9.5 6 9.5 6-3.5 6-9.5 6-9.5-6-9.5-6Z" stroke="currentColor" stroke-width="1.7"/><circle cx="12" cy="12" r="2.5" stroke="currentColor" stroke-width="1.7"/></svg>
                  <svg v-else viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M3 3 21 21M9.9 6.2A10 10 0 0 1 12 6c6 0 9.5 6 9.5 6a13 13 0 0 1-3.1 3.6M6.5 7.7C4 9.4 2.5 12 2.5 12s3.5 6 9.5 6c1 0 2-.2 2.9-.5M10 10a3 3 0 0 0 4 4" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/></svg>
                </button>
              </div>
            </div>
          </div>
          <p v-if="error" class="login-error" role="alert" aria-live="assertive"><span aria-hidden="true">!</span>{{ error }}</p>
          <button class="login-submit" type="submit" :disabled="busy" :aria-busy="busy">
            <span>{{ busy ? 'Signing in…' : 'Sign In' }}</span>
            <svg v-if="!busy" viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M4 12h15m-6-6 6 6-6 6" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>
            <span v-else class="login-spinner" aria-hidden="true"></span>
          </button>
          <div class="login-card-footer">
            <svg viewBox="0 0 32 32" fill="none" aria-hidden="true"><path d="m16 3 11 4v8c0 7-4.2 11.2-11 14-6.8-2.8-11-7-11-14V7l11-4Zm-5 13 3.2 3.2L21 12" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>
            <div><strong>Secure single-admin access</strong><span>Your home data. Your control.</span></div>
          </div>
        </form>
        <div class="login-panel-footnote">A PRIVATE SPACE FOR YOUR HOME SYSTEMS <span></span> HAP</div>
      </section>
    </div>
  </main>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { postApiData, setCsrfToken } from '@/api/client';
import './login.css';

const route = useRoute();
const router = useRouter();
const username = ref('admin');
const password = ref('');
const passwordVisible = ref(false);
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
