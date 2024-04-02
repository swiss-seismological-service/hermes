# User Guide

A number of work flows are described to cover the main eventualities.

### Hierarchy of configuration

#### Project

All forecasts made in a particular project will share the same data. This includes data sources and window of data capture. If different data is required for different forecasts, they will have to be created in a different project.

`ramsis project ls` to see what projects exist

#### Model

Each model configuration contains variables that will be sent to the forecast model, and describes the model location and url it is available at.

`ramsis model ls` to see what model configs exist

#### Forecast Series

A forecast series describes what times forecasts will be run, and what model configuration (and injection plans if applicable) will be used.

`ramsis forecastseries ls` to see what forecast series exist

Once a forecast series has been scheduled, forecasts will be created when they are due to run.

`ramsis forecast ls` to see what forecasts exist



### Simple Work Flow

Aim: Add a new forecast series to the database and start running the forecasts.

The simplest way to add all your configuration at once is with the **ramsis create-all** command.

This creates a new project, updates or creates model config and creates a new forecast series.



In the case when there is already be projects, forecast series and models, the following rules must be adhered to:

- A project must have a unique name
- A forecast series does not need a unique name but you should consider giving it one
- Existing model configuration may not be modified after a forecast is associated, see 'Archiving Models' or update the model name to create a new model config.



The ramsis create-all command runs the following commands in order, with inputs from a configuration file, default named config.json:

​	`ramsis project create`

​	`ramsis model load`

​	`ramsis forecastseries creat`e



#### Schedule the forecast series

To start the forecast series running you must schedule it. This command determines if there is a finite range of times for a forecast to be started, or if it is ongoing occurrence. Forecasts where the start time as passed are scheduled where the first overdue forecast will be executed immediately, and after a break, the next will be run, and so on. This break length is the '--overdue-interval'.  A longer interval may be preferable in cases where model runs take a long time to complete, or where you want to stagger the load to minimize  risk of overloading the model worker.

`ramsis forecastseries schedule 25 --overdue-interval 30`

This command also works when the schedule has been interrupted, and you would like to resume the schedule. The most recent forecast on the forecast series will be found, and the forecasts due after this will be scheduled. instances where this may happen:

- The prefect agent/server has been restarted and doesn't show scheduled runs with `ramsis list-scheduled-forecasts`
- The computer needed to be restarted
- You accidentally deleted the most recent forecasts and you would like to run the forecast series again. In this case you will have to delete anything in progress first with `ramsis delete-scheduled-flow-runs` so that ramsis does not run multiple forecasts for the same times. 



#### What happens after scheduling?

After the schedule command is run, the Prefect Server picks up the schedule request. This request contains information on when to execute the forecast, the forecast start time and the forecast series id. The clock within the Prefect Server knows when a forecast is due, and will send the information to the Prefect Agent to run the code, or as Prefect calls it, the 'flow'.

A forecast object will be created, and tags* are compared with model configs. If relevant, the number of injection plans is found. The total number of model runs created per forecast will be:

no. model configs x no. injection plans

or simply 

no. model configs if injection plans have not been defined as required in the project config.

> [!NOTE]
>
> Tags are strings that are associated with a model config or a forecast series. They can be descriptive but they serve as an identifier of which model configs to run with which forecast series. If a model can only be used with an induced dataset, then you may add an 'induced' tag to a model config. If a model is calibrated only to Europe, then a 'europe' tag may be added. Multiple tags may be added to either a model config or forecast series and if a model config has one or more tags in common, this model config will be run.



The forecast flow will retrieve and store data. Each model run will then be run concurrently and a request sent to the model worker for each model . This request will be accepted if there appears to be no errors in the data, and the model worker will be polled with an exponential time relationship. When a request to the model worker on the status of the model run returns data, this data will get stored in the ramsis database. The status of various objects in the database also get updated through the flow, and the forecast will finish with a status of COMPLETED.

Errors produced in the forecast model will be logged in the database  and the model run and also the forecast will have a status of FAILED. Failure to get data from web services or mismatch between data and IO will also result in failures, although these failures will not be logged in the database and investigation into the prefect agent log will be required.



#### Data

Data can come from web services:

FDSNWS - Catalogs required in quakeml format

HYDWS - Hydraulic well data required in JSON format

Or for replay cases, when the data is not changing in time, data can be attached to a project at configuration time. This data will be cloned and attached to each forecast as it is run.



#### Avoiding model run overload

The main way of controlling the number of model runs at a time,  is to run **ramsis update-model-run-concurrency**. The number of model runs you should allow at one time should not exceed the number of models that can comfortably run at the same time with the most memory intensive configuration that you want to use.

`ramsis update-model-run-concurrency 3`

`ramsis read-model-run-concurrency`

`ramsis remove-model-run-concurrency`

If there is no limit set on model run concurrency, every model run created will immediately be sent to the model worker, and run.



#### In case of major crashes or laptop failing

In the case where everything needs restarting, restart the prefect agent, the prefect server and the model worker. 

If a forecast series was in progress and it is not finished, check to see if there are any forecasts scheduled: `ramsis list-scheduled-forecasts`

if there are, then it looks like the server has resumed processing of the forecast series and nothing further should be done.

In the case where there are no scheduled runs, you can reschedule the forecast series with the `ramsis forecastseries schedule` command. This will restart the forecast series scheduling from the last run forecast.



#### Archiving Models

A model config cannot be deleted after a model run is associated with it. This is a safeguard because model runs need to maintain all their configuration to trace how the data was created. If you want to update a model configuration that has already been used, you can archive the existing model configuration, which renames it with ARCHIVED-datestamp appended.



#### Rerunning Forecasts

In the case of an error on a forecast, don't delete the forecast, you can just rerun it.

The command

`ramsis forecast rerun 1 2 3 4`

where 1 2 3 4 are the ids of the forecasts we want to rerun.

can be used in the case where you want to rerun a forecast. Running it will update the datasources if urls are configured. any model runs with a status of PENDING or FAILED will be sent to the model worker again. Any model runs with a status of RUNNING are assumed to be in progress with the model worker, and the model worker will be polled. Any model runs that are already COMPLETED are ignored.

In the case where the model run/ forecast status are wrong (for instance, a crash means that a status is RUNNING rather than FAILED) or you simply want to rerun it freshly, you can use the --force option which resets the statuses of the forecast and all associated model runs back to PENDING.

`ramsis forecast rerun <forecast_ids> --force`



### Checking status of forecasts

`ramsis list-scheduled-forecasts`

This command shows the user what forecasts are scheduled

`ramsis forecast ls`

This prints a table including all the information on the forecasts. If the  `--full` option is used, all the information is given on the forecast, including some log information. The log for each forecast will contain the status of the model runs that have been run for the forecast.



### Project Configuration



A project contains:

- Descriptive name and description
- start time - This defines the beginning of data retrieval window
- end time (Optional) - This defines the end of data retrieval window. In cases of ongoing projects it can be undefined, and end of the data window is defined as the current time.
- data specifications - whether certain data is required, optional (in which case retrieval is attempted but does not cause an error if not available) or not required. Also the web service urls.



`ramsis create-all --directory forge_2022 --config config.json --delete-existing`



#### Troubleshooting

Sometimes, when there have been crashes or failed runs, there are prefect tasks that are no longer running but that may fill up the concurrency limit. `ramsis delete-all-flow-runs` will delete the existing flow runs in the prefect database, which will not affect anything already completed. If there are still things running, I would recommend to use this command anyway as they will likely not complete if the concurrency limit has been reached. Forecasts that are scheduled 

`ramsis delete-incomplete-flow-runs` is another option, and will delete anything that is not scheduled or already complete.

If rerunning a forecast doesn't gets stuck after this, you can look at the prefect concurrency limits and if they are filled with active tasks using:

`prefect concurrency-limit inspect model_run`

I think that the currently used version of prefect (2.10.9) has a bug where sometimes all the tasks are not removed when deleting a flow run. (Yes, very annoying) which will hopefully be resolved when upgrading prefect.

If this is the case, and all the slots are filled with active tasks, the concurrency limit can be reset:

`prefect concurrency-limit reset model_run`



If that doesn't work, you can do a full prefect database reset:

`prefect server database reset -y`

don't forget to set the concurrency limit again after this.

The only other thing that might need to be done if you are doing a hard reset of prefect, is deleting the ~/.prefect folder as this contains all configuration and might not be updated correctly.