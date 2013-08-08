%% call_loss
%  this script calls deterministic and probabilistic loss assessment for
%  induced seismicity

clear all;clc;clf; close all;
% close all;


%% General Input Parameters
%  1    Borehole/Quake Coordinates
xquake = 611643;    % CH coordinates of earthquake    
yquake = 270420;
depth_quake = 4700;

%  2    Switch of methods (s... for switch)
%  2.1  GMPE (Ground Motion Prediction Equation
sGMPE=  'ECOS-02'; % ECOS-02, ECOS-02new, ECOS-09, Allen-2012
%  2.2  Site Amplification yes or no?
sAMPL=  'AMPno';  % yes or no
%  2.3  Distribution Functions
sDISTR= 'BinPDF';  % BinPDF, BetaPDF
%  2.4  Cost Functions
sCOST=  'Expert_SER';   % Expert_SER, Cochrane92, Risk_UE, SED_Del

%% Mmin/Mmax for deterministic calc.
M_Mmin =  0.9;    % Magnitude of completeness
M_dm =    0.1;    % Magnitude increment
M_Mmax =  4.5;    % Mmax
M_Magn = M_Mmin:M_dm:M_Mmax;

%% Mmin/Mmax for Probabilistic calc.
Mmin=0.9;
Mmax=4.1;

% %% DATA IMPORT
% %% Load building stock
% load bs_basel_ser.mat
% %  adaption to code: Building Stock's name must be "building_stock"
% building_stock = bs_basel_ser;
% clear bs_basel_ser
% 
% %%  Vulnerability and Building Classification
% mVi_type=importdata('vulnerability_classes_serianex_typology.csv');
% mVi_type=char(mVi_type);
% mVi=importdata('vulnerability_classes_serianex_vi_base.csv');   % just Vo
% %mVi=importdata('vulnerability_classes_serianex_vi_all.csv');   % all Vi
% mVi_EMS=importdata('vulnerability_classes_serianex_vi_EMS.csv');
% mVi_EMS=char(mVi_EMS);
% 
% 
% %% Load data for casualty calc.
% % collapse rates according to World Housing Encyclopedia
% mCollapseRate=load('CollapseRateSwitzerland.dat');
% 
% % casualty matrices
% load casualty_rates.mat
% 
% %% Load forecast rates
% load com.mat
% model = com;
% 
% M_Magn = M_Mmin:M_dm:M_Mmax;
% 
% tic
% %% Code Body
% 
% %%  CODE BODY
% %   all magnitudes loop
% for iMag=1:1:length(M_Magn)
%     %% location/settlement loop
%     % prestorage
%     GMPE_dist = zeros(size(building_stock,2),1); % prestorage
%     for iLoc=1:1:size(building_stock,2)
%         %% GMPE (Ground Motion Prediction Equation)
%         %  Distance Calculation (Earthquake - Settlement)
%         GMPE_dist_hyp(iLoc,1) = (sqrt((xquake-building_stock{iLoc}.xkoordCH)^2+(yquake-building_stock{iLoc}.ykoordCH)^2+depth_quake^2))/1000;
%         GMPE_dist_epi(iLoc,1) = (sqrt((xquake-building_stock{iLoc}.xkoordCH)^2+(yquake-building_stock{iLoc}.ykoordCH)^2))/1000;
%         
%         %  GMPE itself
%         switch sGMPE
%             case 'ECOS-02'
%                 [GMPE_fIobs(iLoc,1)] = fct_GMPE_ECOS_02(M_Magn(iMag),GMPE_dist_epi(iLoc));
%                 % Site Amplification
%                 switch sAMPL
%                     case 'AMPyes'
%                         GMPE_fIobs(iLoc,1)=GMPE_fIobs(iLoc,1)+building_stock{iLoc}.Iamp;
%                     case 'AMPno'
%                         GMPE_fIobs(iLoc,1)=GMPE_fIobs(iLoc,1);
%                 end
%             case 'ECOS-02new'
%                 [GMPE_fIobs(iLoc,1)] = fct_GMPE_ECOS_02_new(M_Magn(iMag),GMPE_dist_epi(iLoc));
%                 % Site Amplification
%                 switch sAMPL
%                     case 'AMPyes'
%                         GMPE_fIobs(iLoc,1)=GMPE_fIobs(iLoc,1)+building_stock{iLoc}.Iamp;
%                     case 'AMPno'
%                         GMPE_fIobs(iLoc,1)=GMPE_fIobs(iLoc,1);
%                 end
%             case 'ECOS-09'
%                 [GMPE_fIobs(iLoc,1)] = fct_GMPE_ECOS_09(M_Magn(iMag),GMPE_dist_hyp(iLoc),depth_quake_km);
%                 % Site Amplification
%                 switch sAMPL
%                     case 'AMPyes'
%                         GMPE_fIobs(iLoc,1)=GMPE_fIobs(iLoc,1)+building_stock{iLoc}.Iamp_ECOS09;
%                     case 'AMPno'
%                         GMPE_fIobs(iLoc,1)=GMPE_fIobs(iLoc,1);
%                 end
%             case 'Allen-2012'
%                 [GMPE_fIobs(iLoc,1)] = fct_GMPE_Allen2012(M_Magn(iMag),GMPE_dist_hyp(iLoc));
%                 % Site Amplification
%                 switch sAMPL
%                     case 'AMPyes'
%                         GMPE_fIobs(iLoc,1)=GMPE_fIobs(iLoc,1)+building_stock{iLoc}.Iamp;
%                     case 'AMPno'
%                         GMPE_fIobs(iLoc,1)=GMPE_fIobs(iLoc,1);
%                 end
%         end
%         
%                 
%         % OUTPUT for plot
%         % 1: iLoc (Location)
%         % 2: iMag (Magnitude)
%         GMPE_fIobs_allLocs_allMags(iLoc,iMag) = GMPE_fIobs(iLoc,1);
%                 
%        
%         %% Building Class and Vuln. Class loop
%         % Vulnerability Classes (V-, Vo, V+) loop
%         for iVC=1:1:size(mVi,2) % 1 vulnerability class so far
%             % Building classes (BC) loop
%             for iBC=1:1:size(mVi,1) % mVi= vulnerability index for 16 building classes (building typologies)
%                 %% Mean Damage Grade (fMDG)
%                 [fMDG(iBC,iVC)] = fct_mean_damage_degree(GMPE_fIobs(iLoc),mVi(iBC,iVC));
%                 %                 plot(fMDG);  hold on;
%                 % OUTPUT for plot
%                 % 1: iBC   (Building Class)
%                 % 2: iMag  (Magnitude)
%                 % 3: iVC   (V-, Vo, V+)
%                 % 4: iLoc  (Location)
%                 fMDG_allVC_allLocs_allMags(iBC,iMag,iVC,iLoc) = fMDG(iBC,iVC);
%                 
%                 %% Probability Density Functions (PDF)
%                 switch sDISTR
%                     case 'BinPDF'
%                         [mBinPDF(iBC,:)] = fct_damage_grade_distribution_bin(fMDG(iBC,iVC));
%                         PDF = mBinPDF;
%                         
%                         % OUTPUT for plot
%                         % 1: iBC    (Building Class)
%                         % 2: DG     (Damage Grade, 0-5)
%                         % 3: iVC     (V-, Vo, V+)
%                         % 4: iLoc   (Location)
%                         % 5: iMag   (Magnitude)
%                         PDF_allVC_allLocs_allMags(iBC,:,iVC,iLoc,iMag) = PDF(iBC,:);
%                         
%                     case 'BetaPDF'
%                         [mBetaPDF(iBC,:)] = fct_damage_grade_distribution_beta(fMDG(iBC,iVC));
%                         % Eliminating NaN
%                         for i=1:1:size(mBetaPDF,1)
%                             for j=1:1:size(mBetaPDF,2)
%                                 if isnan(mBetaPDF(i,j))==1
%                                     if j==1
%                                         mBetaPDF(i,j)=1;
%                                     else
%                                         mBetaPDF(i,j)=0;
%                                     end
%                                 else
%                                     mBetaPDF(i,j) = mBetaPDF(i,j);
%                                 end
%                             end
%                         end %end elimination NaN
%                         PDF = mBetaPDF;
%                         % OUTPUT for plot
%                         % 1: iBC    (Building Class)
%                         % 2: DG     (Damage Grade, 0-5)
%                         % 3: iVC     (V-, Vo, V+)
%                         % 4: iLoc   (Location)
%                         % 5: iMag   (Magnitude)
%                         PDF_allVC_allLocs_allMags(iBC,:,iVC,iLoc,iMag) = PDF(iBC,:);
%                         
%                 end %end switch PDF
%                 
%                 
%                 %% Insured Value Loss (IVL)
%                 % number of buildings in each damage class
%                 num_build_BC_DG(iBC,:) = PDF(iBC,:).*num_build_vuln(iBC,iLoc);
%                 num_build_per_BC_DG(iBC,:,iVC,iLoc,iMag)=num_build_BC_DG(iBC,:);
%                 
%                 %% Casualties (QLARM adapted code)
%                 % modify damage rates (EMS -> HAZUS damage states)
%                 mDam_mod=PDF;
%                 mDam_mod(isinf(mDam_mod))=0;
%                 for i=1:size(mDam_mod,2)
%                     fKC=interp1(1:12,mCollapseRate(i,:),GMPE_fIobs(iLoc))/100;
%                     mDam_mod(5)=(1-fKC).*(PDF(5) + PDF(6)); % get non-collapsed buildings
%                     mDam_mod(6)=fKC.*(PDF(5) + PDF(6));     % get collapsed building
%                 end
%                 
%                 % Casualty rates
%                 % loop over all casualty degrees
%                 switch mVi_EMS(iBC)
%                     case {'A','B'}
%                         for iC=1:5; % Going through all casualty degrees
%                             mCas(iC,:)=mDam_mod(1,:).*mICM1(iC,:);
%                         end
%                     case {'C'}
%                         for iC=1:5; % Going through all casualty degrees
%                             mCas(iC,:)=mDam_mod(1,:).*mICM2(iC,:);
%                         end
%                     case {'D','E','F'}
%                         for iC=1:5; % Going through all casualty degrees
%                             mCas(iC,:)=mDam_mod(1,:).*mICM3(iC,:);
%                         end
%                 end %end switch EMS
%                                 
%                 % Calculation of the number of casualties per BC
%                 % perc_build(iBC,iLoc)=num_build_vuln(iBC,iLoc)/building_stock{iLoc}.Build_tot; % get percentage of people in BC
%                 % 1: iBC, 2: iC, 3: DG
%                 mNoCas(iBC,:,:)=mCas*building_stock{iLoc}.Pop*perc_build(iBC,iLoc);
%                  
%                 % total no of casualties per c. degree
%                 % Casualty degrees: C1- non injured; C2 - slightly injured; C3 -
%                 % moderately injured; C4 - seriously injured; C5 - dying or dead
%                 % 1: BC
%                 % 2: Casualty Degree
%                 mCasSum = sum(mNoCas,3);
%                 
%               
%             end %end BC loop
%             
%             % Output for plot:
%             % 1: DG     (Damage Grade, 0-5)
%             % 2: iVC     (V-, Vo, V+)
%             % 3: iLoc   (Location)
%             % 4: iMag   (Magnitude) 
%             num_build_per_DG(:,iVC,iLoc,iMag) = sum(num_build_BC_DG,1);
%             
%             
%             % summing casualties over all BC
%             mCasSum_BC(iMag,iLoc,iVC,:) = sum(mCasSum,1);
%            
%                 
%             %% IVL continued: insured value loss per BC and DG
%             
%             % COST FUNCTION
%             % percentage of Insured Building Value to pay for each DG
%             switch sCOST    % Expert_SER, Cochrane92, Risk_UE
%                 case 'Expert_SER'
%                     repcost = [0 .02 .15 .55 .91 1];
%                 case 'Cochrane92'
%                     repcost = [0 .05 .20 .58 .94 1];
%                 case 'Risk_UE'
%                     repcost = [0 .01 .10 .35 .75 1];
%                 case 'SED_Del'
%                     repcost = [0 .006 .10 .35 .75 1];
%             end %end sCOST
%             
%             for i=1:1:size(repcost,2)
%                 IVL_BC_DG_aux(:,i) = num_build_BC_DG(:,i).*repcost(1,i);
%             end
%             IVL_BC_DG = IVL_BC_DG_aux.*building_stock{iLoc}.ins_value_bdg;
%             % OUTPUT for plot
%             % 1: iBC    (Building Class)
%             % 2: DG     (Damage Grade, 0-5)
%             % 3: iVC     (V-, Vo, V+)
%             % 4: iLoc   (Location)
%             % 5: iMag   (Magnitude)
%             IVL_BC_DG_allVC_allLocs_allMags(:,:,iVC,iLoc,iMag) = IVL_BC_DG(:,:);
%             
%             IVL_DG = sum(IVL_BC_DG);
%             % OUTPUT for plot
%             % 1: DG     (Damage Grade, 0-5)
%             % 2: iVC     (V-, Vo, V+)
%             % 3: iLoc   (Location)
%             % 4: iMag   (Magnitude)
%             IVL_DG_aux = IVL_DG';
%             IVL_DG_allVC_allLocs_allMags(:,iVC,iLoc,iMag) = IVL_DG_aux;
%             
%             IVL_BC = sum(IVL_BC_DG,2);
%             % OUTPUT for plot
%             % 1: iBC    (Building Class)
%             % 2: iVC     (V-, Vo, V+)
%             % 3: iLoc   (Location)
%             % 4: iMag   (Magnitude)
%             IVL_BC_allVC_allLocs_allMags(:,iVC,iLoc,iMag) = IVL_BC;
%             
%             IVL_tot_loc(iLoc,iVC) = sum(sum(IVL_BC_DG));
%             % OUTPUT for plot
%             % 1: iLoc   (Location)
%             % 2: iVC     (V-, Vo, V+)
%             % 3: iMag   (Magnitude)
%             IVL_tot_allLocs_allMags(iLoc,iVC,iMag) = IVL_tot_loc(iLoc,iVC);
%             
%             stand = [M_Magn(iMag) iVC];
%             disp('Magn/Vuln.Class:')
%             disp(stand)    
%         end %end Vuln. Class (V-, Vo, V+) loop
%         
%     end %end location/settlement loop
%     %% summing IVL over all locations
%     % 1: iMag  (Magnitude)
%     % 2: iVC   (V-, Vo, V+)
%     IVL_tot(iMag,:) = sum(IVL_tot_loc,1);
%     
%     
%           
%     %disp('Magnitude:')
%     %disp(M_Magn(iMag))
%     end %end magnitude loop
% toc
% 
% %% summing casualties over all locations
%     % 1: iMag   (Magnitude)
%     % 2: iLoc   (Location, always 1)
%     % 3: iVC    (V-, Vo, V+)
%     % 4: iC     (casualty degree)
%     mCasSum_allMagVC = sum(mCasSum_BC,2);
% 
% %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% %%%%%%%%%%             SAVING DETERMINISTIC PART               %%%%%%%%%%%    
% %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%    
% M_Mmax_name = num2str(M_Mmax);
% filename_det = ['det_int3_6.5_' sGMPE '_' sDISTR '_' sAMPL '_' sCOST '_Mmax_' M_Mmax_name '.mat'];
% save(filename_det);


load det_int3_6.5_ECOS-02_BinPDF_AMPno_Expert_SER_Mmax_4.1.mat

%% HAZARD CURVE CALCULATION
for ii=1:size(GMPE_fIobs_allLocs_allMags,1);
    Intensity(ii).vec=GMPE_fIobs_allLocs_allMags(ii,:);
end


datax=sum(com(1:48)); % Total rates in 12 days during stimulation period
% datax=sum(model(1:24)); % Total rates in 12 days during stimulation period
b=1.5;
dm=M_dm;
r_epi=GMPE_dist_epi;
r_hyp=GMPE_dist_hyp;
for i=1:length(r_epi); % here r_epi is taken, because length(r_epi)=length(r_hyp)
    Int=Intensity(i).vec;
    [scp7]=HAZ_calc_int2(b,datax,Mmin,Mmax,dm,Int,sGMPE,r_epi(i),r_hyp(i),depth_quake);
    HC(i).scp=scp7; % Hazard curve at different locations
    clear Int;
end

% FRAGILITY CURVES FOR EACH DAMAGE GRADE (DG=[0 1 2 3 4 5])
for iLoc=1:size(building_stock,2); % for 79 settlement locations
    % for j=1:1; % for 79 settlement locations
    HAZ=HC(iLoc).scp;
    HAZ=HAZ';
    for iVC=1:size(mVi,2); % (5) vulnerability classes
        for iBC=1:size(mVi,1); % 16 building classes
            % FRAGILITY CURVE
            fr1=zeros(length(M_Magn),1); fr1(:)=PDF_allVC_allLocs_allMags(iBC,1,iVC,iLoc,:);fr1_all(:,iBC,iVC,iLoc)=fr1;
            fr2=zeros(length(M_Magn),1); fr2(:)=PDF_allVC_allLocs_allMags(iBC,2,iVC,iLoc,:);fr2_all(:,iBC,iVC,iLoc)=fr2;
            fr3=zeros(length(M_Magn),1); fr3(:)=PDF_allVC_allLocs_allMags(iBC,3,iVC,iLoc,:);fr3_all(:,iBC,iVC,iLoc)=fr3;
            fr4=zeros(length(M_Magn),1); fr4(:)=PDF_allVC_allLocs_allMags(iBC,4,iVC,iLoc,:);fr4_all(:,iBC,iVC,iLoc)=fr4;
            fr5=zeros(length(M_Magn),1); fr5(:)=PDF_allVC_allLocs_allMags(iBC,5,iVC,iLoc,:);fr5_all(:,iBC,iVC,iLoc)=fr5;
            fr6=zeros(length(M_Magn),1); fr6(:)=PDF_allVC_allLocs_allMags(iBC,6,iVC,iLoc,:);fr6_all(:,iBC,iVC,iLoc)=fr6;
        
            % GLOBAL DAMAGE GRADE PROBABILITY DISTRIBUTION = FRAGILITY CURVE X HAZARD CURVE
            PO1=fr1.*HAZ; % HAZARD  X FRAGILITY = GLOBAL DAMAGE GRADE PROBABILITY DISTRIBUTION
            PO2=fr2.*HAZ; % HAZARD  X FRAGILITY = GLOBAL DAMAGE GRADE PROBABILITY DISTRIBUTION
            PO3=fr3.*HAZ; % HAZARD  X FRAGILITY = GLOBAL DAMAGE GRADE PROBABILITY DISTRIBUTION
            PO4=fr4.*HAZ; % HAZARD  X FRAGILITY = GLOBAL DAMAGE GRADE PROBABILITY DISTRIBUTION
            PO5=fr5.*HAZ; % HAZARD  X FRAGILITY = GLOBAL DAMAGE GRADE PROBABILITY DISTRIBUTION
            PO6=fr6.*HAZ; % HAZARD  X FRAGILITY = GLOBAL DAMAGE GRADE PROBABILITY DISTRIBUTION
        
            
            P1=sum(PO1); PO1_all(:,iBC,iVC,iLoc)=PO1;
            P2=sum(PO2); PO2_all(:,iBC,iVC,iLoc)=PO2;
            P3=sum(PO3); PO3_all(:,iBC,iVC,iLoc)=PO3;
            P4=sum(PO4); PO4_all(:,iBC,iVC,iLoc)=PO4;
            P5=sum(PO5); PO5_all(:,iBC,iVC,iLoc)=PO5;
            P6=sum(PO6); PO6_all(:,iBC,iVC,iLoc)=PO6;
            
            POC=[P1 P2 P3 P4 P5 P6]; % PROBABILITY OF OCCURENCE vs. DAMAGE GRADE (Figure 36 in SERIANEX AP5000-93/124)
            POC_norm = POC./POC(1);
            POC_all(:,iBC,iVC,iLoc)=POC;
            POC_norm_all(:,iBC,iVC,iLoc)=POC_norm;
            
            % most probable affected building number
            num_build_BC_DG_PROB(iLoc,iVC,iBC,:) = (POC.*repcost).*num_build_vuln(iBC,iLoc);
            % Most probable insured value loss
            IVL_loc_BC_DG_PROB(iLoc,iVC,iBC,:) = num_build_BC_DG_PROB(iLoc,iVC,iBC,:).*building_stock{iLoc}.ins_value_bdg;
            
            % POC-normed
            % most probable affected building number
            num_build_BC_DG_PROB_norm(iLoc,iVC,iBC,:) = (POC_norm.*repcost).*num_build_vuln(iBC,iLoc);
            % Most probable insured value loss
            IVL_loc_BC_DG_PROB_norm(iLoc,iVC,iBC,:) = num_build_BC_DG_PROB_norm(iLoc,iVC,iBC,:).*building_stock{iLoc}.ins_value_bdg;
            
            % summing over all DG
             IVL_tot_BC_PROB(iLoc,iVC,iBC) = sum(IVL_loc_BC_DG_PROB(iLoc,iVC,iBC,:));
            IVL_tot_BC_PROB_norm(iLoc,iVC,iBC) = sum(IVL_loc_BC_DG_PROB_norm(iLoc,iVC,iBC,:));
            
        PIC(iBC).d=POC;
        
        clear POC;
        end %iBC
        
        % summing over all BC
        IVL_tot_loc_VC_PROB(iLoc,iVC) = sum(IVL_tot_BC_PROB(iLoc,iVC,:));
        IVL_tot_loc_VC_PROB_norm(iLoc,iVC) = sum(IVL_tot_BC_PROB_norm(iLoc,iVC,:));
        
    end %iVC
    clear HAZ;
    

end %iLoc

% summing over all localities
for iVC=1:1:size(mVi,2)
    IVL_tot_PROB(iVC) = sum(IVL_tot_loc_VC_PROB(:,iVC))
    IVL_tot_PROB_norm(iVC) = sum(IVL_tot_loc_VC_PROB_norm(:,iVC))
end


    
% %%SAVING
% % Saving intermediate steps
% Mmax_name = num2str(M_Mmax);
% filename_inter_steps = ['sumDel_int_prob_Mmax_'...
%      Mmax_name '_' sGMPE '_' sDISTR];
% save(filename_inter_steps,...
%     'mVi_type',...    
%     'M_Magn',...
%     'GMPE_fIobs_allLocs_allMags',...
%     'fMDG_allVC_allLocs_allMags',...
%     'PDF_allVC_allLocs_allMags',...
%     'fr1_all',...
%     'fr2_all',...
%     'fr3_all',...
%     'fr4_all',...
%     'fr5_all',...
%     'fr6_all',...
%     'PO1_all',...
%     'PO2_all',...
%     'PO3_all',...
%     'PO4_all',...
%     'PO5_all',...
%     'PO6_all',...
%     'POC_all',...
%     'POC_norm_all',...
%     'HC',...
%     'IVL_tot_PROB',...
%     'IVL_tot_PROB_norm'...
%     );



%% PLOTING
%% Plot over all magnitudes
XX=num2str(round(IVL_tot(24)));
X=[XX,' CHF'];
figure;
semilogy(M_Magn,IVL_tot(:,1),'*-k','LineWidth',2); hold on;
semilogy(3.2,IVL_tot(24),'ro','MarkerSize',12,'MarkerFaceColor','r'); hold on;
semilogy(3.7,IVL_tot(29),'ro','MarkerSize',12,'MarkerFaceColor','r'); hold on;
semilogy(4.1,IVL_tot(33),'ro','MarkerSize',12,'MarkerFaceColor','r'); hold on;
% text(3.2,IVL_tot(24),X); hold on;
set(gca,'LineWidth',2,'FontSize',24,'FontWeight','normal','FontName','Times')
set(get(gca,'Title'),'String','Deterministic Loss Curve','FontSize',24,'FontName','Times')
set(get(gca,'XLabel'),'String','Magnitude','FontSize',24,'FontName','Times')
set(get(gca,'YLabel'),'String','IVL [CHF]','FontSize',24,'FontName','Times')
grid on;
% SERIANEX RESULTS
Mser=[3.2 3.7 4.1];
IVLser=[10521479 53946072 158832248];
semilogy(Mser,IVLser,'^g','MarkerSize',10,'MarkerFaceColor','g');



% RATES IN MAGNITUDE BINS
[C_forecast_magbin]=calc_rates_magbins2(model,M_Mmin,M_Mmax,dm);

% LOSS x RATES = PROBABILITY OF INSURED VALUE LOSS
prob=IVL_tot(2:end).*C_forecast_magbin';

%% Deterministic
figure; subplot(3,1,1);
semilogy(M_Magn,IVL_tot(:,1),'*-k','LineWidth',2); ylim([10^-2 10^12]);
set(gca,'LineWidth',2,'FontSize',24,'FontWeight','normal','FontName','Times')
set(get(gca,'YLabel'),'String','IVL [CHF]','FontSize',24,'FontName','Times')
subplot(3,1,2);
plot(M_Magn(2:end),C_forecast_magbin,'k','LineWidth',2);
set(gca,'LineWidth',2,'FontSize',24,'FontWeight','normal','FontName','Times')
set(get(gca,'YLabel'),'String','Rates in M bins','FontSize',24,'FontName','Times')
subplot(3,1,3);
plot(M_Magn(2:end),prob,'k','LineWidth',2);
set(gca,'LineWidth',2,'FontSize',24,'FontWeight','normal','FontName','Times')
set(get(gca,'XLabel'),'String','Magnitude','FontSize',24,'FontName','Times')
set(get(gca,'YLabel'),'String','Prob. of IVL','FontSize',24,'FontName','Times')



%% PROBABILISTIC LOSS CURVE
for Loc=1:1:size(building_stock,2);
    ind1(Loc)=max(find(min(abs(HC(Loc).scp-1))==abs(HC(Loc).scp-1)));
    ind2(Loc)=max(find(min(abs(HC(Loc).scp-0.1))==abs(HC(Loc).scp-0.1)));
    ind3(Loc)=max(find(min(abs(HC(Loc).scp-0.01))==abs(HC(Loc).scp-0.01)));
    ind4(Loc)=max(find(min(abs(HC(Loc).scp-0.001))==abs(HC(Loc).scp-0.001)));

    
%     Int1(Loc)=GMPE_fIobs_allLocs_allMags(Loc,ind1(Loc));
%     Int2(Loc)=GMPE_fIobs_allLocs_allMags(Loc,ind2(Loc));
%     Int3(Loc)=GMPE_fIobs_allLocs_allMags(Loc,ind3(Loc));
%     Int4(Loc)=GMPE_fIobs_allLocs_allMags(Loc,ind4(Loc));
    
    IVL1(Loc)=IVL_tot_allLocs_allMags(Loc,1,ind1(Loc));
    IVL2(Loc)=IVL_tot_allLocs_allMags(Loc,1,ind2(Loc));
    IVL3(Loc)=IVL_tot_allLocs_allMags(Loc,1,ind3(Loc));
    IVL4(Loc)=IVL_tot_allLocs_allMags(Loc,1,ind4(Loc));
    
end

IVLOSS1=sum(IVL1);
IVLOSS2=sum(IVL2);
IVLOSS3=sum(IVL3);
IVLOSS4=sum(IVL4);

exrate=[1 0.1 0.01 0.001];
losses=[IVLOSS1 IVLOSS2 IVLOSS3 IVLOSS4];

exrate_ser=[1 0.1 0.01 0.001];
losses_ser=[2.5 122 390 968];

figure;
loglog(losses./10^6,exrate,'ko-','LineWidth',2,'DisplayName','SED'); grid on;hold on;
loglog(losses_ser,exrate_ser,'ro-','LineWidth',2,'DisplayName','SERIANEX');
set(gca,'LineWidth',2,'FontSize',24,'FontWeight','normal','FontName','Times')
set(get(gca,'XLabel'),'String','Insured Value Loss (Million CHF)','FontSize',24,'FontName','Times')
set(get(gca,'YLabel'),'String','12 Days Exceedance Rate','FontSize',24,'FontName','Times')
set(get(gca,'Title'),'String','Probabilistic Loss Curve','FontSize',24,'FontName','Times')

legend('show','Location','Best');

%%
matris=zeros(length(GMPE_dist),length(M_Magn));
for ii=1:length(M_Magn);
    for Loc=1:length(GMPE_dist);
            matris(Loc,ii)=IVL_tot_allLocs_allMags(Loc,1,ii);
    end
end


for jj=1:length(M_Magn);
    tot_loss(jj)=sum(matris(:,jj));
end
    

prob=HC(1).scp;

figure;
loglog(losses,exrate,'ko-','LineWidth',2); grid on;
hold on;
loglog(tot_loss,prob,'g','LineWidth',2); 
set(gca,'LineWidth',2,'FontSize',24,'FontWeight','normal','FontName','Times')
set(get(gca,'XLabel'),'String','Insured Value Loss (CHF)','FontSize',24,'FontName','Times')
set(get(gca,'YLabel'),'String','12 Days Exceedance Rate','FontSize',24,'FontName','Times')
set(get(gca,'Title'),'String','Probabilistic Loss Curve','FontSize',24,'FontName','Times')
axis([10^6 10^11 10^-3 1])






% PLOTING
% HAZARD CURVE
figure;
for i=1:79;
    semilogy(GMPE_fIobs_allLocs_allMags(i,:),HC(i).scp); hold on;
end
ylabel('Probability of exceeding EMS intensity','FontSize',20);
xlabel('EMS Intensity','FontSize',20);
legend('Mmax=7');
ylim([10^-4 10^0]);
xlim([2 10]);
grid on;
set(gca,'LineWidth',2,'FontSize',24,'FontWeight','normal','FontName','Times')
set(get(gca,'XLabel'),'String','EMS Intensity','FontSize',24,'FontName','Times')
set(get(gca,'YLabel'),'String','Probability of exceeding EMS intensity','FontSize',24,'FontName','Times')




