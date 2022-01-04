import json

import lark
from lark import Transformer

parser = lark.Lark("""
solutions: "{" (solution ("," solution)*)? "}"
solution: "{" (gate ("," gate)*)? "}" | "[" (gate ("," gate)*)? "]"  
gate: "Gate" ":"? "{" tt "," delay "," gate_type "}"
tt: "truth_table" ":" INT
delay: "delay" ":" INT
gate_type: "gate_type" ":" CNAME ("(" (INT ("," INT)*)? ")")?

%import common.INT
%import common.CNAME
%import common.WS

%ignore WS
""", parser='lalr', start=['solutions', 'solution'])


class ToJson(Transformer):
    def __default__(self, data, children, meta):
        raise NotImplementedError(data, children, meta)

    def gate_type(self, children):
        return children[0].value, tuple(int(a.value) for a in children[1:])

    def tt(self, children):
        return int(children[0])

    def delay(self, children):
        return int(children[0])

    def gate(self, children):
        tt, delay, (gt, args) = children
        return {"truth_table": tt, "delay": delay, "gate_type": gt, "args": args}

    def solution(self, children):
        return children

    def solutions(self, children):
        return children


# tree = parser.parse(open("FA_6_4.txt").read())
tree = parser.parse("""
[Gate { truth_table: 15, delay: 0, gate_type: InputGate }, 
Gate { truth_table: 51, delay: 0, gate_type: InputGate }, 
Gate { truth_table: 85, delay: 0, gate_type: InputGate }, 
Gate { truth_table: 65514, delay: 2, gate_type: Nand(3, 4) }, 
Gate { truth_table: 65429, delay: 4, gate_type: Nand(7, 8) }, 
Gate { truth_table: 65532, delay: 2, gate_type: Nand(1, 2) }, 
Gate { truth_table: 23, delay: 4, gate_type: Nand(8, 32) }, 
Gate { truth_table: 105, delay: 6, gate_type: Nand(40, 80) }, 
Gate { truth_table: 105, delay: 6, gate_type: Or(128) }, 
Gate { truth_table: 23, delay: 4, gate_type: Or(64) }]
""", start="solution")

data = ToJson().transform(tree)

inputs = [0, 0b0000_1111, 0b0011_0011, 0b0101_0101, 0b1111_1111]
outputs = [0b0110_1001, 0b0001_0111]


def std_from_bitfield(network, known_inputs, outputs):
    indexed_gates = []
    out_gates = []

    for gate in network:
        match gate:
            case {"gate_type": "Nand" | "InputGate", "truth_table": tt}:
                indexed_gates.append(tt & 0xFF)

    known_ors = set()

    def get_or(bitfield):
        needed_tts = []
        i = 0
        result = 0
        while bitfield:
            if bitfield & 1:
                needed_tts.append(indexed_gates[i])
                result |= indexed_gates[i]
            bitfield //= 2
            i += 1
        needed_tts = tuple(sorted(needed_tts))
        if len(needed_tts) > 1 and needed_tts not in known_ors:
            out_gates.append({
                "gate_type": "or",
                "truth_table": result,
                "sources": needed_tts
            })
            known_ors.add(needed_tts)
        return result

    for gate in network:
        match gate:
            case {"gate_type": "Nand", "truth_table": tt, "delay": delay, "args": [left, right]}:
                out_gates.append({
                    "gate_type": "nand",
                    "truth_table": tt,
                    "delay": delay,
                    "sources": [get_or(left), get_or(right)]
                })
            case {"gate_type": "Or", "truth_table": tt, "delay": delay, "args": [value]}:
                get_or(value)
            case {"gate_type": "InputGate", "truth_table": tt}:
                assert tt in known_inputs, (tt, bin(tt))
            case other:
                raise NotImplementedError(other)
    return {
        "inputs": known_inputs,
        "outputs": outputs,
        "gates": out_gates
    }


s = json.dumps(std_from_bitfield(data, inputs, outputs), indent=2)
print(s)
