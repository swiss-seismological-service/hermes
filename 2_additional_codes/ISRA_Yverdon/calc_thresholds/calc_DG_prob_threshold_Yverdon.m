function [fixed_prob_DG] = calc_DG_prob_threshold_Yverdon(num_DG,prob_input,prob_threshold,iDG)
% function [fixed_prob] =
% calc_prob_threshold(IVL_tot,prob_input,prob_threshold)
%
% Input:
% prob_threshold
% IVL_tot
% prob_input

for iDist=1:size(num_DG,2)
    for iVC=1:size(num_DG,4)
        % debugging (take care of non-distinct values)
        vSelIVL=~(diff(num_DG(:,iDist,iDG,iVC))==0);vSelIVL=vSelIVL';vSelIVL=[vSelIVL 1];vSelIVL=logical(vSelIVL);
        vSelHC=~(diff(prob_input)==0);vSelHC=[vSelHC 0];vSelHC=logical(vSelHC);
        for i=1:length(vSelHC)
            if vSelHC(i) == 1 && vSelIVL(i) == 1
                vSel(i) = 1;
            else
                vSel(i) = 0;
            end
        end
        vSel = logical(vSel);
        % end of debugging
        
        fixed_prob_DG(iDist,iVC)=interp1(prob_input(vSel),num_DG(vSel,iDist,iDG,iVC),prob_threshold,'linear','extrap');
        if fixed_prob_DG(iDist,iVC)<0
            fixed_prob_DG(iDist,iVC)=0.0000000001;
        else
            fixed_prob_DG(iDist,iVC)=fixed_prob_DG(iDist,iVC);
        end
    end
end