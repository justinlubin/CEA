from src.cea.framework import *
from src.cea.library import *
import src.cea.souffle as souffle


begin()

c = CondLit("c")
Transfect.R(TimeLit(1), c)
Seq.R(TimeLit(3), c)
Seq.R(TimeLit(5), c)

end(SGRE.R(TimeLit(4), TimeLit(5), CondLit("c")))

output = souffle.run(dl_compile())
if output["Goal.csv"]:
    print("Possible!")
else:
    print("Not possible!")
