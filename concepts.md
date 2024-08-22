# Conepts

The general concepts of the software's domain are described here.

## Project:
*I want to run models and do forecasts for a certain reason and use the results together, eg. in the same frontend*

| Question                                        | field(s)             |
| ----------------------------------------------- | -------------------- |
| Give your project a name.                       | name                 |
| Describe your Project.                          | description          |
| During which time frame is this project active. | start and/or enddate |


## Forecast Series:
*I'd like to do forecasts at multiple points in time, using multiple models, and be able to compare them*

| Question                                                                    | field(s)                               |
| --------------------------------------------------------------------------- | -------------------------------------- |
| Give this series a name.                                                    | name                                   |
| Are there any forecasts scheduled, paused, .... ?                           | status                                 |
| What is the spatial extent for which the forecasts are made?                | bounding_polygon, depth_max, depth_min |
| What data is needed for the models to run?                                  | seismicityobservation_required         |
|                                                                             | injectionobservation_required          |
|                                                                             | injectionplan_required                 |
| Where are the data sources?                                                 | fdsnws_url, hydws_url                  |
| From which date should we start using the input data?                       | observation_starttime                  |
| Should we always use all available input data or only until a certain date? | observation_endtime                    |
| **Scheduling**: From which date should we start running forecasts?          | forecast_starttime                     |
| **Scheduling**: Until which date should we run the forecasts?               | forecast_endtime                       |
| **Scheduling**: How often should we run the forecasts?                      | forecast_interval                      |
| **Scheduling**: How long should each forecast be?                           | forecast_duration                      |

### Scheduling combinations

#### forecast_starttime, forecast_endtime, forecast_interval
- start running forecasts at forecast_starttime 
- run forecasts every forecast_interval until forecast_endtime
- each forecast lasts from when it was started until forecast_endtime

#### forecast_starttime, forecast_endtime, forecast_interval, forecast_duration
- start running forecasts at forecast_starttime
- run forecasts every forecast_interval until forecast_endtime
- each forecast lasts forecast_duration

#### forecast_starttime, forecast_interval, forecast_duration
- start running forecasts at forecast_starttime
- run forecasts every forecast_interval
- each forecast lasts forecast_duration
- run forecasts until manually stopped


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