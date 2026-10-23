<script setup lang="ts">
withDefaults(defineProps<{ compact?: boolean }>(), { compact: false })
</script>

<template>
  <NuxtLink
    to="/offers"
    class="flex items-center gap-2"
    aria-label="We.Info Jobs — liste des offres"
  >
    <span class="grid h-8 w-8 shrink-0 place-items-center rounded-lg bg-sky-600 text-white">
      <svg
        width="18"
        height="18"
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
    <span
      v-if="!compact"
      class="flex items-center gap-1.5"
    >
      <span class="text-base font-extrabold tracking-tight text-slate-900">We.Info</span>
      <span class="rounded bg-sky-100 px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wider text-sky-700">Jobs</span>
    </span>
  </NuxtLink>
</template>
