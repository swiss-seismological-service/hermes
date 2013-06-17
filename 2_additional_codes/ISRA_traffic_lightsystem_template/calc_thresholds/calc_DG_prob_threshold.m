function [fixed_DG_prob] = calc_DG_prob_threshold(DG,prob_input,prob_threshold,iDG)
% % function [fixed_IVL] =
% % calc_IVL_threshold(IVL_tot,prob_input,IVL_threshold)
% %
% % Input:
% % IVL_threshold
% % IVL_tot
% % prob_input

for iVC=1:size(DG,3)
        % debugging (take care of non-distinct values)
        vSelIVL=~(diff(DG(:,iDG,iVC))==0);vSelIVL=vSelIVL';vSelIVL=[vSelIVL 1];vSelIVL=logical(vSelIVL);
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
                
        fixed_DG_prob(iVC)=interp1(prob_input(vSel),DG(vSel,iDG,iVC),prob_threshold,'linear','extrap');
        if fixed_DG_prob(iVC)<0
            fixed_DG_prob(iVC)=0.1;
        else
            fixed_DG_prob(iVC)=fixed_DG_prob(iVC);
        end
end
