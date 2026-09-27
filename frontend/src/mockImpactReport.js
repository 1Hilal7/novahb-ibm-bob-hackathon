const mockImpactReport = {
  commit: {
    id: 'fafa0ce0',
    author: 'Batuhan',
    summary: 'feat: allow nullable user email',
  },

  semantic_change: {
    summary: 'User email changed from required to optional',
    domains: ['shared-core', 'user-model'],
    criticality: 'high',
    evidence: ['sample_repo/shared/user.py'],
    broken_contracts: [],
  },

  affected_modules: [
    {
      module: 'billing',
      status: 'affected',
      reason: 'Module uses User.email without null-guard — nullable email will cause runtime error',
      evidence: 'sample_repo/billing/',
    },
    {
      module: 'notifications',
      status: 'safe',
      reason: 'Module already guards against nullable email — no action required',
      evidence: 'sample_repo/notifications/',
    },
    {
      module: 'auth',
      status: 'safe',
      reason: 'Module already guards against nullable email — no action required',
      evidence: 'sample_repo/auth/',
    },
  ],

  routing: [
    {
      developer_id: 'hilal',
      decision: 'SILENT',
      reason: 'Auth already handles nullable email safely.',
      recommended_action: null,
    },
    {
      developer_id: 'batuhan',
      decision: 'ACTION',
      reason: 'Billing depends on User.email and currently lacks a null guard.',
      recommended_action: 'Add explicit missing-email handling to invoice delivery and update invoice tests.',
    },
    {
      developer_id: 'ayse',
      decision: 'SILENT',
      reason: 'Notifications already handle nullable email safely.',
      recommended_action: null,
    },
    {
      developer_id: 'emre',
      decision: 'REVIEW_REQUIRED',
      reason: 'The shared User schema changed and requires backward-compatibility review.',
      recommended_action: 'Review backward compatibility, migration behavior, and persisted user records.',
    },
    {
      developer_id: 'selin',
      decision: 'SILENT',
      reason: 'No security action is required for this change.',
      recommended_action: null,
    },
    {
      developer_id: 'mert',
      decision: 'SILENT',
      reason: 'Platform work has no dependency on User.email.',
      recommended_action: null,
    },
  ],
}

export default mockImpactReport
