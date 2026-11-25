<script lang="ts">
  import ThemeToggle from './ThemeToggle.svelte'
</script>

<!-- University branding above every page, with the light/dark toggle -->
<div class="bg-uw-red text-white dark:bg-uw-red-dark">
  <div
    class="mx-auto flex h-9 max-w-6xl items-center justify-between px-4 text-xs font-medium tracking-wide sm:text-sm"
  >
    <a href="https://www.wisc.edu" class="hover:underline">University of Wisconsin–Madison</a>
    <ThemeToggle />
  </div>
</div>
