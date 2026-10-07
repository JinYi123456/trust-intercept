# Aegis Signal Lab — Redeemed Credit Utilization Plan

The project should not depend on any of these services. Credits are treated as temporary acceleration resources.

| Service | Decision | Best use in TRUST//INTERCEPT | Priority |
|---|---|---|---|
| GonkaRouter | USE | hosted Arbiter / counterfactual synthesis; monthly free pool | P0 |
| Featherless | USE | open-model comparison, alternative Arbiter, evaluation | P0 |
| Gemini | USE | free fallback + multimodal/audio | P0 |
| Adaption Labs | OPTIONAL USE | adapt/augment a scam-focused dataset or experiment with model training if credits are sufficient | P1 |
| Agentboxd | OPTIONAL USE | create a controlled demo inbox for suspicious-email ingestion and webhook-driven agent workflow | P1 |
| Momen | OPTIONAL | only if we need a lightweight hosted workflow/admin surface; not core to the product | P2 |
| ForgeHacks/Adaption | OPTIONAL | inspect redeemed benefits; use only if it gives a concrete engineering service relevant to the build | P2 |
| Perfect Corp YCE | DO NOT USE | beauty/image-generation APIs are not relevant to scam defence; no reason to consume the credit | P3 |
| DevSwarm | SKIP | requires a workflow/development setup that adds dependency without a clear advantage | P3 |
| n8n voucher | SKIP | voucher failed; no need to recover it | P3 |
| Kariaa | SKIP | user does not plan to use it | P3 |
| Project AAL | HOLD | evaluate only if it provides a concrete agent capability we cannot implement locally | P2 |

## Spending rule

1. Never spend a credit just to make the architecture look more complex.
2. Spend credits on measurable value: better evidence, better benchmark results, better demo reliability, or a genuinely useful integration.
3. Keep a local/offline implementation for every competition-critical path.
4. Never commit provider keys to GitHub.
5. Record which provider/model produced a hosted inference result in the case audit trail.
