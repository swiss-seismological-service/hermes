function [fixed_IVL] = calc_IVL_threshold(IVL_tot,prob_input,IVL_threshold)
% % function [fixed_IVL] =
% % calc_IVL_threshold(IVL_tot,prob_input,IVL_threshold)
% %
% % Input:
% % IVL_threshold
% % IVL_tot
% % prob_input

for iVC=1:size(IVL_tot,2)
        % debugging (take care of non-distinct values)
        vSelIVL=~(diff(IVL_tot(:,iVC))==0);vSelIVL=vSelIVL';vSelIVL=[vSelIVL 1];vSelIVL=logical(vSelIVL);
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
                
        fixed_IVL(iVC)=interp1(IVL_tot(vSel,iVC),prob_input(vSel),IVL_threshold,'linear','extrap');
        if fixed_IVL(iVC)<0
            fixed_IVL(iVC)=0.0000000001;
        else
            fixed_IVL(iVC)=fixed_IVL(iVC);
        end
end
