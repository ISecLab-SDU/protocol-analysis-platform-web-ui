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

  it('merges alternating artifact checks and file output into one shared card', () => {
    const messages = [
      '[pg-builder][2026-10-15T02:51:45Z] [claude-artifact] copied config.toml',
      '[pg-builder][2026-10-15T02:51:45Z] [claude-artifact] validated program.bc',
      '[pg-builder][artifact-file] program.bc: LLVM bitcode',
      '[pg-builder][2026-10-15T02:51:45Z] [claude-artifact] validated program.ll',
      '[pg-builder][artifact-file] program.ll: ASCII text',
    ];
    const wrapper = mount(StageLiveLogPanel, {
      props: {
        lines: messages.map((text, index) =>
          archiveLine(String(index), {
            text,
            metadata: index % 2 ? undefined : { activity: 'status' },
            stage: index % 2 ? 'builder-log' : 'builder',
          }),
        ),
        progress: { label: 'Agent 构建', description: '正在构建' },
        running: true,
      },
    });
    expect(wrapper.findAll('.agent-line')).toHaveLength(1);
    expect(wrapper.get('.agent-event-head').text()).toContain('产物校验');
    expect(wrapper.get('summary').text()).toContain('5 条记录');
    expect(wrapper.findAll('.output-lines > div')).toHaveLength(5);
  });

  it('merges untagged snapshots across metadata differences and preserves errors and stage boundaries', () => {
    const lines = [
      archiveLine('snapshot', {
        text: '[pg-builder][2026-10-15T02:51:45Z] Final workspace snapshot',
      }),
      archiveLine('total', {
        text: 'total 16444',
        metadata: undefined,
        stage: 'builder-log',
      }),
      archiveLine('file', {
        text: '-rw-r--r-- 1 user user 123 config.toml',
        metadata: undefined,
        stage: 'builder-log',
      }),
      archiveLine('error', {
        text: 'validation failed',
        kind: 'error',
        metadata: undefined,
      }),
      archiveLine('after', { text: 'continuing', metadata: undefined }),
      archiveLine('next', {
        text: 'next stage',
        stage: 'analysis',
        metadata: undefined,
      }),
    ];
    const wrapper = mount(StageLiveLogPanel, {
      props: {
        lines,
        progress: { label: 'Agent 构建', description: '正在构建' },
        running: true,
      },
    });
    expect(wrapper.findAll('.agent-line')).toHaveLength(4);
    expect(wrapper.get('summary').text()).toContain('3 条记录');
    expect(wrapper.get('.agent-line--error').text()).toContain(
      'validation failed',
    );
    expect(wrapper.findAll('.log-line')).toHaveLength(4);
    const exposed = wrapper.vm as unknown as { getAllLogText: () => string };
    for (const line of lines)
      expect(exposed.getAllLogText()).toContain(line.text);
  });

  it.each([
    'rule_config.json',
    'config.toml',
    'prompt-preview',
    'workspace',
    'new-category',
  ])('groups consecutive %s output and preserves indentation', (category) => {
    const contents = ['{', '  "items": [', '    "value"', '  ]', '}'];
    const wrapper = mount(StageLiveLogPanel, {
      props: {
        lines: contents.map((text, index) =>
          archiveLine(String(index), {
            text: `[pg-builder][${category}] ${text}`,
          }),
        ),
        progress: { label: 'Agent 构建', description: '正在构建' },
        running: true,
      },
    });
    expect(wrapper.findAll('.log-line')).toHaveLength(1);
    expect(wrapper.get('.agent-event-head').text()).toContain(category);
    expect(wrapper.get('summary').text()).toContain('5 条记录');
    const rows = wrapper.findAll('.output-lines > div');
    for (const [index, content] of contents.entries()) {
      expect(rows[index]?.element.textContent).toContain(content);
      expect(rows[index]?.text()).not.toContain('[pg-builder]');
    }
  });

  it('separates categories, lifecycle timestamps and repeated previews', () => {
    const categories = [
      'rule_config.json',
      'rule_config.json',
      'config.toml',
      'rule_config.json',
      '2026-10-15T03:00:00Z',
      'rule_config.json',
    ];
    const wrapper = mount(StageLiveLogPanel, {
      props: {
        lines: categories.map((category, index) =>
          archiveLine(String(index), {
            text: `[pg-builder][${category}] output ${index}`,
          }),
        ),
        progress: { label: 'Agent 构建', description: '正在构建' },
        running: true,
      },
    });
    expect(wrapper.findAll('.log-line')).toHaveLength(5);
    expect(wrapper.findAll('details')).toHaveLength(1);
    expect(wrapper.get('summary').text()).toContain('2 条记录');
    expect(wrapper.text()).toContain('output 4');
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
    expect(wrapper.get('.agent-event-head time').text()).toContain('10:40:15');
    expect(wrapper.findAll('.output-lines > div')).toHaveLength(3);
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
    expect(wrapper.findAll('.log-line')).toHaveLength(9);
    expect(wrapper.findAll('details')).toHaveLength(1);
    expect(wrapper.findAll('summary')[0]?.text()).toContain('3 条记录');
    expect(wrapper.get('.agent-line--error').text()).toContain('src/error.c');
    expect(wrapper.get('.agent-line--command').text()).toContain(
      'src/command.c',
    );
    expect(wrapper.findAll('.log-line')[0]?.text()).toContain('Extracting zip');
  });

  it('does not merge across hidden events and preserves multiline output', () => {
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
    expect(wrapper.findAll('details')).toHaveLength(1);
    expect(wrapper.findAll('.log-line')).toHaveLength(2);
    expect(wrapper.get('.agent-primary').text()).toContain('src/first.c');
    expect(wrapper.get('.output-lines').text()).toContain('warning: failed');
    const exposed = wrapper.vm as unknown as { getAllLogText: () => string };
    expect(exposed.getAllLogText()).toContain('src/hidden.c');
  });

  it('renders workflow events using the same card layout as Agent events', () => {
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

    const line = wrapper.get('.agent-line');
    expect(line.find('.agent-rail').exists()).toBe(true);
    expect(line.get('.agent-event-head').text()).toContain('输入接收');
    expect(line.get('.agent-event-head').text()).toContain('13:53:04');
    expect(line.get('.agent-primary').text()).toContain(
      'Preparing assertion generation inputs',
    );
    expect(line.find('.log-text').exists()).toBe(false);
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
