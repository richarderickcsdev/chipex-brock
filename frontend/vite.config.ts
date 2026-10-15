import { defineConfig } from 'vitest/config';
import { loadEnv } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';
import { VitePWA } from 'vite-plugin-pwa';

export default defineConfig(({ mode, command }) => {
  const env = loadEnv(mode, process.cwd(), '');
  return {
    define: {
      'import.meta.env.VITE_API_URL': JSON.stringify(
        command === 'serve' && mode !== 'test'
          ? '/api'
          : (env.VITE_API_URL ?? ''),
      ),
    },
    server: {
      proxy: env.VITE_API_URL?.startsWith('https://')
        ? {
            '/api': {
              target: env.VITE_API_URL,
              changeOrigin: true,
              rewrite: (path) => path.replace(/^\/api/, ''),
            },
          }
        : undefined,
    },
    plugins: [
      react(),
      tailwindcss(),
      VitePWA({
        registerType: 'prompt',
        manifest: {
          id: '/',
          name: 'Brock — Planificador de comidas',
          short_name: 'Brock',
          lang: 'es',
          start_url: '/',
          display: 'standalone',
          theme_color: '#166534',
          background_color: '#f0fdf4',
          icons: [
            {
              src: '/brock-192.png',
              sizes: '192x192',
              type: 'image/png',
              purpose: 'any',
            },
            {
              src: '/brock-512.png',
              sizes: '512x512',
              type: 'image/png',
              purpose: 'any',
            },
            {
              src: '/brock-512.png',
              sizes: '512x512',
              type: 'image/png',
              purpose: 'maskable',
            },
            {
              src: '/brock.svg',
              sizes: 'any',
              type: 'image/svg+xml',
              purpose: 'any',
            },
          ],
        },
        workbox: { navigateFallbackDenylist: [/^\/api\//], runtimeCaching: [] },
      }),
    ],
    test: {
      environment: 'jsdom',
      setupFiles: ['./tests/setup.ts'],
      include: ['src/**/*.test.{ts,tsx}', 'tests/**/*.test.{ts,tsx}'],
      passWithNoTests: false,
    },
  };
});
