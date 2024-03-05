import pandas as pd
import json
from datetime import datetime, timedelta


def create_df(plan, resample_rule, starttime):
    # Take input as nested lists defining the minutes
    # after starttime and the flow in L/m
    # Outputs a dataframe with a datetime index
    # and topflow column, resamples according to resample rule and
    # changes the units of topflow to m^3/s
    rows_list = []
    for row in plan:
        dict1 = {'datetime': starttime + timedelta(minutes=row[0]),
                 'L/m': row[1]}

        rows_list.append(dict1)
    df = pd.DataFrame(rows_list)
    df['datetime'] = pd.to_datetime(df['datetime'])
    df.set_index('datetime', inplace=True)
    # get topflow in m^3/s
    df['topflow'] = df['L/m'] * 0.06
    df.drop(columns='L/m', inplace=True)
    df = df.resample(resample_rule).ffill()
    df = df.reset_index()
    return df


def main():
    # INPUTS
    # ----------------------------------------------------------------
    reference_file = \
        "/home/sarsonl/repos/rt-ramsis/forge_2022/2022-04-21_hydws.json"

    # Define starttime of the hydraulics for all plans
    starttime = datetime(2022, 4, 21, 14, 0)

    # The resample rule will resample the hydraulic data
    # to this frequency of data point.
    resample_rule = timedelta(minutes=20)

    # Define hydraulic input in Litres per minute
    # This will be recalculated to metres cubes per second for the file
    # The format of each nested list is:
    # [minutes after starttime, litres per minute]
    plan_1 = [
        [0, 150],
        [60 * 4, 150]]
    plan_2 = [
        [0, 200],
        [60 * 4, 200]]
    plan_3 = [
        [0, 150],
        [60, 150],
        [70, 200],
        [60 * 4, 200]]

    # Define output filenames for the different plans
    # Files with the same name will be overwritten.
    plan_filenames = {
        "plan_150Lm.json": plan_1,
        "plan_200Lm.json": plan_2,
        "plan_150Lm-200Lm.json": plan_3}

    # READ AND VALIDATE REFERENCE FILE
    # ----------------------------------------------------------------

    # Open the reference file and use the information in there,
    # not including the hydraulic data.
    with open(reference_file, 'r') as o_ref:
        ref_json = json.load(o_ref)
    if isinstance(ref_json, list):
        if len(ref_json) != 1:
            raise IOError("There are the wrong number of boreholes in "
                          f"the reference file {len(ref_json)}")
        else:
            ref_json = ref_json[0]
    # Check that there is only one section, as multiple sections may not
    # be used in a plan.
    if len(ref_json['sections']) != 1:
        raise IOError("There are the wrong number of borehole sections in "
                      f"the reference file {len(ref_json['sections'])}")

    # CREATE DATAFRAME AND FILES
    # ----------------------------------------------------------------

    # Loop through filenames and hydraulic plans associated.
    for fname, plan in plan_filenames.items():
        df = create_df(plan, resample_rule, starttime)
        json_hyd = df.to_json(date_format='iso', date_unit='s',
                              orient='records')
        ref_json['sections'][0]['hydraulics'] = json.loads(json_hyd)
        for hyd_values in ref_json['sections'][0]['hydraulics']:
            for key in hyd_values.keys():
                hyd_values[key] = dict(value=hyd_values[key])
        with open(fname, 'w') as o_file:
            json.dump(ref_json, o_file)


if __name__ == "__main__":
    main()
