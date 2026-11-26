<!-- Ported from WISP 3: app/frontend/test/FakeForm.svelte -->
<script lang="ts" module>
  // A stand-in for Inertia's <Form> in component tests: renders its children with the errors set
  // here (as the server would send them back), and calls onError with them.
  // vi.mock('@inertiajs/svelte', async () => ({ ...(await import('@/test/page.svelte')), Form: (await import('@/test/FakeForm.svelte')).default }))
  export const form = $state({ errors: {} as Record<string, string> })
</script>

<script lang="ts">
  import type { Snippet } from 'svelte'

  let {
    children,
    onError,
    class: className,
  }: {
    children: Snippet<[{ errors: Record<string, string>; processing: boolean }]>
    onError?: (errors: Record<string, string>) => void
    class?: string
    [key: string]: unknown
  } = $props()

  $effect(() => {
    if (Object.keys(form.errors).length) onError?.(form.errors)
  })
</script>

<form class={className}>{@render children({ errors: form.errors, processing: false })}</form>
