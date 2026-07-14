import { mount } from '@vue/test-utils';

import { describe, expect, it } from 'vitest';

import StageAssertGen from './StageAssertGen.vue';

describe('stageAssertGen structured logs', () => {
  it('renders Claude Agent SDK events with the shared timeline component', () => {
    const wrapper = mount(StageAssertGen, {
      global: {
        stubs: {
          Card: {
            template:
              '<section><slot name="title" /><slot /><slot name="extra" /></section>',
          },
          Empty: true,
          IconifyIcon: true,
          Tag: true,
        },
      },
      props: {
        diffContent: '',
        events: [
          {
            message: 'Preparing assertion generation inputs',
            stage: 'init',
            timestamp: '2026-07-14T05:00:00Z',
          },
          {
            message: 'Preparing instrumentation environment',
            stage: 'instrumentation',
            timestamp: '2026-07-14T05:00:01Z',
          },
          {
            message: 'Bash: make instrumented',
            metadata: {
              sdk_message_type: 'ToolUseBlock',
              tool: 'Bash',
              tool_input: {
                command: 'make instrumented',
                description: '构建插桩后的目标程序',
              },
            },
            stage: 'claude-command',
            timestamp: '2026-07-14T05:00:02Z',
          },
        ],
        logText: '',
        result: null,
        running: true,
      },
    });

    const claudeLine = wrapper.get('.claude-line--command');
    expect(claudeLine.text()).toContain('LLM 断言插桩');
    expect(claudeLine.text()).toContain('make instrumented');
    expect(claudeLine.text()).toContain('构建插桩后的目标程序');
    expect(wrapper.text()).not.toContain('PG_PROGRESS_JSON');
  });
});
