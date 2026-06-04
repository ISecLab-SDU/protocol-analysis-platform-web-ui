import { defineConfig } from '@vben/vite-config';
import fs from 'node:fs';
import type { ServerResponse } from 'node:http';
import path from 'node:path';
import type { Plugin } from 'vite';

const DEMO_INPUT_ROUTE = '/New-Input/';
const DEMO_INPUT_DIR = path.resolve(__dirname, '../..', 'New-Input');
const DEMO_INPUT_MIME_TYPES: Record<string, string> = {
  '.json': 'application/json',
  '.tar': 'application/x-tar',
  '.toml': 'application/toml',
};

function resolveDemoInputRequest(requestUrl?: string) {
  if (!requestUrl) return null;
  const pathname = new URL(requestUrl, 'http://localhost').pathname;
  const routeIndex = pathname.indexOf(DEMO_INPUT_ROUTE);
  if (routeIndex === -1) return null;

  const relativeName = decodeURIComponent(
    pathname.slice(routeIndex + DEMO_INPUT_ROUTE.length),
  );
  if (
    !relativeName ||
    relativeName.includes('/') ||
    relativeName.includes('\\')
  ) {
    return null;
  }

  const filePath = path.resolve(DEMO_INPUT_DIR, relativeName);
  if (!filePath.startsWith(`${DEMO_INPUT_DIR}${path.sep}`)) return null;
  return filePath;
}

function sendDemoInputFile(
  requestUrl: string | undefined,
  response: ServerResponse,
) {
  const filePath = resolveDemoInputRequest(requestUrl);
  if (!filePath) return false;
  if (!fs.existsSync(filePath) || !fs.statSync(filePath).isFile()) {
    response.statusCode = 404;
    response.end('Demo input file not found');
    return true;
  }

  const contentType =
    path.basename(filePath) === 'Dockerfile'
      ? 'text/plain'
      : DEMO_INPUT_MIME_TYPES[path.extname(filePath).toLowerCase()] ||
        'application/octet-stream';
  response.setHeader('Content-Type', contentType);
  response.setHeader('Cache-Control', 'no-store');
  fs.createReadStream(filePath).pipe(response);
  return true;
}

function demoInputStaticPlugin(): Plugin {
  return {
    name: 'protocol-demo-input-static',
    configurePreviewServer(server) {
      server.middlewares.use((request, response, next) => {
        if (sendDemoInputFile(request.url, response)) return;
        next();
      });
    },
    configureServer(server) {
      server.middlewares.use((request, response, next) => {
        if (sendDemoInputFile(request.url, response)) return;
        next();
      });
    },
  };
}

export default defineConfig(async () => {
  return {
    application: {
      nitroMock: false,
    },
    vite: {
      plugins: [demoInputStaticPlugin()],
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
