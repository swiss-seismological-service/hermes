
% Matlab wrapper for the spatial shapiro model
%
% Input variables are received from ATLS as simple arrays. 
% The wrapper collects the input variables in structs that can
% be passed to the model code.
%
% All input variables from ATLS are prefixed with atls_
% All variables which are read back are prefixed with forecast_


% Add the path to the model code
addpath(fullfile('..', 'external', 'shapiro_spatial'))

% Initialize
forecast_success = false;
forecast_no_result_reason = 'An error occured while running matlab code';
% min inflow [l/min] - should correspond to the value defined in the model
% TODO: it would be more robust if we passed this to the model
STIMULATION_THRESHOLD = 1.0;

% TODO: for some reason the basel project has all flow data in xt
% (dh would probably make more sense).
flow_rate = atls_hydraulic_events_flow_xt;

%% Compile input data sets

% The shapiro model does not produce meaningful results before the injection
% starts
if (sum(flow_rate)) < STIMULATION_THRESHOLD
    forecast_no_result_reason = 'Cumulative flow is zero';
    return
end
    
% Seismic event data
% - convert event location to relative locations (rel. to well tip)
% - convert unix time stamps to datenums
x = atls_seismic_events_x;
y = atls_seismic_events_y;
wx = atls_injection_well_well_tip_x;
wy = atls_injection_well_well_tip_y;
                          
catalogLP.x = x - wx;
catalogLP.y = y - wy;
catalogLP.z = atls_seismic_events_z - atls_injection_well_well_tip_z;
catalogLP.time = atls_seismic_events_date_time/86400 + datenum(1970,1,1);
catalogLP.mag = atls_seismic_events_magnitude;
catalogLP.mc = atls_mc;

% Hydraulic data
% - Convert flow rates to cumulative flow
% - Convert liters -> m3
hydroLP.time = atls_hydraulic_events_date_time/86400 + datenum(1970,1,1);
hydroLP.cumflow = cumtrapz(hydroLP.time, flow_rate * 60 * 24) / 1000;
hydroLP.startPump = hydroLP.time(find(hydroLP.cumflow > 0, 1));


% Other forecasting parameters
% - Convert lenFP from hours to days
% - Convert expected_flow from l/min to m3/d
fcParams.endLP = atls_forecast_times(1)/86400 + datenum(1970,1,1);
fcParams.lenFP = atls_t_bin / 24.0;
% FIXME: compute from the forecast_mag_range tuple
fcParams.fBinning = 0.1;
fcParams.expectedFlow = atls_expected_flow / 1000 * 60*24 ;
% FIXME: justify this assumption (or don't make it)
fcParams.mMax = 5.0;



% Setup the grid for the spatial forecast resolution
% TODO: this should probably be configurable in ATLS
grid.voxelLen = 100.0;
[grid.centers, ~] = gridRes([-2000.0, 2000.0], grid.voxelLen);


%% Run the model
forecast = forecastShapiroSpatial(catalogLP, hydroLP, fcParams, grid)

%% Unpack the results for reding back in ATLS
forecast_success = true;
forecast_numev = forecast.NUMEV;
forecast_vol_rates = forecast.SumVolPdfWtExpNorm
%forecast_vol_rates = forecast.SumVolPdfWtSSNorm
%forecast_vol_rates = forecast.SumVolPdfWtH1Norm

%% Output a summary for this run (for testing only)
% run_data = {datestr(fcParams.endLP), fcParams.lenFP, fcParams.expectedFlow, hydroLP.cumflow(end), datestr(hydroLP.startPump), numel(catalogLP.mag), forecast.post, forecast.NUMEV};
% first = true;
% if exist('run_summary.csv')
%   first = false;
% end
% fid = fopen('run_summary.csv','a');
% if first
%     headers = {'endLP', 'lenFP', 'expFlow', 'cumFlow', 'startPump', 'numEvents', 'fcPost', 'fcNumEvents'};
%     fprintf(fid,'%20s, %10s, %12s, %12s, %20s, %10s, %10s, %12s\n',headers{:});
% end
% fprintf(fid,'%20s, %10f, %12f, %12f, %20s, %10d, %10d, %12f\n', run_data{:});
% fclose(fid)
