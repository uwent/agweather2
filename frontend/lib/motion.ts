// Ported from WISP 3: app/frontend/lib/motion.ts
// Reduced motion (WCAG 2.3.3). CSS transitions and animations are cut short in application.css;
// Svelte's transitions run through the Web Animations API, so they take their duration from here.

/** A transition's duration, or 0 when the user asked for less motion */
export function motion(ms: number): number {
  return typeof matchMedia !== 'undefined' && matchMedia('(prefers-reduced-motion: reduce)').matches ? 0 : ms
}
