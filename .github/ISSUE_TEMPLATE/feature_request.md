name: Feature request
about: Suggest a focused improvement for Flux-Titan as a self-hosted AI newsroom for Telegram channels
title: "[feature] "
labels: enhancement
body:
  - type: markdown
    attributes:
      value: |
        Flux-Titan is currently scoped as a Telegram-first, self-hosted AI newsroom.
        Requests that require a web dashboard, a new output platform, or a general-purpose agent workflow are out of scope for this phase.

  - type: dropdown
    id: workflow_step
    attributes:
      label: Workflow step
      description: Which newsroom step does this improve?
      options:
        - collect
        - filter
        - rank
        - rewrite
        - attach image
        - publish
    validations:
      required: true

  - type: textarea
    id: problem
    attributes:
      label: Problem
      description: What concrete problem does this solve for a Telegram newsroom workflow?
    validations:
      required: true

  - type: textarea
    id: why_it_matters
    attributes:
      label: Why it matters
      description: Why is this important for a focused self-hosted newsroom tool?
    validations:
      required: true

  - type: textarea
    id: proposal
    attributes:
      label: Proposed solution
      description: Describe the smallest useful solution.
    validations:
      required: true

  - type: textarea
    id: scope_now
    attributes:
      label: Why now and why in scope?
      description: Explain why this belongs in the current Telegram-only product direction.
    validations:
      required: true

  - type: textarea
    id: acceptance
    attributes:
      label: Acceptance criteria
      description: List the concrete conditions that would make this issue complete.
    validations:
      required: true

  - type: checkboxes
    id: scope_checks
    attributes:
      label: Scope checks
      options:
        - label: This keeps Telegram as the only output channel for this change
          required: true
        - label: This does not require a web dashboard
          required: true
        - label: This does not turn Flux-Titan into a general-purpose agent system
          required: true
