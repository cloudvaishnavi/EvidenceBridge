"""
Tests for EvidenceBridge Evaluation Harness & Calibration Service (Layer 6).
Validates classification metrics (precision, recall, F1), cost anomaly detection metrics,
abstention gate calibration (over/under-abstention tracking), binned reliability ECE calculation,
Markdown report rendering, and FastAPI evaluation endpoints.
"""

from datetime import datetime, timezone
import pytest
from starlette.testclient import TestClient

from app.main import app
from app.models.schemas import (
    AbstentionMetrics,
    CalibrationBin,
    EvaluationLabel,
    EvaluationReport,
    MetricResult,
)
from app.services.evaluation import EvaluationService, evaluation_service
from app.services.storage import storage_service


# ==============================================================================
# Unit Tests for Statistical Metrics Calculations
# ==============================================================================

class TestEvaluationMetricMath:
    """Mathematical validation of statistical metric functions."""

    def test_classification_metrics_perfect(self):
        """100% agreement should yield 1.0 for accuracy, precision, recall, and F1."""
        y_true = ["supported", "contradicted", "insufficient_evidence", "supported"]
        y_pred = ["supported", "contradicted", "insufficient_evidence", "supported"]
        classes = ["supported", "contradicted", "insufficient_evidence"]

        acc, macro_f1, per_class = EvaluationService.calculate_classification_metrics(y_true, y_pred, classes)

        assert acc == 1.0
        assert macro_f1 == 1.0
        for c in classes:
            assert per_class[c].precision == 1.0
            assert per_class[c].recall == 1.0
            assert per_class[c].f1_score == 1.0

    def test_classification_metrics_hand_calculated_mixed(self):
        """
        Hand-calculated 4-sample test:
        y_true = ["supported", "supported", "contradicted", "insufficient_evidence"]
        y_pred = ["supported", "contradicted", "contradicted", "insufficient_evidence"]

        For 'supported':
          TP = 1, FP = 0, FN = 1.
          Precision = 1/1 = 1.0, Recall = 1/2 = 0.5, F1 = 2*1*0.5 / (1.5) = 2/3 ~= 0.6667
        For 'contradicted':
          TP = 1, FP = 1, FN = 0.
          Precision = 1/2 = 0.5, Recall = 1/1 = 1.0, F1 = 2*0.5*1 / (1.5) = 2/3 ~= 0.6667
        For 'insufficient_evidence':
          TP = 1, FP = 0, FN = 0.
          Precision = 1.0, Recall = 1.0, F1 = 1.0
        Accuracy = 3/4 = 0.75
        Macro F1 = (0.6667 + 0.6667 + 1.0) / 3 = 2.3334 / 3 = 0.7778
        """
        y_true = ["supported", "supported", "contradicted", "insufficient_evidence"]
        y_pred = ["supported", "contradicted", "contradicted", "insufficient_evidence"]
        classes = ["supported", "contradicted", "insufficient_evidence"]

        acc, macro_f1, per_class = EvaluationService.calculate_classification_metrics(y_true, y_pred, classes)

        assert acc == 0.75
        assert abs(macro_f1 - 0.7778) < 0.001
        assert per_class["supported"].precision == 1.0
        assert per_class["supported"].recall == 0.5
        assert abs(per_class["supported"].f1_score - 0.6667) < 0.001
        assert per_class["contradicted"].precision == 0.5
        assert per_class["contradicted"].recall == 1.0
        assert abs(per_class["contradicted"].f1_score - 0.6667) < 0.001
        assert per_class["insufficient_evidence"].f1_score == 1.0

    def test_cost_anomaly_metrics_hand_calculated(self):
        """
        Hand-calculated binary cost anomaly metrics:
        gold = [True,  True,  False, False, True]
        pred = [True,  False, True,  False, True]

        TP = 2 (items 0, 4)
        FP = 1 (item 2)
        FN = 1 (item 1)
        TN = 1 (item 3)
        Precision = 2 / (2 + 1) = 2/3 ~= 0.6667
        Recall    = 2 / (2 + 1) = 2/3 ~= 0.6667
        F1        = 2/3 ~= 0.6667
        Accuracy  = (2 + 1) / 5 = 0.6000
        """
        gold = [True, True, False, False, True]
        pred = [True, False, True, False, True]

        m = EvaluationService.calculate_cost_anomaly_metrics(gold, pred)

        assert m.true_positives == 2
        assert m.false_positives == 1
        assert m.false_negatives == 1
        assert abs(m.precision - 0.6667) < 0.001
        assert abs(m.recall - 0.6667) < 0.001
        assert abs(m.f1_score - 0.6667) < 0.001
        assert m.accuracy == 0.6

    def test_abstention_metrics_over_and_under_abstentions(self):
        """
        Tests abstention gate safety tracking:
        Sample 0: Gold ABSTAIN, Pred ABSTAIN -> Correct Abstention (TP)
        Sample 1: Gold ACCEPT,  Pred ABSTAIN -> Over-Abstention (FP, excessive refusal)
        Sample 2: Gold ABSTAIN, Pred FLAG    -> Under-Abstention (FN, dangerous failure to abstain)
        Sample 3: Gold ACCEPT,  Pred ACCEPT  -> Conclusive Agreement
        """
        gold_actions = ["ABSTAIN", "ACCEPT", "ABSTAIN", "ACCEPT"]
        pred_actions = ["ABSTAIN", "ABSTAIN", "FLAG", "ACCEPT"]
        gold_verdicts = ["insufficient_evidence", "supported", "insufficient_evidence", "supported"]
        pred_verdicts = ["insufficient_evidence", "insufficient_evidence", "supported", "supported"]

        m = EvaluationService.calculate_abstention_metrics(
            gold_actions, pred_actions, gold_verdicts, pred_verdicts
        )

        assert m.total_samples == 4
        assert m.total_abstained == 2  # Samples 0 and 1
        assert m.abstention_rate == 0.5
        assert m.correct_abstentions == 1  # Sample 0
        assert m.over_abstentions == 1     # Sample 1
        assert m.under_abstentions == 1    # Sample 2
        assert m.abstention_precision == 0.5  # 1 / (1 + 1)
        assert m.abstention_recall == 0.5     # 1 / (1 + 1)
        assert m.abstention_f1 == 0.5

    def test_calibration_ece_hand_calculated(self):
        """
        Hand-calculated ECE test with 5 equal bins: [0, 0.2), [0.2, 0.4), [0.4, 0.6), [0.6, 0.8), [0.8, 1.0].
        4 samples:
        s0: conf = 0.10, acc = False -> Bin 0: [0, 0.2)
        s1: conf = 0.50, acc = True  -> Bin 2: [0.4, 0.6)
        s2: conf = 0.85, acc = True  -> Bin 4: [0.8, 1.0]
        s3: conf = 0.95, acc = True  -> Bin 4: [0.8, 1.0]

        Bin 0 (count=1):
          avg_conf = 0.10, emp_acc = 0.0 -> cal_err = |0.0 - 0.10| = 0.10
        Bin 1 (count=0):
          cal_err = 0.0
        Bin 2 (count=1):
          avg_conf = 0.50, emp_acc = 1.0 -> cal_err = |1.0 - 0.50| = 0.50
        Bin 3 (count=0):
          cal_err = 0.0
        Bin 4 (count=2):
          avg_conf = (0.85 + 0.95)/2 = 0.90, emp_acc = 2/2 = 1.0 -> cal_err = |1.0 - 0.90| = 0.10

        Weighted ECE:
          (1/4)*0.10 + (1/4)*0.50 + (2/4)*0.10 = 0.025 + 0.125 + 0.050 = 0.2000
        """
        confs = [0.10, 0.50, 0.85, 0.95]
        accs = [False, True, True, True]

        bins, ece = EvaluationService.calculate_calibration_ece(confs, accs, num_bins=5)

        assert len(bins) == 5
        assert bins[0].sample_count == 1
        assert bins[0].calibration_error == 0.10
        assert bins[1].sample_count == 0
        assert bins[2].sample_count == 1
        assert bins[2].calibration_error == 0.50
        assert bins[4].sample_count == 2
        assert bins[4].calibration_error == 0.10
        assert abs(ece - 0.2000) < 0.001


# ==============================================================================
# End-to-End Evaluation Engine Tests
# ==============================================================================

class TestEvaluationEngine:
    """Tests for EvaluationService.run_evaluation() over controlled cases."""

    @pytest.mark.asyncio
    async def test_run_evaluation_offline_controlled_cases(self):
        """Run complete benchmark evaluation in offline mode."""
        svc = EvaluationService()
        report = await svc.run_evaluation(offline_mode=True)

        assert report.total_samples == 8
        assert report.run_id.startswith("eval_")
        assert report.overall_verdict_accuracy == 1.0
        assert report.overall_action_accuracy == 1.0
        assert report.macro_action_f1 == 1.0
        assert report.cost_anomaly_metrics.f1_score == 1.0
        assert report.abstention_metrics.abstention_recall == 1.0
        assert report.abstention_metrics.over_abstentions == 0
        assert report.abstention_metrics.under_abstentions == 0
        assert len(report.sample_evaluations) == 8
        assert len(report.calibration_bins) == 5
        assert len(report.markdown_report) > 200
        assert "# 📊 EvidenceBridge Evaluation Report" in report.markdown_report
        assert "## 1. Executive Summary Table" in report.markdown_report
        assert "## 6. Confidence Reliability Calibration" in report.markdown_report

    @pytest.mark.asyncio
    async def test_run_evaluation_subset_by_case_ids(self):
        """Evaluate only a specified subset of cases."""
        svc = EvaluationService()
        sub_cases = ["ctrl_01_supported_metformin", "ctrl_03_contradicted_bronchitis_antibiotic"]
        report = await svc.run_evaluation(case_ids=sub_cases, offline_mode=True)

        assert report.total_samples == 2
        case_ids_evaluated = [s.case_id for s in report.sample_evaluations]
        assert set(case_ids_evaluated) == set(sub_cases)

    @pytest.mark.asyncio
    async def test_run_evaluation_custom_labels(self):
        """Evaluate custom user-supplied labels in-memory."""
        svc = EvaluationService()
        custom = [
            EvaluationLabel(
                case_id="custom_01",
                raw_text="Patient prescribed Metformin 1,000 mg for type 2 diabetes. Cost: $10.",
                expected_entity="Metformin",
                gold_verdict="supported",
                gold_action="ACCEPT",
                cost_anomaly_flag=False,
            )
        ]
        report = await svc.run_evaluation(custom_labels=custom, offline_mode=True)

        assert report.total_samples == 1
        assert report.dataset_name == "custom_labels"
        assert report.overall_verdict_accuracy == 1.0


# ==============================================================================
# FastAPI Endpoint Integration Tests
# ==============================================================================

class TestEvaluationAPI:
    """Tests for Layer 6 FastAPI routes (/evaluate)."""

    def setup_method(self):
        from app.services.auth import (
            create_access_token,
            DEMO_USER_ID,
            DEMO_USER_EMAIL,
            DEMO_USER_NAME,
        )
        self.client = TestClient(app)
        token = create_access_token(DEMO_USER_ID, DEMO_USER_EMAIL, DEMO_USER_NAME)
        self.client.headers["Authorization"] = f"Bearer {token}"

    def test_post_evaluate_endpoint_offline(self):
        """POST /evaluate should trigger an evaluation run and return report."""
        payload = {"offline_mode": True}
        response = self.client.post("/evaluate", json=payload)
        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert "run_id" in data
        assert "report" in data
        report = data["report"]
        assert report["total_samples"] == 8
        assert report["overall_verdict_accuracy"] == 1.0
        assert report["overall_action_accuracy"] == 1.0
        assert "markdown_report" in report

    def test_get_evaluate_list_endpoint(self):
        """GET /evaluate should return recent evaluation runs."""
        # Ensure at least one run exists
        self.client.post("/evaluate", json={"offline_mode": True})

        response = self.client.get("/evaluate?limit=5")
        assert response.status_code == 200
        data = response.json()

        assert "total" in data
        assert "runs" in data
        assert isinstance(data["runs"], list)

    def test_get_evaluate_by_run_id_found_and_not_found(self):
        """GET /evaluate/{run_id} returns report if found, 404 if missing."""
        # 1. Create a run
        post_res = self.client.post("/evaluate", json={"offline_mode": True})
        assert post_res.status_code == 200
        run_id = post_res.json()["run_id"]

        # 2. Fetch by run_id
        get_res = self.client.get(f"/evaluate/{run_id}")
        if get_res.status_code == 200:
            data = get_res.json()
            assert data["run_id"] == run_id
            assert data["total_samples"] == 8
        else:
            # If MongoDB was offline during TestClient execution, verify 404 is handled cleanly
            assert get_res.status_code == 404

        # 3. Non-existent run_id
        missing_res = self.client.get("/evaluate/eval_nonexistent123")
        assert missing_res.status_code == 404
