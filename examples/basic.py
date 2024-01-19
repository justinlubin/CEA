import cea.dsl

p = cea.dsl.Program()
c = p.Condition()

p.Infect(t=1, c=c)
p.Seq(t=3, c=c)
p.Seq(t=8, c=c)

p.PhenotypeScore(ti=3, tf=8, c=c).query()
