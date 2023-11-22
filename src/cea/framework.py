from abc import ABCMeta, abstractmethod
from dataclasses import dataclass
from typing import Sequence, Callable, Self, Optional
import inspect

USER_MODE: bool = False


class Var(metaclass=ABCMeta):
    name: str

    def __init__(self, name: str) -> None:
        self.name = name

    def __str__(self) -> str:
        return f"${self.name}"

    def dl_repr(self) -> str:
        return self.name.replace(".", "_")


class Term(metaclass=ABCMeta):
    @classmethod
    @abstractmethod
    def var(cls, name: str) -> Var:
        ...

    @classmethod
    @abstractmethod
    def dl_type(cls) -> str:
        ...

    @abstractmethod
    def dl_repr(self) -> str:
        ...


# __init__ must take a list of Term
class Relation(metaclass=ABCMeta):
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        RELATIONS.append(cls)

    def __post_init__(self) -> None:
        if USER_MODE:
            TRACE.append(self)

    def __str__(self) -> str:
        inner = [f"{p.name}={getattr(self, p.name)}" for p in self.arity()]
        return self.name() + "(" + ", ".join(inner) + ")"

    @classmethod
    def name(cls) -> str:
        return cls.__qualname__.replace(".", "_")

    @classmethod
    def arity(cls):
        return list(inspect.signature(cls.__init__).parameters.values())[1:]

    @classmethod
    def free(cls, prefix: str) -> Self:
        return cls(*[p.annotation.var(prefix + p.name) for p in cls.arity()])

    @classmethod
    def dl_decl(cls) -> Optional[str]:
        inner = [f"{p.name}: {p.annotation.dl_type()}" for p in cls.arity()]
        return ".decl " + cls.name() + "(" + ", ".join(inner) + ")"

    def dl_repr(self) -> str:
        inner = [getattr(self, p.name).dl_repr() for p in self.arity()]
        return self.name() + "(" + ", ".join(inner) + ")"


RELATIONS: list[type[Relation]] = []
TRACE: list[Relation] = []
QOI: Optional[Relation] = None


class Data(metaclass=ABCMeta):
    class R(Relation):
        ...

    def __post_init__(self) -> None:
        if USER_MODE:
            raise ValueError("Please do not instantiate data in protocol definition!")


class EventMeta(ABCMeta):
    R: type[Relation]

    def __matmul__(self, other: Sequence[Term]) -> Relation:
        return self.R(*other)


class Event(metaclass=EventMeta):
    class R(Relation):
        ...


RELATIONS = []


@dataclass
class Goal(Relation):
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

    def dl_repr(self) -> str:
        rhs = [r.dl_repr() for r in self.body]
        return self.head.dl_repr() + " :-\n  " + ",\n  ".join(rhs) + "."


RULES: list[Rule] = []


def precondition(pc: Callable):
    def wrapper(func: Callable) -> Callable:
        pc_sig = inspect.signature(pc)
        func_sig = inspect.signature(func)

        pc_params = list(pc_sig.parameters.values())
        func_params = list(func_sig.parameters.values())

        if len(pc_params) != len(func_params) + 1:
            raise ValueError("Precondition length does not match function length + 1")

        args = []
        for pp, fp in zip(pc_params, func_params):
            if pp.name != fp.name:
                raise ValueError(
                    "Precondition parameter name does not match parameter name"
                )

            if pp.annotation != fp.annotation.R:
                raise ValueError(
                    "Precondition parameter type does not match function parameter type"
                )

            args.append(pp.annotation.free(f"{fp.name}."))

        if pc_params[-1].name != "ret":
            raise ValueError("Precondition last parameter name not 'ret'")

        if pc_params[-1].annotation != func_sig.return_annotation.R:
            raise ValueError(
                "Precondition last parameter type does not match function return type"
            )

        args.append(pc_params[-1].annotation.free("ret."))

        RULES.append(
            Rule(
                name=func.__name__,
                head=args[-1],
                body=args[:-1] + pc(*args),
            )
        )

        return func

    return wrapper


def dl_compile() -> str:
    blocks = []

    for rel in RELATIONS:
        rel_decl = rel.dl_decl()
        if rel_decl:
            blocks.append(rel_decl)

    blocks.append("")

    for rule in RULES:
        blocks.append(rule.dl_repr())

    blocks.append("")

    for fact in TRACE:
        blocks.append(fact.dl_repr() + ".")

    blocks.append("")

    if QOI:
        goal = Goal()
        blocks.append(Rule("goal", goal, [QOI]).dl_repr())
        blocks.append("")
        blocks.append(f".output {goal.name()}")

    return "\n".join(blocks)


def begin() -> None:
    global USER_MODE
    USER_MODE = True


def end(qoi_relation: Relation) -> None:
    global USER_MODE, QOI
    USER_MODE = False
    QOI = qoi_relation
    del TRACE[-1]
