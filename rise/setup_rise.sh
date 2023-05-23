#!/bin/bash

# Run this file with $. setup_rise.sh or $source setup_rise.sh
(
cd /home/ramsis/repos/rt-ramsis/rise &&
ramsis model load --model-config config/model_etas_1992.json &&
ramsis model load --model-config config/model_etas_2010.json &&
ramsis project create --config config/project_etas.json &&
ramsis forecastseries create --config config/forecast_series_etas.json &&
cd /home/ramsis/repos/rt-ramsis/RAMSIS &&
ramsis forecastseries schedule 1 --overdue-interval 6000)
