from collections import OrderedDict
from dataclasses import dataclass
from typing import Optional

from cea.shared.sexp import SAtom, SList, SExp

################################################################################
## Exception


class ParseException(Exception):
    expected: str
    got: SExp


################################################################################
## Values

# Types


@dataclass(frozen=True)
class IntValueType:
    pass


@dataclass(frozen=True)
class StrValueType:
    pass


ValueType = IntValueType | StrValueType

Env = dict[str, ValueType]

# Values


@dataclass(frozen=True)
class VarValue:
    name: str
    typ: ValueType


@dataclass(frozen=True)
class IntValue:
    val: int


@dataclass(frozen=True)
class StrValue:
    val: str


ConstantValue = IntValue | StrValue

Value = ConstantValue | VarValue

# S-Expression conversion


def value_type_of_sexp(s: SExp) -> ValueType:
    match s:
        case SAtom("int"):
            return IntValueType()

        case SAtom("str"):
            return StrValueType()

        case _:
            raise ParseException("ValueType", s)


def value_of_sexp(s: SExp, *, env: Env | None = None) -> Value:
    env = env if env else {}
    match s:
        case SAtom(val):
            try:
                return IntValue(int(val))
            except ValueError:
                if val[0] == '"' and val[-1] == '"':
                    return StrValue(val[1:-1])
                elif val in env:
                    return VarValue(name=val, typ=env[val])
                else:
                    raise ParseException("Value", s)

        case SList(_):
            raise ParseException("Value", s)


def sexp_of_value(v: Value) -> SExp:
    match v:
        case VarValue(name, _):
            return SAtom(name)
        case IntValue(val):
            return SAtom(str(val))
        case StrValue(val):
            return SAtom(f'"{val}"')


################################################################################
## Facts

# Types


@dataclass(frozen=True)
class EventType:
    name: str
    params: OrderedDict[str, ValueType]


@dataclass(frozen=True)
class AnalysisType:
    name: str
    params: OrderedDict[str, ValueType]


FactType = EventType | AnalysisType


def event_type_of_sexp(s: SExp) -> EventType:
    match s:
        case SList([SAtom("event"), SAtom(name), *param_sexps]):
            params = OrderedDict()
            for p in param_sexps:
                match p:
                    case SList([SAtom(lhs), rhs_sexp]):
                        params[lhs] = value_type_of_sexp(rhs_sexp)

                    case _:
                        raise ParseException("EventType binding", p)
            return EventType(name, params)

        case _:
            raise ParseException("EventType", s)


# Values


@dataclass(frozen=True)
class Event:
    name: str
    args: OrderedDict[str, Value]


@dataclass(frozen=True)
class Analysis:
    name: str
    args: OrderedDict[str, Value]


Fact = Event | Analysis

################################################################################
## Protocols


@dataclass(frozen=True)
class Protocol:
    events: list[Event]
    goal: Optional[Analysis]


################################################################################
## Predicates


@dataclass(frozen=True)
class SelectorAtom:
    selector: str
    arg: str


PredicateAtom = ConstantValue | SelectorAtom


@dataclass(frozen=True)
class EqRelation:
    lhs: PredicateAtom
    rhs: PredicateAtom


@dataclass(frozen=True)
class LtRelation:
    lhs: PredicateAtom
    rhs: PredicateAtom


PredicateRelation = EqRelation | LtRelation

Predicate = list[PredicateRelation]


################################################################################
## Computations


@dataclass(frozen=True)
class ComputationType:
    name: str
    params: OrderedDict[str, FactType]
    ret: AnalysisType
    precondition: Predicate


################################################################################
## Libraries


@dataclass(frozen=True)
class Library:
    eventTypes: list[EventType]
    analysisTypes: list[AnalysisType]
    computationTypes: list[ComputationType]


################################################################################
## Parse
