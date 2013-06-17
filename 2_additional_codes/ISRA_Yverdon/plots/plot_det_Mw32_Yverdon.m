clear all;close all;clf;clc;

load case_yverdon_Mmax37_SiteAmp.mat

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

line_w=1.5;

%% Det. Plot: IVL for Mw 3.2 event
figure(1)
% Plot Font
SetPlotFont('Helvetica', 15);
set(gcf, 'renderer', 'painters');   % vector based renderer

set(gcf, 'renderer', 'painters');   % vector based renderer
plot(xquake./1000,IVL_tot1_final(iMag_int,:,3)./10^6,'Color',c_lblue,'LineWidth',line_w,'LineStyle','-','MarkerSize',8,'Marker','*',...
    'DisplayName',  'I_a_m_p = 0');hold on
plot(xquake./1000,IVL_tot2_final(iMag_int,:,3)./10^6,'Color',c_orange,'LineWidth',line_w,'MarkerSize',8,'Marker','*',...
    'DisplayName',  'I_a_m_p = 0.25');hold on
plot(xquake./1000,IVL_tot3_final(iMag_int,:,3)./10^6,'Color',c_lred,'LineWidth',line_w,'MarkerSize',8,'Marker','*',...
    'DisplayName',  'I_a_m_p = 0.35');hold on
plot(xquake./1000,IVL_tot4_final(iMag_int,:,3)./10^6,'Color',c_red,'LineWidth',line_w,'MarkerSize',8,'Marker','*',...
    'DisplayName',  'I_a_m_p = 0.5');hold on
plot(xquake./1000,IVL_tot5_final(iMag_int,:,3)./10^6,'Color',c_dark,'LineWidth',line_w,'MarkerSize',8,'Marker','*',...
    'DisplayName',  'I_a_m_p = 0.75');hold on

% title('Deterministic case: M_w 3.2 event');
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
    'YTick'        , [0.25:0.25:1.75],...
    'XGrid'        , 'on'      , ...    % turn on y-grid
    'YGrid'        , 'on'     , ...
    'LineWidth'    , .5         );      % make axis thinner

%% MATLAB PLOTTING PACKAGE
% set the plot size to 20x15cm for exporting
SetPlotSize([20 15],'centimeters');

% Save the plot into a postscript file
% and fix the line definitions
WritePlot('plot_det_IVL_Mw32_Yverdon.ai');


figure(2)
% Plot Font
SetPlotFont('Helvetica', 15);
set(gcf, 'renderer', 'painters');   % vector based renderer

set(gcf, 'renderer', 'painters');   % vector based renderer
plot(xquake./1000,num_DG1_final(iMag_int,:,2,3),'Color',c_lblue,'LineWidth',line_w,'LineStyle','-','MarkerSize',8,'Marker','*',...
    'DisplayName',  'I_a_m_p = 0');hold on
plot(xquake./1000,num_DG2_final(iMag_int,:,2,3),'Color',c_orange,'LineWidth',line_w,'MarkerSize',8,'Marker','*',...
    'DisplayName',  'I_a_m_p = 0.25');hold on
plot(xquake./1000,num_DG3_final(iMag_int,:,2,3),'Color',c_lred,'LineWidth',line_w,'MarkerSize',8,'Marker','*',...
    'DisplayName',  'I_a_m_p = 0.35');hold on
plot(xquake./1000,num_DG4_final(iMag_int,:,2,3),'Color',c_red,'LineWidth',line_w,'MarkerSize',8,'Marker','*',...
    'DisplayName',  'I_a_m_p = 0.5');hold on
plot(xquake./1000,num_DG5_final(iMag_int,:,2,3),'Color',c_dark,'LineWidth',line_w,'MarkerSize',8,'Marker','*',...
    'DisplayName',  'I_a_m_p = 0.75');hold on

% title('Deterministic case: M_w 3.2 event');
xlabel('distance [km]');ylabel('number of houses in DG1');
legend('show','Location','NorthEast');

% configure axes
set(gca, ...
    'YDir'         , 'normal' , ...    % plot upside down   
    'Box'          , 'off'     , ...    % turn off box around figure
    'XAxisLocation', 'bottom'     , ...    % place x axis on top
    'TickDir'      , 'out'      , ...    % tickmarks inside
    'TickLength'   , [.02 .02 ], ...    % make ticks a bit longer
    'XMinorTick'   , 'off'      , ...    % turn on minor ticks
    'YMinorTick'   , 'off'      , ...
    'XTick'        , [0:5:20],...
...%     'YTick'        , [0.25:0.25:1.75],...
    'XGrid'        , 'on'      , ...    % turn on y-grid
    'YGrid'        , 'on'     , ...
    'LineWidth'    , .5         );      % make axis thinner

%% MATLAB PLOTTING PACKAGE
% set the plot size to 20x15cm for exporting
SetPlotSize([20 15],'centimeters');

% Save the plot into a postscript file
% and fix the line definitions
WritePlot('plot_det_DG_Mw32_Yverdon.ai');

% figure(3)
% plot(xquake./1000,mCasSum1_final(iMag_int,:,2,3),'Color',c_lblue,'LineWidth',line_w);hold on
% plot(xquake./1000,mCasSum2_final(iMag_int,:,2,3),'Color',c_dark,'LineWidth',line_w);hold on
% plot(xquake./1000,mCasSum3_final(iMag_int,:,2,3),'Color',c_orange,'LineWidth',line_w);hold on
% plot(xquake./1000,mCasSum4_final(iMag_int,:,2,3),'Color',c_lred,'LineWidth',line_w);hold on
% plot(xquake./1000,mCasSum5_final(iMag_int,:,2,3),'Color',c_red,'LineWidth',line_w);hold on
% 
% plot(xquake./1000,mCasSum1_final(iMag_int_low,:,2,3),'Color',c_lblue,'LineWidth',line_w,'LineStyle','--');hold on
% plot(xquake./1000,mCasSum2_final(iMag_int_low,:,2,3),'Color',c_dark,'LineWidth',line_w,'LineStyle','--');hold on
% plot(xquake./1000,mCasSum3_final(iMag_int_low,:,2,3),'Color',c_orange,'LineWidth',line_w,'LineStyle','--');hold on
% plot(xquake./1000,mCasSum4_final(iMag_int_low,:,2,3),'Color',c_lred,'LineWidth',line_w,'LineStyle','--');hold on
% plot(xquake./1000,mCasSum5_final(iMag_int_low,:,2,3),'Color',c_red,'LineWidth',line_w,'LineStyle','--');hold on
% 
% 
% title('Casualties C2: M_w 2.9 (dotted lines), M_w 3.2 (solid lines)');
% xlabel('distance [km]');ylabel('number of casualties C2');
% legend('Iamp = 0','Iamp = 0.25','Iamp = 0.35','Iamp = 0.5','Iamp = 0.75');
% grid on


% figure(4)
% loglog(IVL_tot1(:,3,21),prob1);

% figure(4)
% semilogy(M_Magn1,IVL_tot1(:,3),'Color',c_lblue,'LineWidth',line_w);hold on
% semilogy(M_Magn1,IVL_tot2(:,3),'Color',c_dark,'LineWidth',line_w);hold on
% semilogy(M_Magn1,IVL_tot3(:,3),'Color',c_lred,'LineWidth',line_w);hold on
% semilogy(M_Magn1,IVL_tot4(:,3),'Color',c_red,'LineWidth',line_w);
% title('total IVL as a function of M_w, at 20km distance from the city');
% xlabel('Magnitude M_w');ylabel('IVL [CHF]');
% legend('Iamp = -0.5','Iamp = 0','Iamp = 0.5','Iamp = 1','Location','Best');
% grid on
