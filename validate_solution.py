import json
from collections import deque
from dataclasses import dataclass
from functools import cached_property, reduce
from operator import or_
from typing import Callable


class ValidationError(ValueError):
    pass


@dataclass
class Validator:
    n: int

    @cached_property
    def tt_length(self):
        return 2 ** self.n

    @cached_property
    def f(self) -> Callable[[int], str]:
        return f"{{:0{self.tt_length}b}}".format

    @cached_property
    def mask(self):
        return (2 ** self.tt_length - 1)

    def validate(self, gates, known):
        tts = set(known)

        def require(inside_gt, inside_tt, tt):
            if tt not in tts:
                raise ValidationError(
                    f"{inside_gt} resulting in {self.f(inside_tt)} failed to validate. It uses "
                    f"Truth Table {self.f(tt)}, which hasn't been produced at this point.\n"
                    f"Available at this point: {', '.join(map(self.f, tts))}"
                )

        def check_tt(tt: int) -> int:
            if tt < 0 or int(tt) != tt or tt > self.mask:
                raise ValidationError(f"Encountered Invalid Truth Table {tt!r}")
            return int(tt)

        for gate in gates:
            match gate:
                case {"gate_type": "nand", "truth_table": expected, "sources": [left, right]}:
                    expected = check_tt(expected)
                    left = check_tt(left)
                    right = check_tt(right)
                    if (v := (~(left & right)) & self.mask) != expected:
                        raise ValidationError(
                            f"Nand Gate failed to validated. Claims to produce {self.f(expected)} from "
                            f"``{self.f(left)} NAND {self.f(right)}``, "
                            f"but that is actually {v}"
                        )
                    require("Nand Gate", expected, left)
                    require("Nand Gate", expected, right)
                    tts.add(expected)
                case {"gate_type": "not", "truth_table": expected, "sources": [source]}:
                    expected = check_tt(expected)
                    source = check_tt(source)
                    if (v := (~source) & self.mask) != expected:
                        raise ValidationError(
                            f"Not Gate failed to validated. Claims to produce {self.f(expected)} from "
                            f"``NOT {self.f(source)}``, but that is actually {v}"
                        )
                    require("Not Gate", expected, source)
                    tts.add(expected)
                case {"gate_type": "or", "truth_table": expected, "sources": [*sources]}:
                    expected = check_tt(expected)
                    *sources, = map(check_tt, sources)
                    if (v := reduce(or_, sources)) & self.mask != expected:
                        expr = " OR ".join(map(self.f, sources))
                        raise ValidationError(
                            f"Or Gate failed to validated. Claims to produce {self.f(expected)} from "
                            f"``{expr}``, "
                            f"but that is actually {v}"
                        )
                    for source in sources:
                        require("Or Gate", expected, source)
                    tts.add(expected)
                case other:
                    raise ValidationError(f"Unknown Gate type: {other}")

    def sort(self, gates, inputs):
        """

        :param gates:
        :param inputs:
        :return:
        """
        all_available = {*inputs, *(gate["truth_table"] for gate in gates)}
        remaining = deque(gates)
        done = set(inputs)
        out = []
        seen_since_insert = set()
        while remaining:
            current = remaining.popleft()
            if current["truth_table"] in seen_since_insert:
                raise ValidationError(f"Detected Circle involving these truth table gates: {seen_since_insert}")
            if any((witness := source) not in all_available for source in current["sources"]):
                raise ValidationError(f"Required Truth table {witness} appears to be unreachable")
            if all(source in done for source in current["sources"]):
                seen_since_insert.clear()
                out.append(current)
                done.add(current["truth_table"])
            else:
                seen_since_insert.add(current["truth_table"])
                remaining.append(current)

        return out

    def to_pydot(self, tcsol):
        import pydot

        dot = pydot.Dot(rankdir="LR")

        for inp in tcsol["inputs"]:
            if inp not in (0, self.mask):
                dot.add_node(pydot.Node(str(inp), label=self.f(inp), ))

        by_tt = {gate["truth_table"]: gate for gate in tcsol["gates"]}

        k = 2 ** tcsol["input_count"]

        done = set()
        queue = list(tcsol["outputs"])
        while queue:
            current = queue.pop()
            if current in done:
                continue
            done.add(current)
            if current in tcsol["inputs"]:
                c = "#90EE90"
                if current in tcsol["outputs"]:
                    c = "#9090EE"
                dot.add_node(pydot.Node(str(current), label=f'Input:\n{current:0{k}b}', fillcolor=c, style="filled"))
            else:
                gate = by_tt[current]
                gt = gate["gate_type"]
                if current in tcsol["outputs"]:
                    c = "#9090EE"
                elif gt in ("nand", "not"):
                    c = "#EE9090"
                else:
                    c = "#FFFFFF"
                dot.add_node(pydot.Node(str(current), label=f'{gt}:\n{current:0{k}b}', fillcolor=c, style="filled"))
                for source in gate["sources"]:
                    dot.add_edge(pydot.Edge(str(source), str(current)))
                    if source not in done: queue.append(source)
        return dot


def validate(tcsol):
    if not 2 <= tcsol["input_count"] <= 6:
        raise ValidationError(f"Expected Input count to be between 2 and 6, got {tcsol['input_count']}")
    validator = Validator(tcsol["input_count"])
    validator.validate(validator.sort(tcsol["gates"], tcsol["inputs"]), tcsol["inputs"])
    validator.to_pydot(tcsol).write_png("test.png")


validate(json.load(open("es_fa_6_4.tcsol.json")))
