import inspect
from typing import Callable, Optional, TypeVar, ClassVar, ParamSpec, Sequence

from .core import *


class Globals:
    _events: ClassVar[list["Relation"]] = []
    _analyses: ClassVar[list["Relation"]] = []
    _rules: ClassVar[list["Rule"]] = []

    @staticmethod
    def defined_events() -> list["Relation"]:
        return Globals._events.copy()

    @staticmethod
    def defined_analyses() -> list["Relation"]:
        return Globals._analyses.copy()

    @staticmethod
    def defined_relations() -> list["Relation"]:
        return Globals.defined_events() + Globals.defined_analyses()

    @staticmethod
    def defined_rules() -> list["Rule"]:
        return Globals._rules.copy()


class Metadata(Atom):
    _relation: ClassVar[Relation]

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)

        # Order is undefined but fixed!
        arity = OrderedDict()

        for name, typ in cls.__annotations__.items():
            assert issubclass(typ, Term)
            arity[name] = typ.sort()

        cls._relation = Relation(
            name=cls.__qualname__.replace(".", "_"),
            arity=arity,
            infix_symbol=cls.infix_symbol(),
        )

    def __init__(self, **kwargs: Term):
        ra = self.relation().arity()
        assert kwargs.keys() == ra.keys()
        for k in self.relation().arity():
            assert kwargs[k].sort() == ra[k]
            setattr(self, k, kwargs[k])

    @classmethod
    def class_relation(cls) -> Relation:
        return cls._relation

    @override
    def get_arg(self, key: str) -> Term:
        return getattr(self, key)

    @override
    def set_arg(self, key: str, val: Term) -> "Atom":
        new_args = {}
        for k in self.relation().arity():
            if k == key:
                new_args[k] = val
            else:
                new_args[k] = self.get_arg(k)
        return type(self)(**new_args)

    @override
    def relation(self) -> Relation:
        return self.class_relation()

    @classmethod
    def infix_symbol(cls) -> Optional[str]:
        return None

    M = TypeVar("M", bound="Metadata")

    @classmethod
    def free(cls: type[M], prefix: str) -> M:
        return cls(**cls.class_relation().free_args(prefix))


P = ParamSpec("P")
T = TypeVar("T")


def precondition(
    pc: Callable[..., Sequence[Atom]]
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    def wrapper(func: Callable[P, T]) -> Callable[P, T]:
        pc_sig = inspect.signature(pc)
        func_sig = inspect.signature(func)

        pc_params = list(pc_sig.parameters.values())
        func_params = list(func_sig.parameters.values())

        if len(pc_params) != len(func_params) + 1:
            raise ValueError("Precondition length does not match function length + 1")

        args: list[Metadata] = []
        for pp, fp in zip(pc_params, func_params):
            if pp.name != fp.name:
                raise ValueError(
                    "Precondition parameter name does not match parameter name"
                )

            if pp.annotation.__qualname__ != fp.annotation.__qualname__ + ".M":
                raise ValueError(
                    "Precondition parameter type does not match function parameter type"
                )

            if not issubclass(pp.annotation, Metadata):
                raise ValueError("Precondition parameter type is not metadata")

            args.append(pp.annotation.free(f"{fp.name}__"))

        if pc_params[-1].name != "ret":
            raise ValueError("Precondition last parameter name not 'ret'")

        if (
            pc_params[-1].annotation.__qualname__
            != func_sig.return_annotation.__qualname__ + ".M"
        ):
            raise ValueError(
                "Precondition last parameter type does not match function return type"
            )

        if not issubclass(pc_params[-1].annotation, Metadata):
            raise ValueError("Precondition last parameter type is not metadata")

        args.append(pc_params[-1].annotation.free("ret__"))

        Globals._rules.append(
            Rule(
                label=func,
                head=args[-1],
                dependencies=tuple(args[:-1]),
                checks=tuple(pc(*args)),
            )
        )

        return func

    return wrapper


def event(cls):
    Globals._events.append(cls.M.class_relation())
    return cls


def analysis(cls):
    Globals._analyses.append(cls.M.class_relation())
    return cls
