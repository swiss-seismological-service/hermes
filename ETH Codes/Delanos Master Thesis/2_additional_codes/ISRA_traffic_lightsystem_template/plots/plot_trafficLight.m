%% Calls traffic light functions
%  in terms of e.g. probability or IVL thresholds
clear all;clf;close all;clc;

%  load data including daily probabilities
% load prob_ECOS09_diffMmax_hazAllDay_daily.mat
load prob_ECOS09_diffMmax_hazAllDay_daily_MEAN.mat
% load prob_ECOS09_diffMmax_haz6_periodback.mat

%% quake-events
%  load data 
data_basel = importdata('spi_mag_all_swc.dat');
data_basel = data_basel(1:3221,:);

year = data_basel(:,3);
month = data_basel(:,4);
days = data_basel(:,5);
magnitudes = data_basel(:,6);
hours = data_basel(:,8);
minutes= data_basel(:,9);

minutes_dec=minutes./60;
hours_dec=hours+minutes_dec;
hours_dec=hours_dec./24;
days_dec=days+hours_dec-2.75;

vSel=(data_basel(:,6))>0.1;
vSel = logical(vSel);
magnitudes_red = magnitudes(vSel)
time_red = days_dec(vSel)

% define thresholds
prob_threshold=0.3;
IVL_threshold1=2*10^6;
IVL_threshold2=5*10^6
shut_in_prob=   0.1     *ones(1,15);
shut_in_IVL=    10^6    *ones(1,15);

iDG = 2;    % DG to look at
DG_threshold1=50;
DG_threshold2=150;

% time period
day=1:1:15;

for iDay=1:15
   % Mmax=3.7
   [fixed_prob1(iDay,:)] = calc_IVL_prob_threshold(IVL_tot1,prob1(iDay,:),prob_threshold);
   [fixed_IVL1(iDay,:)] = calc_IVL_threshold(IVL_tot1,prob1(iDay,:),IVL_threshold1);
   [fixed_IVL2(iDay,:)] = calc_IVL_threshold(IVL_tot1,prob1(iDay,:),IVL_threshold2);  
      
   [fixed_DG1(iDay,:)] = calc_DG_threshold(DG1,prob1(iDay,:),DG_threshold1,iDG);
   [fixed_DG2(iDay,:)] = calc_DG_threshold(DG1,prob1(iDay,:),DG_threshold2,iDG);
   [fixed_DG_prob1(iDay,:)] = calc_DG_prob_threshold(DG1,prob1(iDay,:),prob_threshold,iDG);
   
%    % Mmax=5
%    [fixed_prob2(iDay,:)] = calc_IVL_prob_threshold(IVL_tot2,prob2(iDay,:),prob_threshold);
%    [fixed_IVL2(iDay,:)] = calc_IVL_threshold(IVL_tot2,prob2(iDay,:),IVL_threshold);
%    
%    % Mmax=7
%    [fixed_prob3(iDay,:)] = calc_IVL_prob_threshold(IVL_tot3,prob3(iDay,:),prob_threshold);
%    [fixed_IVL3(iDay,:)] = calc_IVL_threshold(IVL_tot3,prob3(iDay,:),IVL_threshold);
end


%% calc magnitude bins
load com.mat
model = com;
b=1.5; Mmin=0.9; Mmax=3.7; dm=0.1

for iDay=1:length(day)
    rate_index(1) = (day(iDay)*4)-3;
    rate_index(2) = day(iDay)*4;
    datax=sum(model(rate_index(1):rate_index(2))); % Total rates in 12 days during stimulation period
    [mag_bins(iDay,:)]=calc_mag_bin(b,datax,Mmin,Mmax,dm);
end



%% PLOT CONFIG
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

line_w=2;


%% probability of exceeding a certain IVL
figure(1)
% Plot Font
SetPlotFont('Helvetica', 15);
set(gcf, 'renderer', 'painters');   % vector based renderer

% threshold 1
semilogy(day,fixed_IVL1(:,2),'Color',c_dblue,'LineWidth',line_w,'LineStyle','--',...
    'DisplayName',  'lower plausible boundary');hold on
semilogy(day,fixed_IVL1(:,3),'Color',c_dblue,'LineWidth',line_w,'LineStyle','-','MarkerSize',8,'Marker','*',...
    'DisplayName',  'most plausible');hold on
semilogy(day,fixed_IVL1(:,4),'Color',c_dblue,'LineWidth',line_w,'LineStyle','--',...
    'DisplayName',  'upper plausible boundary');hold on

% % threshold 2
% semilogy(day,fixed_IVL2(:,2),'Color',c_lblue,'LineWidth',line_w,'LineStyle','--',...
%     'DisplayName',  'lower plausible boundary');hold on
% semilogy(day,fixed_IVL2(:,3),'Color',c_lblue,'LineWidth',line_w,'LineStyle','-',...
%     'DisplayName',  'most plausible');hold on
% semilogy(day,fixed_IVL2(:,4),'Color',c_lblue,'LineWidth',line_w,'LineStyle','--',...
%     'DisplayName',  'upper plausible boundary');hold on

name_IVL_threshold = num2str(IVL_threshold1/10^6);
name_title_IVL = ['probability of exceeding ' name_IVL_threshold ' Mio. CHF'];
title('Mmax=3.7');
xlabel('time [days]');ylabel(name_title_IVL);

% configure axes
set(gca, ...
    'YDir'         , 'normal' , ...    % plot upside down   
    'Box'          , 'off'     , ...    % turn off box around figure
    'XAxisLocation', 'bottom'     , ...    % place x axis on top
    'TickDir'      , 'out'      , ...    % tickmarks inside
    'TickLength'   , [.02 .02 ], ...    % make ticks a bit longer
    'XMinorTick'   , 'off'      , ...    % turn on minor ticks
    'YMinorTick'   , 'on'      , ...
    'XTick'        , [0:5:15],...
...%     'YTick'        , [0.25:0.25:1.75],...
    'XGrid'        , 'on'      , ...    % turn on y-grid
    'YGrid'        , 'on'     , ...
    'LineWidth'    , .5         );      % make axis thinner

ylim([10^-4 10^0])

%% MATLAB PLOTTING PACKAGE
% set the plot size to 20x15cm for exporting
SetPlotSize([20 15],'centimeters');

% Save the plot into a postscript file
% and fix the line definitions
WritePlot('plot_prob_IVL_threshold_Basel.ai');


%% probability of exceeding a certain num. of houses in DG1
figure(2)

% Plot Font
SetPlotFont('Helvetica', 15);
set(gcf, 'renderer', 'painters');   % vector based renderer

% threshold 1
semilogy(day,fixed_DG1(:,2),'Color',c_dblue,'LineWidth',line_w,'LineStyle','--',...
    'DisplayName',  'lower plausible boundary');hold on
semilogy(day,fixed_DG1(:,3),'Color',c_dblue,'LineWidth',line_w,'LineStyle','-','MarkerSize',8,'Marker','*',...
    'DisplayName',  'most plausible');hold on
semilogy(day,fixed_DG1(:,4),'Color',c_dblue,'LineWidth',line_w,'LineStyle','--',...
    'DisplayName',  'upper plausible boundary');hold on

% % threshold 2
% semilogy(day,fixed_DG2(:,2),'Color',c_lblue,'LineWidth',line_w,'LineStyle','--',...
%     'DisplayName',  'lower plausible boundary');hold on
% semilogy(day,fixed_DG2(:,3),'Color',c_lblue,'LineWidth',line_w,'LineStyle','-',...
%     'DisplayName',  'most plausible');hold on
% semilogy(day,fixed_DG2(:,4),'Color',c_lblue,'LineWidth',line_w,'LineStyle','--',...
%     'DisplayName',  'upper plausible boundary');hold on

name_DG_threshold = num2str(DG_threshold1);
name_title_DG = ['probability of exceeding ' name_DG_threshold ' damaged houses in DG1'];
title('Mmax=3.7');
xlabel('time [days]');ylabel(name_title_DG);


% configure axes
set(gca, ...
    'YDir'         , 'normal' , ...    % plot upside down   
    'Box'          , 'off'     , ...    % turn off box around figure
    'XAxisLocation', 'bottom'     , ...    % place x axis on top
    'TickDir'      , 'out'      , ...    % tickmarks inside
    'TickLength'   , [.02 .02 ], ...    % make ticks a bit longer
    'XMinorTick'   , 'off'      , ...    % turn on minor ticks
    'YMinorTick'   , 'on'      , ...
    'XTick'        , [0:5:15],...
...%     'YTick'        , [0.25:0.25:1.75],...
    'XGrid'        , 'on'      , ...    % turn on y-grid
    'YGrid'        , 'on'     , ...
    'LineWidth'    , .5         );      % make axis thinner

ylim([10^-4 10^0])

%% MATLAB PLOTTING PACKAGE
% set the plot size to 20x15cm for exporting
SetPlotSize([20 15],'centimeters');

% Save the plot into a postscript file
% and fix the line definitions
WritePlot('plot_prob_DG_threshold_Basel.ai');



figure(3)
% Plot Font
SetPlotFont('Helvetica', 15);
set(gcf, 'renderer', 'painters');   % vector based renderer

plot(time_red,magnitudes_red,'MarkerSize',8,'Marker','.','LineStyle','none','Color',c_dgreen);

name_DG_threshold = num2str(DG_threshold1);
name_title_DG = ['probability of exceeding ' name_DG_threshold ' damaged houses in DG1'];
% title('Mmax=3.7');
% xlabel('time [days]');ylabel(name_title_DG);


% configure axes
set(gca, ...
    'YDir'         , 'normal' , ...    % plot upside down   
    'Box'          , 'off'     , ...    % turn off box around figure
    'XAxisLocation', 'bottom'     , ...    % place x axis on top
    'YAxisLocation', 'right'     , ...    % place x axis on top
    'TickDir'      , 'out'      , ...    % tickmarks inside
    'TickLength'   , [.02 .02 ], ...    % make ticks a bit longer
    'XMinorTick'   , 'off'      , ...    % turn on minor ticks
    'YMinorTick'   , 'off'      , ...
    'XTick'        , [0:5:15],...
...%     'YTick'        , [0.25:0.25:1.75],...
    'XGrid'        , 'off'      , ...    % turn on y-grid
    'YGrid'        , 'on'     , ...
    'LineWidth'    , .5         );      % make axis thinner

ylim([0 4])
xlim([0 15]);

%% MATLAB PLOTTING PACKAGE
% set the plot size to 20x15cm for exporting
SetPlotSize([20 4.5],'centimeters');
% SetPlotSize([20 6],'centimeters');

% Save the plot into a postscript file
% and fix the line definitions
WritePlot('plot_events_Basel.ai');

%% testplots
% figure(3)
% subplot(2,1,1)
% semilogy(day,fixed_DG1(:,2),'--b');hold on
% semilogy(day,fixed_DG1(:,3),'-b');hold on
% semilogy(day,fixed_DG1(:,4),'--b');hold on
% % semilogy(day,shut_in_IVL,'LineWidth',2,'Color','r');hold on
% 
% % ylim([10^0 10^9])
% title('Mmax=3.7');
% xlabel('day');ylabel('IVL [CHF]');
% grid on
% 
% subplot(2,1,2)
% semilogy(day,fixed_DG_prob1(:,2),'--b');hold on
% semilogy(day,fixed_DG_prob1(:,3),'-b');hold on
% semilogy(day,fixed_DG_prob1(:,4),'--b');hold on
% % plot(day,fixed_DG_prob1(:,2),'--b');hold on
% % plot(day,fixed_DG_prob1(:,3),'-b');hold on
% % plot(day,fixed_DG_prob1(:,4),'--b');hold on
% title('Mmax=3.7');
% xlabel('day');ylabel('number of buildings in DG1');
% grid on
% ylim([0 10^3])
% 
% 
% figure(4)
% subplot(2,1,1)
% semilogy(day,fixed_prob1(:,2),'--b');hold on
% semilogy(day,fixed_prob1(:,3),'-b');hold on
% semilogy(day,fixed_prob1(:,4),'--b');hold on
% 
% semilogy(day,shut_in_IVL,'LineWidth',2,'Color','r');hold on
% 
% 
% ylim([10^0 10^9])
% title('Mmax=3.7');
% xlabel('day');ylabel('IVL [CHF]');
% grid on
% 
% 
% subplot(2,1,2)
% semilogy(day,fixed_IVL1(:,2),'--b');hold on
% semilogy(day,fixed_IVL1(:,3),'-b');hold on
% semilogy(day,fixed_IVL1(:,4),'--b');hold on
% 
% semilogy(day,shut_in_prob,'LineWidth',2,'Color','r');hold on
% 
% 
% grid on
% ylim([10^-5 10^0])
% title('Mmax=3.7');
% xlabel('day');ylabel('exceeding probability');