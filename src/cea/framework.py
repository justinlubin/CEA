from abc import ABCMeta
from collections import OrderedDict
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
from .util import override


class Library:
    _rules: list[NamedRule]

    def __init__(self) -> None:
        self._rules = []

    def register_rule(self, named_rule: NamedRule) -> None:
        self._rules.append(named_rule)

    def rules(self) -> list[NamedRule]:
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
            if name.startswith("_"):
                continue
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

    def __repr__(self) -> str:
        return self.unparse()

    def unparse(self) -> str:
        arg_string = ", ".join(
            [f"{k}={self.get_arg(k).unparse()}" for k in self.relation().arity()]
        )
        return self.__class__.__qualname__ + "(" + arg_string + ")"


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
        for pc_param, func_param in zip(pc_params, func_params):
            if pc_param.name != func_param.name:
                raise ValueError(
                    "Precondition parameter name does not match parameter name"
                )

            if pc_param.name == "ret":
                raise ValueError("Non-last parameter name is ret")

            assert issubclass(pc_param.annotation, Metadata)
            assert issubclass(func_param.annotation, Value)

            if pc_param.annotation._parent != func_param.annotation:
                raise ValueError(
                    "Precondition parameter type does not match function parameter type"
                )

            args.append(pc_param.annotation.free(f"{pc_param.name}__"))

        if pc_params[-1].name != "ret":
            raise ValueError("Precondition last parameter name not 'ret'")

        if func_sig.return_annotation._parent != pc_params[-1].annotation._parent:
            raise ValueError(
                "Precondition last parameter type does not match function return type"
            )

        args.append(pc_params[-1].annotation.free("ret__"))

        library.register_rule(
            NamedRule(
                label=func,
                rule=Rule(
                    head=args[-1],
                    dependencies=OrderedDict(
                        (f.name, a) for f, a in zip(func_params, args[:-1])
                    ),
                    checks=tuple(pc(*args)),
                ),
            )
        )

        return func

    return wrapper


class Value(metaclass=ABCMeta):
    class D:
        _parent: ClassVar[type]
        ...

    class M(Metadata):
        _parent: ClassVar[type]
        ...

    d: object
    m: Metadata

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        cls.M._parent = cls
        cls.D._parent = cls

    def __init__(self, d: object, m: Metadata):
        assert isinstance(d, self.D)
        assert isinstance(m, self.M)
        self.d = d
        self.m = m

    @classmethod
    def matches(cls, d: type, m: type):
        return d == cls.D and m == cls.M

    def __repr__(self) -> str:
        return (
            self.__class__.__qualname__
            + "(d="
            + repr(self.d)
            + ", m="
            + repr(self.m)
            + ")"
        )


class Event(Value):
    pass


class Analysis(Value):
    pass
