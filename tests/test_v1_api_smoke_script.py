from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from fastapi.testclient import TestClient

from backend.app.main import STRICT_DELIBERATION_PROVIDERS, _is_strict_completed_deliberation, create_app


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "v1_api_smoke.py"


def load_module():
    spec = importlib.util.spec_from_file_location("v1_api_smoke", SCRIPT)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_seeded_v1_smoke_deliberation_matches_strict_provider_contract(tmp_path: Path) -> None:
    module = load_module()
    client = TestClient(create_app(data_dir=tmp_path, llm_client=module.V1SmokeLLM(), load_env_file=False))
    project_id = module._create_standard_project(client, module.GOLDEN_CASES[0])

    run_id = module._seed_completed_deliberation(client, project_id)

    run = client.app.state.store.get_deliberation_run(project_id, run_id)
    assert run is not None
    assert run.providers == list(STRICT_DELIBERATION_PROVIDERS)
    assert _is_strict_completed_deliberation(run)
