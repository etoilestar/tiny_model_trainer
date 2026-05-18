from abc import ABC, abstractmethod
from typing import Callable


class BaseTrainer(ABC):
    """Abstract base class for all model trainers."""

    @abstractmethod
    def train(
        self,
        config: dict,
        log_callback: Callable[[str, str], None],
        metric_callback: Callable[[int, str, float, int], None],
    ) -> dict:
        """
        Run training.

        Args:
            config: Training configuration dictionary.
            log_callback: fn(level, message) – persist a log line.
            metric_callback: fn(epoch, metric_name, metric_value, step) – persist a metric.

        Returns:
            A dict containing final metrics / model output paths.
        """
        raise NotImplementedError
