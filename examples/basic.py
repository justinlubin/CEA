from cea.dsl import Program
from cea.stdbiolib import *

p = Program()
c = p.Condition()

p.do(Infect, at=dict(t=1, c=c), where=dict(library="library.csv"))
p.do(Seq, at=dict(t=3, c=c), where=dict(path="seq1.csv"))
p.do(Seq, at=dict(t=8, c=c), where=dict(path="seq2.csv"))

p.query(PhenotypeScore, at=dict(ti=3, tf=8, c=c))
