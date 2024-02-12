from cea.dsl import Program
from cea.stdbiolib import *

p = Program()

unsorted = Pop("unsorted")
off = Pop("off")
on = Pop("on")

inf = Inf(
    library="/Users/jlubin/Desktop/ex/library.csv",
    negative_controls="/Users/jlubin/Desktop/ex/negative_controls.csv",
)

p.do(
    Infect.M(t=Day(1), pop=unsorted, inf=inf),
    Infect.D(),
)

p.do(
    CellSort.M(t=Day(2), pop_in=unsorted, pop_no=off, pop_yes=on),
    CellSort.D(),
)

p.do(
    Seq.M(t=Day(3), pop=off),
    Seq.D(path="/Users/jlubin/Desktop/ex/off.fastq"),
)

p.do(
    Seq.M(t=Day(3), pop=on),
    Seq.D(path="/Users/jlubin/Desktop/ex/on.fastq"),
)

p.query(
    PhenotypeScore.M(
        t1=Day(3),
        t2=Day(3),
        pop1=off,
        pop2=on,
    )
)
