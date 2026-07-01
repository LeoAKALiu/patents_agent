import { createRequire } from "node:module";
import { fileURLToPath, URL } from "node:url";

const requireFromFrontend = createRequire(
  new URL("../../frontend/package.json", import.meta.url),
);

const { defineConfig } = requireFromFrontend("vite") as typeof import("vite");
const react = requireFromFrontend("@vitejs/plugin-react").default as typeof import("@vitejs/plugin-react").default;
const tailwindcss = requireFromFrontend("@tailwindcss/vite").default as typeof import("@tailwindcss/vite").default;

export default defineConfig({
  base: "./",
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("../../frontend/src", import.meta.url)),
    },
  },
  server: {
    port: 5175,
    proxy: {
      "/api": "http://127.0.0.1:8001",
    },
  },
});
