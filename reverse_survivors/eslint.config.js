import js from '@eslint/js'
import react from '@eslint-react/eslint-plugin'
import vitest from '@vitest/eslint-plugin'
import { defineConfig } from 'eslint/config'
import reactHooks from 'eslint-plugin-react-hooks'
import reactRefresh from 'eslint-plugin-react-refresh'
import globals from 'globals'
import tseslint from 'typescript-eslint'

export default defineConfig(
  { ignores: ['dist', 'coverage', 'node_modules'] },
  {
    files: ['**/*.{ts,tsx}'],
    extends: [
      js.configs.recommended,
      tseslint.configs.strictTypeChecked,
      tseslint.configs.stylisticTypeChecked,
      react.configs['strict-type-checked'],
      reactHooks.configs.flat.recommended,
      reactRefresh.configs.vite,
    ],
    languageOptions: {
      globals: globals.browser,
      parserOptions: {
        projectService: true,
        tsconfigRootDir: import.meta.dirname,
      },
    },
    rules: {
      '@typescript-eslint/explicit-function-return-type': 'error',
      '@typescript-eslint/consistent-type-imports': 'error',
      '@typescript-eslint/no-shadow': 'error',
      'no-console': 'error',
      'eqeqeq': ['error', 'always'],
      'prefer-const': ['error', { destructuring: 'all' }],
    },
  },
  {
    files: ['src/**/*.test.{ts,tsx}', 'src/test/**/*.ts'],
    extends: [vitest.configs.recommended],
    languageOptions: { globals: { ...globals.browser, ...globals.node } },
  },
  {
    files: ['eslint.config.js'],
    extends: [tseslint.configs.disableTypeChecked],
  },
)
