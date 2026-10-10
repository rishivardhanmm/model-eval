"""KLL streaming quantile sketch (Karnin, Lang & Liberty, 2016)."""

# hashlib gives a stable fingerprint of the sketch state (Python's hash() is salted per run)
import hashlib
# math.ceil is used for level capacities and for the nearest-rank target
import math
# random.Random gives a private, seedable generator for the compaction coin flips
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
        # k is the one knob: it trades accuracy against memory
        self.k = k
        # c shrinks each lower level's capacity, so most space goes to the heavy top levels
        self.c = c
        # Own seeded generator, so the same seed always gives the same summary
        self.rng = random.Random(seed)
        # Start with a single empty level (level 0 = raw values, weight 1)
        self.levels = [[]]
        # n counts every value ever seen; it is the total weight of the sketch
        self.n = 0
        # size counts items actually held in memory right now
        self.size = 0
        # peak_size records the highest size ever reached, for the memory check
        self.peak_size = 0
        # Cache the compaction threshold; it only changes when a level is added
        self.limit = self.max_size()

    def capacity(self, h):
        """Return how many items level h may hold before it must compact.

        Args:
            h: Level index, 0 being the bottom level.

        Returns:
            max(2, ceil(k * c ** depth)), where depth counts levels below the top.
        """
        # depth 0 is the top level; deeper (lower) levels get geometrically smaller capacity
        depth = len(self.levels) - h - 1
        # The top level holds k items; lower levels shrink by c each step, never below 2
        return max(2, math.ceil(self.k * self.c ** depth))

    def max_size(self):
        """Return the total capacity across all current levels.

        Returns:
            The item count at which the sketch compacts.
        """
        # Sum of every level's capacity = the most items the sketch holds before compacting
        return sum(self.capacity(h) for h in range(len(self.levels)))

    def memory_bound(self):
        """Return the hard cap on retained items for streams under 2**32 values.

        Returns:
            3k + 64: the level capacities sum to under 3k + 2H, and the level
            count H never exceeds log2(n) <= 32.
        """
        # Geometric series k*(1 + c + c^2 + ...) < 3k, plus up to 2 per level for rounding/floors
        return 3 * self.k + 64

    def update(self, value):
        """Add one value from the stream.

        Args:
            value: The number to summarize.
        """
        # Every new value enters the bottom level with weight 1
        self.levels[0].append(value)
        # One more value seen in the stream
        self.n += 1
        # One more item held in memory
        self.size += 1
        # Track the high-water mark before any compaction shrinks it
        self.peak_size = max(self.peak_size, self.size)
        # Full? Compact one level to free space
        if self.size >= self.limit:
            # Halve the first over-capacity level
            self._compress()

    def _compress(self):
        """Compact the first level that is at or over its capacity."""
        # Walk from the bottom up and compact the first level that is full
        for h, level in enumerate(self.levels):
            # This level has reached its capacity, so it must compact
            if len(level) >= self.capacity(h):
                # Compacting the top level needs a new level above it
                if h + 1 == len(self.levels):
                    # Add a new top level; every capacity shifts, so...
                    self.levels.append([])
                    # ...recompute the cached threshold
                    self.limit = self.max_size()
                # Sort so that "every other item" keeps the rank structure intact
                level.sort()
                # With an odd count, hold back one item so the weight stays exact
                keep = [level.pop()] if len(level) % 2 else []
                # Coin flip: keep the even or the odd positions (this is where the seed matters)
                offset = self.rng.randint(0, 1)
                # Half the items move up one level, each now standing for twice as many values
                self.levels[h + 1].extend(level[offset::2])
                # This level keeps only the held-back item (if any)
                self.levels[h] = keep
                # Recount items held after the compaction
                self.size = sum(len(lv) for lv in self.levels)
                # Only one compaction per call; that is enough to get back under the limit
                return

    def quantile(self, q):
        """Estimate a quantile using the same nearest-rank rule as exact_quantile.

        Args:
            q: Quantile in the range (0, 1].

        Returns:
            The retained item whose cumulative weight first reaches ceil(q * n).
        """
        # Pair every retained item with its weight 2**level, then sort by value
        weighted = sorted((v, 2 ** h) for h, lv in enumerate(self.levels) for v in lv)
        # Same nearest-rank target the exact function uses: ceil(q * n)
        target = max(1, math.ceil(q * self.n))
        # Running total of weight seen so far
        total = 0
        # Walk the items in value order
        for value, weight in weighted:
            # Each item covers 'weight' original values
            total += weight
            # The first item that reaches the target rank is the estimate
            if total >= target:
                return value
        # Fallback: return the largest item (only reachable through rounding at q = 1)
        return weighted[-1][0]

    def digest(self):
        """Return a fingerprint of the full sketch state.

        Returns:
            A short SHA-256 hex digest of every level's retained items.
        """
        # repr of the sorted levels is deterministic text describing the whole summary
        state = repr([sorted(lv) for lv in self.levels]).encode()
        # A 16-hex-char SHA-256 prefix is enough to show two runs match
        return hashlib.sha256(state).hexdigest()[:16]
