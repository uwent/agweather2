<!-- A model's status as a small label: "Beta" until it's validated and the app launches (D46), "Stable" after -->
<script lang="ts">
  let { status, class: className = '' }: { status: string; class?: string } = $props()

  const label = $derived(status === 'beta' ? 'Beta' : status === 'stable' ? 'Stable' : 'Retired')
</script>

<span class="inline-block rounded-full border border-line px-2 py-px text-xs font-medium text-ink-muted {className}">
  {label}
</span>
