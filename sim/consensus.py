from typing import List
from sim.types import Block

DIFFICULTY_ADJUST_WINDOW = 60
SECOND_POW_EDGE_BITS = 29
BASE_EDGE_BITS = 24

DIFF_DAMP_FACTOR = 3
AR_DAMP_FACTOR = 3
NEW_AR_DAMP = 0
CLAMP_FACTOR = 2
BLOCK_TIME_WINDOW = DIFFICULTY_ADJUST_WINDOW * 60


def graph_weight(edge_bits: int) -> int:
    return (2 << (edge_bits - BASE_EDGE_BITS)) * edge_bits

INITIAL_GRAPH_WEIGHT = graph_weight(SECOND_POW_EDGE_BITS)


class HeaderInfo:
    def __init__(self, timestamp: int, difficulty: int, scaling: int, is_secondary: bool):
        self.timestamp = timestamp
        self.difficulty = difficulty
        self.scaling = scaling
        self.is_secondary = is_secondary

    def __str__(self):
        return "HeaderInfo<timestamp={} difficulty={} scaling={} {}>".format(
            self.timestamp, self.difficulty, self.scaling, "secondary" if self.is_secondary else "primary"
        )

    def __repr__(self):
        return self.__str__()

    @staticmethod
    def from_block(block: Block):
        return HeaderInfo(block.timestamp, block.difficulty, block.scaling, block.is_secondary)

    @staticmethod
    def from_ts_diff(timestamp: int, difficulty: int):
        return HeaderInfo(timestamp, difficulty, INITIAL_GRAPH_WEIGHT, False)

    @staticmethod
    def from_diff_scaling(difficulty: int, scaling: int):
        return HeaderInfo(1, difficulty, scaling, False)


def difficulty_data_to_vector(blocks: List[Block]) -> List[HeaderInfo]:
    need = DIFFICULTY_ADJUST_WINDOW + 1
    diff = need - len(blocks)

    last = [HeaderInfo.from_block(x) for x in blocks]

    if diff > 0:
        intervals = [HeaderInfo.from_ts_diff(x.timestamp, x.difficulty) for x in blocks]
        for i in range(len(intervals)-1, 0, -1):
            intervals[i].timestamp = intervals[i].timestamp - intervals[i-1].timestamp
        if len(intervals) > 1:
            intervals.pop(0)
        else:
            intervals[0].timestamp = 60
        last_ts = last[0].timestamp
        last_diff = intervals[len(intervals)-1].difficulty

        for i in range(diff):
            last_ts = max(0, last_ts-intervals[len(intervals)-1].timestamp)
            last.insert(0, HeaderInfo.from_ts_diff(last_ts, last_diff))
    return last


def secondary_pow_ratio(height: int) -> int:
    return max(0, 90 - int(height / 10080))


def damp(actual: int, goal: int, damp_factor: int) -> int:
    return int((actual + (damp_factor - 1) * goal) / damp_factor)


def clamp(actual: int, goal: int, clamp_factor: int) -> int:
    return max(int(goal / clamp_factor), min(actual, goal*clamp_factor))


def secondary_pow_scaling(height: int, diff_data: List[HeaderInfo]) -> int:
    if NEW_AR_DAMP > 0:
        last = diff_data[-1]
        scale = last.scaling
        target_pct = secondary_pow_ratio(height)
        if last.is_secondary:
            scale -= (100 - target_pct) / NEW_AR_DAMP
        else:
            scale += target_pct / NEW_AR_DAMP
        return max(AR_DAMP_FACTOR, scale)
    diff_iter = iter(diff_data)
    next(diff_iter)
    secondary_count = 0
    scale_sum = 0
    for x in diff_iter:
        scale_sum += x.scaling
        if x.is_secondary:
            secondary_count += 1
    secondary_count *= 100

    target_pct = secondary_pow_ratio(height)
    target_count = int(DIFFICULTY_ADJUST_WINDOW * target_pct)
    adj_count = clamp(
        damp(secondary_count, target_count, AR_DAMP_FACTOR),
        target_count,
        CLAMP_FACTOR
    )
    scale = int(scale_sum * target_pct / max(1,adj_count))
    return max(AR_DAMP_FACTOR, scale)


def next_difficulty(height: int, blocks: List[Block]) -> HeaderInfo:
    diff_data = difficulty_data_to_vector(blocks)
    sec_pow_scaling = secondary_pow_scaling(height, diff_data)
    ts_delta = diff_data[DIFFICULTY_ADJUST_WINDOW].timestamp - diff_data[0].timestamp
    diff_sum = 0
    diff_iter = iter(diff_data)
    next(diff_iter)
    for diff in diff_iter:
        diff_sum += diff.difficulty

    adj_ts = clamp(
        damp(ts_delta, BLOCK_TIME_WINDOW, DIFF_DAMP_FACTOR),
        BLOCK_TIME_WINDOW,
        CLAMP_FACTOR
    )
    difficulty = max(1, int(diff_sum * 60 / adj_ts))
    return HeaderInfo.from_diff_scaling(difficulty, sec_pow_scaling)
