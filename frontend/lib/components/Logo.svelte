<script lang="ts">
  let { class: className = '' }: { class?: string } = $props()
</script>

<span class="font-display inline-flex items-center gap-2 font-semibold tracking-tight {className}">
  <img src="/static/icon.svg" alt="" class="size-7" />
  <span>AgWeather</span>
</span>
