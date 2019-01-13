import json
import random
from sim.consensus import INITIAL_GRAPH_WEIGHT, SECOND_POW_EDGE_BITS, DIFFICULTY_ADJUST_WINDOW, \
    next_difficulty, graph_weight, secondary_pow_ratio
from sim.types import Block


TAKE = DIFFICULTY_ADJUST_WINDOW+1


def primary_graph_rate(edge_bits: int, height: int):
    if edge_bits == 30:
        return 0 if height < 40000 else 0
    if edge_bits == 31:
        return 1 if height < 40000 else 2
    return 0


def secondary_graph_rate(height: int):
    return 36 if height < 40000 else 36


def test_difficulty_adjustment():
    timestamps = [1539806400, 1539811015, 1539812035, 1539812572, 1539812806, 1539813230, 1539813497, 1539813905,
                  1539813960, 1539813969, 1539814182, 1539814256, 1539814263, 1539814486, 1539814501, 1539814894]
    difficulties = [1856000, 1856000, 928000, 479466, 266413, 166988, 121418, 100911,
                    91854, 107797, 134334, 105762, 108798, 133690, 105059, 127093]
    scalings = [1856, 2758, 2756, 2752, 2749, 2747, 2743, 2740,
                2738, 2734, 2731, 2728, 2725, 2722, 2719, 2715]
    edge_bits = [29] * 16
    blocks = []

    for height in range(len(timestamps)):
        if height == 0:
            block = Block(height, timestamps[height], 0,  1000 * INITIAL_GRAPH_WEIGHT, INITIAL_GRAPH_WEIGHT,
                          edge_bits[height] == SECOND_POW_EDGE_BITS, edge_bits[height])
        else:
            info = next_difficulty(height, blocks)
            block = Block(height, timestamps[height], 0, info.difficulty, info.scaling,
                          edge_bits[height] == SECOND_POW_EDGE_BITS, edge_bits[height])
        blocks.append(block)

        assert block.difficulty == difficulties[height]
        assert block.scaling == scalings[height]


def simulation():
    active_edge_bits = [30, 31]
    random.seed(1337)
    end_height = 100000
    t_zero = 1539806400
    t = t_zero
    t_last = t
    blocks = [Block(0, t, 0, 1000 * INITIAL_GRAPH_WEIGHT, INITIAL_GRAPH_WEIGHT, True, SECOND_POW_EDGE_BITS)]
    next_diff = next_difficulty(1, blocks[-TAKE:])
    height = 1

    while True:
        t += 1

        for edge_bits in active_edge_bits:
            rate = primary_graph_rate(edge_bits, height)
            for i in range(rate):
                if random.random() * 42 < 1 and random.random() * next_diff.difficulty / graph_weight(edge_bits) < 1:
                    dt = t-t_last
                    # print("dt={}: found primary block at {}".format(dt, height))
                    blocks.append(Block(height, t, dt, next_diff.difficulty, next_diff.scaling, False, edge_bits))
                    t_last = t
                    height += 1
                    next_diff = next_difficulty(height, blocks[-TAKE:])

        rate = secondary_graph_rate(height)
        for i in range(rate):
            if random.random() * 42 < 1 and random.random() * next_diff.difficulty / next_diff.scaling < 1:
                dt = t-t_last
                # print("dt={}: found secondary block at {}".format(dt, height))
                blocks.append(Block(height, t, dt, next_diff.difficulty, next_diff.scaling, True, SECOND_POW_EDGE_BITS))
                t_last = t
                height += 1
                next_diff = next_difficulty(height, blocks[-TAKE:])

        if height >= end_height:
            break

    difficulty_chart = []
    pow_type_chart = []
    graph_rate_chart = []
    for height in range(1, len(blocks)):
        q = secondary_pow_ratio(height)/100
        r = 1 - q

        if height % 100 != 0:
            continue
        block = blocks[height]
        window = blocks[max(0, height-59):(height + 1)]
        sma_loop = 0
        count_primary = 0
        count_primaries = [0 for _ in active_edge_bits]
        for x in window:
            sma_loop += x.time_passed
            if not x.is_secondary:
                count_primary += 1
                count_primaries[active_edge_bits.index(x.edge_bits)] += 1
        sma_loop = int(sma_loop / len(window))
        perc_primary = int(count_primary / len(window)*100)
        graph_rate_sec = round(42 * block.difficulty * q / block.scaling / 60, 1)
        graph_rate_prim = []
        for i in range(len(active_edge_bits)):
            if count_primary > 0:
                edge_bits = active_edge_bits[i]
                f = count_primaries[i] / count_primary
                graph_rate_prim.append(round(42 * block.difficulty * r * f / graph_weight(edge_bits) / 60, 1))
            else:
                graph_rate_prim.append(0)

        difficulty_chart.append([block.timestamp, height, block.difficulty, sma_loop])
        pow_type_chart.append([block.timestamp, height, perc_primary, 100-secondary_pow_ratio(height), block.scaling])
        graph_rate_chart.append([block.timestamp, height, [graph_rate_prim, graph_rate_sec]])

    f = open("difficulty.js", "w")
    f.write("fillGraph('difficulty', "+json.dumps(difficulty_chart)+");")
    f.close()

    f = open("pow_type.js", "w")
    f.write("fillGraph('pow_type', " + json.dumps(pow_type_chart) + ");")
    f.close()

    f = open("graph_rate.js", "w")
    f.write("fillGraph('graph_rate', " + json.dumps(graph_rate_chart) + ");")
    f.close()


simulation()
