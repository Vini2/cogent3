from unittest import TestCase, main
from unittest.mock import MagicMock

from cogent3 import LoadSeqs, LoadTree
from cogent3.app import evo as evo_app
from cogent3.app.result import hypothesis_result


__author__ = "Gavin Huttley"
__copyright__ = "Copyright 2007-2019, The Cogent Project"
__credits__ = ["Gavin Huttley"]
__license__ = "BSD-3"
__version__ = "2019.07.10a"
__maintainer__ = "Gavin Huttley"
__email__ = "Gavin.Huttley@anu.edu.au"
__status__ = "Alpha"


class TestModel(TestCase):
    basedir = "data"

    def test_model_str(self):
        """correct str representation"""
        model = evo_app.model("HKY85", time_het="max")
        got = str(model)
        self.assertEqual(
            got,
            (
                "model(type='model', sm='HKY85', tree=None, "
                "name=None, sm_args=None, lf_args=None, "
                "time_het='max', param_rules=None, "
                "opt_args=None, split_codons=False, "
                "show_progress=False, verbose=False)"
            ),
        )

    def test_model_tree(self):
        """allows tree to be string, None or tree"""
        treestring = "(a,b,c)"
        for tree in (treestring, LoadTree(treestring=treestring), None):
            mod = evo_app.model("HKY85", tree=tree)
            expect = None if tree is None else LoadTree(treestring=treestring)
            self.assertIsInstance(mod._tree, expect.__class__)

    def test_unique_models(self):
        """hypothesis raises ValueError if models not unique"""
        model1 = evo_app.model("HKY85")
        model2 = evo_app.model("HKY85", time_het="max")
        with self.assertRaises(ValueError):
            hyp = evo_app.hypothesis(model1, model2)

    def test_model_time_het(self):
        """support lf time-het argument edge_sets"""
        _data = {
            "Human": "ATGCGGCTCGCGGAGGCCGCGCTCGCGGAG",
            "Mouse": "ATGCCCGGCGCCAAGGCAGCGCTGGCGGAG",
            "Opossum": "ATGCCAGTGAAAGTGGCGGCGGTGGCTGAG",
        }
        aln = LoadSeqs(data=_data, moltype="dna")
        mod = evo_app.model(
            "GN",
            time_het=[dict(edges=["Mouse", "Human"], is_independent=False)],
            opt_args=dict(max_evaluations=25, limit_action="ignore"),
        )
        result = mod(aln)
        # 11 free params per calibrated GN matrix, there are 2
        # 3 params for root motif probs, 3 branch lengths
        expect_nfp = 11 * 2 + 3 + 3
        self.assertEqual(result.lf.nfp, expect_nfp)

    def test_model_hypothesis_result_repr(self):
        """result objects __repr__ and _repr_html_ methods work correctly"""
        _data = {
            "Human": "ATGCGGCTCGCGGAGGCCGCGCTCGCGGAG",
            "Mouse": "ATGCCCGGCGCCAAGGCAGCGCTGGCGGAG",
            "Opossum": "ATGCCAGTGAAAGTGGCGGCGGTGGCTGAG",
        }
        aln = LoadSeqs(data=_data, moltype="dna")
        model1 = evo_app.model(
            "F81", opt_args=dict(max_evaluations=25, limit_action="ignore")
        )
        model2 = evo_app.model(
            "HKY85", opt_args=dict(max_evaluations=25, limit_action="ignore")
        )
        hyp = evo_app.hypothesis(model1, model2)
        result = hyp(aln)
        self.assertIsInstance(result.__repr__(), str)
        self.assertIsInstance(result._repr_html_(), str)
        self.assertIsInstance(result.null.__repr__(), str)
        self.assertIsInstance(result.null._repr_html_(), str)

    def test_hypothesis_str(self):
        """correct str representation"""
        model1 = evo_app.model("HKY85")
        model2 = evo_app.model("HKY85", name="hky85-max-het", time_het="max")
        hyp = evo_app.hypothesis(model1, model2)
        got = str(hyp)
        expect = (
            "hypothesis(type='hypothesis', null='HKY85', "
            "alternates=(model(type='model', sm='HKY85', tree=None, "
            "name='hky85-max-het', sm_args=None, lf_args=None, "
            "time_het='max', param_rules=None, opt_args=None,"
            " split_codons=False, show_progress=False, verbose=False),),"
            " init_alt=None)"
        )
        self.assertEqual(got, expect)

    def test_split_pos_model(self):
        """model with split codons, access .lf using codon position int"""
        _data = {
            "Human": "ATGCGGCTCGCGGAGGCCGCGCTCGCGGAG",
            "Mouse": "ATGCCCGGCGCCAAGGCAGCGCTGGCGGAG",
            "Opossum": "ATGCCAGTGAAAGTGGCGGCGGTGGCTGAG",
        }
        aln = LoadSeqs(data=_data, moltype="dna")
        tree = LoadTree(tip_names=aln.names)
        mod = evo_app.model(
            "F81",
            tree=tree,
            split_codons=True,
            opt_args=dict(max_evaluations=5, limit_action="ignore"),
        )
        result = mod(aln)
        aln1 = result.lf[1].get_param_value("alignment").todict()
        self.assertEqual(aln1, aln[::3].todict())


class TestHypothesisResult(TestCase):
    def test_get_best_model(self):
        """should correctly identify the best model"""

        def make_getter(val):
            def call(**kwargs):
                return val

            return call

        def make_hyp(aic1, aic2, aic3, nfp1, nfp2, nfp3):
            null = MagicMock()
            null.name = "unrooted"
            null.lf.get_aic = make_getter(aic1)
            null.nfp = nfp1
            alt1 = MagicMock()
            alt1.name = "alt1"
            alt1.lf.get_aic = make_getter(aic2)
            alt1.nfp = nfp2
            alt2 = MagicMock()
            alt2.name = "alt2"
            alt2.lf.get_aic = make_getter(aic3)
            alt2.nfp = nfp3
            hyp = hypothesis_result("unrooted", source="something")
            for m in (null, alt1, alt2):
                hyp[m.name] = m
            return hyp

        # aic order is null, alt1, alt2
        # in this case, no substantial diff, so should return smaller nfp, ie null
        hyp = make_hyp(112, 110, 111, 10, 11, 12)
        got = hyp.get_best_model(threshold=0.05)
        self.assertIs(got, hyp.null)
        # here alt2 is winner
        hyp = make_hyp(110, 111, 104, 10, 11, 12)
        got = hyp.get_best_model(threshold=0.05)
        self.assertIs(got, hyp["alt2"])
        # but if we set threshold more permissive, it will return null
        got = hyp.get_best_model(threshold=0.03)
        self.assertIs(got, hyp.null)


if __name__ == "__main__":
    main()
