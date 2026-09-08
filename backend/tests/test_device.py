import os
import importlib.util
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

MODULE_PATH = Path(__file__).parents[1] / "app" / "trainers" / "device.py"
class FakeDevice:
    def __init__(self, kind, index=None):
        self.type = kind
        self.index = index

    def __str__(self):
        return self.type if self.index is None else f"{self.type}:{self.index}"


fake_torch = SimpleNamespace(
    device=FakeDevice,
    cuda=SimpleNamespace(is_available=lambda: False, device_count=lambda: 0),
)
sys.modules.setdefault("torch", fake_torch)
SPEC = importlib.util.spec_from_file_location("trainer_device", MODULE_PATH)
device_module = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = device_module
SPEC.loader.exec_module(device_module)
_parse_device = device_module._parse_device
resolve_accelerator = device_module.resolve_accelerator


class DeviceSelectionTest(unittest.TestCase):
    def test_parses_supported_device_names(self):
        self.assertEqual(_parse_device("cpu"), ("cpu", None))
        self.assertEqual(_parse_device("cuda:3"), ("cuda", 3))
        self.assertEqual(_parse_device("npu:7"), ("npu", 7))
        self.assertEqual(_parse_device("0"), ("cuda", 0))

    def test_rejects_invalid_device(self):
        with self.assertRaisesRegex(ValueError, "不支持的设备配置"):
            _parse_device("tpu")

    def test_cpu_never_probes_accelerators(self):
        selected = resolve_accelerator("cpu")
        self.assertEqual(selected.kind, "cpu")
        self.assertEqual(str(selected.device), "cpu")
        self.assertEqual(selected.distributed_backend, "gloo")

    @patch.dict(os.environ, {"DEVICE_TYPE": "cpu"})
    def test_environment_controls_empty_device(self):
        self.assertEqual(_parse_device(None), ("cpu", None))


if __name__ == "__main__":
    unittest.main()
