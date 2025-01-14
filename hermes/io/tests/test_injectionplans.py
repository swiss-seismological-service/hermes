import json
import os
from datetime import datetime, timedelta

import pytest
from hydws.parser import BoreholeHydraulics

from hermes.io.injectionplans import (InjectionPlanBuilder, build_constant,
                                      build_fixed, build_multiply)

MODULE_LOCATION = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               'data')
start = datetime.strptime('2022-04-19T14:00:00', '%Y-%m-%dT%H:%M:%S')
end = datetime.strptime('2022-04-19T14:10:00', '%Y-%m-%dT%H:%M:%S')

with open(os.path.join(MODULE_LOCATION, 'hydraulics_ip.json'), 'r') as f:
    data = json.load(f)
hydraulics = BoreholeHydraulics(data)
hydraulics_df = hydraulics.nloc['16A-32/section_02'].hydraulics


class TestInjectionPlanBuilder:

    def test_builder(self):
        with open(os.path.join(MODULE_LOCATION, 'constant_template.json'),
                  'r') as f:
            template = json.load(f)

        builder = InjectionPlanBuilder(template, [data])
        plan = builder.build(start, end)
        assert plan['publicid'] == "caf65646-8093-4aaf-989c-1c837f497667"
        assert plan['sections'][0]['name'] == "16A-32/section_02"
        assert len(plan['sections'][0]['hydraulics']) == 11
        assert plan['sections'][0]['hydraulics'][0]['bottomflow']['value'] \
            == 0.02

        template['type'] = 'xx'
        with pytest.raises(ValueError):
            InjectionPlanBuilder(template)

    def test_build_fixed(self):
        with open(os.path.join(MODULE_LOCATION, 'fixed_template.json'),
                  'r') as f:
            template = json.load(f)

        plan = build_fixed(start, end, 60, template['config'], hydraulics_df)

        assert plan.shape[0] == 12
        assert plan['topflow'].iloc[0] == 0.04
        assert plan['topflow'].iloc[-1] == 0.05
        assert plan['bottomflow'].iloc[0] == 0.03

        assert plan['topflow_uncertainty'].iloc[5] == 0.0001

        plan = build_fixed(start + timedelta(minutes=2), end,
                           60, template['config'], hydraulics_df)

        assert plan.shape[0] == 10
        assert plan['topflow'].iloc[0] == 0.04

    def test_build_constant(self):
        with open(os.path.join(MODULE_LOCATION, 'constant_template.json'),
                  'r') as f:
            template = json.load(f)

        plan = build_constant(
            start, end, 60, template['config'], hydraulics_df)

        assert plan.shape[0] == 11
        assert plan['bottomflow'].unique() == [0.02]
        assert {'topflow', 'bottomflow'}.issubset(
            set(plan.columns))

    def test_build_multiply(self):
        with open(os.path.join(MODULE_LOCATION, 'multiply_template.json'),
                  'r') as f:
            template = json.load(f)

        plan = build_multiply(
            start, end, 60, template['config'], hydraulics_df)

        assert plan.shape[0] == 11
        assert plan['topflow'].unique() == [0.042]
        assert plan['bottomflow'].unique() == [0.03]
        assert plan['topflow_uncertainty'].unique() == [0]
        assert len(plan.columns) == 3
