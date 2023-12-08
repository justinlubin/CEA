import cea.dsl

p = cea.dsl.Program()
c = p.Condition()

p.Infect(1, c)
p.Seq(3, c)
p.Seq(8, c)

p.PhenotypeScore(3, 8, c).qoi()
