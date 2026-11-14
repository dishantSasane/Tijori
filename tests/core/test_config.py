from pathlib import Path

import pytest

from trading.core.config import ConfigNotFoundError, load_risk_global_config, load_yaml

CONFIG_DIR = Path(__file__).parents[2] / "config"


def test_load_yaml_falls_back_to_example() -> None:
    data = load_yaml(CONFIG_DIR / "risk.yaml")
    assert "global" in data


def test_load_yaml_raises_when_neither_file_exists(tmp_path: Path) -> None:
    with pytest.raises(ConfigNotFoundError):
        load_yaml(tmp_path / "does_not_exist.yaml")


def test_load_risk_global_config_from_example() -> None:
    config = load_risk_global_config(CONFIG_DIR)
    assert config.mode == "paper"
    assert config.max_open_positions_total == 15
