from abc import ABCMeta, abstractmethod
from dataclasses import dataclass
from typing import assert_never

import enum

from . import util

from .core import *

# Derivation trees

Breadcrumbs = list[str]
PathedAtom = tuple[Atom, Breadcrumbs]


class Tree(metaclass=ABCMeta):
    @abstractmethod
    def children(self) -> list["Tree"]:
        ...

    @abstractmethod
    def computation(self) -> Optional[Callable]:
        ...

    @abstractmethod
    def goals(self) -> list[PathedAtom]:
        ...

    @abstractmethod
    def is_leaf(self) -> bool:
        ...

    @abstractmethod
    def replace(
        self,
        breadcrumbs: Breadcrumbs,
        new_subtree: "Tree",
    ) -> "Tree":
        ...

    @abstractmethod
    def tree_string(self, depth: int = 1, prefix: str = "") -> str:
        ...

    def postorder(self) -> list["Tree"]:
        ret = []
        for c in self.children():
            ret.extend(c.postorder())
        ret.append(self)
        return ret

    @staticmethod
    def _make_dashes(amount: int, dash_size: int = 2) -> str:
        return "-" * amount * dash_size


@dataclass
class Step(Tree):
    label: Callable
    consequent: Atom
    antecedents: OrderedDict[str, Tree]

    @override
    def children(self) -> list[Tree]:
        return list(self.antecedents.values())

    @override
    def computation(self) -> Optional[Callable]:
        return self.label

    @override
    def goals(self) -> list[PathedAtom]:
        return util.flatten(
            [
                [(g, crumbs + [k]) for g, crumbs in a.goals()]
                for k, a in self.antecedents.items()
            ]
        )

    @override
    def is_leaf(self) -> bool:
        return False

    @override
    def replace(
        self,
        breadcrumbs: Breadcrumbs,
        new_subtree: Tree,
    ) -> Tree:
        if not breadcrumbs:
            return new_subtree
        child = breadcrumbs.pop()  # modifies breadcrumbs
        if child not in self.antecedents:
            raise ValueError("Invalid breadcrumbs for derivation tree")
        return Step(
            label=self.label,
            consequent=self.consequent,
            antecedents=OrderedDict(
                (k, v.replace(breadcrumbs, new_subtree) if k == child else v)
                for k, v in self.antecedents.items()
            ),
        )

    @override
    def tree_string(self, depth: int = 1, prefix: str = "") -> str:
        ret = (
            f"{self._make_dashes(depth)} {prefix}"
            + self.consequent.dl_repr()
            + f" [{self.label.__name__}]"
        )
        for k, a in self.antecedents.items():
            ret += "\n" + a.tree_string(
                depth=depth + 1,
                prefix=f"<{k}>: ",
            )
        return ret


@dataclass
class Goal(Tree):
    goal: Atom

    @override
    def children(self) -> list[Tree]:
        return []

    @override
    def computation(self) -> Optional[Callable]:
        return None

    @override
    def goals(self) -> list[PathedAtom]:
        return [(self.goal, [])]

    @override
    def is_leaf(self) -> bool:
        return False

    @override
    def replace(self, breadcrumbs: Breadcrumbs, new_subtree: Tree) -> Tree:
        if not breadcrumbs:
            return new_subtree
        raise ValueError("Invalid breadcrumbs for derivation tree")

    @override
    def tree_string(self, depth: int = 1, prefix: str = ""):
        return self._make_dashes(depth) + f" {prefix}*** " + self.goal.dl_repr()


@dataclass
class Leaf(Tree):
    leaf: Atom

    @override
    def children(self) -> list[Tree]:
        return []

    @override
    def computation(self) -> Optional[Callable]:
        return None

    @override
    def goals(self) -> list[PathedAtom]:
        return []

    @override
    def is_leaf(self) -> bool:
        return True

    @override
    def replace(self, breadcrumbs: Breadcrumbs, new_subtree: Tree) -> Tree:
        raise ValueError("Cannot replace a leaf")

    @override
    def tree_string(self, depth: int = 1, prefix: str = ""):
        return self._make_dashes(depth) + f" {prefix}" + self.leaf.dl_repr() + " [leaf]"


# Interactions


class Interactor(metaclass=ABCMeta):
    @abstractmethod
    def display_tree(self, derivation_tree: Tree) -> None:
        ...

    @abstractmethod
    def select_goal(self, goals: list[PathedAtom]) -> PathedAtom:
        ...

    @abstractmethod
    def select_rule(
        self, rules: list[tuple[NamedRule, list[Assignment]]]
    ) -> tuple[NamedRule, list[Assignment]]:
        ...

    @abstractmethod
    def select_assignment(self, assignments: list[Assignment]) -> Assignment:
        ...


class CLIInteractor(Interactor):
    @enum.unique
    class Mode(enum.Enum):
        MANUAL = enum.auto()
        FAST_FORWARD = enum.auto()
        AUTO = enum.auto()

    _goal_mode: Mode
    _rule_mode: Mode

    def __init__(self, goal_mode: Mode, rule_mode: Mode):
        self._goal_mode = goal_mode
        self._rule_mode = rule_mode

    def display_tree(self, dt: Tree) -> None:
        dt_string = dt.tree_string()
        width = util.string_width(dt_string)
        header_prefix = "== DERIVATION TREE "
        print("\n" + header_prefix + "=" * (width - len(header_prefix)) + "|\n")
        print(dt.tree_string())
        print("\n" + "=" * width + "|")

    def select_goal(self, goals: list[PathedAtom]) -> PathedAtom:
        auto_prompt = self._auto_prompt(self._goal_mode, goals)
        if auto_prompt:
            print(f"\n{auto_prompt} goal:\n\n  {goals[0][0].dl_repr()}")
            return goals[0]
        else:
            print("\nSelect a goal to work on:")
            for i, (g, _) in enumerate(goals):
                print(f"{i}. {g.dl_repr()}")
            return goals[int(input("> "))]

    def select_rule(
        self, rules: list[tuple[NamedRule, list[Assignment]]]
    ) -> tuple[NamedRule, list[Assignment]]:
        valid_rules = [(r, aa) for (r, aa) in rules if aa]
        auto_prompt = self._auto_prompt(self._rule_mode, valid_rules)
        if auto_prompt:
            print(f"\n{auto_prompt} rule:\n\n  {valid_rules[0][0].name()}")
            return valid_rules[0]
        else:
            print("\nSelect a rule to use:")
            for i, (r, _) in enumerate(valid_rules):
                print(f"{i}. {r.name()}")
            return valid_rules[int(input("> "))]

    def select_assignment(self, assignments: list[Assignment]) -> Assignment:
        if len(assignments) == 1:
            return assignments[0]

        print("\nSelect an assignment to use:")
        for i, a in enumerate(assignments):
            print(f"{i}. {self._assignment_string(a)}")
        return assignments[int(input("> "))]

    @staticmethod
    def _assignment_string(assignment: Assignment) -> str:
        return (
            "{"
            + ", ".join(f"{k} -> {v.dl_repr()}" for k, v in assignment.items())
            + "}"
        )

    @staticmethod
    def _auto_prompt(mode: Mode, choices: list) -> Optional[str]:
        match mode:
            case CLIInteractor.Mode.MANUAL:
                return None

            case CLIInteractor.Mode.FAST_FORWARD:
                return "Automatically selecting only" if len(choices) == 1 else None

            case CLIInteractor.Mode.AUTO:
                return "Automatically selecting first"

            case _ as unreachable:
                assert_never(unreachable)


# Construction algorithm


class Constructor:
    _base_program: DatalogProgram

    def __init__(self, base_program: DatalogProgram, interactor: Interactor):
        self._base_program = base_program
        self._interactor = interactor

    def construct(self, initial_goal: Atom) -> Tree:
        dt: Tree = Goal(goal=initial_goal)
        rules = self._base_program.idbs()
        while True:
            self._interactor.display_tree(dt)

            subgoals = dt.goals()
            if not subgoals:
                return dt

            goal_atom, goal_bc = self._interactor.select_goal(subgoals)

            selected_rule, possible_assignments = self._interactor.select_rule(
                [(r, self._rule_options(goal_atom, r)) for r in rules]
            )

            selected_assignment = self._interactor.select_assignment(
                possible_assignments
            )

            dt = dt.replace(
                goal_bc,
                Step(
                    label=selected_rule.label(),
                    consequent=goal_atom,
                    antecedents=OrderedDict(
                        (k, self._make_leaf(a.substitute_all(selected_assignment)))
                        for k, a in selected_rule.rule().dependencies().items()
                    ),
                ),
            )

    def _rule_options(self, goal: Atom, named_rule: NamedRule) -> list[Assignment]:
        rule = named_rule.rule()

        if rule.head().relation() != goal.relation():
            return []

        def make_substitutions(atom: Atom) -> Atom:
            new_atom = atom
            for k in rule.head().relation().arity():
                lhs = rule.head().get_arg(k)
                assert isinstance(lhs, Var)
                rhs = goal.get_arg(k)
                new_atom = new_atom.substitute(lhs.dl_repr(), rhs)
            return new_atom

        query = Query([make_substitutions(a) for a in rule.body()])
        return self._base_program.run_query(query=query)

    def _make_leaf(self, atom: Atom) -> Tree:
        if atom in self._base_program.edbs():
            return Leaf(atom)
        else:
            return Goal(atom)
