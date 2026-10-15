import { mount } from '@vue/test-utils';

import { beforeEach, describe, expect, it, vi } from 'vitest';

import { useAnalysisModules } from '../useAnalysisModules';
import AssertGenerationModule from './AssertGenerationModule.vue';

vi.mock('../useAnalysisModules', async () => {
  const { reactive } = await import('vue');
  const state = reactive({
    assertGeneration: {
      diffContent: '',
      error: '',
      job: null,
      logText: '',
      result: null,
      started: false,
      status: 'idle',
    },
    assertInputs: { analysisDocument: null, codeArchive: null },
    codeLocate: { result: null },
  });
  return {
    useAnalysisModules: () => ({
      ...state,
      resetAssertGenerationOutput: () => {
        state.assertGeneration.started = false;
        state.assertGeneration.status = 'idle';
      },
      runAssertGeneration: () => {
        state.assertGeneration.started = true;
        state.assertGeneration.status = 'running';
      },
      stopAssertGeneration: () => {
        state.assertGeneration.status = 'stopped';
      },
      useLatestCodeLocateOutput: vi.fn(),
    }),
  };
});
vi.mock('#/api/protocol-compliance', () => ({
  downloadProtocolAssertionArtifact: vi.fn(),
}));

const modules = useAnalysisModules();

function renderModule() {
  return mount(AssertGenerationModule, {
    global: {
      stubs: {
        Button: { template: '<button><slot /></button>' },
        Card: {
          template: '<section><h2>{{ title }}</h2><slot /></section>',
          props: ['title'],
        },
        IconifyIcon: true,
        StageAssertGen: { template: '<section data-testid="status" />' },
        Tag: true,
        Upload: { template: '<div><slot /></div>' },
      },
    },
  });
}

beforeEach(() => {
  modules.assertGeneration.started = false;
  modules.assertGeneration.status = 'idle';
});

describe('assertion generation workspace', () => {
  it('starts with inputs and no runtime settings or status card', () => {
    const wrapper = renderModule();
    expect(wrapper.text()).toContain('开始断言生成');
    expect(wrapper.text()).toContain('源码压缩包');
    expect(wrapper.text()).not.toContain('断言插桩运行时');
    expect(wrapper.find('[data-testid="status"]').exists()).toBe(false);
  });

  it('replaces inputs with the focused status card and returns after stopping', async () => {
    const wrapper = renderModule();
    const start = wrapper
      .findAll('button')
      .find((button) => button.text() === '开始断言生成');
    await start?.trigger('click');
    expect(wrapper.find('[data-testid="status"]').exists()).toBe(true);
    expect(wrapper.classes()).toContain('analysis-module--focused');
    expect(wrapper.text()).not.toContain('源码压缩包');
    expect(wrapper.text()).not.toContain('开始断言生成');
    expect(wrapper.text()).not.toContain('返回输入');
    await wrapper
      .findAll('button')
      .find((button) => button.text() === '停止')
      ?.trigger('click');
    expect(wrapper.find('[data-testid="status"]').exists()).toBe(true);
    await wrapper
      .findAll('button')
      .find((button) => button.text() === '返回输入')
      ?.trigger('click');
    expect(wrapper.find('[data-testid="status"]').exists()).toBe(false);
    expect(wrapper.text()).toContain('开始断言生成');
  });
});
