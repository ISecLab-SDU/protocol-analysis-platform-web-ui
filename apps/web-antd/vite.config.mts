import path from 'node:path';
import process from 'node:process';

import { defineConfig } from '@vben/vite-config';

export default defineConfig(async () => {
  const backendProxyTarget =
    process.env.VITE_BACKEND_PROXY_TARGET || 'http://localhost:5000';

  return {
    application: {
      nitroMock: false,
    },
    vite: {
      resolve: {
        alias: {
          '@': path.resolve(import.meta.dirname, 'src'),
        },
      },
      server: {
        proxy: {
          '/api': {
            changeOrigin: true,
            target: backendProxyTarget,
            ws: true,
          },
          '/auth': {
            changeOrigin: true,
            target: backendProxyTarget,
          },
          '/uploads': {
            changeOrigin: true,
            target: backendProxyTarget,
          },
        },
      },
    },
  };
});
