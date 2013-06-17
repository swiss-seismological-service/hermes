function [mBetaPDF] = fct_damage_grade_distribution_beta(fMDG)
% function [mBetaPDF] = fct_damage_grade_distribution(fMDG)
% -------------------------------------------------------------------------
% Calculation of Mean Damage Grade Distribution, Beta-Distribution
% using Mean Damage Degree (fMDG)
% Formula:
%
% 
% Function written by Delano Landtwing, 16.05.2012, delanol@ethz.ch
%
% Incoming:
% fMDG           matrix containing Mean Damage Degrees at different
%                settlements and vulnerability classes
%
% Outcoming:     mBetaPDF
% 

% calculation of damage rate
    t=8;a=0;b=6;
    r=t*(0.007*fMDG.^3-0.052*fMDG.^2+0.2875.*fMDG);
    vXfinal=[0:5]';
    vX=[0.1:0.1:b]';
    vXi=[a:0.1:b]';
    
   
    % beta distribution pdf
    %  see also test_BetaDistribution
    for kr=1:size(r,1)
        Y=@(x)(x-a).^(r(kr)-1).*(b-x).^(t-r(kr)-1).*(b-a)^(-t+1).*gamma(t)./(gamma(r(kr)).*gamma(t-r(kr)));
        for kx=1:size(vX,1)
            vY(kx)=Y(vX(kx));
            %     %             y_pdf(kr,kx)=Y(vX(kx));
            %             y_cdf(kr,kx)=quad(Y,0,vX(kx),1e-3);
        end;
        vY=vY';
        vY(end)=vY(end-1);
        vYi=interp1(vX,vY,vXi,'linear','extrap');
        vYi(vYi<0)=0;
        vY2i=cumsum(vYi)./sum(vYi);
        
        for kx=1:size(vXfinal,1)
            vYcdf(kx)=vY2i(find(vXi==vXfinal(kx)));
        end;
        vYcdf=[vYcdf 1]';
        for kx=1:size(vYcdf,1)-1
            mBetaPDF(kr,kx)=vYcdf(kx+1)-vYcdf(kx);
        end
        clear vYcdf
    
    end;

    
