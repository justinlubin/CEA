from collections import OrderedDict
from dataclasses import dataclass
from typing import Optional

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

# Values


@dataclass(frozen=True)
class VarValue:
    typ: ValueType
    name: str


@dataclass(frozen=True)
class IntValue:
    val: int


@dataclass(frozen=True)
class StrValue:
    val: str


ConstantValue = IntValue | StrValue

Value = ConstantValue | VarValue

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
