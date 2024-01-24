from abc import ABCMeta, abstractmethod
from typing import Iterator

from . import util

from .core import *

# Derivation trees

Breadcrumbs = list[int]
PathedAtom = tuple[Atom, Breadcrumbs]


class Tree(metaclass=ABCMeta):
    @abstractmethod
    def children(self) -> list["Tree"]:
        ...

    @abstractmethod
    def goals(self) -> list[PathedAtom]:
        ...

    @abstractmethod
    def replace(
        self,
        breadcrumbs: Breadcrumbs,
        new_subtree: "Tree",
    ) -> "Tree":
        ...

    @abstractmethod
    def tree_string(self, depth: int = 1) -> str:
        ...

    def postorder(self) -> list["Tree"]:
        ret = []
        for c in self.children():
            ret.extend(c.postorder())
        ret.append(self)
        return ret

    def __str__(self) -> str:
        return self.tree_string(depth=0)


@dataclass
class Step(Tree):
    label: Callable
    consequent: Atom
    antecedents: list[Tree]

    @override
    def children(self) -> list[Tree]:
        return self.antecedents

    @override
    def goals(self) -> list[PathedAtom]:
        return util.flatten(
            [
                [(g, crumbs + [i]) for g, crumbs in a.goals()]
                for i, a in enumerate(self.antecedents)
            ]
        )

    @override
    def replace(
        self,
        breadcrumbs: Breadcrumbs,
        new_subtree: Tree,
    ) -> Tree:
        if not breadcrumbs:
            return new_subtree
        child = breadcrumbs.pop()  # modifies breadcrumbs
        if child < 0 or child >= len(self.antecedents):
            raise ValueError("Invalid breadcrumbs for derivation tree")
        return Step(
            label=self.label,
            consequent=self.consequent,
            antecedents=(
                self.antecedents[:child]
                + [self.antecedents[child].replace(breadcrumbs, new_subtree)]
                + self.antecedents[child + 1 :]
            ),
        )

    @override
    def tree_string(self, depth: int = 1) -> str:
        ret = "-" * depth + f" [{self.label.__name__}] " + self.consequent.dl_repr()
        for a in self.antecedents:
            ret += "\n" + a.tree_string(depth=depth + 1)
        return ret


@dataclass
class Goal(Tree):
    goal: Atom

    @override
    def children(self) -> list[Tree]:
        return []

    @override
    def goals(self) -> list[PathedAtom]:
        return [(self.goal, [])]

    @override
    def replace(self, breadcrumbs: Breadcrumbs, new_subtree: Tree) -> Tree:
        if not breadcrumbs:
            return new_subtree
        raise ValueError("Invalid breadcrumbs for derivation tree")

    @override
    def tree_string(self, depth: int = 1):
        return "-" * depth + " *** " + self.goal.dl_repr()


@dataclass
class Leaf(Tree):
    leaf: Atom

    @override
    def children(self) -> list[Tree]:
        return []

    @override
    def goals(self) -> list[PathedAtom]:
        return []

    @override
    def replace(self, breadcrumbs: Breadcrumbs, new_subtree: Tree) -> Tree:
        raise ValueError("Cannot replace a leaf")

    @override
    def tree_string(self, depth: int = 1):
        return "-" * depth + " [leaf] " + self.leaf.dl_repr()


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
        self, rules: list[tuple[Rule, list[Assignment]]]
    ) -> tuple[Rule, list[Assignment]]:
        ...

    @abstractmethod
    def select_assignment(self, assignments: list[Assignment]) -> Assignment:
        ...


class CLIInteractor(Interactor):
    def display_tree(self, dt: Tree) -> None:
        print("\n===== Derivation tree =====")
        print(dt.tree_string())
        print("===================================")

    def select_goal(self, goals: list[PathedAtom]) -> PathedAtom:
        print("\nSelect a goal to work on:")
        for i, (g, _) in enumerate(goals):
            print(f"{i}. {g.dl_repr()}")
        return goals[int(input("> "))]

    def select_rule(
        self, rules: list[tuple[Rule, list[Assignment]]]
    ) -> tuple[Rule, list[Assignment]]:
        print("\nSelect a rule to use:")
        valid_rules = [(r, aa) for (r, aa) in rules if aa]
        for i, (r, _) in enumerate(valid_rules):
            print(f"{i}. {r.name()}")
        return valid_rules[int(input("> "))]

    def select_assignment(self, assignments: list[Assignment]) -> Assignment:
        if len(assignments) == 1:
            return assignments[0]

        print("\nSelect an assignment to use:")
        for i, a in enumerate(assignments):
            print(f"{i}. {CLIInteractor._assignment_string(a)}")
        return assignments[int(input("> "))]

    @staticmethod
    def _assignment_string(assignment: Assignment) -> str:
        return (
            "{"
            + ", ".join(f"{k} -> {v.dl_repr()}" for k, v in assignment.items())
            + "}"
        )


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
                    label=selected_rule.label,
                    consequent=goal_atom,
                    antecedents=[
                        self._make_leaf(a.substitute_all(selected_assignment))
                        for a in selected_rule.dependencies
                    ],
                ),
            )

    def _rule_options(self, goal: Atom, rule: Rule) -> list[Assignment]:
        if rule.head.relation() != goal.relation():
            return []

        def make_substitutions(atom: Atom) -> Atom:
            new_atom = atom
            for k in rule.head.relation().arity():
                lhs = rule.head.get_arg(k)
                assert isinstance(lhs, Var)
                rhs = goal.get_arg(k)
                new_atom = new_atom.substitute(lhs.dl_repr(), rhs)
            return new_atom

        query = Query([make_substitutions(a) for a in rule.dependencies + rule.checks])
        return self._base_program.run_query(query=query)

    def _make_leaf(self, atom: Atom) -> Tree:
        if atom in self._base_program.edbs():
            return Leaf(atom)
        else:
            return Goal(atom)
