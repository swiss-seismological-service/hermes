clear all;close all;clf;clc;

load case_yverdon_Mmax37prob_45det_SiteAmp.mat
prob1 = prob1(1,:);

% define thresholds
prob_threshold=0.1;
CAS_threshold=1;
DG_threshold=25;
CD=5;   % defining casualty degree to look at
iDG=2;  % DG of houses to look at

exc_prob = num2str(100*prob_threshold);
name_title=['values for ' exc_prob '% exceedance probability'];


% Iamp = 0
[fixed_IVL_prob1] = calc_IVL_prob_threshold_Yverdon(IVL_tot1_final,prob1,prob_threshold);
[fixed_DG_prob1] = calc_DG_prob_threshold_Yverdon(num_DG1_final,prob1,prob_threshold,iDG);
[fixed_DG_1] = calc_DG_threshold_Yverdon(num_DG1_final,prob1,DG_threshold,iDG);
[fixed_CAS1] = calc_CAS_threshold_Yverdon(mCasSum1_final,prob1,CAS_threshold,CD);

% Iamp = 0.25
[fixed_IVL_prob2] = calc_IVL_prob_threshold_Yverdon(IVL_tot2_final,prob1,prob_threshold);
[fixed_DG_prob2] = calc_DG_prob_threshold_Yverdon(num_DG2_final,prob1,prob_threshold,iDG);
[fixed_DG_2] = calc_DG_threshold_Yverdon(num_DG2_final,prob1,DG_threshold,iDG);
[fixed_CAS2] = calc_CAS_threshold_Yverdon(mCasSum2_final,prob1,CAS_threshold,CD);

% Iamp = 0.35
[fixed_IVL_prob3] = calc_IVL_prob_threshold_Yverdon(IVL_tot3_final,prob1,prob_threshold);
[fixed_DG_prob3] = calc_DG_prob_threshold_Yverdon(num_DG3_final,prob1,prob_threshold,iDG);
[fixed_DG_3] = calc_DG_threshold_Yverdon(num_DG3_final,prob1,DG_threshold,iDG);
[fixed_CAS3] = calc_CAS_threshold_Yverdon(mCasSum3_final,prob1,CAS_threshold,CD);

% Iamp = 0.5
[fixed_IVL_prob4] = calc_IVL_prob_threshold_Yverdon(IVL_tot4_final,prob1,prob_threshold);
[fixed_DG_prob4] = calc_DG_prob_threshold_Yverdon(num_DG4_final,prob1,prob_threshold,iDG);
[fixed_DG_4] = calc_DG_threshold_Yverdon(num_DG4_final,prob1,DG_threshold,iDG);
[fixed_CAS4] = calc_CAS_threshold_Yverdon(mCasSum4_final,prob1,CAS_threshold,CD);

% Iamp = 0.75
[fixed_IVL_prob5] = calc_IVL_prob_threshold_Yverdon(IVL_tot5_final,prob1,prob_threshold);
[fixed_DG_prob5] = calc_DG_prob_threshold_Yverdon(num_DG5_final,prob1,prob_threshold,iDG);
[fixed_DG_5] = calc_DG_threshold_Yverdon(num_DG5_final,prob1,DG_threshold,iDG);
[fixed_CAS5] = calc_CAS_threshold_Yverdon(mCasSum5_final,prob1,CAS_threshold,CD);


%% Prob. Plot: Mmax 3.7
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
c_beige =   [.95, .87, .73];


%% plot IVL as a function of distance
Magnitude_low =3.0;
Magnitude   = 3.2;
iMag_int_low=floor((Magnitude_low-0.9)*10+1);
iMag_int=floor((Magnitude-0.9)*10+1);

line_w=2;

%% IVL
figure(1)
% Plot Font
SetPlotFont('Helvetica', 15);
set(gcf, 'renderer', 'painters');   % vector based renderer

set(gcf, 'renderer', 'painters');   % vector based renderer
plot(xquake./1000,fixed_IVL_prob1(:,3)./10^6,'Color',c_lblue,'LineWidth',line_w,'LineStyle','-',...
    'DisplayName',  'I_a_m_p = 0');hold on
plot(xquake./1000,fixed_IVL_prob2(:,3)./10^6,'Color',c_orange,'LineWidth',line_w,...
    'DisplayName',  'I_a_m_p = 0.25');hold on
plot(xquake./1000,fixed_IVL_prob3(:,3)./10^6,'Color',c_lred,'LineWidth',line_w,...
    'DisplayName',  'I_a_m_p = 0.35');hold on
plot(xquake./1000,fixed_IVL_prob4(:,3)./10^6,'Color',c_red,'LineWidth',line_w,...
    'DisplayName',  'I_a_m_p = 0.5');hold on
plot(xquake./1000,fixed_IVL_prob5(:,3)./10^6,'Color',c_dark,'LineWidth',line_w,...
    'DisplayName',  'I_a_m_p = 0.75');hold on

title(name_title);
xlabel('distance [km]');ylabel('Insured Value Loss IVL [Mio. CHF]');
legend('show','Location','NorthEast');

% axis config
% xlim([2 5]);
% ylim([10^4 10^10]);

% configure axes
set(gca, ...
    'YDir'         , 'normal' , ...    % plot upside down   
    'Box'          , 'off'     , ...    % turn off box around figure
    'XAxisLocation', 'bottom'     , ...    % place x axis on top
    'TickDir'      , 'out'      , ...    % tickmarks inside
    'TickLength'   , [.02 .02 ], ...    % make ticks a bit longer
    'XMinorTick'   , 'off'      , ...    % turn on minor ticks
    'YMinorTick'   , 'on'      , ...
    'XTick'        , [0:5:20],...
...%     'YTick'        , [0.25:0.25:1.75],...
    'XGrid'        , 'on'      , ...    % turn on y-grid
    'YGrid'        , 'on'     , ...
    'LineWidth'    , .5         );      % make axis thinner

%% MATLAB PLOTTING PACKAGE
% set the plot size to 20x15cm for exporting
% SetPlotSize([20 15],'centimeters');

% Save the plot into a postscript file
% and fix the line definitions
% WritePlot('plot_prob_IVL_Yverdon.ai');

%% DG1
figure(2)
% Plot Font
SetPlotFont('Helvetica', 15);
set(gcf, 'renderer', 'painters');   % vector based renderer

set(gcf, 'renderer', 'painters');   % vector based renderer
plot(xquake./1000,fixed_DG_prob1(:,3),'Color',c_lblue,'LineWidth',line_w,'LineStyle','-',...
    'DisplayName',  'I_a_m_p = 0');hold on
plot(xquake./1000,fixed_DG_prob2(:,3),'Color',c_orange,'LineWidth',line_w,...
    'DisplayName',  'I_a_m_p = 0.25');hold on
plot(xquake./1000,fixed_DG_prob3(:,3),'Color',c_lred,'LineWidth',line_w,...
    'DisplayName',  'I_a_m_p = 0.35');hold on
plot(xquake./1000,fixed_DG_prob4(:,3),'Color',c_red,'LineWidth',line_w,...
    'DisplayName',  'I_a_m_p = 0.5');hold on
plot(xquake./1000,fixed_DG_prob5(:,3),'Color',c_dark,'LineWidth',line_w,...
    'DisplayName',  'I_a_m_p = 0.75');hold on

title(name_title);
xlabel('distance [km]');ylabel('number of houses in DG1');
legend('show','Location','NorthEast');

% axis config
% xlim([2 5]);
% ylim([10^4 10^10]);

% configure axes
set(gca, ...
    'YDir'         , 'normal' , ...    % plot upside down   
    'Box'          , 'off'     , ...    % turn off box around figure
    'XAxisLocation', 'bottom'     , ...    % place x axis on top
    'TickDir'      , 'out'      , ...    % tickmarks inside
    'TickLength'   , [.02 .02 ], ...    % make ticks a bit longer
    'XMinorTick'   , 'off'      , ...    % turn on minor ticks
    'YMinorTick'   , 'on'      , ...
    'XTick'        , [0:5:20],...
...%     'YTick'        , [0.25:0.25:1.75],...
    'XGrid'        , 'on'      , ...    % turn on y-grid
    'YGrid'        , 'on'     , ...
    'LineWidth'    , .5         );      % make axis thinner

%% MATLAB PLOTTING PACKAGE
% set the plot size to 20x15cm for exporting
% SetPlotSize([20 15],'centimeters');

% Save the plot into a postscript file
% and fix the line definitions
% WritePlot('plot_prob_DG_Yverdon.ai');


%% Casualties (exceeding 1 casualty)
figure(3)
% Plot Font
SetPlotFont('Helvetica', 15);
set(gcf, 'renderer', 'painters');   % vector based renderer

set(gcf, 'renderer', 'painters');   % vector based renderer
% plot(xquake./1000,fixed_CAS1(:,3),'Color',c_lblue,'LineWidth',line_w,'LineStyle','-',...
%     'DisplayName',  'I_a_m_p = 0');hold on
% plot(xquake./1000,fixed_CAS2(:,3),'Color',c_orange,'LineWidth',line_w,...
%     'DisplayName',  'I_a_m_p = 0.25');hold on
% plot(xquake./1000,fixed_CAS3(:,3),'Color',c_lred,'LineWidth',line_w,...
%     'DisplayName',  'I_a_m_p = 0.35');hold on
% plot(xquake./1000,fixed_CAS4(:,3),'Color',c_red,'LineWidth',line_w,...
%     'DisplayName',  'I_a_m_p = 0.5');hold on
% plot(xquake./1000,fixed_CAS5(:,3),'Color',c_dark,'LineWidth',line_w,...
%     'DisplayName',  'I_a_m_p = 0.75');hold on

semilogy(xquake./1000,fixed_CAS1(:,3),'Color',c_lblue,'LineWidth',line_w,'LineStyle','-',...
    'DisplayName',  'I_a_m_p = 0');hold on
semilogy(xquake./1000,fixed_CAS2(:,3),'Color',c_orange,'LineWidth',line_w,...
    'DisplayName',  'I_a_m_p = 0.25');hold on
semilogy(xquake./1000,fixed_CAS3(:,3),'Color',c_lred,'LineWidth',line_w,...
    'DisplayName',  'I_a_m_p = 0.35');hold on
semilogy(xquake./1000,fixed_CAS4(:,3),'Color',c_red,'LineWidth',line_w,...
    'DisplayName',  'I_a_m_p = 0.5');hold on
semilogy(xquake./1000,fixed_CAS5(:,3),'Color',c_dark,'LineWidth',line_w,...
    'DisplayName',  'I_a_m_p = 0.75');hold on

% title(name_title);
xlabel('distance [km]');ylabel('probability of exceeding 1 fatality');
legend('show','Location','NorthEast');

% axis config
% xlim([2 5]);
% ylim([10^4 10^10]);

% configure axes
set(gca, ...
    'YDir'         , 'normal' , ...    % plot upside down   
    'Box'          , 'off'     , ...    % turn off box around figure
    'XAxisLocation', 'bottom'     , ...    % place x axis on top
    'TickDir'      , 'out'      , ...    % tickmarks inside
    'TickLength'   , [.02 .02 ], ...    % make ticks a bit longer
    'XMinorTick'   , 'off'      , ...    % turn on minor ticks
    'YMinorTick'   , 'on'      , ...
    'XTick'        , [0:5:20],...
...%     'YTick'        , [0.25:0.25:1.75],...
    'XGrid'        , 'on'      , ...    % turn on y-grid
    'YGrid'        , 'on'     , ...
    'LineWidth'    , .5         );      % make axis thinner

%% MATLAB PLOTTING PACKAGE
% set the plot size to 20x15cm for exporting
% SetPlotSize([20 15],'centimeters');

% Save the plot into a postscript file
% and fix the line definitions
% WritePlot('plot_prob_CAS_Yverdon.ai');
