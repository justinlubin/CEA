import inspect
from dataclasses import dataclass


class Event:
    pass


class Analysis:
    pass


@dataclass
class Transfect(Event):
    lib: str


@dataclass
class Seq(Event):
    gcat: str


@dataclass
class Sgre(Analysis):
    fold_change: float


### Library


@dataclass
class Atom:
    rel: str
    args: list

    def __str__(self) -> str:
        return self.rel + "(" + ", ".join([str(x) for x in self.args]) + ")"


@dataclass
class Formula:
    params: list[list[str]]
    body: list[Atom]


@dataclass
class Function:
    name: str
    param_types: list[type]
    ret_type: type
    precondition: Formula


@dataclass
class Rule:
    name: str
    head: Atom
    body: list[Atom]

    def __str__(self):
        return (
            f"== {self.name} ============================\n"
            + "\n".join(map(str, self.body))
            + "\n--------------------\n"
            + str(self.head)
            + "\n=============================="
            + "=" * (len(self.name) + 2)
        )


funs: list[Function] = []


def precondition(fvs, conds):
    def wrapper(func):
        sig = inspect.signature(func)
        funs.append(
            Function(
                func.__name__,
                [p.annotation for p in sig.parameters.values()],
                sig.return_annotation,
                Formula(fvs, conds),
            )
        )
        return func

    return wrapper


def rule_of_fun(f: Function) -> Rule:
    return Rule(
        f.name,
        Atom(f.ret_type.__name__, f.precondition.params[-1]),
        [
            Atom(t.__name__, fv)
            for t, fv in zip(f.param_types, f.precondition.params[:-1])
        ]
        + f.precondition.body,
    )


################################################################################
# Library


class Time:
    def uniq(self) -> Atom:
        return Atom("TimeUnique", [self])

    def __lt__(self, other):
        return Atom("TimeLt", [self, other])

    def __eq__(self, other):
        return Atom("TimeEq", [self, other])


class TimeVar(Time):
    name: str

    def __init__(self, name):
        self.name = name

    def __str__(self):
        return self.name


class TimeLit(Time):
    day: int

    def __init__(self, day):
        self.day = day

    def __str__(self):
        return "d" + str(self.day)


t0 = TimeVar("t0")
t1 = TimeVar("t1")
t2 = TimeVar("t2")
t3 = TimeVar("t3")
t4 = TimeVar("t4")


@precondition(
    fvs=[[t0], [t1], [t2], [t3, t4]],
    conds=[t0.uniq(), t0 < t1, t1 < t2, t1 == t3, t2 == t4],
)
def sgre_ttest(tr: Transfect, x: Seq, y: Seq) -> Sgre:
    return Sgre(1.0)


for f in funs:
    print(str(rule_of_fun(f)) + "\n")


log: list[Atom] = []


def do(e: type, *args) -> None:
    log.append(Atom(e.__name__, list(args)))


#### Script

do(Transfect, TimeLit(1))
do(Seq, TimeLit(3))
do(Seq, TimeLit(4))


print("== TRACE ================")
for l in log:
    print(l)
