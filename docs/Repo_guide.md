#### Repo Guide

General guide to repo and some ideas for changes.

##### RAMSIS/cli

All of the functions that interact with prefect are in RAMSIS/cli/utils.py

These are the ones that will have to be updated when prefect gets upgraded.

Which sets the logging level at this point, I think this will be a centrally set option in the future, as setting env variables is not too simple in the new setup.

Most of the cli code is self contained, with only datamodel.io.configuration.py used for schemas.

When I stop a flow from the cli, I usually do it by deleting the flow run, which does seem to work fine. I believe there is a prefect function to instead stop the flow run by setting the status to stopped, but as the current approach is not causing any problems, I would keep it. Also prefect python client functions have been changing a lot over prefect versions.

the top level for the cli at RAMSIS/cli/__init__.py has been the location for all miscellaneous commands, however since many have been added, at some point it will be worth moving some to a config level, or moving some to within the forecastseries level.



##### RAMSIS/clients/datasources.py

Code for requesting data from fdsnws and hydws



##### RAMSIS/clients/sfm.py

Code for sending requests to the worker.



##### RAMSIS/flows/forecast.py

This contains all the prefect flows:

**scheduled_ramsis_flow** is the one called by the prefect server which creates a forecast and model runs in the db.

**ramsis_flow** is then called from within scheduled_ramsis_flow with the new forecast id. The map function is used for tasks where multiple tasks are required that can be parallel, like dispatching model runs.

**polling flow** is an internal flow found within ramsis_flow. The reason this is a flow and not just a task, is because it must be executed repeatedly until all the model runs have a result, and each time it is executed a different set of model run ids must be input. It is tricky to make this dependency on itself clear in the flow unless it is a sub-flow, in which case the flow must be fully completed before the next loop can take place.



##### RAMSIS/tasks/forecast.py

All the prefect tasks that are used within the flows are here. To be called in a flow, a function must have a @task decorator that contains at least a name, which is displayed in the logs. The f-string used in the task_run_name can use parameters given in the task inputs.

In the **update_fdsn** task, I hardcoded a timeout of 700 seconds for the request. This was set as there were some large catalogs (for OEF i think) that were occasionally taking longer than 500 seconds. However, the timeout on the fdsnws side also had to be updated to be made longer - which Philipp Ka did for me. But just a heads up.

###### Note on concurrency limit:

The tasks **model_run_executor** and **poll_model_run** are the two tasks with the tag="model_run" in the task decorator. This is used to set the concurrency limit. The concurrency limit is not a perfect solution, as it only minimizes the chances that too many model runs will be submitted to the worker at a time. if the limit is set to 2, then theoretically, 2 submissions of model_run_executor can take place, which submits the model run to the worker. These tasks will not take very long, and afterwards prefect has the choice to submit 2 more model runs to the worker, or to use up the 2 spaces with polling for the model runs with poll_model_run. I depend on prefect not preferentially running model_run_executor for some reason (i.e. it appears first in the flow or it takes a shorter time to run), and it appears to work, however I think that something more sophisticated will have to be introduced, or on the worker end.

Potentially a solution is that these two tasks could be joined together. The submission of the model run to the worker could be dependent on the status of the model_run, it is only sent off when not RUNNING, and then the concurrency limit would really limit the number of model runs to the number set.



##### Upgrading prefect

RAMSIS/cli/utils.py contain some functions that will have to be updated when prefect gets upgraded, as Deployment.build_from_flow will no longer work. 

Another change that will be caused by the upgrade is a parameter set in the build_from_flow function which is: infra_overrides={"env": {"PREFECT_LOGGING_LEVEL": logging_level}}, which sets the logging level (the idea was that access from the cli could let the user pick what logging level they wanted for a particular forecast series or forecast, but it is not an important feature.)

Thinking more on separating the code into different bases, I am not convinced about it any more. Both local execution of the flows and deployment would need access to the full set of cli commands, and maybe it is ok just to give the user a choice of how they want to execute it.

- For ramsis forecastseries schedule, and ramsis forecast rerun, a choice could be given of serving it or deploying it. Deploying it would probably just automatically use the main or master branch on git. Just making a couple of new functions in cli/utils could be enough to satisfy the requirements.

In the case of deploying, the prefect agent will change to a prefect worker, where a work pool can be defined or I think one may just get created by default. Specified in the inputs to build_from_flow is the work_queue_name, which I hard coded to have the name 'default'. This can probably also be the name of the new work pool.

##### RAMSIS/tests/flows/test_ramsis_flow

There are two tests here, one for grids and one for catalogs. They are full pipeline tests - you can set an option **--use-data-ws** to decide not to patch the web services that are set in the configuration. Leaving this option out will mock the data. Another option is **--use-model-ws**. This will actually make a call to the model worker. Leaving it out will mock the result. 

Each time a test is run, the database and user will get dropped and created as per the .env.test config file.

I have found these tests to be the most useful, as they test the two main use cases for ramsis. There are no unit tests here, it just felt more important to spend the time developing features for the main cases than catching edge cases.

I usually run the tests:

pytest -k etas --capture=tee-sys

pytest -k forge --capture=tee-sys



##### Updating Injection plan on Forecast Series

In the case that you do want to add this feature, I think the best course would be to implement a new command: **ramsis forecastseries update-plan**, and even if the forecast series is already in progress, as the injection plan only gets copied over when a new model run is created, so all new forecasts will use the new plan. You have to look at the model run rather than the forecast series to find which plan is associated.

In the datamodel, you would want to remove the delete behavior of the forecast series of a detached plan, which means that there may end up being detached plans floating around unless some trigger for deletion is created. 





