import json
import os
from datetime import datetime

from hydws.parser import BoreholeHydraulics

from hermes.io.injectionplans import (InjectionPlanBuilder, build_constant,
                                      build_fixed, build_multiply)

MODULE_LOCATION = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               'data')
start = datetime.strptime('2022-04-19T14:00:00', '%Y-%m-%dT%H:%M:%S')
end = datetime.strptime('2022-04-19T14:10:00', '%Y-%m-%dT%H:%M:%S')

with open(os.path.join(MODULE_LOCATION, 'hydraulics_ip.json'), 'r') as f:
    hydraulics = BoreholeHydraulics(json.load(f))


class TestInjectionPlanBuilder:

    # def test_constant(self):
    #     with open(os.path.join(MODULE_LOCATION, 'constant_template.json'),
    #               'r') as f:
    #         template = json.load(f)

    #     builder = InjectionPlanBuilder(template)
    #     plan = builder.build(start, end)
    #     pass

    def test_build_fixed(self):
        with open(os.path.join(MODULE_LOCATION, 'fixed_template.json'),
                  'r') as f:
            template = json.load(f)[0]

        plan = build_fixed(start, end, 60, template['config'])

        assert plan.shape[0] == 12
        assert plan['topflow'].iloc[0] == 0.04
        assert plan['topflow'].iloc[-1] == 0.05
        assert plan['bottomflow'].iloc[0] == 0.03

        assert plan['topflow_uncertainty'].iloc[5] == 0.0001

    def test_build_constant(self):
        with open(os.path.join(MODULE_LOCATION, 'constant_template.json'),
                  'r') as f:
            template = json.load(f)[0]

        plan = build_constant(start, end, 60, template['config'])

        assert plan.shape[0] == 11
        assert plan['bottomflow'].unique() == [0.02]
        assert {'topflow', 'bottomflow'}.issubset(
            set(plan.columns))

    def test_build_multiply(self):
        with open(os.path.join(MODULE_LOCATION, 'multiply_template.json'),
                  'r') as f:
            template = json.load(f)[0]

        hydraulics_df = hydraulics.nloc[template['section_name']].hydraulics

        plan = build_multiply(
            start, end, 60, template['config'], hydraulics_df)
        print(plan)

        assert plan.shape[0] == 11
        assert plan['topflow'].unique() == [0.042]
        assert plan['bottomflow'].unique() == [0.03]
        assert plan['topflow_uncertainty'].unique() == [0]
        assert len(plan.columns) == 3
