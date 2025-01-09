# Concepts

The general concepts of the software's domain are described here.

## Project:
*I want to run models and do forecasts for a certain reason and use the results together, eg. in the same frontend*

| Question                                        | field(s)             |
| ----------------------------------------------- | -------------------- |
| Give your project a name.                       | name                 |
| Describe your Project.                          | description          |
| During which time frame is this project active. | start and/or enddate |


## Forecast Series:
*I would like to run forecasts at different points in time, using multiple models, and be able to compare them*

| Question                                                             | field(s)                       | default                                         |
| -------------------------------------------------------------------- | ------------------------------ | ----------------------------------------------- |
| Give this series a name.                                             | name                           | required                                        |
| Are there any forecasts scheduled, paused, .... ?                    | status                         | required                                        |
| What is the spatial extent for which the forecasts are made?         | bounding_polygon,              | None                                            |
|                                                                      | depth_max,                     | None                                            |
|                                                                      | depth_min                      | None                                            |
| What data is needed for the models to run?                           | seismicityobservation_required | False                                           |
|                                                                      | injectionobservation_required  | False                                           |
|                                                                      | injectionplan_required         | False                                           |
| Where are the data sources?                                          | fdsnws_url,                    | required                                        |
|                                                                      | hydws_url                      | None                                            |
| From which datetime should we start using the input data? (optional) | observation_starttime          | None, will use all available records            |
| Only use input data up until this datetime.                          | observation_endtime            | None, will use all records up to forecast start |

## Forecast Series Scheduling
*I'd like to schedule those forecasts at multiple points in time, having them run automatically*

| Question                                               | field(s)           | default                                       |
| ------------------------------------------------------ | ------------------ | --------------------------------------------- |
| How long should each forecast be? (optional*)          | forecast_duration  | None, this or `forecast_endtime` is required  |
| All forecasts start at this datetime. (optional)       | forecast_starttime | None, forecasts will start when triggered     |
| All forecasts end at this datetime. (optional*)        | forecast_endtime   | None, this or `forecast_duration` is required |
| From when onwards should we trigger forecasts?         | schedule_starttime | required                                      |
| Until when should we trigger forecasts? (optional)     | schedule_endtime   | None, forecasts will keep being triggered     |
| Every how many seconds should a forecast be triggered? | schedule_interval  | required                                      |

### Scheduling combinations

#### schedule_starttime, schedule_endtime, schedule_interval, forecast_endtime
- start running forecasts at `schedule_starttime`,run them every `schedule_interval` until `schedule_endtime`.
- each forecast begins from when it was started until `forecast_endtime`.

#### schedule_starttime, schedule_endtime, schedule_interval, forecast_duration
- ""
- each forecast begins from when it was started and lasts for `forecast_duration` seconds.

#### schedule_starttime, schedule_endtime, schedule_interval, forecast_duration, forecast_endtime (special case)
- ""
- each forecast begins from when it was started and lasts for `forecast_duration` seconds (duration takes precedence over endtime).

#### schedule_starttime, schedule_endtime, schedule_interval, forecast_duration, forecast_starttime
- start running forecasts at `schedule_starttime`,run them every `schedule_interval` until `schedule_endtime`.
- each forecast begins from `forecast_starttime` and lasts for `forecast_duration` seconds.
- 
#### schedule_starttime, schedule_interval, forecast_duration
- start running forecasts at `schedule_starttime`, run them every `schedule_interval` until manually stopped.
- each forecast begins from when it was started until `forecast_duration`.

#### schedule_starttime, schedule_interval, forecast_endtime (special case)
- start running forecasts at `schedule_starttime`,run them every `schedule_interval` until `forecast_endtime`.
- ""


## Forecast
*I'd like to run a series of models, at a specific point in time, and produce results for a certain time period.*

### Model - Forecast - Comparisons
*I'd like to compare the results of different models, or the same model at different points in time*

Let's assume, that Forecast 1 runs at 13:00, and produces results until 15:00, Forecast 2 runs at 14:00, and produces results until 16:00, and Forecast 3 runs at 15:00, and produces results until 17:00. All of them using input data starting at 12:00, until the point in time when they were run.

|         |             |             |             |
| ------- | ----------- | ----------- | ----------- |
| Model 1 | *Result_11* | *Result_12* | *Result_13* |
| Model 2 | *Result_21* | *Result_22* | *Result_23* |
| Model 3 | *Result_31* | *Result_32* | *Result_33* |
|         | Forecast 1  | Forecast 2  | Forecast 3  |

The above table is a representation of how the results are stored. By fixing the spatial extent and aligning the forecasting timeframes, it is possible to compare the results of different models over time.

## Model Run
*A single execution of a model.*

## Model Result
*A single realization of the model result.*  

Models usually either define uncertainties by producing many realizations (Model Results), or by returning a single result with absolute uncertainties already specified.

## Time Step
*The time interval for which the Model Result is valid.*

## Grid Cell
*The spatial extent for which the Model Result is valid.*

## Result Type
*The representation of the forecasted seismicity, specified for the associated time step and grid cell.*

Seismicity can be represented in different ways:
- Catalog: A list of seismic events (earthquakes) with their properties.
- GRParameters: the parameters of the Gutenberg-Richter distribution.
- Bins: A histogram of the number of earthquakes in different magnitude bins.

## Model
*A model that can be run to produce Model Results.*
