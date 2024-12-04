source env/bin/activate
hermes project create FEAR24 --config scripts/bedretto/project.json
hermes forecastseries create fear_day1 --config scripts/bedretto/forecastseries.json --project FEAR24
hermes injectionplan create equal --forecastseries fear_day1 --file scripts/bedretto/injectionplan.json
hermes injectionplan create double --forecastseries fear_day1 --file scripts/bedretto/injectionplan_double.json
hermes model create em1 --config scripts/bedretto/em1.json
hermes model create ml1 --config scripts/bedretto/ml1.json
hermes model create hm1d --config scripts/bedretto/hm1d.json
hermes forecast run fear_day1 --start 2024-12-03T14:00:00 --end 2024-12-03T17:00:00 --local
deactivate