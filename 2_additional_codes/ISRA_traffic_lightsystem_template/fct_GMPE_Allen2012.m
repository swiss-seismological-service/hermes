function [fIobs,sigma_Allen,distance] = fct_GMPE_Allen2012(magnitude,distance)
% function [fIobs] = fct_GMPE_Allen2012(M_mang,GMPE_dist)
% -------------------------------------------------------------------------
% Ground Motion Prediction Equation (GMPE)
% "Intensity attenuation for active crustal regions", 
% Trevor I. Allen, David J. Wald, C. Bruce Worden, 2012
% 
%
% 
% Function written by Delano Landtwing, 29.06.2012, delanol@ethz.ch
%
% Incoming:
% magnitude      Earthquake Magnitude
% distance       distance [km] earthquake to current location
%                (hypocentral distances are used!)
%
% Outcoming:     
% fIobs          observed Mercalli Intensity at current location
% sigma_Allen    sigma/standard deviation
%
% Modifications:
% Since results are not reliable for distances <= 6km, all distances
% <= 6km will be set equal to 6km distance.

% Distance modification 
if distance <= 6
    distance = 6;
else
    distance = distance;
end

% constants
c0=2.085; 
c1=1.428;
c2=-1.402;
c4=0.078;
m1=-0.209;
m2=2.042;

Rm=m1+m2*exp(magnitude-5);

% sigma for hypocentral distances
s1 = 0.82;
s2 = 0.37; 
s3 = 22.9;


% GMPE itself
if distance<=50;
  Rm=m1+m2*exp(magnitude-5);
  fIobs=c0+c1*magnitude+c2*log(sqrt(distance^2+Rm^2));
else
  Rm=m1+m2*exp(m(k)-5);
  fIobs=c0+c1*magnitude+c2*log(sqrt(distance^2+Rm^2))+c4*log(distance/50);
end

% sigma
sigma_Allen = s1 + s2/(1+(distance/s3)^2);

