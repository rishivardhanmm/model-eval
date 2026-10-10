"""KLL streaming quantile sketch (Karnin, Lang & Liberty, 2016)."""

import hashlib
import math
import random


class KLLSketch:
    """Approximate quantile summary that keeps a bounded number of items.

    Items live in a stack of compactors. An item at level h stands for 2**h
    original values. When the sketch is full, the first over-capacity level is
    sorted and every other item (random offset) is promoted one level up.
    """

    def __init__(self, k=200, c=2 / 3, seed=0):
        """Create an empty sketch.

        Args:
            k: Accuracy parameter; capacity of the top level. Larger k means
                lower error and more memory.
            c: Capacity shrink factor per level below the top (0.5 < c < 1).
            seed: Seed for the compaction coin flips, for reproducible summaries.
        """
        self.k = k
        self.c = c
        self.rng = random.Random(seed)
        self.levels = [[]]
        self.n = 0
        self.size = 0
        self.peak_size = 0
        self.limit = self.max_size()

    def capacity(self, h):
        """Return how many items level h may hold before it must compact.

        Args:
            h: Level index, 0 being the bottom level.

        Returns:
            max(2, ceil(k * c ** depth)), where depth counts levels below the top.
        """
        depth = len(self.levels) - h - 1
        return max(2, math.ceil(self.k * self.c ** depth))

    def max_size(self):
        """Return the total capacity across all current levels.

        Returns:
            The item count at which the sketch compacts.
        """
        return sum(self.capacity(h) for h in range(len(self.levels)))

    def memory_bound(self):
        """Return the hard cap on retained items for streams under 2**32 values.

        Returns:
            3k + 64: the level capacities sum to under 3k + 2H, and the level
            count H never exceeds log2(n) <= 32.
        """
        return 3 * self.k + 64

    def update(self, value):
        """Add one value from the stream.

        Args:
            value: The number to summarize.
        """
        self.levels[0].append(value)
        self.n += 1
        self.size += 1
        self.peak_size = max(self.peak_size, self.size)
        if self.size >= self.limit:
            self._compress()

    def _compress(self):
        """Compact the first level that is at or over its capacity."""
        for h, level in enumerate(self.levels):
            if len(level) >= self.capacity(h):
                if h + 1 == len(self.levels):
                    self.levels.append([])
                    self.limit = self.max_size()
                level.sort()
                keep = [level.pop()] if len(level) % 2 else []
                offset = self.rng.randint(0, 1)
                self.levels[h + 1].extend(level[offset::2])
                self.levels[h] = keep
                self.size = sum(len(lv) for lv in self.levels)
                return

    def quantile(self, q):
        """Estimate a quantile using the same nearest-rank rule as exact_quantile.

        Args:
            q: Quantile in the range (0, 1].

        Returns:
            The retained item whose cumulative weight first reaches ceil(q * n).
        """
        weighted = sorted((v, 2 ** h) for h, lv in enumerate(self.levels) for v in lv)
        target = max(1, math.ceil(q * self.n))
        total = 0
        for value, weight in weighted:
            total += weight
            if total >= target:
                return value
        return weighted[-1][0]

    def digest(self):
        """Return a fingerprint of the full sketch state.

        Returns:
            A short SHA-256 hex digest of every level's retained items.
        """
        state = repr([sorted(lv) for lv in self.levels]).encode()
        return hashlib.sha256(state).hexdigest()[:16]
