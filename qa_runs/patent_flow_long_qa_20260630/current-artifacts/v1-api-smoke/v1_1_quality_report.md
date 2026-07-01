# GrantAtlas v1.1 deterministic quality gate

- passed: true
- deterministic: true
- live_provider_tests: opt-in only; default suite uses TestClient and V1SmokeLLM
- completed_workflows: 5/5
- failed_workflows: 0
- repeatability_failures: 0
- categories: algorithmic, external_draft, mechanical_device, sensing_inspection, software

## Loop Engineering Gates

- objective: final patent draft quality
- standard: full-process stability and reliability
- repeat_count: 1

### stability
- quality_trend_present: 5/5
- official_export_hygiene: 5/5

### reliability
- official_export_blocked_before_compile: 5/5
- official_export_blocked_before_review: 5/5
- post_draft_review_unlocks_export: 5/5

### final_draft_quality
- research_evidence_count: 5/5
- grantability_report_present: 5/5
- evidence_binding_rate: 5/5
- core_feature_support_rate: 5/5
- unverified_effect_leak_count: 5/5

## Workflows

### software

- category: software
- project_id: faf93db8620941f18c355fe86d428295
- research_evidence_count: 2
- research_confidence: medium
- grantability_status: medium
- official_package_hash: fbf50893036108a07527fc10f31e81cf193d1c177213cb75e19c7c74ef913ff2
- official_text_hash: f200b4c100375e214b05ad2bd5c8c3c601bc4ffce7a8de35c149af93d759e7c2
- quality_trend:
  - authorization_stability: 0
  - support_strength: 0
  - prior_art_distinction: 65
  - official_hygiene: 52
  - overall: 27
- drafting_quality:
  - evidence_binding_rate: 0.3
  - core_feature_support_rate: 1.0
  - unsupported_core_feature_count: 0
  - unverified_effect_leak_count: 0
  - dependent_fallback_depth: 3
  - embodiment_density: 0.7
  - patch_delta: -1
- gates:
  - research_evidence_count: pass (2)
  - grantability_report_present: pass (rows=2 fail_closed=False)
  - quality_trend_present: pass ({"authorization_stability": 0, "support_strength": 0, "prior_art_distinction": 65, "official_hygiene": 52, "overall": 27})
  - evidence_binding_rate: pass (0.3)
  - core_feature_support_rate: pass (1.0)
  - unverified_effect_leak_count: pass (0)
  - official_export_blocked_before_compile: pass (409)
  - official_export_blocked_before_review: pass (409)
  - post_draft_review_unlocks_export: pass (true)
  - official_export_hygiene: pass (clean)

### sensing_inspection

- category: sensing_inspection
- project_id: f13ac623705c46e8927539e06549a331
- research_evidence_count: 2
- research_confidence: medium
- grantability_status: medium
- official_package_hash: f91f01fc91606ec5a83ee21304bc03e4f47ccb0d7731df4d8ab9b80d698a6c29
- official_text_hash: f221a228949ef76ecc43bd6231ec0191d3dc5ad31419b64e752c0d8fd56c85b8
- quality_trend:
  - authorization_stability: 0
  - support_strength: 0
  - prior_art_distinction: 65
  - official_hygiene: 52
  - overall: 27
- drafting_quality:
  - evidence_binding_rate: 0.3
  - core_feature_support_rate: 1.0
  - unsupported_core_feature_count: 0
  - unverified_effect_leak_count: 0
  - dependent_fallback_depth: 3
  - embodiment_density: 0.7
  - patch_delta: 1
- gates:
  - research_evidence_count: pass (2)
  - grantability_report_present: pass (rows=2 fail_closed=False)
  - quality_trend_present: pass ({"authorization_stability": 0, "support_strength": 0, "prior_art_distinction": 65, "official_hygiene": 52, "overall": 27})
  - evidence_binding_rate: pass (0.3)
  - core_feature_support_rate: pass (1.0)
  - unverified_effect_leak_count: pass (0)
  - official_export_blocked_before_compile: pass (409)
  - official_export_blocked_before_review: pass (409)
  - post_draft_review_unlocks_export: pass (true)
  - official_export_hygiene: pass (clean)

### mechanical_device

- category: mechanical_device
- project_id: ce64f0b48750469dadf06d40fe2d9eaf
- research_evidence_count: 2
- research_confidence: medium
- grantability_status: medium
- official_package_hash: e3d6bb248c01dfaa7c56571cb44445f1635b2709d6ff6f21f523c7ce3737cdb4
- official_text_hash: 7b44d77b6878e2b0d21d3af0fbc101b6498c0530bf042f7fa286dbe7757d0d42
- quality_trend:
  - authorization_stability: 0
  - support_strength: 0
  - prior_art_distinction: 65
  - official_hygiene: 52
  - overall: 26
- drafting_quality:
  - evidence_binding_rate: 0.273
  - core_feature_support_rate: 0.889
  - unsupported_core_feature_count: 1
  - unverified_effect_leak_count: 0
  - dependent_fallback_depth: 2
  - embodiment_density: 0.727
  - patch_delta: -1
- gates:
  - research_evidence_count: pass (2)
  - grantability_report_present: pass (rows=2 fail_closed=False)
  - quality_trend_present: pass ({"authorization_stability": 0, "support_strength": 0, "prior_art_distinction": 65, "official_hygiene": 52, "overall": 26})
  - evidence_binding_rate: pass (0.273)
  - core_feature_support_rate: pass (0.889)
  - unverified_effect_leak_count: pass (0)
  - official_export_blocked_before_compile: pass (409)
  - official_export_blocked_before_review: pass (409)
  - post_draft_review_unlocks_export: pass (true)
  - official_export_hygiene: pass (clean)

### algorithmic

- category: algorithmic
- project_id: 40cac48d87624db880a33d72c31f0063
- research_evidence_count: 2
- research_confidence: medium
- grantability_status: medium
- official_package_hash: ff432fb07f2c436a768e158c1e077988309bf14baa10ac9937fea5f4a772778d
- official_text_hash: 4448987afa867874fff15e9b49cff5dde0706dff9e9e3eb3018b8cc041df58ff
- quality_trend:
  - authorization_stability: 0
  - support_strength: 0
  - prior_art_distinction: 65
  - official_hygiene: 52
  - overall: 26
- drafting_quality:
  - evidence_binding_rate: 0.273
  - core_feature_support_rate: 1.0
  - unsupported_core_feature_count: 0
  - unverified_effect_leak_count: 0
  - dependent_fallback_depth: 3
  - embodiment_density: 0.727
  - patch_delta: 2
- gates:
  - research_evidence_count: pass (2)
  - grantability_report_present: pass (rows=2 fail_closed=False)
  - quality_trend_present: pass ({"authorization_stability": 0, "support_strength": 0, "prior_art_distinction": 65, "official_hygiene": 52, "overall": 26})
  - evidence_binding_rate: pass (0.273)
  - core_feature_support_rate: pass (1.0)
  - unverified_effect_leak_count: pass (0)
  - official_export_blocked_before_compile: pass (409)
  - official_export_blocked_before_review: pass (409)
  - post_draft_review_unlocks_export: pass (true)
  - official_export_hygiene: pass (clean)

### external_draft

- category: external_draft
- project_id: 538f0b65da6449f6b70b291e9dfe461a
- research_evidence_count: 2
- research_confidence: medium
- grantability_status: medium
- official_package_hash: a09e8c1f2d8dd86cac6f9c5c3ebdc5fd56acaa7d1d01f10aceecbb7b272ae2f8
- official_text_hash: eb9882f109621100213bfea8ff328d74132911b8970b4597301454eb67b582ef
- quality_trend:
  - authorization_stability: 4
  - support_strength: 0
  - prior_art_distinction: 65
  - official_hygiene: 85
  - overall: 37
- drafting_quality:
  - evidence_binding_rate: 0.214
  - core_feature_support_rate: 1.0
  - unsupported_core_feature_count: 0
  - unverified_effect_leak_count: 0
  - dependent_fallback_depth: 2
  - embodiment_density: 0.857
  - patch_delta: 2
- gates:
  - research_evidence_count: pass (2)
  - grantability_report_present: pass (rows=2 fail_closed=False)
  - quality_trend_present: pass ({"authorization_stability": 4, "support_strength": 0, "prior_art_distinction": 65, "official_hygiene": 85, "overall": 37})
  - evidence_binding_rate: pass (0.214)
  - core_feature_support_rate: pass (1.0)
  - unverified_effect_leak_count: pass (0)
  - official_export_blocked_before_compile: pass (409)
  - official_export_blocked_before_review: pass (409)
  - post_draft_review_unlocks_export: pass (true)
  - official_export_hygiene: pass (clean)
