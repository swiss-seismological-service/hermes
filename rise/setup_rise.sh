#!/bin/bash

# Run this file with $. setup_rise.sh or $source setup_rise.sh
(cd /home/ramsis/repo/rt-ramsis/rise &&
ramsis model load --model-config config/model_etas.json &&
ramsis project create --config config/project_etas.json &&
ramsis forecastseries create --config config/forecast_etas.json)
