import { defineConfig } from '@vben/vite-config';

export default defineConfig(async () => {
  return {
    application: {
      nitroMock: false,
    },
    vite: {
      server: {
        proxy: {
          '/api': {
            changeOrigin: true,
            target: 'http://localhost:5001',
            ws: true,
          },
          '/auth': {
            changeOrigin: true,
            target: 'http://localhost:5001',
          },
          '/uploads': {
            changeOrigin: true,
            target: 'http://localhost:5001',
          },
        },
      },
    },
  };
});
