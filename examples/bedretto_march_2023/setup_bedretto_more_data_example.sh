#!/bin/bash

(cd /home/ramsis/repo/rt-ramsis/examples/bedretto_march_2023 &&
#ramsis model add-seismicity --model-config model_bedretto_22062022.json --hazardsourcemodeltemplate-path model_haz.json &&
#ramsis model add-seismicity --model-config model_seis.json --hazardsourcemodeltemplate-path model_haz.json &&
#ramsis model add-hazard --model-config model_haz.json --gsimlogictree-path gmpe_logic_tree.xml &&
ramsis project create --config project_bedretto_14032023_no_ws.json &&
ramsis forecast create --project-id 2 --config forecast_bedretto_14032023.json --inj-plan-directory /home/ramsis/repo/rt-ramsis/examples/bedretto_march_2023 --hyd-data well_data2023-03-14T11-00_2023-03-14T20-50.json --catalog-data catalog_data2023-03-14T11-00_2023-03-14T20-50.xml)
