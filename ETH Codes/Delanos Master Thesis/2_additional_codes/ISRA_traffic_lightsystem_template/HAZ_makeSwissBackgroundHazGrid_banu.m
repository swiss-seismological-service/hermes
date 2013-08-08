function [scgx,scgy,scP,logP] = HAZ_makeSwissBackgroundHazGrid_banu(mBackGroundRates,nIntLevel,Mmin,Mmax,dm,sGMPE,r_epi,r_hyp,depth_quake_km)
% function[scgx,scgy,scP,logP] = HAZ_makeSwissBackgroundHazGrid(sFileIn,sFileOut,nIntLevel)
% -------------------------------------------------------------------------
% Calculate probabilities of exceeding EMS level V for the background in
% Switzerland
%
% Incoming:
% mBackGroundRates: Yearly background seismicity rates
%                   Format: [lat lon m=4 m=4.1 ... m=8]
% sFileOut        : Filename of output file saving scgx,scgy,scP,logP
%
% Outgoing
% scgx: Latitude
% scgy: Longitude
% scP : probability of exceeding EMS level
% logP: log10 probability of exceeding EMS level
%
% J. Woessner, j.woessner@sedc.ethz.ch

% THIS FILE ONLY GOES FROM M4-M8
bvg = mBackGroundRates;
bvg = [zeros(length(bvg(:,1)),1) bvg];
bvg(:,2) = mBackGroundRates(:,1);
bvg(:,3) = mBackGroundRates(:,2);
%minimum magnitude and maximum magnitude
RDefs.MMIN = Mmin;
RDefs.MMAX = Mmax;
RDefs.pgalev = nIntLevel; % This is EMS intensity level!!!!

% integration solution params for full hazard calculation
d1 = .0498673470;
d2 = .0211410061;
d3 = .0032776263;
d4 = .0000380036;
d5 = .0000488906;
d6 = .0000053830;

% Swiss attenuation relation parameters for Mag->MMI
% a70 = 1.27;
% b70 = -0.096;
% c70 = 0.043;
% a200 = 1.27;
% b200 = 1.93;
% c200 = 0.0064;
% sigmaCH = .5; %%% THIS IS ABSOLUTELY MADE UP!!!!!!!

NumRates = length(RDefs.MMIN:dm:RDefs.MMAX);
leng = length(bvg(:,1))*NumRates;
Y0 = zeros(leng,1);
sigma = zeros(leng,1);
Pn = zeros(leng,1);
x = zeros(leng,1);
%FindInd = (1:NumRates:leng);
FindInd = (1:NumRates);

% Forecast period in days

%nIntLevel
% Normalize to day
% bvg(:,4:NumRates+3) = bvg(:,4:NumRates+3)./365.25;
% T = 0.25; bvg(:,4:NumRates+3) = bvg(:,4:NumRates+3).*4;
% T = 12; bvg(:,4:NumRates+3) = bvg(:,4:NumRates+3)./12;
% T = 6; bvg(:,4:NumRates+3) = bvg(:,4:NumRates+3)./6;
%  T = 6; bvg(:,4:NumRates+3) = bvg(:,4:NumRates+3);
% T = 12; bvg(:,4:NumRates+3) = bvg(:,4:NumRates+3);
T = 1; bvg(:,4:NumRates+3) = bvg(:,4:NumRates+3);   % for daily calculation


le = length(bvg(:,1));
le2 = le*length(RDefs.MMIN:dm:RDefs.MMAX);
Y0 = zeros(le2,1);

ste = (1:le:le2+le);

sP = bvg(:,4:NumRates+3);
[lP wP] = size(sP);
P = reshape(sP',lP*wP,1);
nanP = isnan(P);
P(nanP) = [];
Rate = P;


K = 0;
for i = 1:length(bvg(:,1));
    K = 0;
    if rem(i,100) == 0
        i
    end
%     xl = bvg(i,2);
%     yl = bvg(i,3);
%     di2 = deg2km((distance(bvg(:,3),bvg(:,2),repmat(yl,le,1),repmat(xl,le,1))));
%     l = di2 < 1;
%     di2(l) = di2(l)*+1;
%     r = di2
% %     r=4
%     lenY = max(size(r));

    %%
    % Attenuation relationshiop for Switzerland
    % there are different params for distances of >= 70km
    %
    % This is the Mag->MMI relationship
    %%
    Ks = 0;
    for m = RDefs.MMIN:dm:RDefs.MMAX;
        Ks = Ks + 1;
        
        switch sGMPE
            case 'ECOS-02'
                [fIobs] = fct_GMPE_ECOS_02(m,r_epi);
                sigmaGMPE = 0.1; %%% THIS IS ABSOLUTELY MADE UP!!!!!!!
            case 'ECOS-02new'
                [fIobs] = fct_GMPE_ECOS_02_new(m,r_epi);
                sigmaGMPE = 0.1; %%% THIS IS ABSOLUTELY MADE UP!!!!!!!
            case 'ECOS-09'
                [fIobs] = fct_GMPE_ECOS_09(m,r_hyp,depth_quake_km);
                sigmaGMPE = 0.1; %%% THIS IS ABSOLUTELY MADE UP!!!!!!!
            case 'Allen-2012'
                [fIobs,sigma_Allen] = 0.1;%fct_GMPE_Allen2012(m,r_hyp);
                sigmaGMPE = sigma_Allen; 
        end        
        Y = [fIobs];
             
        %Y = a70*m-b70-c70*r ;
%         isDistant = r >  55;
%         Y(isDistant) = a200*m-b200-c200*r(isDistant);
        Y0(FindInd(Ks)) = Y;
        sigma(FindInd(Ks)) = sigmaGMPE;
    end



    %% California relationship BJF/Wald
    %         for m = MMIN:dm:MMAX
    %             K = K+1;
    %             %Y = 0.53*(m-6) - 0.39*log(r.^2 + 31) + 0.25;
    %             Yunder5 = 2.4066+1.3171*(m-6)-1.757*log(sqrt(r.^2 + 6^2)) - 0.473*log(620/760);
    %             YGreater5 = -.313+.527*(m-6) -.778*log(sqrt(r.^2 + 5.57^2)) - 0.371*log(620/1396);
    %             RampfL = (5 - m);
    %             RampfH = (m - 4);
    %             if RampfL < 0
    %                RampfL = 0;
    %             end
    %            if RampfH > 1
    %                RampfH = 1;
    %            end
    %            Y = Yunder5*RampfL+YGreater5*RampfH;
    %             %Y = exp(Y);
    %             Y0(ste(K):ste(K+1)-1) = Y;
    %         end

    % K=0;  % Reset counter
    %pga = zeros(0:0.02:0.8,2);
    %I = 0;
    %Sum up all obs groud motions

    %%
    % Y0: PGA @ each node for each Mag (each source)
    % Pn: Probability of exceeding each PGA were an event to occur in the Magbin
    % Rate: Daily rate of forecasted events
    % RateTot: Pn*Rate = Rate of exceeding a PGA k based on forecast
    %          in each MBIN for each grid node
    % pg: total rate of events exceeding each PGA
    %%

    %% full hazard calc for  events
    xTop = (RDefs.pgalev)-Y0;
    x = xTop./sigma;
    isBelow = x <= 0;
    x(isBelow) = -x(isBelow);
    mPn = 0.5 * (((((((d6*x+d5).*x+d4).*x+d3).*x+d2).*x+d1).*x+1).^-16);
    mPn(isBelow) = 1-mPn(isBelow);
    Pn = mPn;
    RateTot = (Pn).*Rate;

    %% median hazard calc
    %mPn = (1+ c1*x + c2*x.^2 + c3*x.^3 + c4*x.^4);
    
    % Total rate
    mmiRate = sum(RateTot);
    % Probability of exceeding
    probMMI = 1-exp(-mmiRate*T);

    %% pga contains the rate of events that exceed a given ga (in steps of ga)
    bvg(i,NumRates+1) = probMMI;
    
    bvg(i,NumRates+2) = mmiRate;

end  % for i

% Reformat
logP = log10(bvg(:,NumRates+1));
scgx = bvg(:,2);
scgy = bvg(:,3);
scP = bvg(:,NumRates+1);

% Saving the file
%save(sFileOut,'scgx','scgy','scP','logP');

%% reshape it for a plot
%rsx = reshape(scgx,36,61);
%rsy = reshape(scgy,36,61);
%rsc = reshape(logP,36,61);

%figure
%pcolor(rsx,rsy,rsc);
%shading flat
%colorbar
