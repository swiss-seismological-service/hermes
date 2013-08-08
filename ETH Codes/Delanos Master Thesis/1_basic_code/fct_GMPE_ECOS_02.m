function [fIobs] = fct_GMPE_ECOS_02(magnitude,distance)
% function [fIobs] = fct_fct_GMPE_ECOS-02(M_mang,GMPE_dist)
% -------------------------------------------------------------------------
% Ground Motion Prediction Equation (GMPE)
% Published by SED (Swiss Seismological Service) in ECOS-02 (page 31)
% this function is just suitable for quake-location distances below 70 km
% and shallow earthquakes
% 
% Formula used:
% fIobs = a70*magnitude-b70-c70*distance
%
% 
% Function written by Delano Landtwing, 16.05.2012, delanol@ethz.ch
%
% Incoming:
% magnitude      Earthquake Magnitude
% distance       distance [km] earthquake to current location
%
% Outcoming:     
% fIobs          observed Mercalli Intensity at current location


%% Constants for distances lower than 70 km
a70 = 1.27;
b70 = -0.096;
c70 = 0.043;
a200 = 1.27;
b200 = 1.93;
c200 = 0.0064;

%% GMPE itself
fIobs = a70*magnitude-b70-c70*distance;
