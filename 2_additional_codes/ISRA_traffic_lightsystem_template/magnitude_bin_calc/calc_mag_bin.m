function [bgmax]=calc_mag_bin(b,data,Mmin,Mmax,dm)



%% Mmax=7
%from min mag to max mag
bgmax=[];
for m=Mmin:dm:Mmax;
    diff=Mmin-m;
    bgm=(data.*10.^(b*diff));
    bgmax=[bgmax bgm];
end