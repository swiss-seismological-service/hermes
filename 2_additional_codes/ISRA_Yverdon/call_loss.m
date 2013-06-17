%% call_loss
%  this script calls deterministic and probabilistic loss assessment for
%  induced seismicity

clear all;clc;clf; 
close all;


%% General Input Parameters
%  2    Switch of methods (s... for switch)
%  2.1  GMPE (Ground Motion Prediction Equation
sGMPE=  'ECOS-09'; % ECOS-02, ECOS-02new, ECOS-09, Allen-2012
%  2.2  Site Amplification yes or no?
sAMPL=  'AMPyes';  % yes or no
%  2.3  Distribution Functions
sDISTR= 'BinPDF';  % BinPDF, BetaPDF
%  2.4  Cost Functions
sCOST=  'Expert_SER';   % Expert_SER, Cochrane92, Risk_UE, SED_Del

%% Mmin/Mmax for deterministic calc.
M_Mmin =  0.9;    % Magnitude of completeness
M_dm =    0.1;    % Magnitude increment
M_Mmax =  7;    % Mmax
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

%% Site Amplification
% Iamp = [-0.5 0 0.5 1]

%% Different borehole coordinates
xquake = 0:1000:20000;
yquake = 0;

tic
%% For probabilistic calc.
for iDist=1:length(xquake)
Mmin=0.9; Mmax=3.7; Iamp=0;
[M_Magn1,IVL_tot1(:,:,iDist),IVL_tot_PROB_norm1,tot_loss1,prob1(iDist,:),losses1,exrate1,mCasSum1(:,:,:,iDist),num_DG1(:,:,:,iDist)]=calc_loss(M_Mmin,M_dm,M_Mmax,sGMPE,sAMPL,sDISTR,sCOST,com,Mmin,Mmax,Iamp,xquake(iDist),yquake);

Mmin=0.9; Mmax=3.7; Iamp=0.25;
[M_Magn2,IVL_tot2(:,:,iDist),IVL_tot_PROB_norm2,tot_loss2,prob2(iDist,:),losses2,exrate2,mCasSum2(:,:,:,iDist),num_DG2(:,:,:,iDist)]=calc_loss(M_Mmin,M_dm,M_Mmax,sGMPE,sAMPL,sDISTR,sCOST,com,Mmin,Mmax,Iamp,xquake(iDist),yquake);
 
Mmin=0.9; Mmax=3.7; Iamp=0.35;
[M_Magn3,IVL_tot3(:,:,iDist),IVL_tot_PROB_norm3,tot_loss3,prob3(iDist,:),losses3,exrate3,mCasSum3(:,:,:,iDist),num_DG3(:,:,:,iDist)]=calc_loss(M_Mmin,M_dm,M_Mmax,sGMPE,sAMPL,sDISTR,sCOST,com,Mmin,Mmax,Iamp,xquake(iDist),yquake);

Mmin=0.9; Mmax=3.7; Iamp=0.5;
[M_Magn4,IVL_tot4(:,:,iDist),IVL_tot_PROB_norm4,tot_loss4,prob4(iDist,:),losses4,exrate4,mCasSum4(:,:,:,iDist),num_DG4(:,:,:,iDist)]=calc_loss(M_Mmin,M_dm,M_Mmax,sGMPE,sAMPL,sDISTR,sCOST,com,Mmin,Mmax,Iamp,xquake(iDist),yquake);

Mmin=0.9; Mmax=3.7; Iamp=0.75;
[M_Magn5,IVL_tot5(:,:,iDist),IVL_tot_PROB_norm5,tot_loss5,prob5(iDist,:),losses5,exrate5,mCasSum5(:,:,:,iDist),num_DG5(:,:,:,iDist)]=calc_loss(M_Mmin,M_dm,M_Mmax,sGMPE,sAMPL,sDISTR,sCOST,com,Mmin,Mmax,Iamp,xquake(iDist),yquake);

end
toc
% save temporary3.mat

% load temporary2.mat

%% 1
% rearrangment of final casualty matrix
for iMag=1:size(mCasSum1,1)
    for iVC=1:size(mCasSum1,2)
        for iC=1:size(mCasSum1,3)
            for iDist=1:size(mCasSum1,4)
                mCasSum1_final(iMag,iDist,iC,iVC)=mCasSum1(iMag,iC,iVC,iDist);
            end
        end
    end
end
% rearrangment of final IVL
for iMag=1:size(IVL_tot1,1)
    for iVC=1:size(IVL_tot1,2)
        for iDist=1:size(IVL_tot1,3)
            IVL_tot1_final(iMag,iDist,iVC)=IVL_tot1(iMag,iVC,iDist);
        end
    end
end
% rearrangement of final DG
for iMag=1:size(num_DG1,1)
    for iDG=1:size(num_DG1,2)
        for iVC=1:size(num_DG1,3)
            for iDist=1:size(num_DG1,4)
            num_DG1_final(iMag,iDist,iDG,iVC)=num_DG1(iMag,iDG,iVC,iDist);
            end
        end
    end
end

%% 2
% rearrangment of final casualty matrix
for iMag=1:size(mCasSum1,1)
    for iVC=1:size(mCasSum1,2)
        for iC=1:size(mCasSum1,3)
            for iDist=1:size(mCasSum1,4)
                mCasSum2_final(iMag,iDist,iC,iVC)=mCasSum2(iMag,iC,iVC,iDist);
            end
        end
    end
end
% rearrangment of final IVL
for iMag=1:size(IVL_tot1,1)
    for iVC=1:size(IVL_tot1,2)
        for iDist=1:size(IVL_tot1,3)
            IVL_tot2_final(iMag,iDist,iVC)=IVL_tot2(iMag,iVC,iDist);
        end
    end
end
% rearrangement of final DG
for iMag=1:size(num_DG1,1)
    for iDG=1:size(num_DG1,2)
        for iVC=1:size(num_DG1,3)
            for iDist=1:size(num_DG1,4)
            num_DG2_final(iMag,iDist,iDG,iVC)=num_DG2(iMag,iDG,iVC,iDist);
            end
        end
    end
end

%% 3
% rearrangment of final casualty matrix
for iMag=1:size(mCasSum1,1)
    for iVC=1:size(mCasSum1,2)
        for iC=1:size(mCasSum1,3)
            for iDist=1:size(mCasSum1,4)
                mCasSum3_final(iMag,iDist,iC,iVC)=mCasSum3(iMag,iC,iVC,iDist);
            end
        end
    end
end
% rearrangment of final IVL
for iMag=1:size(IVL_tot1,1)
    for iVC=1:size(IVL_tot1,2)
        for iDist=1:size(IVL_tot1,3)
            IVL_tot3_final(iMag,iDist,iVC)=IVL_tot3(iMag,iVC,iDist);
        end
    end
end
% rearrangement of final DG
for iMag=1:size(num_DG1,1)
    for iDG=1:size(num_DG1,2)
        for iVC=1:size(num_DG1,3)
            for iDist=1:size(num_DG1,4)
            num_DG3_final(iMag,iDist,iDG,iVC)=num_DG3(iMag,iDG,iVC,iDist);
            end
        end
    end
end

%% 4
% rearrangment of final casualty matrix
for iMag=1:size(mCasSum1,1)
    for iVC=1:size(mCasSum1,2)
        for iC=1:size(mCasSum1,3)
            for iDist=1:size(mCasSum1,4)
                mCasSum4_final(iMag,iDist,iC,iVC)=mCasSum4(iMag,iC,iVC,iDist);
            end
        end
    end
end
% rearrangment of final IVL
for iMag=1:size(IVL_tot1,1)
    for iVC=1:size(IVL_tot1,2)
        for iDist=1:size(IVL_tot1,3)
            IVL_tot4_final(iMag,iDist,iVC)=IVL_tot4(iMag,iVC,iDist);
        end
    end
end
% rearrangement of final DG
for iMag=1:size(num_DG1,1)
    for iDG=1:size(num_DG1,2)
        for iVC=1:size(num_DG1,3)
            for iDist=1:size(num_DG1,4)
            num_DG4_final(iMag,iDist,iDG,iVC)=num_DG4(iMag,iDG,iVC,iDist);
            end
        end
    end
end

%% 5
% rearrangment of final casualty matrix
for iMag=1:size(mCasSum1,1)
    for iVC=1:size(mCasSum1,2)
        for iC=1:size(mCasSum1,3)
            for iDist=1:size(mCasSum1,4)
                mCasSum5_final(iMag,iDist,iC,iVC)=mCasSum5(iMag,iC,iVC,iDist);
            end
        end
    end
end
% rearrangment of final IVL
for iMag=1:size(IVL_tot1,1)
    for iVC=1:size(IVL_tot1,2)
        for iDist=1:size(IVL_tot1,3)
            IVL_tot5_final(iMag,iDist,iVC)=IVL_tot5(iMag,iVC,iDist);
        end
    end
end
% rearrangement of final DG
for iMag=1:size(num_DG1,1)
    for iDG=1:size(num_DG1,2)
        for iVC=1:size(num_DG1,3)
            for iDist=1:size(num_DG1,4)
            num_DG5_final(iMag,iDist,iDG,iVC)=num_DG5(iMag,iDG,iVC,iDist);
            end
        end
    end
end

save case_yverdon_Mmax37prob_45det_SiteAmpMEAN.mat

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


%% plot IVL as a function of distance
Magnitude_low =3.0;
Magnitude   = 3.2;
iMag_int_low=floor((Magnitude_low-0.9)*10+1);
iMag_int=floor((Magnitude-0.9)*10+1);

line_w=2;

figure(1)
plot(xquake./1000,IVL_tot1_final(iMag_int,:,3),'Color',c_lblue,'LineWidth',line_w);hold on
plot(xquake./1000,IVL_tot2_final(iMag_int,:,3),'Color',c_dark,'LineWidth',line_w);hold on
plot(xquake./1000,IVL_tot3_final(iMag_int,:,3),'Color',c_orange,'LineWidth',line_w);hold on
plot(xquake./1000,IVL_tot4_final(iMag_int,:,3),'Color',c_lred,'LineWidth',line_w);hold on
plot(xquake./1000,IVL_tot5_final(iMag_int,:,3),'Color',c_red,'LineWidth',line_w);hold on

plot(xquake./1000,IVL_tot1_final(iMag_int_low,:,3),'Color',c_lblue,'LineWidth',line_w,'LineStyle','--');hold on
plot(xquake./1000,IVL_tot2_final(iMag_int_low,:,3),'Color',c_dark,'LineWidth',line_w,'LineStyle','--');hold on
plot(xquake./1000,IVL_tot3_final(iMag_int_low,:,3),'Color',c_orange,'LineWidth',line_w,'LineStyle','--');hold on
plot(xquake./1000,IVL_tot4_final(iMag_int_low,:,3),'Color',c_lred,'LineWidth',line_w,'LineStyle','--');hold on
plot(xquake./1000,IVL_tot5_final(iMag_int_low,:,3),'Color',c_red,'LineWidth',line_w,'LineStyle','--');hold on

title('total IVL: M_w 2.9 (dotted lines), M_w 3.2 (solid lines)');
xlabel('distance [km]');ylabel('IVL [CHF]');
legend('Iamp = 0','Iamp = 0.25','Iamp = 0.35','Iamp = 0.5','Iamp = 0.75');
grid on

figure(2)
plot(xquake./1000,num_DG1_final(iMag_int,:,2,3),'Color',c_lblue,'LineWidth',line_w);hold on
plot(xquake./1000,num_DG2_final(iMag_int,:,2,3),'Color',c_dark,'LineWidth',line_w);hold on
plot(xquake./1000,num_DG3_final(iMag_int,:,2,3),'Color',c_orange,'LineWidth',line_w);hold on
plot(xquake./1000,num_DG4_final(iMag_int,:,2,3),'Color',c_lred,'LineWidth',line_w);hold on
plot(xquake./1000,num_DG5_final(iMag_int,:,2,3),'Color',c_red,'LineWidth',line_w);hold on

plot(xquake./1000,num_DG1_final(iMag_int_low,:,2,3),'Color',c_lblue,'LineWidth',line_w,'LineStyle','--');hold on
plot(xquake./1000,num_DG2_final(iMag_int_low,:,2,3),'Color',c_dark,'LineWidth',line_w,'LineStyle','--');hold on
plot(xquake./1000,num_DG3_final(iMag_int_low,:,2,3),'Color',c_orange,'LineWidth',line_w,'LineStyle','--');hold on
plot(xquake./1000,num_DG4_final(iMag_int_low,:,2,3),'Color',c_lred,'LineWidth',line_w,'LineStyle','--');hold on
plot(xquake./1000,num_DG5_final(iMag_int_low,:,2,3),'Color',c_red,'LineWidth',line_w,'LineStyle','--');hold on
title('houses in DG1: M_w 2.9 (dotted lines), M_w 3.2 (solid lines)');
xlabel('distance [km]');ylabel('number of houses in DG1');
legend('Iamp = 0','Iamp = 0.25','Iamp = 0.35','Iamp = 0.5','Iamp = 0.75');
grid on

figure(3)
plot(xquake./1000,mCasSum1_final(iMag_int,:,2,3),'Color',c_lblue,'LineWidth',line_w);hold on
plot(xquake./1000,mCasSum2_final(iMag_int,:,2,3),'Color',c_dark,'LineWidth',line_w);hold on
plot(xquake./1000,mCasSum3_final(iMag_int,:,2,3),'Color',c_orange,'LineWidth',line_w);hold on
plot(xquake./1000,mCasSum4_final(iMag_int,:,2,3),'Color',c_lred,'LineWidth',line_w);hold on
plot(xquake./1000,mCasSum5_final(iMag_int,:,2,3),'Color',c_red,'LineWidth',line_w);hold on

plot(xquake./1000,mCasSum1_final(iMag_int_low,:,2,3),'Color',c_lblue,'LineWidth',line_w,'LineStyle','--');hold on
plot(xquake./1000,mCasSum2_final(iMag_int_low,:,2,3),'Color',c_dark,'LineWidth',line_w,'LineStyle','--');hold on
plot(xquake./1000,mCasSum3_final(iMag_int_low,:,2,3),'Color',c_orange,'LineWidth',line_w,'LineStyle','--');hold on
plot(xquake./1000,mCasSum4_final(iMag_int_low,:,2,3),'Color',c_lred,'LineWidth',line_w,'LineStyle','--');hold on
plot(xquake./1000,mCasSum5_final(iMag_int_low,:,2,3),'Color',c_red,'LineWidth',line_w,'LineStyle','--');hold on


title('Casualties C2: M_w 2.9 (dotted lines), M_w 3.2 (solid lines)');
xlabel('distance [km]');ylabel('number of casualties C2');
legend('Iamp = 0','Iamp = 0.25','Iamp = 0.35','Iamp = 0.5','Iamp = 0.75');
grid on


figure(4)
loglog(IVL_tot1(:,3,21),prob1);

% figure(4)
% semilogy(M_Magn1,IVL_tot1(:,3),'Color',c_lblue,'LineWidth',line_w);hold on
% semilogy(M_Magn1,IVL_tot2(:,3),'Color',c_dark,'LineWidth',line_w);hold on
% semilogy(M_Magn1,IVL_tot3(:,3),'Color',c_lred,'LineWidth',line_w);hold on
% semilogy(M_Magn1,IVL_tot4(:,3),'Color',c_red,'LineWidth',line_w);
% title('total IVL as a function of M_w, at 20km distance from the city');
% xlabel('Magnitude M_w');ylabel('IVL [CHF]');
% legend('Iamp = -0.5','Iamp = 0','Iamp = 0.5','Iamp = 1','Location','Best');
% grid on
