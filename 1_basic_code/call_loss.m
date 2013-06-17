%% ISRA calculation
%  this script calls deterministic and probabilistic loss assessment for
%  induced seismicity
%
%  Date of last change: 24.08.2012
%  Delano Landtwing, delanol@ethz.ch
clear all;clc;clf;close all;


%% Module selection
%  1    Switch of methods (s... for switch)
%  1.1  IPE/GMPE (Ground Motion Prediction Equation
sGMPE=  'Allen-2012'; % ECOS-02, ECOS-02new, ECOS-09, Allen-2012
%  1.2  Site Amplification yes or no?
sAMPL=  'AMPyes';     % yes or no
%  1.3  Distribution Functions
sDISTR= 'BinPDF';     % BinPDF, BetaPDF
%  1.4  Cost Functions
sCOST=  'SED_Del';    % Expert_SER, Cochrane92, Risk_UE, SED_Del

%% Mmin/Mmax for deterministic calc.
M_Mmin =  0.9;    % Magnitude of completeness
M_dm =    0.1;    % Magnitude increment
M_Mmax =  7;    % Mmax
M_Magn = M_Mmin:M_dm:M_Mmax;


%% Load forecast rates
load com.mat            % combined model, Banu et al, 2012
model = com;
% load com_back.mat
% load all_models.mat;
% 
% SRR=all_models.SR;
% r22=all_models.R2;
% e44=all_models.E4;
% e55=all_models.E5;
% com=all_models.COMB;
% obs_rate=all_models.obs;



%% Deterministic and Probabilistic calculation for different Mmax
%  important: definitions of b-values and the time period for the hazard
%  calculations need to made in the called functions!

Mmin=0.9; Mmax=3.7;
[M_Magn1,IVL_tot1,IVL_tot_PROB_norm1,tot_loss1,prob1,losses1,exrate1,casualties1,DG1]=calc_loss(M_Mmin,M_dm,M_Mmax,sGMPE,sAMPL,sDISTR,sCOST,model,Mmin,Mmax);

Mmin=0.9; Mmax=5;
[M_Magn2,IVL_tot2,IVL_tot_PROB_norm2,tot_loss2,prob2,losses2,exrate2,casualties2,DG2]=calc_loss(M_Mmin,M_dm,M_Mmax,sGMPE,sAMPL,sDISTR,sCOST,model,Mmin,Mmax);

Mmin=0.9; Mmax=7;
[M_Magn3,IVL_tot3,IVL_tot_PROB_norm3,tot_loss3,prob3,losses3,exrate3,casualties3,DG3]=calc_loss(M_Mmin,M_dm,M_Mmax,sGMPE,sAMPL,sDISTR,sCOST,model,Mmin,Mmax);


%% result SAVING
save prob_ECOS09_diffMmax_haz6_period.mat
% save prob_Allen2012_diffMmax_haz6_periodback.mat
% save prob_ECOS09_diffMmax_haz6_oneday.mat
% save prob_Allen2012_diffMmax_haz6_period.mat
% save prob_Allen2012_diffMmax_haz6_periodMEAN4.mat
% save prob_Allen2012_diffMmax_haz6_oneday.mat

% save prob_ECOS09_diffMmax_haz6_periodMEAN4.mat
% save prob_ECOS09_diffMmax_haz6_periodback.mat
% save prob_ECOS09_diffMmax_haz6_onedayTEST2.mat
% save prob_Allen2012_diffMmax_haz6_periodTEST2.mat
% save prob_Allen2012_diffMmax_haz6_onedayTEST2.mat


%% OUTPUT PLOTS
% colordefinitions
c_dark  =   [ 53,  52,  50] ./ 255;
c_gray  =   [ 78,  77,  74] ./ 255;
c_lgreen =  [148, 186, 101] ./ 255;
c_dgreen =  [0 0.498039215803146 0];
c_lblue =   [ 39, 144, 176] ./ 255;
c_dblue =   [ 43,  78, 114] ./ 255;
c_red =     [255,   0,   0] ./ 255;
c_lred =    [255, 102,   0] ./ 255; 
c_dlred =   [1 0.200000002980232 0];
c_orange =  [255, 153,   0] ./ 255;
c_yellow =  [204, 255,   0] ./ 255;

% basic plot definitions
line_w = 2.5;       % linewidth


%% Probabilistic Loss Curve: IVL
figure(1);
loglog(IVL_tot1(:,3),prob1,'LineWidth',line_w,'LineStyle','-','Color',c_dblue,...
    'DisplayName','Mmax 3.7');  hold on;
loglog(IVL_tot2(:,3),prob2,'LineWidth',line_w,'LineStyle','--','Color',c_dblue,...
    'DisplayName','Mmax 5');  hold on;
loglog(IVL_tot3(:,3),prob3,'LineWidth',line_w,'LineStyle',':','Color',c_dblue,...
    'DisplayName','Mmax 7');  hold on;

set(gca,'LineWidth',2,'FontSize',24,'FontWeight','normal','FontName','Times')
set(get(gca,'XLabel'),'String','Insured Value Loss (CHF)','FontSize',24,'FontName','Times')
set(get(gca,'YLabel'),'String','Exceedance Rate','FontSize',24,'FontName','Times')
set(get(gca,'Title'),'String','Probabilistic Loss Curve for IVL','FontSize',24,'FontName','Times')
axis([10^6 10^11 10^-4 1])
legend('show');


%% Probabilistic Loss Curve: num. of houses in DG1
figure(2);
loglog(DG1(:,2,3),prob1,'LineWidth',line_w,'LineStyle','-','Color',c_dblue,...
    'DisplayName','Mmax 3.7');  hold on;
loglog(DG2(:,2,3),prob2,'LineWidth',line_w,'LineStyle','--','Color',c_dblue,...
    'DisplayName','Mmax 5');  hold on;
loglog(DG3(:,2,3),prob3,'LineWidth',line_w,'LineStyle',':','Color',c_dblue,...
    'DisplayName','Mmax 7');  hold on;

set(gca,'LineWidth',2,'FontSize',24,'FontWeight','normal','FontName','Times')
set(get(gca,'XLabel'),'String','number of houses in DG1','FontSize',24,'FontName','Times')
set(get(gca,'YLabel'),'String','Exceedance Rate','FontSize',24,'FontName','Times')
set(get(gca,'Title'),'String','Probabilistic Loss Curve for number of houses in DG1','FontSize',24,'FontName','Times')
xlim([10^1 10^5])
ylim([10^-4 1])
legend('show');


%% Probabilistic Loss Curve: casualties
figure(3);
loglog(casualties1(:,5,3),prob1,'LineWidth',line_w,'LineStyle','-','Color',c_dblue,...
    'DisplayName','Mmax 3.7');  hold on;
loglog(casualties2(:,5,3),prob2,'LineWidth',line_w,'LineStyle','--','Color',c_dblue,...
    'DisplayName','Mmax 5');  hold on;
loglog(casualties3(:,5,3),prob3,'LineWidth',line_w,'LineStyle',':','Color',c_dblue,...
    'DisplayName','Mmax 7');  hold on;

set(gca,'LineWidth',2,'FontSize',24,'FontWeight','normal','FontName','Times')
set(get(gca,'XLabel'),'String','num. casualty degree 5','FontSize',24,'FontName','Times')
set(get(gca,'YLabel'),'String','Exceedance Rate','FontSize',24,'FontName','Times')
set(get(gca,'Title'),'String','Probabilistic Loss Curve for casualties','FontSize',24,'FontName','Times')
xlim([10^-1 100])
ylim([10^-4 1])
legend('show');
