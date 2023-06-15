#!/bin/bash

(cd /home/sarsonl/repos/rt-ramsis/RAMSIS &&
python tests/recreate_test_db.py &&
ramsis model load --model-config tests/resources/model_etas.json &&
ramsis model load --model-config tests/resources/model_etas_altered.json &&
ramsis project create --config tests/resources/project_etas.json &&
ramsis forecastseries create --config tests/resources/forecast_series_etas.json &&
ramsis forecastseries schedule 1 --overdue-interval 200
)
