import json
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
        for gate in gates:
            match gate:
                case {"gate_type": "nand", "truth_table": expected, "sources": [left, right]}:
                    if (v := (~(left & right)) & self.mask) != expected:
                        raise ValidationError(
                            f"Nand Gate failed to validated. Claims to produce {self.f(expected)} from "
                            f"``{self.f(left)} NAND {self.f(right)}``, "
                            f"but that is actually {v}"
                        )
                    require("Nand Gate", expected, left)
                    require("Nand Gate", expected, right)
                    tts.add(expected)
                case {"gate_type": "or", "truth_table": expected, "sources": [*sources]}:
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
                    raise ValidationError(f"Unknown Gate structure: {other}")


def validate(tcsol):
    validator = Validator(tcsol["input_count"])
    validator.validate(tcsol["gates"], tcsol["inputs"])


validate(json.load(open("example.tcsol.json")))
