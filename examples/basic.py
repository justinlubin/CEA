import src.cea.dsl as dsl

p = dsl.Program()

c1 = p.Condition()
c2 = p.Condition()

p.Transfect(1, c1)
p.Transfect(1, c2)

for d in [3, 5, 7]:
    p.Seq(d, c1)

p.SGRE(3, 5, c1).qoi()
