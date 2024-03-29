from abc import ABCMeta, abstractmethod
from collections import OrderedDict
from typing import Callable, Optional

import inspect

from . import souffle

from .util import override


class Sort(metaclass=ABCMeta):
    @abstractmethod
    def dl_repr(self) -> str:
        ...

    @abstractmethod
    def parse(self, s: str) -> "Term":
        ...

    @abstractmethod
    def var(cls, name: str) -> "Var":
        ...


class Term(metaclass=ABCMeta):
    @classmethod
    @abstractmethod
    def sort(cls) -> Sort:
        ...

    @abstractmethod
    def dl_repr(self) -> str:
        ...

    @abstractmethod
    def unparse(self) -> str:
        ...

    def __repr__(self) -> str:
        return self.unparse()

    def free_variables(self) -> set["Var"]:
        return set()

    def ground(self) -> bool:
        return True

    def substitute(self, lhs: str, rhs: "Term") -> "Term":
        return self


class Var(Term):
    _name: str

    def __init__(self, name: str):
        self._name = name

    @override
    def dl_repr(self) -> str:
        return self._name

    @override
    def unparse(self) -> str:
        return self.__class__.__qualname__ + '("' + self._name + '")'

    @override
    def free_variables(self) -> set["Var"]:
        return {self}

    @override
    def ground(self) -> bool:
        return False

    @override
    def substitute(self, lhs: str, rhs: Term) -> Term:
        if lhs == self.dl_repr():
            return rhs
        else:
            return self

    def __hash__(self) -> int:
        return hash(self._name)


Arity = OrderedDict[str, Sort]
Assignment = dict[str, Term]


class Relation:
    _name: str
    _arity: Arity
    _infix_symbol: Optional[str]

    def __init__(
        self,
        name: str,
        arity: Arity,
        infix_symbol: Optional[str] = None,
    ):
        if infix_symbol:
            assert len(arity) == 2

        self._name = name
        self._arity = arity
        self._infix_symbol = infix_symbol

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Relation):
            return False
        if self.name() != other.name():
            return False
        if self.infix_symbol != other.infix_symbol:
            return False
        if self.arity() != other.arity():
            return False
        return True

    def arity(self) -> Arity:
        return self._arity

    def dl_repr(self, output: bool = False) -> str:
        if self.infix_symbol():
            if output:
                raise ValueError("Cannot output infix relation")
            return ""

        ret = (
            f".decl {self.name()}("
            + ", ".join(
                [f"{name}: {sort.dl_repr()}" for name, sort in self.arity().items()]
            )
            + ")"
        )

        if output:
            ret += f"\n.output {self.name()}"

        return ret

    def free_assignment(self, prefix: str) -> Assignment:
        return {name: sort.var(prefix + name) for name, sort in self.arity().items()}

    def infix_symbol(self) -> Optional[str]:
        return self._infix_symbol

    def name(self) -> str:
        return self._name


class Atom(metaclass=ABCMeta):
    @abstractmethod
    def get_arg(self, key: str) -> Term:
        ...

    @abstractmethod
    def set_arg(self, key: str, val: Term) -> "Atom":
        ...

    @abstractmethod
    def relation(self) -> Relation:
        ...

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Atom):
            return False
        if self.relation() != other.relation():
            return False
        for k in self.relation().arity():
            if self.get_arg(k) != other.get_arg(k):
                return False
        return True

    def __hash__(self) -> int:
        return hash(self.dl_repr())

    def dl_repr(self) -> str:
        infix_symbol = self.relation().infix_symbol()
        if infix_symbol:
            left_key, right_key = self.relation().arity().keys()
            return (
                self.get_arg(left_key).dl_repr()
                + " "
                + infix_symbol
                + " "
                + self.get_arg(right_key).dl_repr()
            )
        else:
            return (
                self.relation().name()
                + "("
                + ", ".join(
                    [self.get_arg(k).dl_repr() for k in self.relation().arity()]
                )
                + ")"
            )

    def free_variables(self) -> set[Var]:
        return set.union(
            *[self.get_arg(k).free_variables() for k in self.relation().arity()]
        )

    def ground(self) -> bool:
        for k in self.relation().arity():
            if not self.get_arg(k).ground():
                return False
        return True

    def substitute(self, lhs: str, rhs: Term) -> "Atom":
        new_atom = self
        for k in self.relation().arity():
            new_atom = new_atom.set_arg(k, self.get_arg(k).substitute(lhs, rhs))
        return new_atom

    def substitute_all(self, assignment: Assignment) -> "Atom":
        new_atom = self
        for lhs, rhs in assignment.items():
            new_atom = new_atom.substitute(lhs, rhs)
        return new_atom


class DynamicAtom(Atom):
    _relation: Relation
    _args: dict[str, Term]

    def __init__(
        self,
        relation: Relation,
        args: dict[str, Term],
    ):
        ra = relation.arity()
        assert ra.keys() == args.keys()
        for k in ra:
            assert args[k].sort() == ra[k]

        self._relation = relation
        self._args = args

    @override
    def get_arg(self, key: str) -> Term:
        return self._args[key]

    @override
    def set_arg(self, key: str, val: Term) -> "Atom":
        assert val.sort() == self.relation().arity()[key]
        new_args = self._args.copy()
        new_args[key] = val
        return DynamicAtom(self._relation, new_args)

    @override
    def relation(self) -> Relation:
        return self._relation

    @staticmethod
    def free(relation: Relation, prefix: str) -> "DynamicAtom":
        return DynamicAtom(
            relation=relation,
            args=relation.free_assignment(prefix),
        )


class Rule:
    _head: Atom
    _dependencies: OrderedDict[str, Atom]
    _checks: tuple[Atom, ...]

    def __init__(
        self,
        head: Atom,
        dependencies: OrderedDict[str, Atom],
        checks: tuple[Atom, ...],
    ):
        self._head = head
        self._dependencies = dependencies
        self._checks = checks

    def body(self) -> list[Atom]:
        return list(self.dependencies().values()) + list(self._checks)

    def dependencies(self) -> OrderedDict[str, Atom]:
        return self._dependencies

    def head(self) -> Atom:
        return self._head

    def dl_repr(self) -> str:
        lhs = self.head().dl_repr()
        rhs = ",\n  ".join([r.dl_repr() for r in self.body()]) + "."
        return f"{lhs} :-\n  {rhs}"


class NamedRule:
    _label: Callable
    _rule: Rule
    _source: str

    def __init__(self, label: Callable, rule: Rule):
        if label.__name__ == "<lambda>":
            raise ValueError("Cannot use lambda as a name for rule")
        try:
            source = inspect.getsource(label)
        except OSError:
            raise ValueError("Cannot find source for name for rule")

        self._label = label
        self._rule = rule
        self._source = source

    def dl_repr(self) -> str:
        return f"// {self.name()}\n{self.rule().dl_repr()}"

    def label(self) -> Callable:
        return self._label

    def name(self) -> str:
        return self._label.__name__

    def rule(self) -> Rule:
        return self._rule

    def source(self) -> str:
        return self._source


class Query:
    _rule: Rule

    def __init__(self, atoms: list[Atom]):
        goal_relation = Relation(
            name="Goal",
            arity=OrderedDict(
                (fv.dl_repr(), fv.sort())
                for fv in set.union(*[a.free_variables() for a in atoms])
            ),
        )
        head = DynamicAtom.free(goal_relation, prefix="")
        self._rule = Rule(
            head=head,
            dependencies=OrderedDict((f"q{i}", a) for i, a in enumerate(atoms)),
            checks=tuple(),
        )

    def dl_repr(self) -> str:
        return "\n".join(
            [
                self._rule.head().relation().dl_repr(output=True),
                "",
                self._rule.dl_repr(),
            ]
        )

    def relation(self) -> Relation:
        return self._rule.head().relation()


class DatalogProgram:
    _edbs: list[Atom]
    _idbs: list[NamedRule]
    _relations: list[Relation]

    def __init__(self, edbs: list[Atom], idbs: list[NamedRule]):
        self._relations = []

        for edb in edbs:
            if not edb.ground():
                raise ValueError("Non-ground EDB")
            r = edb.relation()
            if r not in self._relations:
                self._relations.append(r)

        for idb in idbs:
            r = idb.rule().head().relation()
            if r not in self._relations:
                self._relations.append(r)

        self._edbs = edbs
        self._idbs = idbs

    def dl_repr(self) -> str:
        blocks = []

        for r in self._relations:
            blocks.append(r.dl_repr())

        blocks.append("")

        for idb in self._idbs:
            blocks.append(idb.dl_repr())
            blocks.append("")

        for edb in self._edbs:
            blocks.append(edb.dl_repr() + ".")

        blocks.append("")

        return "\n".join(blocks)

    def edbs(self) -> list[Atom]:
        return self._edbs

    def idbs(self) -> list[NamedRule]:
        return self._idbs

    def run_query(self, query: Query) -> list[Assignment]:
        dl_prog = self.dl_repr() + "\n" + query.dl_repr()
        output = souffle.run(dl_prog)

        goal_relation = query.relation()
        assignments = []
        for row in output.facts[goal_relation.name()]:
            assignment = {}
            for (key, key_sort), val in zip(goal_relation.arity().items(), row):
                assignment[key] = key_sort.parse(val)
            assignments.append(assignment)
        return assignments
