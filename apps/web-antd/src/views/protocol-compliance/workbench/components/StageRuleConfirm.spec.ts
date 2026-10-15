import { flushPromises, mount } from '@vue/test-utils';

import { describe, expect, it } from 'vitest';

import StageRuleConfirm from './StageRuleConfirm.vue';

const rule = {
  rule: 'Validate Topic Name.',
  req_type: 'PUBLISH',
  req_fields: ['Topic Name'],
  res_type: '',
  res_fields: [],
};
const global = {
  stubs: {
    Card: { template: '<section><slot/><slot name="extra"/></section>' },
    Button: { template: '<button><slot/></button>' },
    Table: true,
    Tag: { template: '<span><slot/></span>' },
    Empty: true,
    IconifyIcon: true,
  },
};

describe('rule confirmation', () => {
  it('carries original document metadata through rule selection', async () => {
    const wrapper = mount(StageRuleConfirm, {
      global,
      props: {
        showBack: false,
        rulesFile: new File(
          [JSON.stringify({ 'MQTT-3.1.1-rules': [rule] })],
          'rules.json',
        ),
      },
    });
    await flushPromises();
    await wrapper.get('.rule-actions button').trigger('click');
    expect(wrapper.emitted('start')?.[0]?.[0]).toMatchObject({
      ...rule,
      protocol: 'MQTT',
      protocolVersion: '3.1.1',
    });
    await wrapper.setProps({ rulesFile: new File(['{broken'], 'broken.json') });
    await flushPromises();
    expect(wrapper.get('[role="alert"]').text()).toContain('加载规则失败');
    expect(wrapper.get('.rule-actions button').attributes()).toHaveProperty(
      'disabled',
    );
  });
  it('shows an actionable validation error for a rule with no incoming message', async () => {
    const wrapper = mount(StageRuleConfirm, {
      global,
      props: {
        showBack: false,
        rulesFile: new File(
          [JSON.stringify({ 'MQTT-3.1.1-rules': [{ ...rule, req_type: '' }] })],
          'rules.json',
        ),
      },
    });
    await flushPromises();
    await wrapper.get('.rule-actions button').trigger('click');
    expect(wrapper.emitted('start')).toBeUndefined();
    expect(wrapper.get('[role="alert"]').text()).toContain('req_type');
  });
});
