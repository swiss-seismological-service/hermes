source env/bin/activate
hermes drop-tables
hermes create-tables
hermes project create project_induced --config scripts/induced/project.json
hermes forecastseries create fs_induced --config scripts/induced/forecastseries.json --project project_induced
hermes injectionplan create default --forecastseries fs_induced --file scripts/induced/injectionplan.json
hermes model create em1 --config scripts/induced/model_config.json
hermes forecast run fs_induced --start 2022-04-21T15:00:00 --end 2022-04-21T18:00:00
deactivate