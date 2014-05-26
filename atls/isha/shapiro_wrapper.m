
% Matlab wrapper for the spatial shapiro model
%
% Input variables are received from ATLS as simple arrays. 
% The wrapper collects the input variables in structs that can
% be passed to the model code.

% Add the path to the model code
addpath(fullfile('..', 'external', 'shapiro_spatial'))


%% Compile input data sets
    
% Seismic event data
% - convert unix time stamps to datenums
% - convert event location to relative locations (rel. to well tip)
catalogLP.x = atls_seismic_events_longitude - atls_injection_well_well_tip_lon;
catalogLP.y = atls_seismic_events_latitude - atls_injection_well_well_tip_lat;
catalogLP.z = atls_seismic_events_depth - atls_injection_well_well_tip_depth;
catalogLP.time = atls_seismic_events_date_time/86400 + datenum(1970,1,1);
catalogLP.mag = atls_seismic_events_magnitude;
catalogLP.mc = atls_mc;

% Hydraulic data
% - Convert flow rates to cumulative flow
% - Convert liters -> m3
hydroLP.time = atls_hydraulic_events_date_time/86400 + datenum(1970,1,1);
hydroLP.cumflow = cumtrapz(hydroLP.time, atls_hydraulic_events_flow_dh * 60 * 24) / 1000;
hydroLP.startPump = hydroLP.time(find(hydroLP.cumflow > 0, 1));

% Other forecasting parameters
fcParams.endLP = atls_forecast_times(1)/86400 + datenum(1970,1,1);
fcParams.lenFP = atls_t_bin;
% FIXME: compute from the forecast_mag_range tuple
fcParams.fBinning = 0.1;
fcParams.expectedFlow = atls_expected_flow;
% FIXME: justify this assumption (or don't make it)
fcParams.mMax = 5.0;



% Setup the grid for the spatial forecast resolution
% TODO: this should probably be configurable in ATLS
grid.voxelLen = 100.0;
[grid.centers, ~] = gridRes([-2000.0, 2000.0], grid.voxelLen);


%% Run the model
forecast = forecastShapiroSpatial(catalogLP, hydroLP, fcParams, grid)