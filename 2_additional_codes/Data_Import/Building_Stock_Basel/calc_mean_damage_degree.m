% Synthesis code for loss calculations
%  without function-architecture yet
%  Date of last changes: 17.04.2012
%  Delano Landtwing, delanol@ethz.ch

clear all; clc;

% import data
% load build. stock Basel, according to SERIANEX report (Risk-UE classification)
load bs_basel_ser.mat
%  load vulnerability indexes
vuln_typ_ser=importdata('d:\3_ETH\1_Masterarbeit\Building_Stock_Basel\vulnerability_classes_serianex_typology.csv');
vuln_vi_base_ser=importdata('d:\3_ETH\1_Masterarbeit\Building_Stock_Basel\vulnerability_classes_serianex_vi_base.csv');


% Seismic Hazard, Part Banu
%  to be done...


% GMPE - Intensity calc. for all settlements

%  1    - Distance Calculation (Earthquake - Settlement)
%  1.1  - Location Drilling Site = Quake (source coord.: Wikipedia)
xquake = 611825;
yquake = 270532;

%  1.2  - Calculate Distances Quake - Settlements, storage in BS maybe
%  different storage in order to make it more independent?
dist = zeros(size(bs_basel_ser,2),1);
for i = 1:size(bs_basel_ser,2)
    dist(i,1) = sqrt((xquake-bs_basel_ser{i}.xkoordCH)^2+(xquake-bs_basel_ser{i}.xkoordCH)^2);
end

%  1.3  - GMPE itself (here just assumptions, needs to be replaced...)
mmi = 12;
for i=1:size(bs_basel_ser,2)
    bs_basel_ser{i}.mmi = mmi - rand;
end

[fMDG] = mean_damage_degree(bs_basel_ser,vuln_vi_base_ser);
figure(1)
pcolor(fMDG);colorbar;axis ij;

% %  Calculation of Mean Damage Grade (MDG), according to local intensities
% %   Formula:    fMDG=2.5*(1+tanh((fIobs+6.25*mV(:,iV)-13.1)/2.3));
% %   Giovinnazzi, 2005
% %   Reduction factor: see SERIANEX, AP5000, p.97)
% 
% %   Calculation of reduction factor (SERIANEX, AP5000, p. 97)
% Int     = [0,1,2,3,6,7,8,9,10,11,12];                   % Intensity scale 1-12
% redfact = [0,0,0,0,1,1,1,1,1,1,1];  % given reduction factor
% 
% %   Interpolation of missing gap (b/w Int. 3 and 6)
% Xvuln = 3:0.1:6;
% Yvuln = interp1(Int,redfact,Xvuln,'linear');
% ppvuln = interp1(Int,redfact,'linear','pp'); % piecewise polynomial for interpolation
% Yvuln = Yvuln.^2;                                  % cubic of linear interpol. -> SERIANEX
% 
% 
% % % Plot of Reduction factor
% % figure(1)
% % plot(Xvuln,Yvuln);hold on;
% % plot(Int,redfact,'r*')
% % title('Reduction Factor for vulnerability curve');xlabel('Intensity');ylabel('Reduction factor');
% 
% % prelocation of variables
% fIobs = zeros(size(bs_basel_ser,2),1);
% fMDG = zeros(size(vuln_vi_base_ser,1),size(bs_basel_ser,2));
% fMDG_r = zeros(size(vuln_vi_base_ser,1),size(bs_basel_ser,2));
% for i=1:size(vuln_vi_base_ser,1)
%     for j=1:size(bs_basel_ser,2)
%         fIobs(j) = bs_basel_ser{j}.mmi;
%         if fIobs(j) <= 3
%             fMDG(i,j)=0;
%         else
%             if fIobs(j) >= 6
%                 fMDG(i,j)=2.5*(1+tanh((fIobs(j)+6.25*vuln_vi_base_ser(i)-13.1)/2.3));
%                 fMDG_r(i,j) = round(fMDG(i,j).*100)/100; % round to 2 figures after comma, needed?
%             else
%                 fMDG(i,j)=2.5*(1+tanh((fIobs(j)+6.25*vuln_vi_base_ser(i)-13.1)/2.3));
%                 fMDG_r(i,j) = round(fMDG(i,j).*100)/100; % round to 2 figures after comma, needed?
%                 % multiplication factor
%                 fMDG(i,j)=fMDG(i,j)*(ppval(ppvuln,fIobs(j)).^2); % cubic of linear interpol. -> SERIANEX
%             end
%         end 
%     end
% end


% % going through all intensity levels (for all vuln. classes and fIobs
% 1-12)
% fIobs = 1:0.25:12;
% for i=1:size(vuln_vi_base_ser,1)
%     for j=1:size(fIobs,2);
%     fMDG(i,j)=2.5*(1+tanh((fIobs(j)+6.25*vuln_vi_base_ser(i)-13.1)/2.3));
%     end
% end


% Mean Damage Ratio Calculation
%  based on Resonance average curve from Cochrane and Shaad (1992), adapted
%  by SERIANEX (AP5000, page 94, 8.4 - Cost estimation) = Resonance expert
%  judgement curve
%  Damage grade:                    0   1   2   3   4   5  
%  % of reference value to rebuild: 0%  2%  15% 55% 91% 100%
%  in our case: Insured Value Loss (IVL)

% known fixpoints
repcost = [0;.02;.15;.55;.91;1];
damagedeg = [0;1;2;3;4;5];

% Interpolation b/w known fixpoints 
XI = 0:0.01:5;
YI = interp1(damagedeg,repcost,XI,'cubic');

% piecewise polynomial
ppdamage = interp1(damagedeg,repcost,'cubic','pp');

% Mean Damage Ratio Calculation for all settlements and vuln. classes

fMDR = zeros(size(fMDG,1),size(fMDG,2));
for i = 1:size(fMDG,1)
    for j = 1:size(fMDG,2)
        fMDR(i,j) = ppval(ppdamage,fMDG(i,j));
    end
end


% Plots
figure (2)
% Mean Damage Grade vs. Mean Damage Ratio
subplot(2,1,1)
plot(XI,YI); hold on;
plot(damagedeg,repcost,'*');title('Mean Damage Grade vs. Mean Damage Ratio');
xlabel('Mean Damage Grade');ylabel('Mean Damage Ratio [%]'); hold on;

% First settlement as example
subplot(2,1,2)
plot(fMDR(:,1),'r*');title('Vuln. Class vs. Mean Damage Ratio');
xlabel('Vuln. Class');ylabel('Mean Damage Ratio');
