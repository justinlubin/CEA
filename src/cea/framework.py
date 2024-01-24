import inspect
from typing import (
    Callable,
    Optional,
    TypeVar,
    ClassVar,
    ParamSpec,
    Sequence,
    Iterable,
)

from .core import *


class Library:
    _rules: list[Rule]

    def __init__(self):
        self._rules = []

    def register_rule(self, rule: Rule) -> None:
        self._rules.append(rule)

    def rules(self) -> list[Rule]:
        return self._rules

    @staticmethod
    def merge(libraries: Iterable["Library"]) -> "Library":
        ret = Library()
        for lib in libraries:
            ret._rules.extend(lib._rules)
        return ret


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
        for k in ra:
            assert kwargs[k].sort() == ra[k]
            setattr(self, k, kwargs[k])

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
    def class_relation(cls) -> Relation:
        return cls._relation

    @classmethod
    def infix_symbol(cls) -> Optional[str]:
        return None

    M = TypeVar("M", bound="Metadata")

    @classmethod
    def free(cls: type[M], prefix: str) -> M:
        return cls(**cls.class_relation().free_assignment(prefix))


P = ParamSpec("P")
T = TypeVar("T")


def precondition(
    library: Library, pc: Callable[..., Sequence[Atom]]
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

            assert issubclass(fp.annotation, Event) or issubclass(
                fp.annotation, Analysis
            )

            if not fp.annotation.matches(pp.annotation):
                raise ValueError(
                    "Precondition parameter type does not match function parameter type"
                )

            args.append(pp.annotation.free(f"{fp.name}__"))

        if pc_params[-1].name != "ret":
            raise ValueError("Precondition last parameter name not 'ret'")

        if not func_sig.return_annotation.matches(pc_params[-1].annotation):
            raise ValueError(
                "Precondition last parameter type does not match function return type"
            )

        args.append(pc_params[-1].annotation.free("ret__"))

        library.register_rule(
            Rule(
                label=func,
                head=args[-1],
                dependencies=tuple(args[:-1]),
                checks=tuple(pc(*args)),
            )
        )

        return func

    return wrapper


class Event:
    class M(Metadata):
        pass

    @classmethod
    def matches(cls, m: type) -> bool:
        return m == cls.M


class Analysis(metaclass=ABCMeta):
    class M(Metadata):
        pass

    @classmethod
    def matches(cls, m: type) -> bool:
        return m == cls.M
