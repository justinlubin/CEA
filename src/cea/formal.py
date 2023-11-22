from abc import ABCMeta, abstractmethod
from dataclasses import dataclass
from typing import Sequence, Callable, Self
import inspect


################################################################################
# Core


class Var(metaclass=ABCMeta):
    name: str

    def __str__(self) -> str:
        return f"${self.name}"


class Term(metaclass=ABCMeta):
    @classmethod
    @abstractmethod
    def var(cls, name: str) -> Var:
        pass


# __init__ should take a list of Term
class Relation(metaclass=ABCMeta):
    @classmethod
    def arity(cls):
        return list(inspect.signature(cls.__init__).parameters.values())[1:]

    @classmethod
    def full(cls, prefix: str) -> Self:
        return cls(*[p.annotation.var(prefix + p.name) for p in cls.arity()])

    def __str__(self) -> str:
        inner = [f"{p.name}={getattr(self, p.name)}" for p in self.arity()]
        return self.__class__.__qualname__ + "(" + ", ".join(inner) + ")"


class Data(metaclass=ABCMeta):
    @dataclass
    class R(Relation):
        pass


@dataclass
class Rule:
    name: str
    head: Relation
    body: Sequence[Relation]

    def __str__(self) -> str:
        return (
            f"== {self.name} ============================\n"
            + "\n".join(map(str, self.body))
            + "\n--------------------\n"
            + str(self.head)
            + "\n=============================="
            + "=" * (len(self.name) + 2)
        )


################################################################################
# Framework


RULES: list[Rule] = []


def precondition(pc: Callable):
    def wrapper(func: Callable) -> Callable:
        pc_sig = inspect.signature(pc)
        func_sig = inspect.signature(func)

        pc_params = list(pc_sig.parameters.values())
        func_params = list(func_sig.parameters.values())

        if len(pc_params) != len(func_params) + 1:
            raise ValueError("Precondition length does not match function length + 1")

        ars = []
        for pp, fp in zip(pc_params, func_params):
            if pp.name != fp.name:
                raise ValueError(
                    "Precondition parameter name does not match parameter name"
                )

            if pp.annotation != fp.annotation.R:
                raise ValueError(
                    "Precondition parameter type does not match function parameter type"
                )

            ars.append(pp.annotation.full(f"{fp.name}."))

        if pc_params[-1].name != "ret":
            raise ValueError("Precondition last parameter name not 'ret'")

        if pc_params[-1].annotation != func_sig.return_annotation.R:
            raise ValueError(
                "Precondition last parameter type does not match function return type"
            )

        ars.append(pc_params[-1].annotation.full("ret."))

        RULES.append(
            Rule(
                name=func.__name__,
                head=ars[-1],
                body=pc(*ars),
            )
        )

        return func

    return wrapper


################################################################################
# Primitives

### Time


# Terms


class Time(Term):
    def __eq__(self, other) -> "TimeEq":  # type: ignore[override]
        return TimeEq(self, other)

    def __lt__(self, other) -> "TimeLt":  # type: ignore[override]
        return TimeLt(self, other)

    def uniq(self) -> "TimeUnique":
        return TimeUnique(self)

    @classmethod
    def var(cls, name: str) -> Var:
        return TimeVar(name)


class TimeVar(Time, Var):
    name: str

    def __init__(self, name: str):
        self.name = name


class TimeLit(Time):
    day: int

    def __init__(self, day: int):
        if day < 0:
            raise ValueError("Negative day")
        self.day = day


# Relations


@dataclass
class TimeEq(Relation):
    lhs: Time
    rhs: Time


@dataclass
class TimeLt(Relation):
    lhs: Time
    rhs: Time


@dataclass
class TimeUnique(Relation):
    t: Time


### Conditions

# Terms


class Cond(Term, metaclass=ABCMeta):
    def __eq__(self, other) -> "CondEq":  # type: ignore[override]
        return CondEq(self, other)

    @classmethod
    def var(cls, name: str) -> Var:
        return CondVar(name)


class CondVar(Cond, Var):
    name: str

    def __init__(self, name: str) -> None:
        self.name = name


class CondLit(Cond):
    cond: str

    def __init__(self, cond: str) -> None:
        self.cond = cond


# Relations


@dataclass
class CondEq(Relation):
    lhs: Cond
    rhs: Cond


################################################################################
# Instantiation

### Events


@dataclass
class TCRelation(Relation):
    t: Time
    c: Cond


@dataclass
class Transfect(Data):
    library: str

    class R(TCRelation):
        pass


@dataclass
class Seq(Data):
    results: str

    class R(TCRelation):
        pass


### Analyses


@dataclass
class SGRE(Data):
    fold_change: float
    sig: float

    @dataclass
    class R(Relation):
        ti: Time
        tf: Time
        c: Cond


### API


def pc(tr: Transfect.R, s1: Seq.R, s2: Seq.R, ret: SGRE.R) -> list[Relation]:
    return [
        tr.t < s1.t,
        s1.t < s2.t,
        tr.t.uniq(),
        ret.ti == s1.t,
        ret.tf == s2.t,
        tr.c == s1.c,
        tr.c == s2.c,
        tr.c == ret.c,
    ]


@precondition(pc)
def sgre(tr: Transfect, s1: Seq, s2: Seq) -> SGRE:
    return SGRE(2, 0.03)


################################################################################
# Scratch

print(RULES[0])
