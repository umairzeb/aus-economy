import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// The Python pipeline writes JSON to public/data, which Vite serves as-is at /data.
export default defineConfig({
  plugins: [react()],
});
