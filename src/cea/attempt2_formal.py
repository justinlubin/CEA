from abc import ABCMeta, abstractmethod
from dataclasses import dataclass
from typing import Sequence, ClassVar, Generic, TypeVar
import inspect

################################################################################
# Core


Symbol = str


class Sort:
    pass


class Term(metaclass=ABCMeta):
    @staticmethod
    def dom() -> Sequence[Sort]:
        return ()

    @staticmethod
    @abstractmethod
    def cod() -> Sort:
        pass


class Var(Term, metaclass=ABCMeta):
    @abstractmethod
    def name(self) -> str:
        pass


class Relation(metaclass=ABCMeta):
    _counter: ClassVar[int] = 0
    prefix: int | None = None

    @classmethod
    def name(cls) -> Symbol:
        return cls.__name__

    # def __getitem__(self, key) -> Var:
    #     if not isinstance(key, int):
    #         raise ValueError("Key not int")
    #     if key < 0:
    #         raise ValueError("Negative key")
    #     if key >= len(self.arity()):
    #         raise ValueError("Out-of-bounds key")
    #     if not self.prefix:
    #         self.prefix = Relation._counter
    #         Relation._counter += 1

    #     class V(Var):
    #         @staticmethod
    #         def cod() -> Sort:
    #             return self.arity()[key]

    #         @staticmethod
    #         def name() -> str:
    #             return f"{self.name()}-{Relation._counter}-{key}"

    #     return V()

    @staticmethod
    @abstractmethod
    def arity() -> Sequence[Sort]:
        pass


class Fact:
    rel: Relation
    args: list[Term]

    def __init__(self, rel: Relation, args: list[Term]) -> None:
        if len(rel.arity()) != len(args):
            raise ValueError("Mismatched arity length")
        for i, (s, arg) in enumerate(zip(rel.arity(), args)):
            if arg.dom():
                raise ValueError(f"Partially-applied argument: arg {i}")
            if arg.cod() != s:
                raise ValueError(f"Mismatched arity: arg {i}")

        self.rel = rel
        self.args = args


class Application(Term, metaclass=ABCMeta):
    head: Term
    args: list[Term]

    def __init__(self, head: Term, args: list[Term]):
        if len(head.dom()) != len(args):
            raise ValueError("Mismatched domain length")
        for i, (s, arg) in enumerate(zip(head.dom(), args)):
            if arg.dom():
                raise ValueError(f"Partially-applied argument: arg {i}")
            if arg.cod() != s:
                raise ValueError(f"Mismatched domain: arg {i}")
        self.head = head
        self.args = args

    @staticmethod
    def cod() -> Sort:
        return self.head.cod()


class Function(Term, metaclass=ABCMeta):
    def __init__(self):
        if not self.dom():
            raise ValueError("Function with empty domain")

    @abstractmethod
    def name(self) -> str:
        pass


def precondition(rels):
    def wrapper(func):
        class LibraryFunction(Function):
            def cod(self) -> Sort:
                return sig.return_annotation

        sig = inspect.signature(func)
        funs.append(
            Function(
                func.__name__,
                [p.annotation for p in sig.parameters.values()],
                sig.return_annotation,
                Formula(fvs, conds),
            )
        )
        return func

    return wrapper


################################################################################
# Sorts


Time = Sort()
Cond = Sort()

################################################################################
# Values

primitives: list[type] = []


def primitive(cls):
    primitives.append(cls)
    return cls


# Terms


class TimeLit(Term):
    day: int

    def __init__(self, day: int):
        if day < 0:
            raise ValueError("Negative day")
        self.day = day

    def cod(self) -> Sort:
        return Time


class TimeVar(Var):
    _name: str

    def __init__(self, name: str) -> None:
        self._name = name

    def name(self) -> str:
        return self._name

    def cod(self) -> Sort:
        return Time


@dataclass
class CondLit(Term):
    cond: str

    def cod(self) -> Sort:
        return Cond


# Relations


@primitive
class TimeEq(Relation):
    @staticmethod
    def arity() -> Sequence[Sort]:
        return (Time, Time)


@primitive
class TimeLt(Relation):
    @staticmethod
    def arity() -> Sequence[Sort]:
        return (Time, Time)


@primitive
class TimeUnique(Relation):
    @staticmethod
    def arity() -> Sequence[Sort]:
        return (Time,)


@primitive
class CondEq(Relation):
    @staticmethod
    def arity() -> Sequence[Sort]:
        return (Cond, Cond)


################################################################################
# Events

events: list[type] = []


def event(cls):
    events.append(cls)
    return cls


# Relations


@event
@dataclass
class Transfect(Relation):
    library: str

    @staticmethod
    def arity() -> Sequence[Sort]:
        return (Time, Cond)


@event
@dataclass
class Seq(Relation):
    results: str

    @staticmethod
    def arity() -> Sequence[Sort]:
        return (Time, Cond)


################################################################################
# Analyses


analyses: list[type] = []


def analysis(cls):
    analyses.append(cls)
    return cls


# Relations


@analysis
@dataclass
class SGRE(Relation):
    fold_change: float
    sig: float

    @staticmethod
    def arity() -> Sequence[Sort]:
        return (Time, Time, Cond)


t0 = TimeVar("t0")
t1 = TimeVar("t1")
t2 = TimeVar("t2")
t3 = TimeVar("t3")
t4 = TimeVar("t4")

c0 = CondVar("c0")
c1 = CondVar("c1")
c2 = CondVar("c2")


@precondition(
    fvs=[["t0"], ["t1", "c0"], ["t2", "c1"], ["t3", "t4", "c2"]],
    conds=[
        TimeLt(TimeVar("t0"), TimeVar()),
        TimeLt(s1[0], s2[0]),
        TimeUnique(tr[0]),
    ],
)
def sgre(tr: Transfect, s1: Seq, s2: Seq) -> SGRE:
    return SGRE(2, 0.03)


################################################################################
# Scratch

Fact(Transfect("crispri"), [TimeLit(1), CondLit("c")])
