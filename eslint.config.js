import js from '@eslint/js'
import prettier from 'eslint-config-prettier'
import betterTailwindcss from 'eslint-plugin-better-tailwindcss'
import svelte from 'eslint-plugin-svelte'
import globals from 'globals'
import ts from 'typescript-eslint'

export default ts.config(
  {
    ignores: [
      'frontend/types/generated',
      'node_modules',
      'app/static',
      'coverage',
      'playwright-report',
      'test-results',
      'tmp',
      'data',
      '.venv',
    ],
  },
  js.configs.recommended,
  ts.configs.recommended,
  svelte.configs.recommended,
  prettier,
  svelte.configs.prettier,
  {
    languageOptions: { globals: { ...globals.browser, ...globals.node } },
    rules: {
      // {' '} keeps the space between an expression and the markup after it
      'svelte/no-useless-mustaches': 'off',
    },
  },
  {
    files: ['**/*.svelte', '**/*.svelte.ts'],
    languageOptions: { parserOptions: { parser: ts.parser } },
  },
  {
    // Tailwind classes in the frontend (WISP 3's eslint.config.js). Prettier's Tailwind plugin sorts
    // them, so only the rules about the classes themselves are on: Tailwind v4's own spelling of a
    // class (h-128, not h-[32rem]), pairs one class covers (p-2, not px-2 py-2), its renamed classes
    // (rounded is rounded-sm), and duplicates or conflicts. Unknown classes aren't checked: our own
    // classes (keep-motion, countdown) look unknown
    files: ['frontend/**/*.{svelte,ts}'],
    plugins: { 'better-tailwindcss': betterTailwindcss },
    settings: { 'better-tailwindcss': { entryPoint: 'frontend/entrypoints/application.css' } },
    rules: {
      'better-tailwindcss/enforce-canonical-classes': 'error',
      'better-tailwindcss/no-deprecated-classes': 'error',
      'better-tailwindcss/no-duplicate-classes': 'error',
      'better-tailwindcss/no-conflicting-classes': 'error',
      // Merging a pair leaves a gap where the class was, which Prettier keeps
      'better-tailwindcss/no-unnecessary-whitespace': 'error',
    },
  },
)
