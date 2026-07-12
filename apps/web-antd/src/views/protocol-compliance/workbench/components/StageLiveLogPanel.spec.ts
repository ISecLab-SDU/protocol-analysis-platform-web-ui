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
});
