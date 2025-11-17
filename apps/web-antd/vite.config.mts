import { defineConfig } from '@vben/vite-config';
import path from 'node:path';

export default defineConfig(async () => {
  return {
    application: {
      nitroMock: false,
    },
    vite: {
      resolve: {
        alias: {
          '@': path.resolve(__dirname, 'src'),
          },
      },
      server: {
        proxy: {
          '/api': {
            changeOrigin: true,
            target: 'http://localhost:5000',
            ws: true,
          },
          '/auth': {
            changeOrigin: true,
            target: 'http://localhost:5000',
          },
          '/uploads': {
            changeOrigin: true,
            target: 'http://localhost:5000',
          },
        },
      },
    },
  };
});
