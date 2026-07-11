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
});
