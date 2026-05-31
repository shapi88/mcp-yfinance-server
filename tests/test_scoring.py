"""
Unit tests for finance.scoring.
"""
import pytest

from mcp_yfinance_server.finance.scoring import DRIVER_CONFIGS, DriverConfig, score_metric


class TestScoreMetric:
    def test_higher_better_max(self):
        assert score_metric(30, "higher_better", [5, 10, 20, 25]) == 4

    def test_higher_better_mid(self):
        assert score_metric(12, "higher_better", [5, 10, 20, 25]) == 2

    def test_higher_better_min(self):
        assert score_metric(1, "higher_better", [5, 10, 20, 25]) == 0

    def test_lower_better_max(self):
        assert score_metric(1, "lower_better", [5, 10, 20, 25]) == 4

    def test_lower_better_mid(self):
        assert score_metric(15, "lower_better", [5, 10, 20, 25]) == 2

    def test_lower_better_min(self):
        assert score_metric(30, "lower_better", [5, 10, 20, 25]) == 0

    def test_none_returns_zero(self):
        assert score_metric(None, "higher_better", [1, 2, 3, 4]) == 0

    def test_wrong_threshold_count_raises(self):
        with pytest.raises(ValueError):
            score_metric(5, "higher_better", [1, 2, 3])


class TestDriverConfigs:
    def test_ten_drivers(self):
        assert len(DRIVER_CONFIGS) == 10

    def test_all_are_driver_config_instances(self):
        for cfg in DRIVER_CONFIGS:
            assert isinstance(cfg, DriverConfig)

    def test_weights_sum_to_one(self):
        total = sum(cfg.weight for cfg in DRIVER_CONFIGS)
        assert total == pytest.approx(1.0)

    def test_ranks_are_unique_and_sequential(self):
        ranks = sorted(cfg.rank for cfg in DRIVER_CONFIGS)
        assert ranks == list(range(1, 11))

    def test_each_driver_has_explanation(self):
        for cfg in DRIVER_CONFIGS:
            assert cfg.explanation.strip(), f"Driver '{cfg.name}' has no explanation"

    def test_each_driver_has_sub_metrics(self):
        for cfg in DRIVER_CONFIGS:
            assert cfg.sub_metrics, f"Driver '{cfg.name}' has no sub_metrics"
