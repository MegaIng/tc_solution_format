from functools import reduce
from operator import or_


def truth_table(truth: list[bool], endian="little"):
    if endian == "little":
        truth = reversed(truth)  # Little endian
    truth = [2 ** idx if b else 0 for (idx, b) in enumerate(truth)]
    truth = reduce(or_, truth, 0)
    return truth


def make_input(i: int, num_inputs: int, endian="little"):
    mask = 2 ** i
    outputs = [(x & mask) == mask for x in range(2 ** num_inputs)]
    outputs = truth_table(outputs, endian)
    return outputs
