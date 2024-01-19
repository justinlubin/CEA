from abc import ABCMeta, abstractmethod
from . import util
from .core import *

PathedAtom = tuple[Atom, list[int]]


class DerivationTree(metaclass=ABCMeta):
    @abstractmethod
    def tree_string(self, depth: int = 1) -> str:
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
    label: Callable
    consequent: Atom
    antecedents: list[DerivationTree]

    def tree_string(self, depth: int = 1) -> str:
        ret = "-" * depth + " " + self.consequent.dl_repr()
        for a in self.antecedents:
            ret += "\n" + a.tree_string(depth=depth + 1)
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
            label=self.label,
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

    def tree_string(self, depth: int = 1):
        return "-" * depth + " " + self.goal.dl_repr() + " * "

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


def assignment_string(assignment: Assignment) -> str:
    return "{" + ", ".join(f"{k} -> {v.dl_repr()}" for k, v in assignment.items()) + "}"


@dataclass
class CLIDerivationTreeConstructor(DerivationTreeConstructor):
    base_program: DatalogProgram

    def select_goal(self, goals: list[PathedAtom]) -> PathedAtom:
        print()
        print(f"Select a goal to work on (0-{len(goals) - 1}):")
        for i, (g, bc) in enumerate(goals):
            print(f"{i}. {g.dl_repr()} (bc: {bc})")
        return goals[int(input("> "))]

    def select_rule(
        self, rules: list[tuple[Rule, list[Assignment]]]
    ) -> tuple[Rule, list[Assignment]]:
        print()
        print(f"Select a rule to use (0-{len(rules) - 1}):")
        for i, (r, aa) in enumerate(rules):
            print(f"{i}. {r.name()} ({[assignment_string(a) for a in aa]})")
        return rules[int(input("> "))]

    def select_assignment(self, assignments: list[Assignment]) -> Assignment:
        print()
        print(f"Select an assignment to use (0-{len(assignments)-1}):")
        for i, a in enumerate(assignments):
            print(f"{i}. {assignment_string(a)}")
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
                new_atom = new_atom.substitute(lhs.dl_repr(), rhs)
            return new_atom

        query = Query([make_substitutions(a) for a in rule.dependencies + rule.checks])
        return self.base_program.run_query(query=query)


def construct(
    ctor: DerivationTreeConstructor,
    initial_goal: Atom,
    reference_program: DatalogProgram,
) -> DerivationTree:
    dt: DerivationTree = DerivationGoal(goal=initial_goal)
    rules = reference_program.idbs()
    while True:
        print()
        print(dt.tree_string())
        subgoals = dt.goals()
        if not subgoals:
            return dt
        goal_atom, goal_bc = ctor.select_goal(subgoals)
        selected_rule, possible_assignments = ctor.select_rule(
            [(r, ctor.rule_options(goal_atom, r)) for r in rules]
        )
        selected_assignment = ctor.select_assignment(possible_assignments)
        dt = dt.replace(
            goal_bc,
            DerivationStep(
                label=selected_rule.label,
                consequent=goal_atom,
                antecedents=[
                    DerivationGoal(a.substitute_all(selected_assignment))
                    for a in selected_rule.dependencies
                ],
            ),
        )
