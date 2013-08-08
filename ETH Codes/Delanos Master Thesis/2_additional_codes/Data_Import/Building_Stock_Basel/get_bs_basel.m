%%  Create building stock Basel and surroundings
%   source:         SERIANEX report
%   classification: Risk-UE, refined by SERIANEX report
clear all;clc;

%%  import data
%   load vulnerability indexes
vuln_typ_ser=importdata('vulnerability_classes_serianex_typology.csv');
vuln_vi_base_ser=importdata('vulnerability_classes_serianex_vi_base.csv');

%   load building stock Basel
bs_basel_data_ser=importdata('building_stock_basel_CH_D_F_data.csv');
bs_basel_country_ser=importdata('building_stock_basel_CH_D_F_country.csv');
bs_basel_settlement_ser=importdata('building_stock_basel_CH_D_F_settlement.csv');
bs_basel_class_ser=importdata('building_stock_basel_CH_D_F_classification.csv');

%   load site amplifications
bs_basel_site_ampl=importdata('building_stock_basel_site_ampl.csv');

%   load buildings percentage per vuln. class Basel Country
vuln_perc_CH_small=(importdata('buildings_vuln_class_percentage_ser_CH_small_town.csv'))';
vuln_perc_CH_midsize=(importdata('buildings_vuln_class_percentage_ser_CH_mid-size_town.csv'))';
vuln_perc_CH_large=(importdata('buildings_vuln_class_percentage_ser_CH_large_town.csv'))';
vuln_perc_CH_city=(importdata('buildings_vuln_class_percentage_ser_CH_city.csv'))';

%   load buildings percentage per vuln. class Basel City
vuln_perc_CH_grossbasel=(importdata('buildings_vuln_class_percentage_ser_CH_gross_kleinbasel.csv'))';
vuln_perc_CH_vorstaedte=(importdata('buildings_vuln_class_percentage_ser_CH_vorstaedte_ua.csv'))';
vuln_perc_CH_gundeldingen=(importdata('buildings_vuln_class_percentage_ser_CH_gundeldingen_ua.csv'))';
vuln_perc_CH_bachletten=(importdata('buildings_vuln_class_percentage_ser_CH_bachletten_ua.csv'))';
vuln_perc_CH_iselin=(importdata('buildings_vuln_class_percentage_ser_CH_iselin_ua.csv'))';
vuln_perc_CH_klybeck=(importdata('buildings_vuln_class_percentage_ser_CH_klybeck_ua.csv'))';
vuln_perc_CH_bruderholz=(importdata('buildings_vuln_class_percentage_ser_CH_bruderholz_ua.csv'))';

%   load buildings percentage per vuln. class France
vuln_perc_F_small=(importdata('buildings_vuln_class_percentage_ser_F_small_town.csv'))';
vuln_perc_F_midsize=(importdata('buildings_vuln_class_percentage_ser_F_mid-size_town.csv'))';
vuln_perc_F_large=(importdata('buildings_vuln_class_percentage_ser_F_large_town.csv'))';
vuln_perc_F_city=(importdata('buildings_vuln_class_percentage_ser_F_city.csv'))';

%   load buildings percentage per vuln. Germany
vuln_perc_D_small=(importdata('buildings_vuln_class_percentage_ser_D_small_town.csv'))';
vuln_perc_D_midsize=(importdata('buildings_vuln_class_percentage_ser_D_mid-size_town.csv'))';
vuln_perc_D_group=(importdata('buildings_vuln_class_percentage_ser_D_group_town.csv'))';
vuln_perc_D_city=(importdata('buildings_vuln_class_percentage_ser_D_city.csv'))';

%   load insured values
insured_values = (importdata('insured_values.csv'))';



%%  data assignment to structural storage
     for i=1:size(bs_basel_settlement_ser,1)
         bs_basel_ser{i}.Name=bs_basel_settlement_ser(i);
         bs_basel_ser{i}.Country=bs_basel_country_ser(i);
         bs_basel_ser{i}.Classification=bs_basel_class_ser(i);
         bs_basel_ser{i}.Pop=bs_basel_data_ser(i,9);
         bs_basel_ser{i}.Build_tot=bs_basel_data_ser(i,10);
         bs_basel_ser{i}.ins_value_bdg=insured_values(i);
         % settlement coordinates
         bs_basel_ser{i}.xkoordCH=bs_basel_data_ser(i,1);
         bs_basel_ser{i}.ykoordCH=bs_basel_data_ser(i,2);
         
         % site amplifications
         bs_basel_ser{i}.Iamp=bs_basel_site_ampl(i,3);
         bs_basel_ser{i}.Iamp_sigma=bs_basel_site_ampl(i,4);
         bs_basel_ser{i}.Iamp_ECOS09=bs_basel_site_ampl(i,5);
         bs_basel_ser{i}.Iamp_sigma_ECOS09=bs_basel_site_ampl(i,6);

                  
         % load building distribution according to vuln. class
         % get number of buildings/construction age
         sCountry = char(bs_basel_ser{i}.Country);         
         switch sCountry
             case 'Switzerland'                 
                        
                 % get number of buildings/construction age
                 bs_basel_ser{i}.num_build_age(:,1) = bs_basel_data_ser(i,11:15);
                 bs_basel_ser{i}.num_build_age(:,2) = bs_basel_data_ser(i,16:20);
                 
                 % determine settlement classification
                 sClassification = char(bs_basel_ser{i}.Classification);
                 switch sClassification
                     case 'city_district'
                     % determine Basel district
                     sBasel_District = char(bs_basel_ser{i}.Name);
                     switch sBasel_District
                         case {'Basel_Grossbasel' 'Basel_Kleinbasel'}
                            bs_basel_ser{i}.build_vuln_perc(:,:,1) = vuln_perc_CH_grossbasel(1:5,:);
                            bs_basel_ser{i}.build_vuln_perc(:,:,2) = vuln_perc_CH_grossbasel(6:10,:); 
                         case {'Basel_Vorstaedte' 'Basel_Am_Ring' 'Basel_Clara' 'Basel_St-Alban' 'Basel_Wettstein'}
                            bs_basel_ser{i}.build_vuln_perc(:,:,1) = vuln_perc_CH_vorstaedte(1:5,:);
                            bs_basel_ser{i}.build_vuln_perc(:,:,2) = vuln_perc_CH_vorstaedte(6:10,:); 
                         case {'Basel_Gundeldingen' 'Basel_St-Johann' 'Basel_Matthaeus'}
                            bs_basel_ser{i}.build_vuln_perc(:,:,1) = vuln_perc_CH_gundeldingen(1:5,:);
                            bs_basel_ser{i}.build_vuln_perc(:,:,2) = vuln_perc_CH_gundeldingen(6:10,:); 
                         case {'Basel_Bachletten' 'Basel_Hirzbrunnen' 'Basel_Gotthelf'}
                            bs_basel_ser{i}.build_vuln_perc(:,:,1) = vuln_perc_CH_bachletten(1:5,:);
                            bs_basel_ser{i}.build_vuln_perc(:,:,2) = vuln_perc_CH_bachletten(6:10,:);  
                         case {'Basel_Iselin' 'Basel_Breite' 'Basel_Rosental'}
                            bs_basel_ser{i}.build_vuln_perc(:,:,1) = vuln_perc_CH_iselin(1:5,:);
                            bs_basel_ser{i}.build_vuln_perc(:,:,2) = vuln_perc_CH_iselin(6:10,:);  
                         case {'Basel_Klybeck' 'Basel_Kleinhueningen'}
                            bs_basel_ser{i}.build_vuln_perc(:,:,1) = vuln_perc_CH_klybeck(1:5,:);
                            bs_basel_ser{i}.build_vuln_perc(:,:,2) = vuln_perc_CH_klybeck(6:10,:); 
                         case {'Basel_Bruderholz'}
                            bs_basel_ser{i}.build_vuln_perc(:,:,1) = vuln_perc_CH_bruderholz(1:5,:);
                            bs_basel_ser{i}.build_vuln_perc(:,:,2) = vuln_perc_CH_bruderholz(6:10,:);     
                         otherwise
                             disp('no district assigned or not taken:')
                             disp(sBasel_District)
                     end
                     
                     case 'small_town'
                     	bs_basel_ser{i}.build_vuln_perc(:,:,1) = vuln_perc_CH_small(1:5,:);
                        bs_basel_ser{i}.build_vuln_perc(:,:,2) = vuln_perc_CH_small(6:10,:);
                     case 'mid-size_town'
                        bs_basel_ser{i}.build_vuln_perc(:,:,1) = vuln_perc_CH_midsize(1:5,:);
                        bs_basel_ser{i}.build_vuln_perc(:,:,2) = vuln_perc_CH_midsize(6:10,:);
                     case 'large_town'
                        bs_basel_ser{i}.build_vuln_perc(:,:,1) = vuln_perc_CH_large(1:5,:);
                        bs_basel_ser{i}.build_vuln_perc(:,:,2) = vuln_perc_CH_large(6:10,:);
                     case 'city'
                        bs_basel_ser{i}.build_vuln_perc(:,:,1) = vuln_perc_CH_city(1:5,:);
                        bs_basel_ser{i}.build_vuln_perc(:,:,2) = vuln_perc_CH_city(6:10,:);
                     otherwise
                     disp('no classification')
                     disp(char(bs_basel_ser{i}.Name))
                 end
                
             case 'France'
                                 
                 % get number of buildings/construction age
                 bs_basel_ser{i}.num_build_age(:,1) = bs_basel_data_ser(i,11:14);
                 bs_basel_ser{i}.num_build_age(:,2) = bs_basel_data_ser(i,15:18);
                 
                 % determine settlement classification
                 sClassification = char(bs_basel_ser{i}.Classification);
                 switch sClassification
                     case 'small_town'
                         bs_basel_ser{i}.build_vuln_perc(:,:,1) = vuln_perc_F_small(1:4,:);
                         bs_basel_ser{i}.build_vuln_perc(:,:,2) = vuln_perc_F_small(5:8,:);
                     case 'mid-size_town'
                         bs_basel_ser{i}.build_vuln_perc(:,:,1) = vuln_perc_F_midsize(1:4,:);
                         bs_basel_ser{i}.build_vuln_perc(:,:,2) = vuln_perc_F_midsize(5:8,:);
                     case 'large_town'
                         bs_basel_ser{i}.build_vuln_perc(:,:,1) = vuln_perc_F_large(1:4,:);
                         bs_basel_ser{i}.build_vuln_perc(:,:,2) = vuln_perc_F_large(5:8,:);
                     case 'city'
                         bs_basel_ser{i}.build_vuln_perc(:,:,1) = vuln_perc_F_city(1:4,:);
                         bs_basel_ser{i}.build_vuln_perc(:,:,2) = vuln_perc_F_city(5:8,:);
                     otherwise
                         disp('no classification')
                 end
                         
                 
                 
             case 'Germany'
                                  
                 % get number of buildings/construction age
                 bs_basel_ser{i}.num_build_age(:,1) = bs_basel_data_ser(i,11:12);
                 bs_basel_ser{i}.num_build_age(:,2) = bs_basel_data_ser(i,13:14);
                 
                 % determine settlement classification
                 sClassification = char(bs_basel_ser{i}.Classification);
                 switch sClassification
                     case 'small_town'
                         bs_basel_ser{i}.build_vuln_perc(:,:,1) = vuln_perc_D_small(1:2,:);
                         bs_basel_ser{i}.build_vuln_perc(:,:,2) = vuln_perc_D_small(3:4,:);
                     case 'mid-size_town'
                         bs_basel_ser{i}.build_vuln_perc(:,:,1) = vuln_perc_D_midsize(1:2,:);
                         bs_basel_ser{i}.build_vuln_perc(:,:,2) = vuln_perc_D_midsize(3:4,:);
                     case 'group_town'
                         bs_basel_ser{i}.build_vuln_perc(:,:,1) = vuln_perc_D_group(1:2,:);
                         bs_basel_ser{i}.build_vuln_perc(:,:,2) = vuln_perc_D_group(3:4,:);
                     case 'city'
                         bs_basel_ser{i}.build_vuln_perc(:,:,1) = vuln_perc_D_city(1:2,:);
                         bs_basel_ser{i}.build_vuln_perc(:,:,2) = vuln_perc_D_city(3:4,:);
                     otherwise
                         disp('no classification')
                 end
             
             otherwise
                 disp('no country assignment possible')
                 
    
         end
         
         % calculate number of buildings in each vuln. class
         for j=1:size(bs_basel_ser{i}.num_build_age,1)
             % 1-dwelling-units
             bs_basel_ser{i}.num_build_vuln(j,:,1)=bs_basel_ser{i}.num_build_age(j,1).*bs_basel_ser{i}.build_vuln_perc(j,:,1);
             % 2 and more dwelling-units
             bs_basel_ser{i}.num_build_vuln(j,:,2)=bs_basel_ser{i}.num_build_age(j,2).*bs_basel_ser{i}.build_vuln_perc(j,:,2);
         end
         
         num_build_vuln = zeros(size(bs_basel_ser{i}.num_build_vuln,2),size(bs_basel_ser,2));
         for i=1:size(bs_basel_ser,2) % all settlements
            for j=1:size(bs_basel_ser{i}.num_build_vuln,3) % 1 and 2+ dwelling units
                for k=1:size(bs_basel_ser{i}.num_build_vuln,2) % all vuln. classes
                num_build_vuln(k,i) = num_build_vuln(k,i)+sum(bs_basel_ser{i}.num_build_vuln(:,k,j));
                end
            end
         end
         
        
         % CH coordinate storage for quality control
         CHkoord(i,1) = bs_basel_ser{i}.xkoordCH;
         CHkoord(i,2) = bs_basel_ser{i}.ykoordCH;
     end
     
% calculate percentage of buildings in each vuln. class
for iBC=1:1:size(vuln_vi_base_ser,1)
    for iLoc=1:1:size(bs_basel_ser,2)
        perc_build(iBC,iLoc)=num_build_vuln(iBC,iLoc)/bs_basel_ser{iLoc}.Build_tot; % get percentage of people in BC
    end
end

%% control
% for iLoc=1:1:size(bs_basel_ser,2)
%         perc_build_control(iLoc)=sum(perc_build(:,iLoc));
% end

% for iLoc=1:1:size(bs_basel_ser,2)
%     buildings_per_Loc (iLoc) = bs_basel_ser{iLoc}.Build_tot;
%     buildings_per_loc_recalc(iLoc) = sum(sum(sum(bs_basel_ser{iLoc}.num_build_vuln)))
% end

% figure(1)
% plot(buildings_per_Loc,'Color','r');hold on
% plot(buildings_per_loc_recalc,'Color','g');

          


%% clearing not needed variables
clear vuln_typ_ser
clear vuln_vi_base_ser
clear bs_basel_data_ser
clear bs_basel_country_ser
clear bs_basel_settlement_ser
clear bs_basel_class_ser
clear vuln_perc_CH_small
clear vuln_perc_CH_midsize
clear vuln_perc_CH_large
clear vuln_perc_CH_city
clear vuln_perc_CH_grossbasel
clear vuln_perc_CH_vorstaedte
clear vuln_perc_CH_gundeldingen
clear vuln_perc_CH_bachletten
clear vuln_perc_CH_iselin
clear vuln_perc_CH_klybeck
clear vuln_perc_CH_bruderholz
clear vuln_perc_D_small
clear vuln_perc_D_midsize
clear vuln_perc_D_group
clear vuln_perc_D_city
clear vuln_perc_F_small
clear vuln_perc_F_midsize
clear vuln_perc_F_large
clear vuln_perc_F_city
clear sBasel_District
clear sClassification
clear sCountry
clear i
clear j
clear k
clear x
clear y
clear lat
clear lng
clear insured_values
clear iLoc
clear iBC
clear bs_basel_site_ampl
     
save d:\3_ETH\1_Masterarbeit\Codes_ops\Basel_Loss_Assessment_Delano\Building_Stock_Basel\Matlab_codes_inclusiding_data\bs_Basel_ser.mat


%%  End building stock