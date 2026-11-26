<!-- Ported from WISP 3: app/frontend/lib/components/Button.svelte -->
<script lang="ts">
  import type { Snippet } from 'svelte'
  import type { HTMLButtonAttributes } from 'svelte/elements'

  type Variant = 'primary' | 'secondary' | 'danger' | 'ghost' | 'danger-ghost'

  let {
    variant = 'primary',
    type = 'button',
    class: className = '',
    children,
    ...rest
  }: Omit<HTMLButtonAttributes, 'class'> & { class?: string; variant?: Variant; children: Snippet } = $props()

  // Hover only while enabled: a disabled button (its own, or its fieldset's) stays as it is
  const variants: Record<Variant, string> = {
    primary: 'bg-brand-600 text-white enabled:hover:bg-brand-700 dark:text-surface',
    secondary: 'border border-line bg-surface-raised text-ink enabled:hover:bg-surface',
    danger: 'bg-danger text-white enabled:hover:opacity-90',
    ghost: 'text-brand-600 enabled:hover:bg-brand-50',
    'danger-ghost': 'text-danger-ink enabled:hover:bg-danger/10',
  }

  // A class setting the padding or text size replaces the default rather than joining it: Tailwind
  // orders same-property utilities by its own rules, not the class list, so py-1 beside py-2 loses
  const padX = $derived(/(^|\s)!?p[x]?-/.test(className) ? '' : 'px-4')
  const padY = $derived(/(^|\s)!?p[y]?-/.test(className) ? '' : 'py-2')
  const size = $derived(/(^|\s)!?text-(xs|sm|base|lg|xl)(\s|$)/.test(className) ? '' : 'text-sm')
</script>

<button
  {type}
  class="inline-flex items-center justify-center gap-2 rounded-md {padX} {padY} {size} font-medium transition
    focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand-500
    disabled:cursor-not-allowed disabled:opacity-60 {variants[variant]} {className}"
  {...rest}
>
  {@render children()}
</button>
