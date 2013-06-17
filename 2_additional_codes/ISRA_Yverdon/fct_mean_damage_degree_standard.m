function [fMDG] = fct_mean_damage_degree(fIobs,vuln_index)
% function [fMDG] = fct_mean_damage_degree(fIobs,vuln_index)
% -------------------------------------------------------------------------
% Calculation of Mean Damage Grade (MDG), using intensities and
% vulnerability indexes
% Formula:    fMDG=2.5*(1+tanh((fIobs+6.25*mV(:,iV)-13.1)/2.3));
% Giovinnazzi, 2005
% Reduction factor: see SERIANEX, AP5000, p.97)
% Function written by Delano Landtwing, 16.05.2012, delanol@ethz.ch
%
% Incoming:
% fIobs          matrix containing observed intensities at settlements
% vuln_index     vulnerability indexes for diff. vuln. classes
%
% Outcoming:
% fMDG_r:   i x j matrix containing Mean Damage Degree
%           i = vulnerability classes
%           j = settlements




% Calculation of reduction factor (SERIANEX, AP5000, p. 97)
% Reduction factor = 0 for intensities b/w 0 and 3
% Reduction factor = 1 for intensities b/w 6 and 12
% Reduction factor = square of the linear equation b/w int. 3 and 6
Int     = [0,1,2,3,6.5,7,8,9,10,11,12];   % Intensity scale 1-12
redfact = [0,0,0,0,1,1,1,1,1,1,1];      % given reduction factor

% Interpolation of missing gap (b/w Int. 3 and 6)
Xvuln = 3:0.1:6.5;
Yvuln = interp1(Int,redfact,Xvuln,'linear');
ppvuln = interp1(Int,redfact,'linear','pp'); % piecewise polynomial for interpolation
Yvuln = Yvuln.^2;                                  % cubic of linear interpol. -> SERIANEX


% calculation of MDG itself
if fIobs <= 3
    fMDG=0;
else
    if fIobs >= 6.5
        fMDG=2.5*(1+tanh((fIobs+6.25*vuln_index-13.1)/2.3));
    else
        fMDG=2.5*(1+tanh((fIobs+6.25*vuln_index-13.1)/2.3));
        % multiplication factor
        fMDG=fMDG*(ppval(ppvuln,fIobs).^2); % cubic of linear interpol. -> SERIANEX
    end
end 



