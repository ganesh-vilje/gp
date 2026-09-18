import { fileURLToPath } from "node:url";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./src", import.meta.url)),
    },
  },
  test: {
    environment: "jsdom",
    // No islands/components have tests yet (T-002 is scaffolding only); real
    // suites land with the islands that introduce them (T-011+).
    passWithNoTests: true,
  },
});
