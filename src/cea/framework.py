from abc import ABCMeta, abstractmethod
from dataclasses import dataclass
from typing import Callable, Self, Optional, ClassVar
import inspect

from . import util

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
    """Subclass ___init___ must take a list of Term (not checked)."""

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


# Rules


@dataclass
class Rule:
    fn: Callable
    head: Atom
    dependencies: list[Atom]
    checks: list[Atom]

    def __str__(self) -> str:
        return (
            f"== {self.name} ============================\n"
            + "\n".join(map(str, self.body()))
            + "\n--------------------\n"
            + str(self.head)
            + "\n=============================="
            + "=" * (len(self.name()) + 2)
        )

    def name(self) -> str:
        return self.fn.__name__

    def body(self) -> list[Atom]:
        return self.dependencies + self.checks

    def dl_repr(self) -> str:
        lhs = self.head.dl_repr()
        rhs = ",\n  ".join([r.dl_repr() for r in self.body()]) + "."
        return f"{lhs} :-\n  {rhs}"


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
                fn=func,
                head=args[-1],
                dependencies=args[:-1],
                checks=pc(*args),
            )
        )

        return func

    return wrapper


class DerivationTree(metaclass=ABCMeta):
    @abstractmethod
    def tree_string(self, depth: int = 0) -> str:
        ...

    @abstractmethod
    def goals(self) -> list[tuple[Atom, list[int]]]:
        ...

    @abstractmethod
    def replace(
        self, breadcrumbs: list[int], new_subtree: "DerivationTree"
    ) -> "DerivationTree":
        ...

    def __str__(self) -> str:
        return self.tree_string(depth=0)


@dataclass
class DerivationStep(DerivationTree):
    fn: Callable
    consequent: Atom
    antecedents: list[DerivationTree]

    def tree_string(self, depth: int = 0) -> str:
        spine = "-" * depth
        ret = f"{spine} {self.consequent}"
        for a in self.antecedents:
            ret += "\n" + a.tree_string(depth=depth)
        return ret

    def goals(self) -> list[tuple[Atom, list[int]]]:
        return util.flatten(
            [
                [(g, crumbs + [i]) for g, crumbs in a.goals()]
                for i, a in enumerate(self.antecedents)
            ]
        )

    def replace(
        self, breadcrumbs: list[int], new_subtree: DerivationTree
    ) -> DerivationTree:
        if not breadcrumbs:
            return new_subtree
        child = breadcrumbs.pop()  # modifies breadcrumbs
        if child < 0 or child >= len(self.antecedents):
            raise ValueError("Invalid breadcrumbs for derivation tree")
        return DerivationStep(
            fn=self.fn,
            consequent=self.consequent,
            antecedents=(
                self.antecedents[:child]
                + [self.antecedents[child].replace(breadcrumbs, new_subtree)]
                + self.antecedents[child + 1 :]
            ),
        )


@dataclass
class DerivationGoal(DerivationTree):
    goal: Atom

    def tree_string(self, depth: int = 0):
        return "-" * depth + f"{self.goal} *"

    def goals(self) -> list[tuple[Atom, list[int]]]:
        return [(self.goal, [])]

    def replace(
        self, breadcrumbs: list[int], new_subtree: DerivationTree
    ) -> DerivationTree:
        if not breadcrumbs:
            return new_subtree
        raise ValueError("Invalid breadcrumbs for derivation tree")
