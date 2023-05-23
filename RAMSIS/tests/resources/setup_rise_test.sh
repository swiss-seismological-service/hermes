#!/bin/bash

(cd /home/ramsis/repos/rt-ramsis/RAMSIS &&
python tests/recreate_test_db.py &&
ramsis model load --model-config tests/resources/model_etas.json &&
ramsis model load --model-config tests/resources/model_etas_altered.json &&
#ramsis project create --config tests/resources/project_etas.json --catalog-data tests/resources/1992-2021_fdsn_catalog_etas_switz.xml&&
ramsis project create --config tests/resources/project_etas.json &&
ramsis forecastseries create --config tests/resources/forecast_series_etas.json &&
#ramsis project create --config tests/resources/project_etas_recent_timewindow.json &&
#ramsis forecastseries create --config tests/resources/forecast_etas_diffmc.json &&
ramsis forecastseries schedule 1 --overdue-interval 200
#ramsis forecastseries schedule 2 --overdue-interval 200

)
