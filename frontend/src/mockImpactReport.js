const mockImpactReport = {
  commit: {
    id: 'abc123',
    author: 'Hilal',
    summary: 'User.email is now nullable',
  },

  semantic_change: {
    summary: 'User email changed from required to optional',
    domains: ['user-model', 'database'],
    criticality: 'high',
    evidence: ['shared/user.py'],
  },

  affected_modules: [
    {
      module: 'billing',
      status: 'affected',
      reason: 'send_invoice assumes email is always present',
      evidence: 'billing/invoice.py',
    },
    {
      module: 'notifications',
      status: 'safe',
      reason: 'nullable email is already handled',
      evidence: 'notifications/email.py',
    },
  ],

  routing: [
    {
      developer_id: 'batuhan',
      decision: 'ACTION',
      reason: 'Billing depends on User.email being non-null',
      recommended_action:
        'Add fallback behavior and update missing-email invoice tests',
    },
    {
      developer_id: 'db-expert',
      decision: 'REVIEW_REQUIRED',
      reason: 'Shared schema behavior changed',
      recommended_action: 'Review backward compatibility',
    },
    {
      developer_id: 'notification-dev',
      decision: 'SILENT',
      reason: 'Existing null handling makes this change safe',
      recommended_action: null,
    },
  ],
}

export default mockImpactReport