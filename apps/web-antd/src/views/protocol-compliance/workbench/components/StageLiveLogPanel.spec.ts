import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import process from 'node:process';

import { mount } from '@vue/test-utils';

import { describe, expect, it } from 'vitest';

import StageLiveLogPanel from './StageLiveLogPanel.vue';

describe('stageLiveLogPanel', () => {
  const archiveLine = (id: string, overrides = {}) => ({
    id,
    kind: 'normal',
    metadata: { activity: 'status' as const },
    phase: 'Agent 构建',
    stage: 'builder',
    text: `[pg-builder][archive] extracted src/${id}.c`,
    time: '10:40:14',
    ...overrides,
  });

  it('collapses archive listings and preserves expansion and raw copy during streaming', async () => {
    const first = archiveLine('first');
    const second = archiveLine('second');
    const wrapper = mount(StageLiveLogPanel, {
      props: {
        lines: [first, second],
        progress: { label: 'Agent 构建', description: '正在构建' },
        running: true,
      },
    });
    expect(wrapper.findAll('.log-line')).toHaveLength(1);
    const details = wrapper.get('details').element as HTMLDetailsElement;
    expect(details.open).toBe(false);
    expect(wrapper.get('summary').text()).toContain('2 条记录');
    details.open = true;
    const third = archiveLine('third', { time: '10:40:15' });
    await wrapper.setProps({ lines: [first, second, third] });
    expect(wrapper.get('details').element).toBe(details);
    expect(details.open).toBe(true);
    expect(wrapper.get('summary').text()).toContain('3 条记录');
    expect(wrapper.get('summary').text()).toContain('10:40:15');
    expect(wrapper.findAll('.archive-files > div')).toHaveLength(3);
    const exposed = wrapper.vm as unknown as { getAllLogText: () => string };
    expect(exposed.getAllLogText().split('\n')).toHaveLength(3);
    for (const line of [first, second, third]) {
      expect(exposed.getAllLogText()).toContain(line.text);
    }
  });

  it('keeps archive operations, errors, activities and phases in chronological order', () => {
    const wrapper = mount(StageLiveLogPanel, {
      props: {
        lines: [
          archiveLine('start', {
            text: '[pg-builder][archive] Extracting zip archive source.zip',
          }),
          archiveLine('first'),
          archiveLine('second'),
          archiveLine('error', {
            metadata: { activity: 'status', is_error: true },
          }),
          archiveLine('third'),
          archiveLine('command', { metadata: { activity: 'command' } }),
          archiveLine('fourth'),
          archiveLine('phase', { phase: '其他阶段' }),
          archiveLine('stage', { phase: '其他阶段', stage: 'other' }),
          archiveLine('warning', { kind: 'warning' }),
          archiveLine('result', { metadata: { activity: 'result' } }),
        ],
        progress: { label: 'Agent 构建', description: '正在构建' },
        running: false,
      },
    });
    expect(wrapper.findAll('.log-line')).toHaveLength(10);
    expect(wrapper.findAll('details')).toHaveLength(5);
    expect(wrapper.findAll('summary')[0]?.text()).toContain('2 条记录');
    expect(wrapper.get('.agent-line--error').text()).toContain('src/error.c');
    expect(wrapper.get('.agent-line--command').text()).toContain(
      'src/command.c',
    );
    expect(wrapper.findAll('.log-line')[0]?.text()).toContain('Extracting zip');
  });

  it('does not merge across hidden events or swallow multiline output', () => {
    const wrapper = mount(StageLiveLogPanel, {
      props: {
        lines: [
          archiveLine('first'),
          archiveLine('hidden', {
            metadata: { activity: 'status', quiet: true },
          }),
          archiveLine('second'),
          archiveLine('multiline', {
            text: '[pg-builder][archive] extracted src/a.c\nwarning: failed',
          }),
        ],
        progress: { label: 'Agent 构建', description: '正在构建' },
        running: true,
      },
    });
    expect(wrapper.findAll('details')).toHaveLength(2);
    expect(wrapper.findAll('.log-line')).toHaveLength(3);
    expect(wrapper.get('.agent-primary').text()).toContain('warning: failed');
    const exposed = wrapper.vm as unknown as { getAllLogText: () => string };
    expect(exposed.getAllLogText()).toContain('src/hidden.c');
  });

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

  it('renders normalized tool activity and result telemetry', () => {
    const wrapper = mount(StageLiveLogPanel, {
      props: {
        lines: [
          {
            id: 'turn',
            metadata: { activity: 'status', quiet: true },
            phase: 'Agent 构建',
            stage: 'builder',
            text: 'Assistant turn received',
          },
          {
            id: 'command',
            metadata: {
              activity: 'command',
              tool: 'shell',
              primary: 'cmake -S . -B build',
              description: '配置构建目录',
            },
            phase: 'Agent 构建',
            stage: 'builder',
            text: 'shell: cmake -S . -B build',
          },
          {
            id: 'result',
            metadata: {
              activity: 'result',
              duration_ms: 112_197,
              cost_usd: 0.694_785,
              model: 'test-model',
              result: '构建完成，所有必需产物均已生成。',
              status: 'completed',
              input_tokens: 32_957,
              output_tokens: 6160,
              cache_read_tokens: 752_000,
            },
            phase: 'Agent 构建',
            stage: 'builder',
            text: 'Agent builder completed',
          },
        ],
        progress: { description: 'Agent 正在构建项目。', label: 'Agent 构建' },
        running: false,
      },
    });
    expect(wrapper.findAll('.agent-line')).toHaveLength(2);
    expect(wrapper.text()).not.toContain('Assistant turn received');
    expect(wrapper.get('.agent-line--command').text()).toContain(
      'cmake -S . -B build',
    );
    expect(wrapper.get('.agent-line--command').text()).toContain(
      '配置构建目录',
    );
    const result = wrapper.get('.agent-line--result').text();
    expect(result).toContain('$0.6948');
    expect(result).toContain('1 分 52 秒');
    expect(result).toContain('构建完成，所有必需产物均已生成。');
    expect(result).toContain('test-model');
    expect(result).toContain('3.3万');
  });

  it('renders normalized thinking and tool results without SDK parsing', () => {
    const wrapper = mount(StageLiveLogPanel, {
      props: {
        lines: [
          {
            id: 'quiet',
            metadata: { activity: 'tool_result', quiet: true },
            phase: 'Agent 构建',
            stage: 'builder',
            text: 'build ok',
          },
          {
            id: 'thinking',
            metadata: { activity: 'thinking' },
            phase: 'Agent 构建',
            stage: 'builder',
            text: 'Inspect the Makefile.\nThen build.',
          },
          {
            id: 'failure',
            metadata: { activity: 'tool_result', is_error: true },
            phase: 'Agent 构建',
            stage: 'builder',
            text: 'Exit code 127\nunzip: command not found',
          },
          {
            id: 'success',
            metadata: { activity: 'tool_result', is_error: false },
            phase: 'Agent 构建',
            stage: 'builder',
            text: 'compile succeeded',
          },
        ],
        progress: { description: '正在构建项目。', label: 'Agent 构建' },
        running: true,
      },
    });
    expect(wrapper.findAll('.agent-line')).toHaveLength(3);
    expect(wrapper.get('.agent-line--thinking').text()).toContain(
      'Inspect the Makefile.',
    );
    expect(wrapper.get('.agent-line--error').text()).toContain(
      'unzip: command not found',
    );
    expect(wrapper.get('.agent-line--observation').text()).toContain(
      'compile succeeded',
    );
  });

  it('uses activity rather than workflow stage or provider tool name', () => {
    const wrapper = mount(StageLiveLogPanel, {
      props: {
        lines: [
          {
            id: 'edit',
            metadata: {
              activity: 'write',
              tool: 'replace',
              primary: '/workspace/main.c',
            },
            phase: '插桩',
            stage: 'instrumentation',
            text: 'replace: main.c',
          },
        ],
        progress: { description: '插桩', label: '插桩' },
        running: true,
      },
    });
    expect(wrapper.get('.agent-line--write').text()).toContain(
      '/workspace/main.c',
    );
    expect(wrapper.get('.agent-line--write').text()).toContain('replace');
    const exposed = wrapper.vm as unknown as { getAllLogText: () => string };
    expect(exposed.getAllLogText()).toContain('replace: main.c');
  });
});
