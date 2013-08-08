function [fIobs] = fct_GMPE_ECOS_02_new(magnitude,distance)
% function [fIobs] = fct_fct_GMPE_ECOS-02_new(M_mang,GMPE_dist)
% -------------------------------------------------------------------------
% Ground Motion Prediction Equation (GMPE)
% Published by SED (Swiss Seismological Service) in ECOS-02 (page 31),
% corrected "Parameterization of historical earthquakes in Switzerland,
% 2011"
% this function is just suitable for quake-location distances below 70 km
% and shallow earthquakes
% 
% Formula used:
% fIobs = a70*magnitude-b70-c70*distance
%
% 
% Function written by Delano Landtwing, 12.06.2012, delanol@ethz.ch
%
% Incoming:
% magnitude      Earthquake Magnitude
% distance       distance [km] earthquake to current location
%
% Outcoming:     
% fIobs          observed Mercalli Intensity at current location


%% Constants for distances lower than 70 km
a70 = 1.5248;
b70 = 0.9079;
c70 = 0.043;

%% GMPE itself
fIobs = a70*magnitude-b70-c70*distance;