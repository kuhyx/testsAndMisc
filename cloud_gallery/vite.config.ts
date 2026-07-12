import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

// base: "./" so the built asset URLs are relative. The app is served by dufs
// with `render-spa` from the cloud root, and uses HashRouter, so the document
// path is always "/" and "./assets/..." resolves to "/assets/...".
export default defineConfig({
  base: "./",
  plugins: [react()],
  server: { port: 5273 },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/test/setup.ts"],
    coverage: {
      provider: "v8",
      include: ["src/**/*.{ts,tsx}"],
      exclude: ["src/main.tsx", "src/test/**", "src/**/*.d.ts"],
      thresholds: { statements: 90, branches: 85, functions: 90, lines: 90 },
    },
  },
});
