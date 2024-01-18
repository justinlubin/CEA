from abc import ABCMeta, abstractmethod
from dataclasses import dataclass
from typing import Callable, ClassVar
from collections import OrderedDict

import inspect

from . import souffle
from . import util


def override(f):
    return f


# Globals


class Globals:
    _relations: ClassVar[list["Relation"]] = []
    _rules: ClassVar[list["Rule"]] = []

    @staticmethod
    def defined_relations() -> list["Relation"]:
        return Globals._relations.copy()

    @staticmethod
    def defined_rules() -> list["Rule"]:
        return Globals._rules.copy()

    # @staticmethod
    # def matching_rules(rel: "Relation") -> Iterator["Rule"]:
    #     for rule in Globals._rules:
    #         if type(rule.head) is rel:
    #             yield rule


# Variables and terms


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

    def __str__(self) -> str:
        return self.dl_repr()

    def substitute(self, lhs: "Var", rhs: "Term") -> "Term":
        assert lhs.sort() == rhs.sort()
        return self

    def free_vars(self) -> set["Var"]:
        return set()


class Var(Term):
    _name: str

    def __init__(self, name: str):
        self._name = name

    @override
    def dl_repr(self) -> str:
        return self._name.replace(".", "_")

    @override
    def substitute(self, lhs: "Var", rhs: Term) -> Term:
        assert lhs.sort() == rhs.sort()
        if lhs.dl_repr() == self.dl_repr():
            assert lhs.sort() == self.sort()
            return rhs
        else:
            return self

    @override
    def free_vars(self) -> set["Var"]:
        return {self}

    def __hash__(self) -> int:
        return hash(self._name)

    def __str__(self) -> str:
        return f"${self._name}"


# Relations

# Relation = type["Atom"]


Arity = OrderedDict[str, Sort]


class Relation(metaclass=ABCMeta):
    @abstractmethod
    def name(self) -> str:
        ...

    @abstractmethod
    def arity(self) -> Arity:
        ...

    def dl_repr(self) -> str:
        return (
            f".decl {self.name}("
            + ", ".join(
                [f"{name}: {sort.dl_repr()}" for name, sort in self.arity().items()]
            )
            + ")"
        )

    def free(self, prefix: str) -> "Atom":
        return BasicAtom(
            relation=self,
            args={name: sort.var(prefix + name) for name, sort in self.arity().items()},
        )


Assignment = dict[Var, Term]


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

    def dl_repr(self) -> str:
        return (
            self.relation().name()
            + "("
            + ", ".join([self.get_arg(k).dl_repr() for k in self.relation().arity()])
            + ")"
        )

    def substitute(self, lhs: Var, rhs: Term) -> "Atom":
        assert lhs.sort() == rhs.sort()
        new_atom = self
        for k in self.relation().arity():
            new_atom = new_atom.set_arg(k, self.get_arg(k).substitute(lhs, rhs))
        return new_atom

    def substitute_all(self, assignment: Assignment) -> "Atom":
        new_atom = self
        for lhs, rhs in assignment.items():
            new_atom = new_atom.substitute(lhs, rhs)
        return new_atom

    def free_vars(self) -> set[Var]:
        return set.union(
            *[self.get_arg(k).free_vars() for k in self.relation().arity()]
        )


class BasicAtom(Atom):
    _relation: Relation
    _args: dict[str, Term]

    def __init__(self, relation: Relation, args: dict[str, Term]):
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
    def set_arg(self, key: str, val: Term) -> Atom:
        assert val.sort() == self.relation().arity()[key]
        new_args = self._args.copy()
        new_args[key] = val
        return BasicAtom(self._relation, new_args)

    @override
    def relation(self) -> Relation:
        return self._relation


# class Atom(metaclass=ABCMeta):
#     """Subclass ___init___ must take a list of Term (not checked)."""
#
#     def __init_subclass__(cls, **kwargs):
#         super().__init_subclass__(**kwargs)
#         Globals._relations.append(cls)
#
#     # Relation methods
#
#     @classmethod
#     def name(cls) -> str:
#         return cls.__qualname__.replace(".", "_")
#
#     @classmethod
#     def arity(cls):
#         return list(inspect.signature(cls.__init__).parameters.values())[1:]
#
#     @classmethod
#     def free(cls, prefix: str) -> Self:
#         return cls(*[p.annotation.var(prefix + p.name) for p in cls.arity()])
#
#     @classmethod
#     def dl_decl(cls) -> Optional[str]:
#         inner = [f"{p.name}: {p.annotation.sort().dl_repr()}" for p in cls.arity()]
#         return ".decl " + cls.name() + "(" + ", ".join(inner) + ")"
#
#     # Atom methods
#
#     def __str__(self) -> str:
#         inner = [f"{p.name}={str(getattr(self, p.name))}" for p in self.arity()]
#         return self.name() + "(" + ", ".join(inner) + ")"
#
#     def args(self) -> list[Term]:
#         return [getattr(self, p.name) for p in self.arity()]
#
#     def dl_repr(self) -> str:
#         inner = [a.dl_repr() for a in self.args()]
#         return self.name() + "(" + ", ".join(inner) + ")"
#
#     def substitute(self, lhs: str, rhs: Term) -> Self:
#         # Unsafe, since .subsitute returns a generic Term
#         return type(self)(*[a.substitute(lhs, rhs) for a in self.args()])
#
#     def substitute_all(self, subs: dict[str, Term]) -> Self:
#         new_atom = self
#         for lhs, rhs in subs.items():
#             new_atom = new_atom.substitute(lhs, rhs)
#         print(subs)
#         return new_atom
#
#     def free_vars(self) -> set["Var"]:
#         return set.union(*[a.free_vars() for a in self.args()])
#
#     def relation(self) -> Relation:
#         return type(self)


# Rules


@dataclass
class Rule:
    fn: Callable
    head: Atom
    dependencies: list[Atom]
    checks: list[Atom]

    def __str__(self) -> str:
        return (
            f"== {self.name()} ============================\n"
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


class Query:
    atoms: list[Atom]
    _fvs: list[Var]

    def __init__(self, atoms: list[Atom]):
        self.atoms = atoms
        self._fvs = list(set.union(*[a.free_vars() for a in self.atoms]))

    # Returns a list because order is important
    def free_variables(self) -> list[Var]:
        return self._fvs

    def dl_repr(self) -> str:
        free_vars = self.free_variables()

        blocks = []

        blocks.append(
            ".decl Goal("
            + ", ".join([f"{fv.dl_repr()}: {fv.sort().dl_repr()}" for fv in free_vars])
            + ")"
        )
        blocks.append(".output Goal")

        blocks.append(
            "Goal("
            + ", ".join([fv.dl_repr() for fv in free_vars])
            + ") :-\n  "
            + ",\n  ".join([a.dl_repr() for a in self.atoms])
            + "."
        )

        return "\n".join(blocks)


@dataclass
class DatalogProgram:
    edbs: list[Atom]

    def dl_repr(self) -> str:
        blocks = []

        for rel in Globals.defined_relations():
            rel_decl = rel.dl_repr()
            if rel_decl:
                blocks.append(rel_decl)

        blocks.append("")

        for rule in Globals.defined_rules():
            blocks.append(f"// {rule.fn.__name__}")
            blocks.append(rule.dl_repr())
            blocks.append("")

        for edb in self.edbs:
            blocks.append(edb.dl_repr() + ".")

        blocks.append("")

        return "\n".join(blocks)

    def run(self, query: Query) -> list[Assignment]:
        dl_prog = self.dl_repr() + "\n" + query.dl_repr()
        output = souffle.run(dl_prog)
        assignments = []
        for row in output.facts["Goal"]:
            assignment = {}
            for key, val in zip(query.free_variables(), row):
                assignment[key.dl_repr()] = key.sort().parse(val)
            assignments.append(assignment)
        print(assignments)
        return assignments


PathedAtom = tuple[Atom, list[int]]


class DerivationTree(metaclass=ABCMeta):
    @abstractmethod
    def tree_string(self, depth: int = 0) -> str:
        ...

    @abstractmethod
    def goals(self) -> list[PathedAtom]:
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

    def goals(self) -> list[PathedAtom]:
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

    def goals(self) -> list[PathedAtom]:
        return [(self.goal, [])]

    def replace(
        self, breadcrumbs: list[int], new_subtree: DerivationTree
    ) -> DerivationTree:
        if not breadcrumbs:
            return new_subtree
        raise ValueError("Invalid breadcrumbs for derivation tree")


class DerivationTreeConstructor(metaclass=ABCMeta):
    @abstractmethod
    def select_goal(self, goals: list[PathedAtom]) -> PathedAtom:
        ...

    @abstractmethod
    def select_rule(
        self, rules: list[tuple[Rule, list[Assignment]]]
    ) -> tuple[Rule, list[Assignment]]:
        ...

    @abstractmethod
    def select_assignment(self, assignments: list[Assignment]) -> Assignment:
        ...

    @abstractmethod
    def rule_options(self, goal_atom: Atom, rule: Rule) -> list[Assignment]:
        ...


@dataclass
class CLIDerivationTreeConstructor(DerivationTreeConstructor):
    base_program: DatalogProgram

    def select_goal(self, goals: list[PathedAtom]) -> PathedAtom:
        print(f"Select a goal to work on (0-{len(goals) - 1}):")
        for i, (g, bc) in enumerate(goals):
            print(f"{i}. {g} (bc: {bc})")
        return goals[int(input("> "))]

    def select_rule(
        self, rules: list[tuple[Rule, list[Assignment]]]
    ) -> tuple[Rule, list[Assignment]]:
        print(f"Select a rule to use (0-{len(rules) - 1}):")
        for i, (r, a) in enumerate(rules):
            print(f"{i}. {r.name()} - {a}")
        return rules[int(input("> "))]

    def select_assignment(self, assignments: list[Assignment]) -> Assignment:
        print(f"Select an assignment to use (0-{len(assignments)-1}):")
        for i, a in enumerate(assignments):
            print(f"{i}. {a}")
        return assignments[int(input("> "))]

    def rule_options(self, goal_atom: Atom, rule: Rule) -> list[Assignment]:
        if rule.head.relation() != goal_atom.relation():
            return []

        def make_substitutions(atom: Atom) -> Atom:
            new_atom = atom
            for k in rule.head.relation().arity():
                lhs = rule.head.get_arg(k)
                assert isinstance(lhs, Var)
                rhs = goal_atom.get_arg(k)
                new_atom = new_atom.substitute(lhs, rhs)
            return new_atom

        query = Query([make_substitutions(a) for a in rule.dependencies + rule.checks])
        return self.base_program.run(query=query)


def construct(ctor: DerivationTreeConstructor, initial_goal: Atom) -> DerivationTree:
    dt: DerivationTree = DerivationGoal(goal=initial_goal)
    while True:
        print(dt.tree_string())
        subgoals = dt.goals()
        if not subgoals:
            return dt
        goal_atom, goal_bc = ctor.select_goal(subgoals)
        selected_rule, possible_assignments = ctor.select_rule(
            [(r, ctor.rule_options(goal_atom, r)) for r in Globals.defined_rules()]
        )
        selected_assignment = ctor.select_assignment(possible_assignments)
        dt = dt.replace(
            goal_bc,
            DerivationStep(
                fn=selected_rule.fn,
                consequent=goal_atom,
                antecedents=[
                    DerivationGoal(a.substitute_all(selected_assignment))
                    for a in selected_rule.dependencies
                ],
            ),
        )
