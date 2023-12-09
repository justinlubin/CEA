import cea.dsl

p = cea.dsl.Program()
c = p.Condition()

p.Infect(1, c, library="library.csv")
p.Seq(3, c, path="before.fasta")
p.Seq(8, c, path="after.fasta")

p.PhenotypeScore(3, 8, c).qoi()
