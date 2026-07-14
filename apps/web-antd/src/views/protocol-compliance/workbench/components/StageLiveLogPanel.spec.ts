import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import process from 'node:process';

import { mount } from '@vue/test-utils';

import { describe, expect, it } from 'vitest';

import StageLiveLogPanel from './StageLiveLogPanel.vue';

describe('stageLiveLogPanel', () => {
  it('renders log metadata and body in the same flow line', () => {
    const wrapper = mount(StageLiveLogPanel, {
      props: {
        lines: [
          {
            id: 'line-1',
            phase: '输入接收',
            source: 'worker',
            text: 'Preparing assertion generation inputs',
            time: '13:53:04',
          },
        ],
        progress: {
          description: 'Generating assertions',
          label: 'Assertion generation',
        },
        running: true,
      },
    });

    const line = wrapper.get('.log-line');
    const directClasses = [...line.element.children].map((element) => [
      ...element.classList,
    ]);

    expect(line.find('.log-meta').exists()).toBe(false);
    expect(directClasses).toEqual([
      ['log-time'],
      ['log-chip', 'log-chip--phase'],
      ['log-text'],
    ]);
  });

  it('middle-aligns inline log chips with the surrounding text', () => {
    const source = readFileSync(
      resolve(
        process.cwd(),
        'apps/web-antd/src/views/protocol-compliance/workbench/components/StageLiveLogPanel.vue',
      ),
      'utf8',
    );

    expect(source).toMatch(/\.log-chip\s*\{[^}]*vertical-align:\s*middle;/);
  });

  it('renders Claude tool activity and result telemetry as a structured timeline', () => {
    const wrapper = mount(StageLiveLogPanel, {
      props: {
        lines: [
          {
            id: 'turn-noise',
            metadata: { sdk_message_type: 'AssistantMessage' },
            phase: 'Claude 构建',
            stage: 'claude-status',
            text: 'Assistant turn received from claude-test',
          },
          {
            id: 'command',
            metadata: {
              sdk_message_type: 'ToolUseBlock',
              tool: 'Bash',
              tool_input: {
                command: 'cmake -S . -B build',
                description: '配置构建目录',
              },
            },
            phase: 'Claude 构建',
            stage: 'claude-command',
            text: 'Bash: cmake -S . -B build',
            time: '13:53:04',
          },
          {
            id: 'result',
            metadata: {
              duration_ms: 112_197,
              model_usage: {
                'claude-opus-4-8[1m]': { costUSD: 0.694_785 },
              },
              result: '构建完成，所有必需产物均已生成。',
              sdk_message_type: 'ResultMessage',
              status: 'completed',
              usage: {
                cache_read_input_tokens: 752_000,
                input_tokens: 32_957,
                output_tokens: 6160,
              },
            },
            phase: 'Claude 构建',
            stage: 'claude-status',
            text: 'Claude builder completed',
            time: '13:54:56',
          },
        ],
        progress: {
          description: 'Claude 正在配置并构建项目。',
          label: 'Claude 构建',
        },
        running: false,
      },
    });

    expect(wrapper.findAll('.claude-line')).toHaveLength(2);
    expect(wrapper.text()).not.toContain('Assistant turn received');
    expect(wrapper.get('.claude-line--command').text()).toContain(
      'cmake -S . -B build',
    );
    expect(wrapper.get('.claude-line--result').text()).toContain('$0.6948');
    expect(wrapper.get('.claude-line--result').text()).toContain('1 分 52 秒');
    expect(wrapper.get('.claude-line--result').text()).toContain(
      '构建完成，所有必需产物均已生成。',
    );
  });

  it('hides successful legacy UserMessage tool results and styles thinking blocks', () => {
    const wrapper = mount(StageLiveLogPanel, {
      props: {
        lines: [
          {
            id: 'tool-result',
            phase: 'Claude 构建',
            stage: 'claude-message',
            text: "UserMessage(content=[ToolResultBlock(tool_use_id='call-1', content='build ok', is_error=False)])",
          },
          {
            id: 'thinking',
            metadata: { sdk_message_type: 'ThinkingBlock' },
            phase: 'Claude 构建',
            stage: 'claude-message',
            text: String.raw`ThinkingBlock(thinking='Inspect the Makefile.\nThen build with gclang.', signature='private-signature')`,
          },
        ],
        progress: {
          description: 'Claude 正在配置并构建项目。',
          label: 'Claude 构建',
        },
        running: true,
      },
    });

    expect(wrapper.findAll('.claude-line')).toHaveLength(1);
    expect(wrapper.text()).not.toContain('UserMessage');
    expect(wrapper.get('.claude-line--thinking').text()).toContain(
      'Inspect the Makefile.\nThen build with gclang.',
    );
    expect(wrapper.get('.claude-line--thinking').text()).not.toContain(
      'private-signature',
    );
    expect(wrapper.get('.claude-line--thinking').text()).toContain(
      'Claude 思考',
    );
  });

  it('keeps failed legacy UserMessage tool results visible', () => {
    const wrapper = mount(StageLiveLogPanel, {
      props: {
        lines: [
          {
            id: 'failed-tool-result',
            phase: 'Claude 构建',
            stage: 'claude-message',
            text: String.raw`UserMessage(content=[ToolResultBlock(tool_use_id='call-1', content='Exit code 127\nunzip: command not found', is_error=True)])`,
          },
        ],
        progress: {
          description: 'Claude 正在配置并构建项目。',
          label: 'Claude 构建',
        },
        running: true,
      },
    });

    expect(wrapper.get('.claude-line--error').text()).toContain(
      'Exit code 127\nunzip: command not found',
    );
    expect(wrapper.text()).not.toContain('UserMessage');
  });

  it('keeps the parsed portion of a truncated ThinkingBlock repr', () => {
    const wrapper = mount(StageLiveLogPanel, {
      props: {
        lines: [
          {
            id: 'truncated-thinking',
            metadata: { sdk_message_type: 'ThinkingBlock' },
            phase: 'Claude 构建',
            stage: 'claude-message',
            text: String.raw`ThinkingBlock(thinking='The clean output looks correct.\nNow inspect the Makefile sh`,
          },
          {
            id: 'truncated-escape',
            metadata: { sdk_message_type: 'ThinkingBlock' },
            phase: 'Claude 构建',
            stage: 'claude-message',
            text: "ThinkingBlock(thinking='Check the next command\\",
          },
        ],
        progress: {
          description: 'Claude 正在配置并构建项目。',
          label: 'Claude 构建',
        },
        running: true,
      },
    });

    const thoughts = wrapper.findAll('.claude-line--thinking');
    const [firstThought, secondThought] = thoughts;
    expect(firstThought).toBeDefined();
    expect(secondThought).toBeDefined();
    expect(firstThought?.text()).toContain(
      'The clean output looks correct.\nNow inspect the Makefile sh...',
    );
    expect(firstThought?.text()).not.toContain('ThinkingBlock(');
    expect(secondThought?.text()).toContain('Check the next command...');
    expect(secondThought?.text()).not.toContain('ThinkingBlock(');
  });
});
