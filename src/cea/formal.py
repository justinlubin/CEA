from abc import ABCMeta, abstractmethod
from dataclasses import dataclass
from typing import Sequence, Callable, Self
import inspect


# https://stackoverflow.com/a/952952
def flatten(l):
    return [item for sublist in l for item in sublist]


################################################################################
# Core


class Var(metaclass=ABCMeta):
    name: str

    def __str__(self) -> str:
        return self.name


class Term(metaclass=ABCMeta):
    @classmethod
    @abstractmethod
    def var(cls, name: str) -> Var:
        pass


@dataclass
class Relation:
    name: str
    arity: Sequence[type[Term]]


class Atom:
    rel: Relation
    args: Sequence[Term]

    def __init__(self, rel: Relation, args: Sequence) -> None:
        if len(rel.arity) != len(args):
            raise ValueError("Mismatched arity length")
        for i, (s, arg) in enumerate(zip(rel.arity, args)):
            if not isinstance(arg, s):
                raise ValueError(f"Mismatched arity: arg {i}")

        self.rel = rel
        self.args = args

    def __str__(self) -> str:
        return str(self.rel.name) + "(" + ", ".join(map(str, self.args)) + ")"


@dataclass
class Formula:
    fvs: Sequence[Sequence[Var]]
    conds: Sequence[Atom]


@dataclass
class Function:
    name: str
    dom: Sequence[type]
    cod: type
    precondition: Formula


@dataclass
class Rule:
    name: str
    head: Atom
    body: Sequence[Atom]

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

RELATIONS: dict[type, Relation] = {}


def primitive(*arity: type):
    def decorator(cls: type) -> type:
        RELATIONS[cls] = Relation(cls.__name__, arity)
        return cls

    return decorator


def event(*arity: type):
    def decorator(cls: type) -> type:
        RELATIONS[cls] = Relation(cls.__name__, arity)
        return cls

    return decorator


def analysis(*arity: type):
    def decorator(cls: type) -> type:
        RELATIONS[cls] = Relation(cls.__name__, arity)
        return cls

    return decorator


API: list[Function] = []


def precondition(pc: Callable):
    def wrapper(func: Callable) -> Callable:
        sig = inspect.signature(func)
        var_names = list(inspect.signature(pc).parameters.keys())

        name = func.__name__
        cod = sig.return_annotation

        dom = []
        fvs: list[list[Var]] = []
        i = 0
        for p in sig.parameters.values():
            dom.append(p.annotation)
            fvs.append([])
            for a in RELATIONS[p.annotation].arity:
                fvs[-1].append(a.var(var_names[i]))
                i += 1

        fvs.append([])
        for a in RELATIONS[cod].arity:
            fvs[-1].append(a.var(var_names[i]))
            i += 1

        conds = pc(*flatten(fvs))

        API.append(Function(name, dom, cod, Formula(fvs, conds)))

        return func

    return wrapper


def rule_of_fun(f: Function) -> Rule:
    return Rule(
        f.name,
        Atom(RELATIONS[f.cod], f.precondition.fvs[-1]),
        [Atom(RELATIONS[t], fv) for t, fv in zip(f.dom, f.precondition.fvs[:-1])]
        + list(f.precondition.conds),
    )


################################################################################
# Primitives

### Time


# Terms


class Time(Term, metaclass=ABCMeta):
    def __eq__(self, other) -> Atom:  # type: ignore[override]
        return Atom(RELATIONS[TimeEq], [self, other])

    def __lt__(self, other) -> Atom:  # type: ignore[override]
        return Atom(RELATIONS[TimeLt], [self, other])

    def uniq(self) -> Atom:
        return Atom(RELATIONS[TimeUnique], [self])

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


@primitive(Time, Time)
class TimeEq:
    pass


@primitive(Time, Time)
class TimeLt:
    pass


@primitive(Time)
class TimeUnique:
    pass


### Conditions

# Terms


class Cond(Term, metaclass=ABCMeta):
    def __eq__(self, other) -> Atom:  # type: ignore[override]
        return Atom(RELATIONS[CondEq], [self, other])

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


@primitive(Cond, Cond)
class CondEq:
    pass


################################################################################
# Instantiation

### Events


@event(Time, Cond)
@dataclass
class Transfect:
    library: str


@event(Time, Cond)
@dataclass
class Seq:
    results: str


### Analyses


@analysis(Time, Time, Cond)
@dataclass
class SGRE:
    fold_change: float
    sig: float


### API


@precondition(
    # lambda tr, s1, s2, ret:
    lambda t0, c0, t1, c1, t2, c2, t3a, t3b, c3: [
        t0 < t1,
        t1 < t2,
        t0.uniq(),
        t1 == t3a,
        t2 == t3b,
        c0 == c1,
        c0 == c2,
        c0 == c3,
    ],
)
def sgre(tr: Transfect, s1: Seq, s2: Seq) -> SGRE:
    return SGRE(2, 0.03)


################################################################################
# Scratch

print(rule_of_fun(API[0]))
