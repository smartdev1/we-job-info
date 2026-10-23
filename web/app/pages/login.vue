<template>
  <div class="relative flex min-h-screen flex-col items-center justify-center overflow-hidden bg-slate-900 px-4 py-12">
    <!-- Decorative background -->
    <div class="pointer-events-none absolute inset-0">
      <div class="absolute -top-32 -left-32 h-96 w-96 rounded-full bg-sky-500/20 blur-3xl" />
      <div class="absolute -bottom-40 -right-32 h-96 w-96 rounded-full bg-sky-400/10 blur-3xl" />
      <div class="absolute inset-0 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-sky-500/10 via-transparent to-transparent" />
    </div>

    <!-- Logo + wordmark -->
    <div class="relative mb-8 flex flex-col items-center gap-3">
      <span class="grid h-16 w-16 shrink-0 place-items-center rounded-2xl bg-white/10 text-white ring-1 ring-white/20 backdrop-blur">
        <svg
          width="32"
          height="32"
          viewBox="0 0 24 24"
          fill="none"
          aria-hidden="true"
        >
          <circle
            cx="12"
            cy="12"
            r="7"
            stroke="currentColor"
            stroke-width="2.5"
          />
          <circle
            cx="12"
            cy="12"
            r="2.5"
            fill="currentColor"
          />
        </svg>
      </span>
      <div class="flex items-center gap-2">
        <span class="text-2xl font-extrabold tracking-tight text-white">We.Info</span>
        <span class="rounded bg-sky-400/20 px-2 py-0.5 text-xs font-bold uppercase tracking-wider text-sky-300">Jobs</span>
      </div>
      <p class="text-sm text-slate-400">
        Collecte, validation et publication des offres d'emploi
      </p>
    </div>

    <!-- Card -->
    <div class="relative w-full max-w-md rounded-2xl border-0 bg-white/95 p-8 shadow-2xl ring-1 ring-black/5 backdrop-blur">
      <div class="mb-6">
        <h1 class="text-xl font-semibold text-slate-900">
          Bonjour 👋
        </h1>
        <p class="mt-1 text-sm text-slate-500">
          Connecte-toi pour accéder au tableau de bord et gérer les offres.
        </p>
      </div>

      <form
        class="space-y-5"
        @submit.prevent="onSubmit"
      >
        <div class="space-y-2">
          <label
            for="email"
            class="block text-sm font-medium text-slate-700"
          >
            Email
          </label>
          <div class="relative">
            <span class="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3 text-slate-400">
              <svg
                width="18"
                height="18"
                viewBox="0 0 24 24"
                fill="none"
                aria-hidden="true"
              >
                <path
                  d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"
                  stroke="currentColor"
                  stroke-width="2"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                />
              </svg>
            </span>
            <input
              id="email"
              v-model="email"
              type="email"
              required
              autocomplete="username"
              placeholder="nom@exemple.com"
              class="w-full rounded-lg border border-slate-300 bg-white px-4 py-2.5 pl-10 text-sm text-slate-900 placeholder-slate-400 shadow-sm transition-colors focus:border-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-500/20"
            />
          </div>
        </div>

        <div class="space-y-2">
          <label
            for="password"
            class="block text-sm font-medium text-slate-700"
          >
            Mot de passe
          </label>
          <div class="relative">
            <span class="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3 text-slate-400">
              <svg
                width="18"
                height="18"
                viewBox="0 0 24 24"
                fill="none"
                aria-hidden="true"
              >
                <rect
                  x="3"
                  y="11"
                  width="18"
                  height="11"
                  rx="2"
                  ry="2"
                  stroke="currentColor"
                  stroke-width="2"
                />
                <path
                  d="M7 11V7a5 5 0 0110 0v4"
                  stroke="currentColor"
                  stroke-width="2"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                />
              </svg>
            </span>
            <input
              id="password"
              v-model="password"
              type="password"
              required
              autocomplete="current-password"
              placeholder="••••••••"
              class="w-full rounded-lg border border-slate-300 bg-white px-4 py-2.5 pl-10 text-sm text-slate-900 placeholder-slate-400 shadow-sm transition-colors focus:border-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-500/20"
            />
          </div>
        </div>

        <button
          type="submit"
          :disabled="auth.loading"
          class="w-full rounded-lg bg-sky-600 px-4 py-2.5 text-sm font-semibold text-white shadow-sm transition-colors hover:bg-sky-700 focus:outline-none focus:ring-2 focus:ring-sky-500/20 disabled:cursor-not-allowed disabled:opacity-75"
        >
          <span
            v-if="auth.loading"
            class="inline-flex items-center gap-2"
          >
            <svg
              class="h-4 w-4 animate-spin"
              viewBox="0 0 24 24"
              fill="none"
              aria-hidden="true"
            >
              <circle
                class="opacity-25"
                cx="12"
                cy="12"
                r="10"
                stroke="currentColor"
                stroke-width="4"
              />
              <path
                class="opacity-75"
                fill="currentColor"
                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
              />
            </svg>
            Connexion en cours…
          </span>
          <span v-else>Se connecter</span>
        </button>

        <p
          v-if="error"
          class="text-sm text-red-500"
        >
          {{ error }}
        </p>
      </form>

      <div class="mt-6 flex items-center justify-center gap-2 text-xs text-slate-400">
        <span class="h-px flex-1 bg-slate-200" />
        <span>ou</span>
        <span class="h-px flex-1 bg-slate-200" />
      </div>

      <div class="mt-6 grid grid-cols-3 gap-2 text-center text-xs">
        <div class="rounded-lg bg-slate-50 py-2">
          <div class="font-semibold text-sky-600">5</div>
          <div class="text-slate-500">Sources</div>
        </div>
        <div class="rounded-lg bg-slate-50 py-2">
          <div class="font-semibold text-sky-600">+500</div>
          <div class="text-slate-500">Offres</div>
        </div>
        <div class="rounded-lg bg-slate-50 py-2">
          <div class="font-semibold text-sky-600">24/7</div>
          <div class="text-slate-500">Collecte</div>
        </div>
      </div>
    </div>

    <p class="relative mt-6 text-xs text-slate-500">
      © {{ new Date().getFullYear() }} We.Info Jobs :-)
    </p>
  </div>
</template>

<script setup lang="ts">
const auth = useAuthStore()
const email = ref('')
const password = ref('')
const error = ref('')
const route = useRoute()

async function onSubmit() {
  error.value = ''
  const ok = await auth.login(email.value, password.value)
  if (ok) {
    const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : '/dashboard'
    await navigateTo(redirect)
  } else {
    error.value = 'Identifiants incorrects. Réessayez.'
  }
}
</script>