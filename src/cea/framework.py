from abc import ABCMeta, abstractmethod
from dataclasses import dataclass
from typing import Sequence, Callable, Self
import inspect


class Var(metaclass=ABCMeta):
    name: str

    def __str__(self) -> str:
        return f"${self.name}"


class Term(metaclass=ABCMeta):
    @classmethod
    @abstractmethod
    def var(cls, name: str) -> Var:
        pass


# __init__ must take a list of Term
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
