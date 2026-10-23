<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()
const offerId = route.params.offerId as string
const api = useApi()

const loading = ref(true)
const error = ref<string | null>(null)
const publishing = ref(false)
const publishMsg = ref<string | null>(null)
const generating = ref(false)
const copiedId = ref<string | null>(null)
const variants = ref<{ id: string; variant: number; text: string | null }[]>([])
const imageUrl = ref<string | null>(null)
const edited = ref<Record<string, string>>({})

async function load() {
  loading.value = true
  error.value = null
  try {
    const { data: vData } = await api.get<{ items?: { id: string; variant: number; text: string | null }[] }>(`/api/v1/offers/${offerId}/copywriting`)
    if (vData?.items) {
      variants.value = vData.items
      for (const variant of variants.value) {
        edited.value[variant.id] = variant.text ?? ''
      }
    }
    const { data: aData } = await api.get<{ image_path?: string | null }[]>(`/api/v1/offers/${offerId}/assets`)
    if (Array.isArray(aData)) {
      const first = (aData).find((a) => a.image_path)
      if (first?.image_path) imageUrl.value = first.image_path
    }
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Erreur inconnue'
  } finally {
    loading.value = false
  }
}

async function generateVariants() {
  generating.value = true
  error.value = null
  try {
    const { error: err } = await api.post(`/api/v1/offers/${offerId}/copywriting`, { count: 3 })
    if (err) throw new Error(err.message)
    await load()
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Génération impossible.'
  } finally {
    generating.value = false
  }
}

async function saveVariant(variantId: string) {
  error.value = null
  const { error: err } = await api.patch(`/api/v1/offers/${offerId}/copywriting/${variantId}`, { text: edited.value[variantId] })
  if (err) {
    error.value = 'Enregistrement impossible.'
    return
  }
  publishMsg.value = 'Variante enregistrée.'
}

async function copy(text: string | null) {
  if (!text) return
  try {
    await navigator.clipboard.writeText(text)
    publishMsg.value = 'Texte copié dans le presse-papiers.'
  } catch {
    error.value = 'Copie impossible : sélectionnez le texte manuellement.'
  }
}

async function markPublished() {
  publishing.value = true
  publishMsg.value = null
  error.value = null
  try {
    const { error: err } = await api.post(`/api/v1/offers/${offerId}/publish`, { channel: 'export_manuel' })
    if (err) throw new Error(err.message)
    publishMsg.value = 'Offre marquée comme publiée.'
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Publication impossible.'
  } finally {
    publishing.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="mx-auto max-w-3xl space-y-6">
    <div class="flex flex-wrap items-center justify-between gap-3">
      <div>
        <h1 class="text-2xl font-extrabold tracking-tight text-slate-900">
          Préparer la publication
        </h1>
        <p class="mt-1 text-sm text-slate-600">
          Générez le texte de l’annonce, corrigez-le, puis copiez-le pour le canal.
        </p>
      </div>
      <NuxtLink
        :to="`/offers/${offerId}`"
        class="inline-flex items-center gap-1.5 rounded-lg px-2 py-1 text-sm font-semibold text-slate-500 transition-colors hover:bg-slate-100 hover:text-slate-900"
      >
        <UIcon
          name="i-lucide-arrow-left"
          class="size-4"
        />
        Retour à l’offre
      </NuxtLink>
    </div>

    <p
      v-if="loading"
      class="text-sm text-slate-500"
    >
      Chargement…
    </p>

    <template v-else>
      <section
        class="rounded-xl border border-slate-200 bg-white p-5 shadow-sm"
        aria-labelledby="variants-heading"
      >
        <div class="flex flex-wrap items-center justify-between gap-3">
          <h2
            id="variants-heading"
            class="text-sm font-bold uppercase tracking-wider text-slate-500"
          >
            Variantes de texte
          </h2>
          <button
            type="button"
            class="inline-flex items-center gap-2 rounded-lg bg-slate-900 px-3 py-2 text-xs font-semibold text-white shadow-sm transition-all hover:bg-slate-700 active:scale-[0.98] disabled:opacity-60"
            :disabled="generating"
            @click="generateVariants"
          >
            <UIcon
              name="i-lucide-wand-sparkles"
              class="size-3.5"
            />
            {{ generating ? 'Génération…' : 'Générer les variantes' }}
          </button>
        </div>

        <p
          v-if="variants.length === 0"
          class="mt-3 text-sm text-slate-500"
        >
          Aucune variante pour l’instant. Générez-en trois, puis retenez la meilleure.
        </p>

        <div
          v-else
          class="mt-4 space-y-4"
        >
          <article
            v-for="variant in variants"
            :key="variant.id"
            class="rounded-lg border border-slate-200 bg-slate-50/60 p-4"
          >
            <div class="flex items-center justify-between gap-3">
              <span class="rounded bg-slate-200 px-2 py-0.5 font-mono text-[10px] font-semibold uppercase tracking-wider text-slate-600">
                Variante {{ variant.variant + 1 }}
              </span>
              <div class="flex items-center gap-2">
                <button
                  type="button"
                  class="rounded-lg bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 ring-1 ring-slate-200 transition-colors hover:bg-slate-50"
                  @click="copy(edited[variant.id] ?? null)"
                >
                  Copier
                </button>
                <button
                  type="button"
                  class="rounded-lg bg-sky-600 px-3 py-1.5 text-xs font-semibold text-white transition-colors hover:bg-sky-700"
                  @click="saveVariant(variant.id)"
                >
                  Enregistrer
                </button>
              </div>
            </div>
            <textarea
              v-model="edited[variant.id]"
              rows="7"
              class="mt-3 w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm leading-relaxed outline-none transition-colors focus:border-sky-500 focus:ring-2 focus:ring-sky-500/25"
            />
          </article>
        </div>
      </section>

      <section
        class="rounded-xl border border-slate-200 bg-white p-5 shadow-sm"
        aria-labelledby="asset-heading"
      >
        <h2
          id="asset-heading"
          class="text-sm font-bold uppercase tracking-wider text-slate-500"
        >
          Visuel
        </h2>
        <img
          v-if="imageUrl"
          :src="imageUrl"
          alt="Aperçu du visuel généré"
          class="mt-3 w-full rounded-lg border border-slate-200"
        >
        <p
          v-else
          class="mt-3 text-sm text-slate-500"
        >
          Aucun visuel généré pour cette offre. La publication se fait manuellement : copiez le texte validé
          et envoyez-le sur le canal.
        </p>
      </section>

      <section class="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
        <button
          type="button"
          class="w-full rounded-lg bg-sky-600 px-4 py-3 text-sm font-semibold text-white shadow-sm transition-all hover:bg-sky-700 active:scale-[0.99] disabled:opacity-60"
          :disabled="publishing"
          @click="markPublished"
        >
          {{ publishing ? 'Publication…' : 'Marquer comme publiée' }}
        </button>
        <p
          v-if="publishMsg"
          class="mt-3 rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-800"
          role="status"
        >
          {{ publishMsg }}
        </p>
      </section>

      <p
        v-if="error"
        class="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700"
        role="alert"
      >
        {{ error }}
      </p>
    </template>
  </div>
</template>
