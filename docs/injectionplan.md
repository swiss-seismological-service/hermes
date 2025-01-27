# Injectionplan Templates

A new way provide injectionplans has been developed, which allows for easier creation of injectionplans, as well as dynamic plans which are based on the latest measurements. This is achieved by using templates, from which the corresponding injectionplans will then be generated at runtime.

## Types of Injectionplan Templates

### Common Basic Parameters

- `borehole_name` the borehole name for which the injectionplan is created.
- `section_name` the section name for which the injectionplan is created.
- `type` the type of the template, explained below.
- `resolution` the resolution at which the injectionplan is created in seconds. E.g. 60 means that the injectionplan will have a data point every 60 seconds.
- `config` a dictionary with the specific configuration for the type of injectionplan template.


## `fixed`
The most basic type of template. Timestamps and corresponding values must be given. Values in between will be filled in at the required resolution.

```json
{
    "borehole_name": "16A-32",
    "section_name": "16A-32/section_02",
    "type": "fixed",
    "resolution": 60,
    "config": {
        "plan": [
            {
                "datetime": {
                    "value": "2022-04-19T14:01:00"
                },
                "topflow": {
                    "value": 0.04
                }
            },
            {
                "datetime": {
                    "value": "2022-04-19T14:05:00"
                },
                "topflow": {
                    "value": 0.045
                }
            },
            {
                "datetime": {
                    "value": "2022-04-19T14:08:30"
                },
                "topflow": {
                    "value": 0.05
                }
            }
        ],
        "interpolation": "none"
    }
}
```
### Parameters
- `plan` a list of dictionaries, each containing at least a timestamp and data point(s).
- `interpolation`: `"linear"`, `"none"` Whether the filled in values should be linearly interpolated between given data points or remain constant until the next data point.

## `constant`
The simplest form of an injectionplan template. A constant value will be assumed for the whole duration of the injectionplan.

```json
{
    "borehole_name": "16A-32",
    "section_name": "16A-32/section_02",
    "type": "constant",
    "resolution": 60,
    "config": {
        "plan": {
            "topflow": {
                "value": 0.04
            }
        }
    }
}
```

### Parameters
- `plan` a dictionary with the data value for each key.

## `multiply`
A template which dynamically creates the injectionplan. The latest injection rate at the time of the forecast is retrieved and multiplied by a constant factor.

```json
{
    "borehole_name": "16A-32",
    "section_name": "16A-32/section_02",
    "type": "multiply",
    "resolution": 60,
    "config": {
        "plan": {
            "topflow": {
                "value": 2,
            }
        },
        "lookback_window": 5,
        "mode": "mean"
    }
}
```

### Parameters
- `plan` a dictionary with the multiplication factor for each data point.
- `lookback_window` how many measurements should be included in the calculation of the latest injection rate. E.g. 5 means that the last 5 measurements will be used. `NaN` values are ignored, but counted towards the window size.
- `mode`: `"mean"`, `"ewma"` The mode of calculation for the latest injection rate.

