import unittest

import pandas as pd

from src.evaluation import development_group_for_report, summarize_development_results


class DevelopmentEvaluationTests(unittest.TestCase):
    def test_group_assignment_is_stable_and_not_named_test(self) -> None:
        first = development_group_for_report("sample-report")
        second = development_group_for_report("sample-report")
        self.assertEqual(first, second)
        self.assertIn(first, {"development_main", "development_diagnostic"})
        self.assertNotIn("test", first)

    def test_summary_uses_agreement_not_accuracy(self) -> None:
        rows = pd.DataFrame(
            [
                {
                    "split": "development_main",
                    "predicted_hint": "A",
                    "matched": True,
                    "ood_decision": "in_domain",
                },
                {
                    "split": "development_diagnostic",
                    "predicted_hint": "B",
                    "matched": False,
                    "ood_decision": "low_relevance",
                },
            ]
        )
        summary = summarize_development_results(rows)
        self.assertIn("agreement", summary.columns)
        self.assertNotIn("accuracy", summary.columns)
        overall = summary.loc[summary["split"] == "all_development"].iloc[0]
        self.assertEqual(overall["agreement"], 0.5)


if __name__ == "__main__":
    unittest.main()
