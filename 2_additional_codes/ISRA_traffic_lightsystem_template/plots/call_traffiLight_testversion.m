%% Calls traffic light functions
%  in terms of e.g. probability or IVL thresholds
clear all;clf;clc;

%  load data including daily probabilities
load prob_ECOS09_diffMmax_hazAllDay_daily_MEAN.mat

% define thresholds
prob_threshold=0.1;
IVL_threshold=10^6;
shut_in_prob=   0.1     *ones(1,15);
shut_in_IVL=    10^6    *ones(1,15);

for iDay=1:15
   % Mmax=3.7
%    [fixed_prob1(iDay,:)] = calc_prob_threshold(IVL_tot1,prob1(iDay,:),prob_threshold);
   [fixed_IVL1(iDay,:)] = calc_IVL_threshold(IVL_tot1,prob1(iDay,:),IVL_threshold);
   
   % Mmax=5
%    [fixed_prob2(iDay,:)] = calc_prob_threshold(IVL_tot2,prob2(iDay,:),prob_threshold);
   [fixed_IVL2(iDay,:)] = calc_IVL_threshold(IVL_tot2,prob2(iDay,:),IVL_threshold);
   
   % Mmax=7
%    [fixed_prob3(iDay,:)] = calc_prob_threshold(IVL_tot3,prob3(iDay,:),prob_threshold);
   [fixed_IVL3(iDay,:)] = calc_IVL_threshold(IVL_tot3,prob3(iDay,:),IVL_threshold);
end


day=1:1:15;
figure(1)
%% Mmax=3.7
% % fixed prob
% subplot(3,2,1)
% semilogy(day,fixed_prob1(:,2),'--b');hold on
% semilogy(day,fixed_prob1(:,3),'-b');hold on
% semilogy(day,fixed_prob1(:,4),'--b');hold on
% 
% semilogy(day,shut_in_IVL,'LineWidth',2,'Color','r');hold on
% 
% ylim([10^0 10^9])
% title('Mmax=3.7');
% xlabel('day');ylabel('IVL [CHF]');
% grid on
% fixed IVL
subplot(3,2,2)
semilogy(day,fixed_IVL1(:,2),'--b');hold on
semilogy(day,fixed_IVL1(:,3),'-b');hold on
semilogy(day,fixed_IVL1(:,4),'--b');hold on

semilogy(day,shut_in_prob,'LineWidth',2,'Color','r');hold on


grid on
ylim([10^-5 10^0])
title('Mmax=3.7');
xlabel('day');ylabel('exceeding probability');

%% Mmax=5
% % fixed prob
% subplot(3,2,3)
% semilogy(day,fixed_prob2(:,2),'--k');hold on
% semilogy(day,fixed_prob2(:,3),'-k');hold on
% semilogy(day,fixed_prob2(:,4),'--k');hold on
% ylim([10^0 10^9])
% grid on
% title('Mmax=5');
% xlabel('day');ylabel('IVL [CHF]');
% fixed IVL
subplot(3,2,4)
semilogy(day,fixed_IVL2(:,2),'--k');hold on
semilogy(day,fixed_IVL2(:,3),'-k');hold on
semilogy(day,fixed_IVL2(:,4),'--k');hold on
grid on
ylim([10^-5 10^0])
title('Mmax=5');
xlabel('day');ylabel('exceeding probability');

%% Mmax=7
% % fixed prob
% subplot(3,2,5)
% semilogy(day,fixed_prob3(:,2),'--r');hold on
% semilogy(day,fixed_prob3(:,3),'-r');hold on
% semilogy(day,fixed_prob3(:,4),'--r');hold on
% ylim([10^0 10^9])
% grid on
% title('Mmax=7');
% xlabel('day');ylabel('IVL [CHF]');
% fixed IVL
subplot(3,2,6)
semilogy(day,fixed_IVL3(:,2),'--r');hold on
semilogy(day,fixed_IVL3(:,3),'-r');hold on
semilogy(day,fixed_IVL3(:,4),'--r');hold on
grid on
ylim([10^-5 10^0])
title('Mmax=7');
xlabel('day');ylabel('exceeding probability');


figure(2)
% Mmax 3.7
% semilogy(day,fixed_IVL1(:,2),'--b');hold on
semilogy(day,fixed_IVL1(:,3),'-b');hold on
% semilogy(day,fixed_IVL1(:,4),'--b');hold on
% Mmax 5
% semilogy(day,fixed_IVL2(:,2),'--k');hold on
semilogy(day,fixed_IVL2(:,3),'-k');hold on
% semilogy(day,fixed_IVL2(:,4),'--k');hold on
% Mmax 7
% semilogy(day,fixed_IVL3(:,2),'--r');hold on
semilogy(day,fixed_IVL3(:,3),'-r');hold on
% semilogy(day,fixed_IVL3(:,4),'--r');hold on
grid on
ylim([10^-5 10^0])
title('Mmax=3.7, 5, 7');
xlabel('day');ylabel('exceeding probability');
legend('Mmax 3.7','Mmax 5','Mmax 7')

figure(3)
% subplot(2,1,1)
% semilogy(day,fixed_prob1(:,2),'--b');hold on
% semilogy(day,fixed_prob1(:,3),'-b');hold on
% semilogy(day,fixed_prob1(:,4),'--b');hold on
% 
% semilogy(day,shut_in_IVL,'LineWidth',2,'Color','r');hold on
% 
% ylim([10^0 10^9])
% title('Mmax=3.7');
% xlabel('day');ylabel('IVL [CHF]');
% grid on
subplot(2,1,2)
semilogy(day,fixed_IVL1(:,2),'--b');hold on
semilogy(day,fixed_IVL1(:,3),'-b');hold on
semilogy(day,fixed_IVL1(:,4),'--b');hold on

semilogy(day,shut_in_prob,'LineWidth',2,'Color','r');hold on


grid on
ylim([10^-5 10^0])
title('Mmax=3.7');
xlabel('day');ylabel('exceeding probability');