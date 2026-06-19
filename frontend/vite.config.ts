import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import { fileURLToPath, URL } from "node:url";

export default defineConfig({
  base: "./",
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./src", import.meta.url)),
    },
  },
  server: {
    port: 5173,
    proxy: {
      "/api": "http://127.0.0.1:8000",
    },
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks(id: string) {
          // Split large vendor deps into separate chunks to keep the
          // main app chunk under Vite's default 500 kB warning limit.
          if (id.includes("node_modules/react-dom/") || id.includes("node_modules/react/")) {
            return "vendor-react";
          }
          if (id.includes("node_modules/lucide-react/")) {
            return "vendor-icons";
          }
          if (id.includes("node_modules/@radix-ui/") || id.includes("node_modules/radix-ui/")) {
            return "vendor-radix";
          }
          if (id.includes("node_modules/class-variance-authority/") || id.includes("node_modules/clsx/") ||
              id.includes("node_modules/tailwind-merge/") || id.includes("node_modules/sonner/") ||
              id.includes("node_modules/next-themes/")) {
            return "vendor-ui-utils";
          }
        },
      },
    },
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/test-setup.ts"],
  },
});
