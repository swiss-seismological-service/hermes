function [fbinPDF] = fct_damage_grade_distribution_bin(fMDG,s)
% function [fDGD] = fct_damage_grade_distribution(fMDG)
% -------------------------------------------------------------------------
% Calculation of Mean Damage Grade Distribution, using intensities and
% calculated Mean Damage Degree (fMDG)
% Formula:
% prob(j,i)=factorial(5)/(factorial(dg(j))*factorial(5-dg(j)))*((fMDG(i)/5)^dg(j))*((1-fMDG(i)/5)^(5-dg(j)));
% (Braga et al., 1982)
% Reduction factor: see SERIANEX, AP5000, p.89ff)
% Function written by Delano Landtwing, 16.05.2012, delanol@ethz.ch
%
% Incoming:
% fMDG           matrix containing Mean Damage Degrees at different
%                settlements and vulnerability classes
%
% Outcoming:
% 


dg = 0:1:5;
for k=1:1:length(dg)
    fbinPDF(k)=factorial(5)/(factorial(dg(k))*factorial(5-dg(k)))*((fMDG/5)^dg(k))*((1-fMDG/5)^(5-dg(k)));
end

