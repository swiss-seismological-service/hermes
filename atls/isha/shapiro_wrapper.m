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
catalogLP.y = atls_seismic_events_longitude - atls_injection_well_well_tip_lat;
catalogLP.z = atls_seismic_events_depth - atls_injection_well_well_tip_depth;
catalogLP.time = atls_seismic_events_date_time/86400 + datenum(1970,1,1);
catalogLP.mag = atls_seismic_events_magnitude;
catalogLP.mc = atls_mc;

% Hydraulic data
% - Convert flow rates to cumulative flow
% 
hydroLP.time = atls_hydraulic_events_date_time/86400 + datenum(1970,1,1);
hydroLP.cumflow = trapz(hydroLP.time, atls_hydraulic_events_flow_dh);
% FIXME: these should not be required and (can be deduced from the
% hydraulic history). Current values are hardcoded for the basel set
hydroLP.startPump = 733013.750011574;
hydroLP.shutIn = 733019.481261574;

% Other forecasting parameters
fcParams.endLP = atls_forecast_times(1);
fcParams.lenFP = atls_t_bin;
% FIXME: compute from the forecast_mag_range tuple
fcParams.fBinning = 1
% FIXME: pass expectedFlow down from ATLS
% calculate expected flow rate during the forecast period by
% computing the linear trend of the cumulative flow during the last 6h. 
% the gradient of this linear trend will give us the expected flow rate
indLP_trend           = (hydroLP.time >= fcParams.endLP - 0.25);
time_trend            = hydroLP.time(indLP_trend);
cumflow_trend         = hydroLP.cumflow(indLP_trend);
% calculate trend
trendCum              = trend(cumflow_trend);
fcParams.expectedFlow = (trendCum(end) - trendCum(1))/(time_trend(end) - time_trend(1));


% Setup the grid for the spatial forecast resolution
% TODO: this should probably be configurable in ATLS
grid.voxelLen = 100;
[grid.centers, ~] = gridRes([-2000, 2000], grid.voxelLen);


%% Run the model
forecast = forecastShapiroSpatial(catalogLP, hydroLP, fcParams, grid)