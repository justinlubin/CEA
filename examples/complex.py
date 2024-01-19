import cea.dsl

p = cea.dsl.Program()

c1 = p.Condition()
c2 = p.Condition()

p.Infect(t=1, c=c1)
p.Infect(t=1, c=c2)

for d in [3, 5, 7]:
    p.Seq(t=d, c=c1)

p.PhenotypeScore(ti=3, tf=5, c=c1).query()
