import pandas as pd
import pytest

from src.skills import code_execution, static_analysis, plausibility_check


@pytest.fixture
def sample_df():
    return pd.DataFrame({"category": ["A", "B", "A"], "revenue": [100.0, 50.0, 200.0]})


class TestCodeExecution:
    def test_valid_code_executes(self, sample_df):
        code = "result = df.groupby('category')['revenue'].sum()"
        res = code_execution.run(code, sample_df)
        assert res.success
        assert res.value["A"] == 300.0

    def test_missing_result_variable_is_rejected(self, sample_df):
        code = "x = df['revenue'].sum()"
        res = code_execution.run(code, sample_df)
        assert not res.success
        assert "guardrail_violation" in res.error

    def test_banned_import_is_rejected_before_execution(self, sample_df):
        code = "import os\nresult = os.listdir('.')"
        res = code_execution.run(code, sample_df)
        assert not res.success
        assert "guardrail_violation" in res.error

    def test_source_dataframe_is_not_mutated(self, sample_df):
        original = sample_df.copy(deep=True)
        code = "df.drop(columns=['category'], inplace=True)\nresult = df.shape"
        code_execution.run(code, sample_df)
        pd.testing.assert_frame_equal(sample_df, original)

    def test_safe_type_builtins_are_available(self, sample_df):
        # float/int/str/bool/isinstance/type are pure, side-effect-free and were
        # previously missing from the whitelist, rejecting ordinary correct code
        # (e.g. casting a computed value) as if it were a guardrail violation.
        code = "result = float(df['revenue'].sum()) if isinstance(df, pd.DataFrame) else None"
        res = code_execution.run(code, sample_df)
        assert res.success
        assert res.value == 350.0

    def test_eval_is_rejected(self, sample_df):
        code = "result = eval('1+1')"
        res = code_execution.run(code, sample_df)
        assert not res.success


class TestStaticAnalysis:
    def test_clean_code_passes(self):
        report = static_analysis.analyze("result = df['revenue'].mean()")
        assert report.passed

    def test_banned_pattern_flagged(self):
        report = static_analysis.analyze("import subprocess\nresult = 1")
        assert not report.passed
        assert any("security" in f for f in report.findings)

    def test_high_complexity_flagged(self):
        code = "\n".join([f"if x == {i}:\n    y = {i}" for i in range(15)]) + "\nresult = y"
        report = static_analysis.analyze(code)
        assert not report.passed
        assert any("complexity" in f for f in report.findings)


class TestPlausibilityCheck:
    def test_normal_value_passes(self):
        report = plausibility_check.check(42.0)
        assert report.passed

    def test_nan_flagged(self):
        report = plausibility_check.check(float("nan"))
        assert not report.passed

    def test_percentage_out_of_bounds_flagged(self):
        report = plausibility_check.check(150.0, is_percentage=True)
        assert not report.passed

    def test_large_growth_rate_needs_scrutiny_not_rejection(self):
        report = plausibility_check.check(5.0, is_growth_rate=True)
        assert report.passed  # not rejected outright
        assert report.needs_extra_scrutiny
