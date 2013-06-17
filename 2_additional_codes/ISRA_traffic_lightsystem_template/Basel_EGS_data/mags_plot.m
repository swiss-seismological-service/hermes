clear all;clf;close all;clc;

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

figure(1)
plot(time_red,magnitudes_red,'MarkerSize',8,'Marker','.','LineStyle','none');
xlim([0 15])
ylim([0 4])

ylabel('Magnitude M_W');xlabel('time[days]');

% configure axes
set(gca, ...
    'YDir'         , 'normal' , ...    % plot upside down   
    'Box'          , 'off'     , ...    % turn off box around figure
    'XAxisLocation', 'bottom'     , ...    % place x axis on top
    'TickDir'      , 'out'      , ...    % tickmarks inside
    'TickLength'   , [.02 .02 ], ...    % make ticks a bit longer
    'XMinorTick'   , 'on'      , ...    % turn on minor ticks
    'YMinorTick'   , 'off'      , ...
...%     'XTick'        , [0:5:20],...
...%     'YTick'        , [0.25:0.25:1.75],...
    'XGrid'        , 'on'      , ...    % turn on y-grid
    'YGrid'        , 'on'     , ...
    'LineWidth'    , .5         );      % make axis thinner
