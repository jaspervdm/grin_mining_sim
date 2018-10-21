class Block:
    def __init__(self, height: int, timestamp: int, time_passed: int, difficulty: int, scaling: int,
                 is_secondary: bool, edge_bits: int):
        self.height = height
        self.timestamp = timestamp
        self.time_passed = time_passed
        self.edge_bits = edge_bits
        self.difficulty = difficulty
        self.scaling = scaling
        self.is_secondary = is_secondary


class Histogram:
    def __init__(self, n_bins: int, range_min: float, range_max: float):
        self.bins = [0] * n_bins
        self.n_bins = n_bins
        self.range_min = range_min
        self.range_max = range_max

    def bin_width(self) -> float:
        return (self.range_max - self.range_min) / self.n_bins
