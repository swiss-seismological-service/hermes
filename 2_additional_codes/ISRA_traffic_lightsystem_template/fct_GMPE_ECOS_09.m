function [fIobs] = fct_GMPE_ECOS_09(magnitude,distance,depth_quake)
% function [fIobs] = fct_fct_GMPE_ECOS-09(M_mang,GMPE_dist)
% -------------------------------------------------------------------------
% Ground Motion Prediction Equation (GMPE)
% Published by SED (Swiss Seismological Service) in ECOS-09 and 
% "Parameterization of historical earthquakes in Switzerland, 2011"
% this function is just suitable for quake-location distances below 70 km
% and shallow earthquakes
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
alpha =         0.7317;
beta =          1.2567;
a =             -0.69182;
b =             -0.00084;
c0 = beta;
c1 = alpha;
c2 = -alpha*a;
c3 = -alpha*b;
   
%% GMPE itself
fIobs=(-c2*log(distance/30)-c3*(distance-30)-c0+magnitude)/c1;  
 