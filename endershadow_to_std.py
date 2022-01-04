import json
from functools import reduce
from operator import or_
from types import SimpleNamespace

from tools import make_input

example = """
GateTree(gateType=NOT, inputs=[1], value=0x5555555555555555, delay=2)
    GateTree(gateType=NAND, inputs=[2, 4], value=0x3f3f3f3f3f3f3f3f, delay=2)
        GateTree(gateType=NOT, inputs=[6], value=0x303030303030303, delay=2)
            GateTree(gateType=NAND, inputs=[14, 24], value=0x8282828282828282, delay=4)
                GateTree(gateType=NAND, inputs=[35, 37], value=0x1414141414141414, delay=4)
                    GateTree(gateType=OR, inputs=[192], value=0x9696969696969696, delay=4) # sum
                GateTree(gateType=NAND, inputs=[16, 40], value=0xe8e8e8e8e8e8e8e8, delay=4) # carry
"""


def to_std(raw: str, input_count, outputs):
    """
    This function calls `eval`. ONLY USE IT WHEN YOU TRUST THE RAW STRING
    """

    def get_or(bitfield):
        assert isinstance(bitfield, int)
        if bitfield not in ors_by_bitfield:
            i = 0
            tts = []
            n = bitfield
            while n:
                if n & 1:
                    tts.append(tts_by_index[i])
                i += 1
                n //= 2
            if len(tts) == 1:
                return tts[0]
            result = reduce(or_, tts)
            out.append({
                "gate_type": "or",
                "truth_table": result,
                "sources": tts
            })
            ors_by_bitfield[bitfield] = result
        return ors_by_bitfield[bitfield]

    m = 2**(2 ** input_count) - 1
    ors_by_bitfield = {}
    tts_by_index = {i: make_input(i , input_count, "big") for i in range(input_count)}
    inputs = set(tts_by_index.values())
    produced_tts = set()
    out: list[dict] = []
    for i, row in enumerate(raw.strip().splitlines(False), start=input_count):
        GateTree = SimpleNamespace
        gt = eval(row, {'GateTree': GateTree, __builtins__: {}},
                  {n: n for n in ('NAND', 'OR', 'NOT')})

        tt = tts_by_index[i] = gt.value & m
        produced_tts.add(tt)

        match gt:
            case GateTree(gateType='NAND', inputs=[left, right]):
                out.append({
                    "gate_type": "nand",
                    "truth_table": tt,
                    "sources": [get_or(left), get_or(right)],
                    "delay": gt.delay
                })
            case GateTree(gateType='OR', inputs=[value]):
                or_tt = get_or(value)
            case GateTree(gateType='NOT', inputs=[value]):
                out.append({
                    "gate_type": "not",
                    "truth_table": tt,
                    "sources": [get_or(value)],
                    "delay": gt.delay
                })
            case _:
                raise NotImplementedError(gt)
    return {
        "input_count": input_count,
        "inputs": list(inputs),
        "outputs": list(outputs),
        "gates": out
    }


json.dump(to_std(example, 3, {0x96, 0xe8}), open("es_fa_6_4.tcsol.json", "w"))
