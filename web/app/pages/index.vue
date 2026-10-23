<script setup lang="ts">
/**
 * The application has no landing page: the first thing an operator needs is
 * the state of the collection, so the root redirects to the dashboard.
 */
navigateTo('/dashboard', { replace: true })
</script>

<template>
  <div />
</template>
