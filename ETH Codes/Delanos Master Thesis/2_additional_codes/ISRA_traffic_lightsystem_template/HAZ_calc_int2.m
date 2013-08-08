
function [scpint7]=HAZ_calc_int2(b,data,Mmin,Mmax,dm,Int,sGMPE,r_epi,r_hyp,depth_quake_km)



%% Mmax=7
%from min mag to max mag
bgmax=[];
for m=Mmin:dm:Mmax;
    diff=Mmin-m;
    bgm=(data.*10.^(b*diff));
    bgmax=[bgmax bgm];
end

k=length(bgmax)+2;
mBack(:,3:k)=bgmax(:,:);
mBack(:,1)=47.6;mBack(:,2)= 7.5; %% arbitrarily selected location, corresponds to the r=0 distance

scpint7=[];

for j=1:length(Int);
    nIntLevel=Int(j);
    [scgx,scgy,scP,logP] = HAZ_makeSwissBackgroundHazGrid_banu(mBack,nIntLevel,Mmin,Mmax,dm,sGMPE,r_epi,r_hyp,depth_quake_km);
    scpint7=[scpint7 scP];

end



