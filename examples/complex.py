import cea.dsl
from cea.stdbiolib import *

p = cea.dsl.Program()

c1 = p.Condition()
c2 = p.Condition()

p.do(Infect, at=dict(t=1, c=c1), where=dict(library="library1.csv"))
p.do(Infect, at=dict(t=1, c=c2), where=dict(library="library2.csv"))

for d in [3, 5, 7]:
    p.do(Seq, at=dict(t=d, c=c1), where=dict(path=f"seq-day{d}.csv"))

p.query(PhenotypeScore, at=dict(ti=3, tf=5, c=c1))
