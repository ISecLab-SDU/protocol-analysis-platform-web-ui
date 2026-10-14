import { beforeEach } from 'vitest';

for (const storageName of ['localStorage', 'sessionStorage'] as const) {
  const storage = new window.Storage();
  Object.defineProperty(globalThis, storageName, {
    configurable: true,
    value: storage,
    writable: true,
  });
  Object.defineProperty(window, storageName, {
    configurable: true,
    value: storage,
    writable: true,
  });
}

beforeEach(() => {
  window.localStorage.clear();
  window.sessionStorage.clear();
});
