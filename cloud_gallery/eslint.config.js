import js from "@eslint/js";
import reactHooksPlugin from "eslint-plugin-react-hooks";
import tseslint from "typescript-eslint";

// Aggressive, type-aware config: everything typescript-eslint's strict +
// stylistic *type-checked* presets flag is an error, plus the React Hooks
// rules. Unused disable directives are themselves errors, so every
// `eslint-disable` must be load-bearing.
//
// eslint-plugin-react is intentionally omitted: 7.37.x still calls the
// `context.getFilename()` API that ESLint 10 removed, so it crashes the run.
// TypeScript already covers prop typing, and react-hooks (v10-ready) covers the
// hook-specific rules that TS cannot.
export default tseslint.config(
  { ignores: ["dist", "coverage"] },
  { linterOptions: { reportUnusedDisableDirectives: "error" } },
  js.configs.recommended,
  ...tseslint.configs.strictTypeChecked,
  ...tseslint.configs.stylisticTypeChecked,
  {
    files: ["**/*.{ts,tsx}"],
    plugins: { "react-hooks": reactHooksPlugin },
    languageOptions: {
      parserOptions: {
        project: "./tsconfig.json",
        tsconfigRootDir: import.meta.dirname,
      },
    },
    rules: {
      ...reactHooksPlugin.configs.recommended.rules,
      "@typescript-eslint/restrict-template-expressions": [
        "error",
        { allowNumber: true },
      ],
    },
  },
  {
    // Asserting on a vitest mock method (e.g. `expect(client.remove)`) trips
    // unbound-method even though the reference is safe; disable it in tests.
    files: ["**/*.test.{ts,tsx}", "src/test/**"],
    rules: { "@typescript-eslint/unbound-method": "off" },
  },
  {
    files: ["*.js", "*.mjs", "*.cjs"],
    ...tseslint.configs.disableTypeChecked,
  },
);
