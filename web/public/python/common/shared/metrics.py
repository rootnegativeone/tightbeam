"""
Metrics collection helpers for fountain encoder/decoder instrumentation.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from statistics import fmean
from typing import Dict, Iterable, List


@dataclass
class FountainMetrics:
    """Track statistics for fountain encoding/decoding runs."""

    degree_hist: Counter[int] = field(default_factory=Counter)
    decode_durations: List[float] = field(default_factory=list)
    decode_attempts: int = 0
    decode_successes: int = 0
    decode_failures: int = 0
    symbols_used: List[int] = field(default_factory=list)
    symbols_available: List[int] = field(default_factory=list)
    rejected_symbols: Counter[str] = field(default_factory=Counter)

    def record_degree(self, degree: int) -> None:
        """Record the degree of an emitted symbol."""
        if degree <= 0:
            return
        self.degree_hist[degree] += 1

    def record_decode(
        self,
        duration: float,
        success: bool,
        symbols_used: int,
        total_symbols: int,
    ) -> None:
        """Record a decode attempt with its duration and outcome."""
        self.decode_attempts += 1
        self.decode_durations.append(duration)
        self.symbols_used.append(symbols_used)
        self.symbols_available.append(total_symbols)
        if success:
            self.decode_successes += 1
        else:
            self.decode_failures += 1

    def record_symbol_rejected(self, reason: str) -> None:
        """Record a symbol that was dropped (e.g., CRC mismatch)."""
        self.rejected_symbols[reason] += 1

    def merge(self, other: "FountainMetrics") -> None:
        """Merge another metrics object into this one."""
        self.degree_hist.update(other.degree_hist)
        self.decode_durations.extend(other.decode_durations)
        self.decode_attempts += other.decode_attempts
        self.decode_successes += other.decode_successes
        self.decode_failures += other.decode_failures
        self.symbols_used.extend(other.symbols_used)
        self.symbols_available.extend(other.symbols_available)
        self.rejected_symbols.update(other.rejected_symbols)

    def summary(self) -> Dict[str, object]:
        """Return aggregated metrics suitable for logging."""
        total_symbols = sum(self.degree_hist.values())
        avg_degree = (
            sum(degree * count for degree, count in self.degree_hist.items())
            / total_symbols
            if total_symbols
            else 0.0
        )
        avg_duration = fmean(self.decode_durations) if self.decode_durations else 0.0
        success_rate = (
            self.decode_successes / self.decode_attempts
            if self.decode_attempts
            else 0.0
        )
        avg_symbols_used = fmean(self.symbols_used) if self.symbols_used else 0.0

        return {
            "total_symbols": total_symbols,
            "degree_hist": dict(self.degree_hist),
            "average_degree": avg_degree,
            "decode_attempts": self.decode_attempts,
            "decode_success_rate": success_rate,
            "average_decode_duration": avg_duration,
            "average_symbols_used": avg_symbols_used,
            "rejected_symbols": dict(self.rejected_symbols),
        }


__all__ = ["FountainMetrics"]
