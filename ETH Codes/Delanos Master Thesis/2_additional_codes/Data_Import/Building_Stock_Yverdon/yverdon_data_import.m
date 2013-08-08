%%  Create building stock Basel and surroundings
%   source:         SERIANEX report
%   classification: Risk-UE, refined by SERIANEX report
clear all;clc;
perc_build=importdata('vuln_classes_percentage.csv')


bs_yverdon{1}.Name='Yverdon';
bs_yverdon{1}.Country='Switzerland';
bs_yverdon{1}.Build_tot=2444;
bs_yverdon{1}.ins_value_bdg=1500000;
bs_yverdon{1}.Pop=27500
bs_yverdon{1}.perc_build=perc_build;
% settlement coordinates
bs_yverdon{1}.xkoordCH=0;
bs_yverdon{1}.ykoordCH=0;

num_build_vuln=importdata('num_build.csv');

save bs_yverdon.mat