import unittest
from spillover import mix, unmix

class TestMixing(unittest.TestCase):
    def test_round_trip(self):
        for a,b in [(0.,0.), (8.,3.), (0.,10.), (10.,0.)]:
            observed = mix(a,b,0.2,0.1)
            recovered = unmix(*observed,0.2,0.1)
            self.assertAlmostEqual(a,recovered[0])
            self.assertAlmostEqual(b,recovered[1])

    def test_singular(self):
        with self.assertRaises(ValueError):
            unmix(1.,2.,1.,1.)

    def test_invalid(self):
        with self.assertRaises(ValueError):
            mix(float("nan"),2.,0.2,0.1)

    def test_unidentifiability_without_calibration(self):
        # One observation can be explained by different true signals
        observed = mix(8.,3.,0.2,0.1)
        other = unmix(*observed,0.,0.)
        self.assertNotAlmostEqual(other[0],8.)

if __name__ == "__main__":
    unittest.main()
