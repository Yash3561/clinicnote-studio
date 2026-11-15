# Longitudinal context / future healthcare assistant contract

This is an integration contract, not an implemented Navierre connector or MCP server.

The host resolves subject identity and permissions. A context snapshot should contain an opaque snapshot ID, trusted tenant/subject/encounter association, allowed purpose, authorization/consent revision, source IDs and immutable versions, observed/effective dates, source type, uncertainty/verification state and revocation dependencies. A browser-supplied tenant field cannot grant access.

A future assistant can call purpose-scoped read_context, read_reviewed_note and read_care_tasks adapters over the existing authorized APIs. Each response must preserve source IDs and whether information is current-encounter, historical, unverified or metadata-only. Server enforcement remains necessary even if calls are exposed through MCP or another tool protocol.

Default documentation input is encounter-only. Longitudinal context inclusion must be an explicit workflow choice with provenance, temporal labeling, relevant permissions and a fresh review. A historical medication is not automatically an active prescription, a prior diagnosis is not a new diagnosis, and missing data is not a normal result. Retrieval, embeddings and summaries must inherit these boundaries and be invalidated when source or permission changes.

A proposed model cannot approve/export, prescribe, change medical records or message patients simply because it can read context. Separate read tools from consequential actions, validate structured arguments, bind approvals to exact versions and targets, enforce idempotency, and confirm external-system outcomes. No third-party action integration exists in this prototype.

Carrier claims, member-authorized clinical data and de-identified risk reporting require distinct purposes and access boundaries. A common interface is not a common unrestricted data lake. Tenant isolation, patient matching, revocation, audit access and incident recovery must be reviewed with the host team before real use.
