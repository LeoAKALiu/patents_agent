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
- project_id: e7d6f091bc7742f49645ad969eb26ed1
- research_evidence_count: 2
- research_confidence: medium
- grantability_status: medium
- official_package_hash: acbd3325d959eb485f667bb602bc3f81fe8c100a35396dd7838872d0773e5f6f
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
- project_id: a9b97f8c534249258e28e316f13e66a3
- research_evidence_count: 2
- research_confidence: medium
- grantability_status: medium
- official_package_hash: c340e9266889c056f577eabfee18a75fc4c920e411f9bdc996f3d360082411a8
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
- project_id: eae815117f5e4716af87ef9ae76a965b
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
- project_id: c351e414b220498fafc3cfe264caf2ce
- research_evidence_count: 2
- research_confidence: medium
- grantability_status: medium
- official_package_hash: bc309cb6391d0666eabf5ffded54837271994f7119b4b7c311127f40c83fd09c
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
- project_id: fdeab25903c246bc8b918a9889f3a79d
- research_evidence_count: 2
- research_confidence: medium
- grantability_status: medium
- official_package_hash: b2d8c33aae24ef6fba103ad7026b0c73c728e911d7dcd09db82d25747ac7528b
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
- project_id: 5d75bda5ec2e436f98b2c588f147bdc6
- research_evidence_count: 2
- research_confidence: medium
- grantability_status: medium
- official_package_hash: c04bc9fa31e783d88396a641c4c585c3ad3bc68ae29bdc6f8e60ba2b8ed026a9
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
- project_id: ab0baeb7d4be4ebaa74451fda2c0ede1
- research_evidence_count: 2
- research_confidence: medium
- grantability_status: medium
- official_package_hash: 3e33b8d860e26bb916a69a3b478cf36a3d19c822304e5cc004b7cb0cd19982fe
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
- project_id: 25a3d19e2fc74bfb9f2cff40d15ea0ec
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
- project_id: e714df063a3d4a26be9e8bfa898680e9
- research_evidence_count: 2
- research_confidence: medium
- grantability_status: medium
- official_package_hash: 4fec4877f642beb5560d02ba20fc0ba8251806473d5f7731dae6622b912137be
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
- project_id: 99f18907cfef4a248492e23a210bfcb1
- research_evidence_count: 2
- research_confidence: medium
- grantability_status: medium
- official_package_hash: 166eab24c82dfc437c03834d89ca39ed915179f77d8d642754c0fba022271d1e
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
