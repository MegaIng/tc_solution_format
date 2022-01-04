import json
from ast import literal_eval
from functools import reduce
from operator import or_

example = """
0    TRUE    (0)    11111111    0    (-,-,-)
1    INPUT    (0)    01010101    0    (0,-,-)
2    INPUT    (1)    00110011    0    (-,0,-)
3    INPUT    (2)    00001111    0    (-,-,0)
4    NAND_BIGORS    ((2),(1))    11101110    1    (2,2,-)
5    NAND_BIGORS    ((3),(1,2))    11111000    1    (2,2,2)
6    NAND_BIGORS    ((1,2,3),(0))    10000000    1    (2,2,2)
7    OUTPUT_BIGOR    (0,(4,5,6))    11111110    3    (2,2,2)
8    OUTPUT_BIGOR    (1,(1,5,6))    11111101    2    (2,2,2)
9    OUTPUT_BIGOR    (2,(2,5,6))    11111011    2    (2,2,2)
10    OUTPUT_BIGOR    (3,(1,2,6))    11110111    1    (2,2,2)
11    OUTPUT_BIGOR    (4,(3,4,6))    11101111    2    (2,2,2)
12    OUTPUT_BIGOR    (5,(1,3,6))    11011111    1    (2,2,2)
13    OUTPUT_BIGOR    (6,(2,3,6))    10111111    1    (2,2,2)
14    OUTPUT_BIGOR    (7,(1,2,3))    01111111    0    (0,0,0)
"""

GATE_TYPE_MAPPING = {
    "TRUE": "input",  # Read "this is given beforehand"
    "INPUT": "input",
    "NAND_BIGORS": "nand",
    "OUTPUT_BIGOR": "or"
}


def to_std(raw: str):
    def get_bigor(indices):
        if isinstance(indices, int):
            return tts_by_index[indices]
        if len(indices) == 0:
            return 0
        elif len(indices) == 1:
            return tts_by_index[indices[0]]
        if indices not in bigors_by_indices:
            tts = [tts_by_index[i] for i in indices]
            result = reduce(or_, tts)
            bigors_by_indices[indices] = result
            out.append({
                "gate_type": "or",
                "truth_table": result,
                "sources": tts
            })
        return bigors_by_indices[indices]

    bigors_by_indices = {}
    tts_by_index = {}
    produced_tts = set()
    out = []
    inputs = set()
    outputs = set()
    n = 0
    for row in raw.strip().splitlines(False):
        index, gt, args, tt, nand_cost, delays = row.split()

        tt = tts_by_index[int(index)] = int(tt, 2)
        produced_tts.add(tt)

        args = literal_eval(args)
        match gt, args:
            case "TRUE", _:
                inputs.add(tt)
            case "INPUT", _:
                inputs.add(tt)
                n += 1
            case "NAND_BIGORS", (left, right):
                out.append({
                    "gate_type": "nand",
                    "truth_table": tt,
                    "sources": [get_bigor(left), get_bigor(right)],
                })
            case "OUTPUT_BIGOR", (out_index, bigor):
                bigor_tt = get_bigor(bigor)
                assert tt == bigor_tt, (out_index, tt, bigor_tt, bigor)
                outputs.add(tt)
            case _:
                raise NotImplementedError(gt, args)
    return {
        "input_count": n,
        "inputs": list(inputs),
        "outputs": list(outputs),
        "gates": out
    }

json.dump(to_std(example), open("inv_dev.tcsol.json", "w"))