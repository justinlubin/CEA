from abc import ABCMeta, abstractmethod
from dataclasses import dataclass
from typing import Sequence, Callable, Self, Optional, ClassVar
import inspect

# Globals


class Globals:
    _relations: ClassVar[list["Relation"]] = []
    _rules: ClassVar[list["Rule"]] = []

    @staticmethod
    def defined_relations():
        return Globals._relations.copy()

    @staticmethod
    def defined_rules():
        return Globals._rules.copy()


# Variables and terms


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


# Relations

Relation = type["Atom"]


class Atom(metaclass=ABCMeta):
    """___init___ must take a list of Term."""

    # @abstractmethod
    # def __init__(self) -> None:
    #     ...

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        Globals._relations.append(cls)

    # Relation methods

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

    # Atom methods

    def __str__(self) -> str:
        inner = [f"{p.name}={getattr(self, p.name)}" for p in self.arity()]
        return self.name() + "(" + ", ".join(inner) + ")"

    def dl_repr(self) -> str:
        inner = [getattr(self, p.name).dl_repr() for p in self.arity()]
        return self.name() + "(" + ", ".join(inner) + ")"


# Observations


# class ObservationMeta(ABCMeta):
#     M: type[Relation]
#
#     def __matmul__(self, other: Sequence[Term]) -> Relation:
#         return self.M(*other)
#
#
# class Observation(metaclass=ABCMeta):
#     # Metadata
#     class M(Relation):
#         ...
#
#     # Data
#     class D:
#         ...
#
#     def __new__(cls, *args, **kwargs):
#         raise TypeError("Cannot instantiate observation; insantiate M or D instead")
#
#
# _RELATIONS = []

# Rules


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

    def dl_repr(self) -> str:
        rhs = [r.dl_repr() for r in self.body]
        return self.head.dl_repr() + " :-\n  " + ",\n  ".join(rhs) + "."


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

            if not pp.annotation.__qualname__.endswith(".M"):
                raise ValueError("Precondition parameter type is not a metadata type")

            if not fp.annotation.__qualname__.endswith(".D"):
                raise ValueError("Function parameter type is not a data type")

            if pp.annotation.__qualname__[:-2] != fp.annotation.__qualname__[:-2]:
                raise ValueError(
                    "Precondition parameter type does not match function parameter type"
                )

            args.append(pp.annotation.free(f"{fp.name}."))

        if pc_params[-1].name != "ret":
            raise ValueError("Precondition last parameter name not 'ret'")

        if not pc_params[-1].annotation.__qualname__.endswith(".M"):
            raise ValueError("Precondition last parameter type is not a metadata type")

        if not func_sig.return_annotation.__qualname__.endswith(".D"):
            raise ValueError("Function return type is not a data type")

        if (
            pc_params[-1].annotation.__qualname__[:-2]
            != func_sig.return_annotation.__qualname__[:-2]
        ):
            raise ValueError(
                "Precondition last parameter type does not match function return type"
            )

        args.append(pc_params[-1].annotation.free("ret."))

        Globals._rules.append(
            Rule(
                name=func.__name__,
                head=args[-1],
                body=args[:-1] + pc(*args),
            )
        )

        return func

    return wrapper
