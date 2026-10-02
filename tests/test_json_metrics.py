import json
import unittest

import numpy as np

from motor_insurance.metrics import finite_json_values


class JsonMetricTests(unittest.TestCase):
    def test_numpy_non_finite_metrics_serialize_as_null(self):
        for scalar_type in (np.float32, np.float64):
            for value in (float("nan"), float("inf"), -float("inf")):
                with self.subTest(scalar_type=scalar_type, value=value):
                    payload = finite_json_values({"loss_ratio": scalar_type(value)})
                    self.assertIsNone(payload["loss_ratio"])
                    self.assertEqual(json.dumps(payload, allow_nan=False), '{"loss_ratio": null}')

    def test_finite_numpy_metrics_preserve_values(self):
        payload = finite_json_values({"loss_ratio": np.float32(0.5), "claims": np.int64(2)})
        self.assertEqual(payload, {"loss_ratio": 0.5, "claims": 2})
        json.dumps(payload, allow_nan=False)
