import cea.dsl

p = cea.dsl.Program()

c1 = p.Condition()
c2 = p.Condition()

p.Infect(1, c1, library="lib1.csv")
p.Infect(1, c2, library="lib2.csv")

for d in [3, 5, 7]:
    p.Seq(d, c1, path=f"day{d}.fasta")

p.PhenotypeScore(3, 5, c1).qoi()
