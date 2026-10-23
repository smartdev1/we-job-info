<script setup lang="ts">
/**
 * The root page is the entry point of the tool: an operator must sign in
 * before anything else, so the root redirects to the login page.
 */
navigateTo('/login', { replace: true })
</script>

<template>
  <div />
</template>