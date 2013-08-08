%% CALL_LOSS
%% this script is modified to compute the hazard after each day of the
%% Basel sequence
%  this script calls deterministic and probabilistic loss assessment for
%  induced seismicity
clear all;clc;clf;close all;


%% General Input Parameters
%  2    Switch of methods (s... for switch)
%  2.1  GMPE (Ground Motion Prediction Equation
sGMPE=  'Allen-2012'; % ECOS-02, ECOS-02new, ECOS-09, Allen-2012
%  2.2  Site Amplification yes or no?
sAMPL=  'AMPyes';  % yes or no
%  2.3  Distribution Functions
sDISTR= 'BinPDF';  % BinPDF, BetaPDF
%  2.4  Cost Functions
sCOST=  'SED_Del';   % Expert_SER, Cochrane92, Risk_UE, SED_Del

%% Mmin/Mmax for deterministic calc.
M_Mmin =  0.9;    % Magnitude of completeness
M_dm =    0.1;    % Magnitude increment
M_Mmax =  4.1;    % Mmax
M_Magn = M_Mmin:M_dm:M_Mmax;


%% Load forecast rates
load com.mat
% load all_models.mat;
% 
% SRR=all_models.SR;
% r22=all_models.R2;
% e44=all_models.E4;
% e55=all_models.E5;
% com=all_models.COMB;
% obs_rate=all_models.obs;

%% time-input
day = 1:15;     % "day-range"
period = 1;     % periods to look at in days
                % period=1: daily probabilities are computed

for iDay=1:length(day)
    rate_index(1) = (day(iDay)*4)-3;
    rate_index(2) = day(iDay)*4;
    
    %% For probabilistic calc.
    Mmin=0.9; Mmax=3.7;
    [M_Magn1,IVL_tot1,IVL_tot_PROB_norm1,tot_loss1,prob1(iDay,:),losses1,exrate1,casualties1,DG1]=calc_loss(M_Mmin,M_dm,M_Mmax,sGMPE,sAMPL,sDISTR,sCOST,com,Mmin,Mmax,rate_index);
    
    Mmin=0.9; Mmax=5;
    [M_Magn2,IVL_tot2,IVL_tot_PROB_norm2,tot_loss2,prob2(iDay,:),losses2,exrate2,casualties2,DG2]=calc_loss(M_Mmin,M_dm,M_Mmax,sGMPE,sAMPL,sDISTR,sCOST,com,Mmin,Mmax,rate_index);

    Mmin=0.9; Mmax=7;
    [M_Magn3,IVL_tot3,IVL_tot_PROB_norm3,tot_loss3,prob3(iDay,:),losses3,exrate3,casualties3,DG3]=calc_loss(M_Mmin,M_dm,M_Mmax,sGMPE,sAMPL,sDISTR,sCOST,com,Mmin,Mmax,rate_index);

end

clf;
%% testplot
figure(1)
subplot(3,1,1)
for iDay=1:length(day)
    semilogy(M_Magn1,prob1(iDay,:),'r');hold on  
end
xlim([1 4.5])
ylim([10^-3 1])

subplot(3,1,2)
for iDay=1:length(day)
    semilogy(M_Magn2,prob2(iDay,:),'r');hold on  
end
xlim([1 4.5])
ylim([10^-3 1])

subplot(3,1,3)
for iDay=1:length(day)
    semilogy(M_Magn3,prob3(iDay,:),'r');hold on  
end
xlim([1 4.5])
ylim([10^-3 1])


%% SAVING
% save prob_ECOS09_diffMmax_haz6_period.mat
% save prob_ECOS09_diffMmax_haz6_oneday.mat
save prob_ECOS09_diffMmax_hazAllDay_daily_MEAN.mat
% save prob_Allen2012_diffMmax_haz6_oneday.mat


% %% Probabilistic Loss Curve: IVL
% figure(1);
% loglog(IVL_tot(:,3),prob1,'k','LineWidth',2);  hold on;
% loglog(IVL_tot(:,3),prob2,'r','LineWidth',2);  hold on;
% loglog(IVL_tot(:,3),prob3,'g','LineWidth',2);  hold on;
% legend('Mmax=3.7','Mmax=5','Mmax=7');
% % loglog(losses1,exrate1,'ko-','LineWidth',2); grid on;
% % loglog(losses2,exrate2,'ro-','LineWidth',2); grid on;
% % loglog(losses3,exrate3,'go-','LineWidth',2); grid on;
% set(gca,'LineWidth',2,'FontSize',24,'FontWeight','normal','FontName','Times')
% set(get(gca,'XLabel'),'String','Insured Value Loss (CHF)','FontSize',24,'FontName','Times')
% set(get(gca,'YLabel'),'String','6 Days Exceedance Rate','FontSize',24,'FontName','Times')
% set(get(gca,'Title'),'String','Probabilistic Loss Curve: IVL (6 days of stimulation)','FontSize',24,'FontName','Times')
% axis([10^6 10^11 10^-4 1])
% 
% % MATLAB PLOTTING PACKAGE
% % Plot Font
% SetPlotFont('Helvetica', 15);
% set(gcf, 'renderer', 'painters');   % vector based renderer
% % 
% % set the plot size to 20x15cm for exporting
% SetPlotSize([20 15],'centimeters');
% 
% % Save the plot into a postscript file
% % and fix the line definitions
% % WritePlot('plot_PLC_haz12_period.ai');
% % WritePlot('plot_PLC_haz12_period.png');
% % WritePlot('plot_PLC_haz12_period.fig');
% 
% 
% %% Probabilistic Loss Curve: casualties
% figure(2);
% loglog(casualties1(:,5,3),prob1,'r','LineWidth',2);  hold on;
% loglog(casualties2(:,5,3),prob2,'g','LineWidth',2);  hold on;
% loglog(casualties3(:,5,3),prob3,'k','LineWidth',2);  hold on;
% % semilogy(casualties1(:,5,3),prob1,'r','LineWidth',2);  hold on;
% % semilogy(casualties2(:,5,3),prob2,'g','LineWidth',2);  hold on;
% % semilogy(casualties3(:,5,3),prob3,'k','LineWidth',2);  hold on;
% legend('Mmax=3.7','Mmax=5','Mmax=7');
% % loglog(losses1,exrate1,'ko-','LineWidth',2); grid on;
% % loglog(losses2,exrate2,'ro-','LineWidth',2); grid on;
% % loglog(losses3,exrate3,'go-','LineWidth',2); grid on;
% set(gca,'LineWidth',2,'FontSize',24,'FontWeight','normal','FontName','Times')
% set(get(gca,'XLabel'),'String','num. casualty degree 5','FontSize',24,'FontName','Times')
% set(get(gca,'YLabel'),'String','6 Days Exceedance Rate','FontSize',24,'FontName','Times')
% set(get(gca,'Title'),'String','Probabilistic Loss Curve: casualties (6 days of stimulation)','FontSize',24,'FontName','Times')
% xlim([10^-1 100])
% ylim([10^-4 1])
% % axis([0 1000 10^-4 1])
% 
% % MATLAB PLOTTING PACKAGE
% % Plot Font
% SetPlotFont('Helvetica', 15);
% set(gcf, 'renderer', 'painters');   % vector based renderer
% % 
% % set the plot size to 20x15cm for exporting
% SetPlotSize([20 15],'centimeters');
% 
% %% Probabilistic Loss Curve: num. of houses in DG1
% 
% 

