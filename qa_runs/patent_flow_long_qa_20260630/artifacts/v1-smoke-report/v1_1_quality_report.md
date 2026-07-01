# GrantAtlas v1.1 deterministic quality gate

- passed: true
- deterministic: true
- live_provider_tests: opt-in only; default suite uses TestClient and V1SmokeLLM
- completed_workflows: 10/10
- failed_workflows: 0
- repeatability_failures: 0
- categories: algorithmic, external_draft, mechanical_device, sensing_inspection, software

## Loop Engineering Gates

- objective: final patent draft quality
- standard: full-process stability and reliability
- repeat_count: 2

### stability
- quality_trend_present: 10/10
- official_export_hygiene: 10/10

### reliability
- official_export_blocked_before_compile: 10/10
- official_export_blocked_before_review: 10/10
- post_draft_review_unlocks_export: 10/10

### final_draft_quality
- research_evidence_count: 10/10
- grantability_report_present: 10/10
- evidence_binding_rate: 10/10
- core_feature_support_rate: 10/10
- unverified_effect_leak_count: 10/10

## Workflows

### software

- category: software
- project_id: e869800621d94e679c6b63745098465b
- research_evidence_count: 2
- research_confidence: medium
- grantability_status: medium
- official_package_hash: 89dca7cb365ad1b9f4cc60e4be709069717630030263128555fd46131e276967
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
- project_id: f7ec9196e69e42de9cc8b153c8b0cb9a
- research_evidence_count: 2
- research_confidence: medium
- grantability_status: medium
- official_package_hash: e6349d2bf7bd804726a33fc51f2b33ae4ef327be7acb2719c525b4ac669aa1fb
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
- project_id: 97b04fab655640a1bb24c74d322f8d18
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
- project_id: 9112eee49d4540f29eea80d652e09664
- research_evidence_count: 2
- research_confidence: medium
- grantability_status: medium
- official_package_hash: 242bd75fedc71d3a2f0368aa219ac62d0f7a258668abb93eb8b1472ba440ee65
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
- project_id: be035b4c0ef641a0b45cfb5e7eec5373
- research_evidence_count: 2
- research_confidence: medium
- grantability_status: medium
- official_package_hash: fc36ed3e5d69305f1e2c5e6d62e53cda9642bdb3fe539111867f8bcf5910e525
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

### software

- category: software
- project_id: f215f918bd344f97b389b5e27c34a2a6
- research_evidence_count: 2
- research_confidence: medium
- grantability_status: medium
- official_package_hash: d22fa2242dcf91c0cfef7d9a9f9e057627976008360c0401a71d83dcb4ec2432
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
- project_id: c2a2a20fa1bc4f118b7f464e50f26d04
- research_evidence_count: 2
- research_confidence: medium
- grantability_status: medium
- official_package_hash: 127ad59a5ba1d088e5173b0d80dbb93dd67034784731dc0f6c60f0f35610d8ef
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
- project_id: a47be9131961424d86c9b78c16b966c3
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
- project_id: 020b15b7736c48b4ac9241a7a6186c2c
- research_evidence_count: 2
- research_confidence: medium
- grantability_status: medium
- official_package_hash: 72656d1b49694430673b31f28fffa9469455d02a5bac575beca4005b2dcea43d
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
- project_id: 7087fe34d5434eba81e588bf11e604e4
- research_evidence_count: 2
- research_confidence: medium
- grantability_status: medium
- official_package_hash: 8f1cb3fff827557bb31e3420308b942e2605ee223b2dc88b97757785fadb53c7
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
