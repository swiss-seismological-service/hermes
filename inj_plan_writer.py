import pandas as pd
import json
from datetime import datetime, timedelta

reference_file = "/home/sarsonl/repos/rt-ramsis/forge_2022/2022-04-21_hydws.json"
resample_rule = timedelta(minutes=20)

with open(reference_file, 'r') as o_ref:
    ref_json = json.load(o_ref)
if isinstance(ref_json, list):
    if len(ref_json) != 1:
        raise IOError(f"There are the wrong number of boreholes in the reference file {len(ref_json)}")
    else:
        ref_json = ref_json[0]
if len(ref_json['sections']) != 1:
    raise IOError(f"There are the wrong number of borehole sections in the reference file {len(ref_json['sections'])}")


starttime = datetime(2022, 4, 21, 14, 0)
plan_1 = [
        [0, 150],
        [60*4, 150]]
plan_2 = [
        [0, 200],
        [60*4, 200]]
plan_3 = [
        [0, 150],
        [60, 150],
        [70, 200],
        [60*4, 200]]

plan_filenames = {
        "plan_150Lm.json": plan_1,
        "plan_200Lm.json": plan_2,
        "plan_150Lm-200Lm.json": plan_3
        }
def create_df(plan):
    rows_list = []
    for row in plan:
        dict1 = {'datetime': starttime + timedelta(minutes=row[0]), 'L/m': row[1]}
        # get input row in dictionary format
        # key = col_name
        #dict1.update(blah..) 
    
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






for fname, plan in plan_filenames.items():
    df = create_df(plan)
    json_hyd = df.to_json(date_format='iso', date_unit='s', orient='records')
    ref_json['sections'][0]['hydraulics'] = json.loads(json_hyd)
    for hyd_values in ref_json['sections'][0]['hydraulics']:
        for key in hyd_values.keys():
            hyd_values[key] = dict(value=hyd_values[key])
    with open(fname, 'w') as o_file:
        json.dump(ref_json, o_file)
