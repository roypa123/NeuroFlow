import js from '@eslint/js'
import globals from 'globals'
import reactHooks from 'eslint-plugin-react-hooks'
import reactRefresh from 'eslint-plugin-react-refresh'
import boundaries from 'eslint-plugin-boundaries'
import tseslint from 'typescript-eslint'
import { defineConfig, globalIgnores } from 'eslint/config'

// Layering rules from docs/04-frontend-architecture.md #4.5, enforced
// mechanically -- a layering rule that is not checked by CI is a comment.
// Only the rules that are cheaply and unambiguously encodable as import
// boundaries are included here; "no business logic in components" has no
// import-graph signature and stays a code-review concern.
const elementTypes = [
  { type: 'config', pattern: 'src/config/**' },
  { type: 'types', pattern: 'src/types/**' },
  { type: 'utils', pattern: 'src/utils/**' },
  { type: 'api', pattern: 'src/api/**' },
  { type: 'endpoints', pattern: 'src/endpoints/**' },
  { type: 'store', pattern: 'src/store/**' },
  { type: 'lib', pattern: 'src/lib/**' },
  { type: 'hooks', pattern: 'src/hooks/**' },
  { type: 'context', pattern: 'src/context/**' },
  { type: 'ui', pattern: 'src/components/ui/**' },
  { type: 'components', pattern: 'src/components/**' },
  { type: 'routing', pattern: 'src/routing/**' },
  { type: 'pages', pattern: 'src/pages/**' },
  { type: 'spike', pattern: 'src/spike/**' },
  { type: 'test', pattern: 'src/test/**' },
]

export default defineConfig([
  globalIgnores([
    'dist',
    // Vendored shadcn primitives -- regenerated via the shadcn CLI, never
    // hand-edited (docs/04-frontend-architecture.md #4.4). Excluded from
    // lint the same way generated code is, rather than suppressed rule by
    // rule for every file the CLI drops in.
    'src/components/ui/**',
  ]),
  {
    files: ['**/*.{ts,tsx}'],
    extends: [
      js.configs.recommended,
      tseslint.configs.recommended,
      reactHooks.configs.flat.recommended,
      reactRefresh.configs.vite,
    ],
    languageOptions: {
      globals: globals.browser,
    },
    settings: {
      'boundaries/elements': elementTypes,
      'boundaries/ignore': ['src/main.tsx', 'src/vite-env.d.ts', 'src/spike/**'],
      // Without this, eslint-plugin-boundaries can't resolve TS path
      // aliases or extensionless imports to a file on disk -- every
      // internal import comes back unresolved and every dependency rule
      // silently no-ops. Verified against a live violation before trusting
      // this config: see the git history on this file.
      'import/resolver': {
        typescript: { project: './tsconfig.app.json' },
      },
    },
    plugins: { boundaries },
    rules: {
      'boundaries/dependencies': [
        'error',
        {
          default: 'allow',
          policies: [
            // config/ is a leaf: nothing in src/ may be imported by it
            // (docs/04-frontend-architecture.md #4.5 rule 3).
            {
              from: { element: { type: 'config' } },
              disallow: {
                to: {
                  element: {
                    types: { anyOf: elementTypes.map((e) => e.type).filter((t) => t !== 'config') },
                  },
                },
              },
              message: 'config/ must not import from src/ (docs/04 #4.5 rule 3).',
            },
            // utils/ is pure: no React, no endpoints, no store, no
            // components (docs/04 #4.5 rule 2).
            {
              from: { element: { type: 'utils' } },
              disallow: {
                to: {
                  element: {
                    types: { anyOf: ['endpoints', 'store', 'components', 'context', 'hooks', 'ui'] },
                  },
                },
              },
              message: 'utils/ must be pure -- no React, no endpoints, no store, no components (docs/04 #4.5 rule 2).',
            },
            // types/ carries no runtime dependencies beyond utils/other
            // types (docs/04 #4.5 rule 4).
            {
              from: { element: { type: 'types' } },
              disallow: {
                to: {
                  element: {
                    types: { anyOf: ['endpoints', 'store', 'components', 'context', 'hooks', 'ui', 'api', 'pages'] },
                  },
                },
              },
              message: 'types/ must not import runtime values beyond utils (docs/04 #4.5 rule 4).',
            },
            // Components never call the transport layer directly -- they go
            // through endpoints/ hooks (docs/04 #4.5 rule 1). Narrowed to
            // the transport internals specifically: ApiError/isApiError are
            // the documented exception (docs/04 #4.4's own file comment on
            // api/errors.ts) -- branching UI on error shape in a page is
            // expected, calling apiClient from one is not.
            {
              from: { element: { types: { anyOf: ['components', 'ui', 'pages'] } } },
              to: { element: { type: 'api' } },
              disallow: {
                dependency: {
                  specifiers: ['apiClient', 'setAccessToken', 'getAccessToken', 'registerSessionExpiredHandler'],
                },
              },
              message: 'Use an endpoints/ hook instead of importing the transport layer directly (docs/04 #4.5 rule 1).',
            },
          ],
        },
      ],
    },
  },
  {
    // Context providers legitimately co-locate a hook with its provider
    // component in one file (useAuth + AuthProvider, useTheme +
    // ThemeProvider) -- an intentional pattern, not an oversight.
    // routes.tsx exports the router object alongside route element
    // factories for the same reason. Losing fast-refresh on these
    // infrequently-edited files is an acceptable trade.
    files: ['src/context/**/*.tsx', 'src/routing/routes.tsx'],
    rules: {
      'react-refresh/only-export-components': 'off',
    },
  },
])
