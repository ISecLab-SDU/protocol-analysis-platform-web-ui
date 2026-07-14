import { mount } from '@vue/test-utils';

import { describe, expect, it } from 'vitest';

import StageCodeLocate from './StageCodeLocate.vue';

describe('stageCodeLocate log parsing', () => {
  it('uses timestamp brackets for time and keeps worker labels in the message', () => {
    const wrapper = mount(StageCodeLocate, {
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
        evidence: null,
        logHtml: '',
        logText: [
          '(init) [13:53:04] Preparing analysis inputs',
          '(analysis) [13:53:05] [pg worker] Launching analysis container image',
        ].join('\n'),
        result: null,
        rule: null,
        running: true,
      },
    });

    const logLines = wrapper.findAll('.log-line');

    expect(logLines[1]?.find('.log-time').text()).toBe('13:53:05');
    expect(logLines[1]?.find('.log-text').text()).toBe(
      '[pg worker] Launching analysis container image',
    );
  });

  it('does not extract bracketed backend metadata as a source label', () => {
    const wrapper = mount(StageCodeLocate, {
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
        evidence: null,
        logHtml: '',
        logText: [
          '(init) [10:19:25] Preparing analysis inputs',
          '(init) [10:19:25] [pg-builder][2026-07-12T02:19:25Z] Preparing analysis inputs',
        ].join('\n'),
        result: null,
        rule: null,
        running: true,
      },
    });

    const secondLine = wrapper.findAll('.log-line')[1];

    expect(secondLine.findAll('.log-chip')).toHaveLength(1);
    expect(secondLine.find('.log-text').text()).toBe(
      '[pg-builder][2026-07-12T02:19:25Z] Preparing analysis inputs',
    );
  });

  it('groups agent builder events under a dedicated phase', () => {
    const wrapper = mount(StageCodeLocate, {
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
        evidence: null,
        logHtml: '',
        logText: [
          '(init) [10:19:24] Preparing analysis inputs',
          '(builder) [10:19:25] Starting Claude builder image protocolguard-claude-builder:latest',
          '(claude-status) [10:19:25] Starting Claude Agent SDK builder typed stream',
          '(claude-command) [10:19:26] Bash: cmake -S . -B build',
        ].join('\n'),
        result: null,
        rule: null,
        running: true,
      },
    });

    const phaseChips = wrapper.findAll('.log-chip--phase');

    expect(phaseChips.map((chip) => chip.text())).toEqual([
      '输入与工作区准备',
      'Agent 构建',
      'Agent 构建',
      'Agent 构建',
    ]);
  });
});
