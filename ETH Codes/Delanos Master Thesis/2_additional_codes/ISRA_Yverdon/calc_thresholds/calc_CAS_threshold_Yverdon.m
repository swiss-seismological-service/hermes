function [fixed_CAS] = calc_prob_threshold_Yverdon(mCasSum,prob_input,CAS_threshold,CD)
% function [fixed_prob] =
% calc_prob_threshold(IVL_tot,prob_input,prob_threshold)
%
% Input:
% prob_threshold
% mCasSum
% prob_input
% CD: casualty degree

for iDist=1:size(mCasSum,2)
    for iVC=1:size(mCasSum,4)
        % debugging (take care of non-distinct values)
        vSelIVL=~(diff(mCasSum(:,iDist,CD,iVC))==0);vSelIVL=vSelIVL';vSelIVL=[vSelIVL 1];vSelIVL=logical(vSelIVL);
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
        
        fixed_CAS(iDist,iVC)=interp1(mCasSum(vSel,iDist,CD,iVC),prob_input(vSel),CAS_threshold,'linear','extrap');
        if fixed_CAS(iDist,iVC)<0
            fixed_CAS(iDist,iVC)=0.0000000001;
        else
            fixed_CAS(iDist,iVC)=fixed_CAS(iDist,iVC);
        end
    end
end