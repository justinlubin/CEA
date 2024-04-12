import unittest
import expecttest

from cea.shared.sexp import *


test = """
(define foo VolcanoPlot $BREAK
  ((s1 Seq) 3 $BREAK (s2 Seq) 2 )
  (and $BREAK
    (a b)
    (c d)))

"""


class Test(expecttest.TestCase):
    def test_without_list_breaks(self) -> None:
        self.assertEqual(
            parse(show(parse(test))),
            without_list_breaks(parse(test)),
        )

    def test_parse_show(self) -> None:
        self.assertExpectedInline(
            show(parse(test)),
            """\
(define foo VolcanoPlot
  ((s1 Seq) 3
    (s2 Seq)
    2)
  (and
    (a b)
    (c d)))""",
        )


if __name__ == "__main__":
    unittest.main()
