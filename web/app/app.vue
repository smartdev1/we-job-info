<script setup lang="ts">
const route = useRoute()
const auth = useAuthStore()

const navigation = [
  { label: 'Offres', to: '/offers' },
  { label: 'Tableau de bord', to: '/dashboard' }
]

const initials = computed(() => {
  const email = auth.user?.email ?? ''
  const name = email.split('@')[0] ?? ''
  if (!name) {
    return 'WI'
  }
  return name.slice(0, 2).toUpperCase()
})

function isActive(to: string) {
  return route.path === to
}

useHead({
  htmlAttrs: { lang: 'fr' },
  title: 'We.Info Jobs :-)',
  meta: [
    { name: 'description', content: 'Collecte, validation et publication des offres d\'emploi.' },
    { name: 'viewport', content: 'width=device-width, initial-scale=1' }
  ],
  link: [{ rel: 'icon', href: '/favicon.ico' }]
})
</script>

<template>
  <UApp>
    <header class="sticky top-0 z-40 border-b border-slate-200 bg-white/95 backdrop-blur">
      <div class="mx-auto flex h-16 max-w-7xl items-center gap-6 px-4 sm:px-6 lg:px-8">
        <BrandLogo />

        <nav
          class="hidden items-center gap-6 text-sm md:flex"
          aria-label="Navigation principale"
        >
          <NuxtLink
            v-for="item in navigation"
            :key="item.to"
            :to="item.to"
            class="border-b-2 pb-1 font-semibold transition-colors"
            :class="isActive(item.to)
              ? 'border-sky-600 text-sky-700'
              : 'border-transparent text-slate-600 hover:text-slate-900'"
          >
            {{ item.label }}
          </NuxtLink>
        </nav>

        <div class="ml-auto flex items-center gap-2">
          <UButton
            to="/offers/new"
            color="primary"
            size="sm"
            icon="i-lucide-plus"
            class="font-semibold"
          >
            Nouvelle offre
          </UButton>

          <UButton
            v-if="!auth.isAuthenticated"
            to="/login"
            color="neutral"
            variant="ghost"
            size="sm"
            icon="i-lucide-log-in"
          >
            Connexion
          </UButton>
          <UAvatar
            v-else
            :text="initials"
            size="sm"
            class="ring-2 ring-slate-200"
          />
        </div>
      </div>
    </header>

    <main class="mx-auto w-full max-w-7xl flex-1 px-4 py-8 sm:px-6 lg:px-8">
      <NuxtPage />
    </main>

    <footer class="border-t border-slate-200 bg-white">
      <div class="mx-auto flex max-w-7xl flex-col items-center justify-between gap-4 py-6 text-sm text-slate-600 md:flex-row">
        <p class="flex items-center gap-2">
          <BrandLogo compact />
          <span>© {{ new Date().getFullYear() }} We.Info Jobs :-)</span>
          <span aria-hidden="true">•</span>
          <span>Tous droits réservés</span>
        </p>
        <nav
          class="flex flex-wrap gap-6"
          aria-label="Liens de pied de page"
        >
          <NuxtLink
            v-for="item in navigation"
            :key="item.to"
            :to="item.to"
            class="transition-colors hover:text-slate-900"
          >
            {{ item.label }}
          </NuxtLink>
        </nav>
      </div>
    </footer>
  </UApp>
</template>
