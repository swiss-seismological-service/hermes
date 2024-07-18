from hermes.schemas.mixins import real_value_mixin


def test_real_value_mixin():
    class Test(real_value_mixin('test', str)):
        pass

    Test(test_value='1', test_uncertainty=2, test_loweruncertainty=3,
         test_upperuncertainty=4, test_confidencelevel=5)
