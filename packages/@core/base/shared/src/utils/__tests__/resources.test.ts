import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { loadScript } from '../resources';

const testJsPath = '/assets/test-script.js';
const errorJsPath = '/assets/error-script.js';
const appendedScripts: HTMLScriptElement[] = [];
const nativeQuerySelector = document.querySelector.bind(document);

describe('loadScript', () => {
  beforeEach(() => {
    // 每个测试前清空 head，保证环境干净
    document.head.innerHTML = '';
    appendedScripts.length = 0;
    vi.spyOn(document, 'querySelector').mockImplementation((selectors) => {
      const src = /^script\[src="(.*)"\]$/.exec(selectors)?.[1];
      if (src) {
        return (
          appendedScripts.find(
            (script) => script.getAttribute('src') === src,
          ) ?? null
        );
      }
      return nativeQuerySelector(selectors);
    });
    vi.spyOn(document.head, 'append').mockImplementation((...nodes) => {
      for (const node of nodes) {
        if (node instanceof HTMLScriptElement) {
          appendedScripts.push(node);
        }
      }
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('should resolve when the script loads successfully', async () => {
    const promise = loadScript(testJsPath);

    // 脚本元素已被创建，并传给 head.append
    const script = document.querySelector(
      `script[src="${testJsPath}"]`,
    ) as HTMLScriptElement;
    expect(script).toBeTruthy();
    expect(script.type).toBe('');

    // 触发一次 load，确认 helper 能完成对应 promise
    script.dispatchEvent(new Event('load'));

    // 等待 promise resolve
    await expect(promise).resolves.toBeUndefined();
  });

  it('should not insert duplicate script and resolve immediately if already loaded', async () => {
    // 先通过 helper 加载脚本并完成 load 事件
    const initialLoad = loadScript(testJsPath);
    const existing = document.querySelector(
      `script[src="${testJsPath}"]`,
    ) as HTMLScriptElement;
    expect(existing).toBeTruthy();
    existing.dispatchEvent(new Event('load'));
    await expect(initialLoad).resolves.toBeUndefined();

    // 再次调用应复用已加载的 script
    const promise = loadScript(testJsPath);

    await expect(promise).resolves.toBeUndefined();

    // 只向 head.append 传入一次 script
    expect(appendedScripts).toHaveLength(1);
  });

  it('should reject when the script fails to load', async () => {
    const promise = loadScript(errorJsPath);

    const script = document.querySelector(
      `script[src="${errorJsPath}"]`,
    ) as HTMLScriptElement;
    expect(script).toBeTruthy();

    // 模拟加载失败
    script.dispatchEvent(new Event('error'));

    await expect(promise).rejects.toThrow(
      `Failed to load script: ${errorJsPath}`,
    );
  });

  it('should handle multiple concurrent calls and only insert one script tag', async () => {
    const p1 = loadScript(testJsPath);
    const p2 = loadScript(testJsPath);

    const script = document.querySelector(
      `script[src="${testJsPath}"]`,
    ) as HTMLScriptElement;
    expect(script).toBeTruthy();

    // 一次 load 事件应同时完成两个并发调用
    script.dispatchEvent(new Event('load'));

    await expect(p1).resolves.toBeUndefined();
    await expect(p2).resolves.toBeUndefined();

    // 只向 head.append 传入一次 script
    expect(appendedScripts).toHaveLength(1);
  });
});
