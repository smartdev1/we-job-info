<script setup lang="ts">
import { ref } from 'vue'

const config = useRuntimeConfig()
const apiBase = (config.public.apiBase as string).replace(/\/$/, '')

const text = ref('')
const loading = ref(false)
const jobId = ref<string | null>(null)
const error = ref<string | null>(null)

const url = ref('')
const loadingUrl = ref(false)
const jobIdUrl = ref<string | null>(null)
const existingOfferId = ref<string | null>(null)
const errorUrl = ref<string | null>(null)

async function submitUrl() {
  loadingUrl.value = true
  errorUrl.value = null
  jobIdUrl.value = null
  existingOfferId.value = null
  try {
    const res = await fetch(`${apiBase}/api/v1/offers/from-url`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({ url: url.value })
    })
    if (!res.ok) {
      let detail = `HTTP ${res.status}`
      try {
        const body = await res.json()
        if (body?.detail) detail = body.detail
      } catch {
        // ignore parse errors, keep HTTP status detail
      }
      throw new Error(detail)
    }
    const data = await res.json()
    if (data.existing) existingOfferId.value = data.offer_id
    else jobIdUrl.value = data.job_id
  } catch (e) {
    errorUrl.value = e instanceof Error ? e.message : 'Erreur inconnue'
  } finally {
    loadingUrl.value = false
  }
}

async function submit() {
  loading.value = true
  error.value = null
  jobId.value = null
  try {
    const res = await fetch(`${apiBase}/api/v1/offers/from-text`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({ text: text.value })
    })
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    const data = await res.json()
    jobId.value = data.job_id
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Erreur inconnue'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="mx-auto max-w-3xl space-y-6">
    <div>
      <h1 class="text-2xl font-extrabold tracking-tight text-slate-900">
        Nouvelle offre
      </h1>
      <p class="mt-1 text-sm text-slate-600">
        Extrayez une offre depuis une URL de plateforme ou en collant directement le texte de l'annonce.
      </p>
    </div>

    <section class="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <h2 class="text-sm font-bold uppercase tracking-wider text-slate-500">
        Depuis une URL
      </h2>
      <div class="mt-3 space-y-3">
        <label
          for="offer-url"
          class="block text-sm font-medium text-slate-700"
        >
          Adresse de l'annonce
        </label>
        <input
          id="offer-url"
          v-model="url"
          type="url"
          placeholder="https://…"
          class="w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-2.5 text-sm outline-none transition-colors placeholder:text-slate-400 focus:border-sky-500 focus:ring-2 focus:ring-sky-500/25"
        >
        <button
          type="button"
          class="inline-flex items-center gap-2 rounded-lg bg-sky-600 px-4 py-2.5 text-sm font-semibold text-white shadow-sm transition-all hover:bg-sky-700 active:scale-[0.98] disabled:opacity-60"
          :disabled="loadingUrl"
          @click="submitUrl"
        >
          <UIcon
            name="i-lucide-link"
            class="size-4"
          />
          {{ loadingUrl ? 'Envoi…' : 'Extraire depuis l’URL' }}
        </button>

        <p
          v-if="jobIdUrl"
          class="rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 font-mono text-xs text-emerald-800"
          role="status"
        >
          Offre extraite — job {{ jobIdUrl }}
        </p>
        <p
          v-if="existingOfferId"
          class="rounded-lg border border-sky-200 bg-sky-50 px-3 py-2 text-xs text-sky-800"
          role="status"
        >
          Cette offre est déjà connue.
          <NuxtLink
            :to="`/offers/${existingOfferId}`"
            class="font-semibold underline underline-offset-2"
          >
            L’ouvrir
          </NuxtLink>
        </p>
        <p
          v-if="errorUrl"
          class="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700"
          role="alert"
        >
          {{ errorUrl }}
        </p>
      </div>
    </section>

    <section class="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <h2 class="text-sm font-bold uppercase tracking-wider text-slate-500">
        Depuis le texte
      </h2>
      <div class="mt-3 space-y-3">
        <label
          for="offer-text"
          class="block text-sm font-medium text-slate-700"
        >
          Texte de l’annonce
        </label>
        <textarea
          id="offer-text"
          v-model="text"
          rows="10"
          placeholder="Collez ici le texte de l’offre…"
          class="w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-2.5 text-sm outline-none transition-colors placeholder:text-slate-400 focus:border-sky-500 focus:ring-2 focus:ring-sky-500/25"
        />
        <button
          type="button"
          class="inline-flex items-center gap-2 rounded-lg bg-slate-900 px-4 py-2.5 text-sm font-semibold text-white shadow-sm transition-all hover:bg-slate-700 active:scale-[0.98] disabled:opacity-60"
          :disabled="loading"
          @click="submit"
        >
          <UIcon
            name="i-lucide-file-text"
            class="size-4"
          />
          {{ loading ? 'Extraction…' : 'Lancer l’extraction' }}
        </button>
        <p
          v-if="jobId"
          class="rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 font-mono text-xs text-emerald-800"
          role="status"
        >
          Extraction lancée — job {{ jobId }}
        </p>
        <p
          v-if="error"
          class="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700"
          role="alert"
        >
          {{ error }}
        </p>
      </div>
    </section>
  </div>
</template>
