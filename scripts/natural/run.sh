source env/bin/activate
hermes drop-tables
hermes create-tables
hermes project create project_natural --config scripts/natural/project.json
hermes forecastseries create fs_natural --config scripts/natural/forecastseries.json --project project_natural
hermes model create etas --config scripts/natural/model_config.json
hermes forecast run fs_natural --start 2024-12-01T00:00:00 --end 2024-12-31T00:00:00
deactivate