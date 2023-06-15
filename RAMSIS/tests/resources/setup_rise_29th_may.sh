#!/bin/bash

(cd /home/ramsis/repos/rt-ramsis/RAMSIS &&
#python tests/recreate_test_db.py &&
ramsis model load --model-config tests/resources/model_etas_29th_may.json &&
ramsis model load --model-config tests/resources/model_etas_altered_29th_may.json &&
ramsis project create --config tests/resources/project_etas.json &&
ramsis forecastseries create --config tests/resources/forecast_series_etas_29th_may.json &&
ramsis forecastseries schedule 1 --overdue-interval 10000
)
