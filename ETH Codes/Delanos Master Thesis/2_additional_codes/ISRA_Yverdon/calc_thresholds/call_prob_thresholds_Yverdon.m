%% Calls traffic light functions
%  in terms of e.g. probability or IVL thresholds
clear all;clf;clc;close all;

%  load data including daily probabilities
load case_yverdon_Mmax37_SiteAmp.mat


% define thresholds
prob_threshold=0.1;
CAS_threshold=1;
DG_threshold=25;
CD=5;   % defining casualty degree to look at
iDG=2;  % DG of houses to look at

% IVL_threshold=10^6;
% shut_in_prob=   0.1     *ones(1,15);
% shut_in_IVL=    10^6    *ones(1,15);

% for iDay=1:15
   % Iamp = 0
   [fixed_IVL_prob1] = calc_IVL_prob_threshold_Yverdon(IVL_tot1_final,prob1,prob_threshold);
   [fixed_DG_prob1] = calc_DG_prob_threshold_Yverdon(num_DG1_final,prob1,prob_threshold,iDG);
   [fixed_DG_1] = calc_DG_threshold_Yverdon(num_DG1_final,prob1,DG_threshold,iDG);
   [fixed_CAS1] = calc_CAS_threshold_Yverdon(mCasSum1_final,prob1,CAS_threshold,CD);
%    [fixed_IVL1(iDay,:)] = calc_IVL_threshold(IVL_tot1,prob1(iDay,:),IVL_threshold);
   
%    % Mmax=5
%    [fixed_prob2(iDay,:)] = calc_prob_threshold(IVL_tot2,prob2(iDay,:),prob_threshold);
%    [fixed_IVL2(iDay,:)] = calc_IVL_threshold(IVL_tot2,prob2(iDay,:),IVL_threshold);
%    
%    % Mmax=7
%    [fixed_prob3(iDay,:)] = calc_prob_threshold(IVL_tot3,prob3(iDay,:),prob_threshold);
%    [fixed_IVL3(iDay,:)] = calc_IVL_threshold(IVL_tot3,prob3(iDay,:),IVL_threshold);
% end


distance = 0:1:20;



figure(1)
plot(distance,fixed_IVL_prob1(:,2),'LineStyle','--');hold on
plot(distance,fixed_IVL_prob1(:,3),'LineStyle','-');hold on
plot(distance,fixed_IVL_prob1(:,4),'LineStyle','--');

figure(2)
% plot(distance,fixed_DG_prob1(:,3));
plot(distance,fixed_DG_1(:,3));

figure(3)
% plot(distance,fixed_CAS1(:,2),'LineStyle','--');hold on
semilogy(distance,fixed_CAS1(:,3),'LineStyle','-');hold on
% plot(distance,fixed_CAS1(:,4),'LineStyle','--');

% figure(4)
% plot(distance,mCasSum1_final(24,:,5,3));