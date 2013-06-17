function [forecast_magbin]=calc_rates_magbins2(lamda,Mmin,Mmax,dM)
%% INPUT %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% lamda_SR: cumulative forecasted seismicity rates
%% OUTPUT %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% forecast_magbin: forecast seismicity for each magnitude bin
% observed_magbin: observed seismicity for each magnitude bin
% mag: mag=1:0.1:Mmax;
% difr: difr=forecast_magbin-observed_magbin
% mb: forecasted rates following Gutenberg Richter M-f distribution

% %% Read the catalog
% fid = fopen(['/Users/banumenacabrera/GEISER/ETAS/DATA/cat.dat'],'r');
% line=fgetl(fid);
% data = fscanf(fid,'%e %e %e %e %e',[5 inf]);  
% fclose(fid);
% data = data';
% ctime = data(:,2); % catalog time
% mg = data(:,5); % catalog magnitude
% 
% 
% Mcat=0.9;

% % The first 5.75 days of the catalog
% % t2=ctime(ctime<=5.75);
% t2=ctime(ctime<=15);
% mg2=mg(1:length(t2));
% % Events with magnitudes greated than or equal to the catalog magnitude
% MT=mg2(mg2>=Mcat); % magnitudes larger than catalog magnitude
% ind=find(mg2>=Mcat); % indices of magnitudes >= Mcat
% % Time vector corresponding to events of M>=Mcat
% for i=1:length(ind);
%     t(i)=t2(ind(i));
% end
% t=t';
% 
% mg=1:0.1:3;
% for ii=1:length(mg);
%     rt=MT>=mg(ii);
%     ind=find(rt); 
%     NN(ii)=length(ind);
%     clear rt, ind
% end
% % figure; semilogy(mg,NN,'ko-');







% % Observed rates
% load obs_rate.mat;


load b_upd.mat;
b=b_upd(1:(length(lamda)));
b=b';


%% SR
mBack2=[];
bgmax2=[];

m=Mmin:dM:Mmax;
for jj=1:length(m);
    %if input magnitude changes, change here
    diff(jj)=0.9-m(jj);
    for ii=1:length(lamda);
    bgm2(ii)=(lamda(ii)*(10^(b(ii)*diff(jj))));
    end
    mb(jj)=sum(bgm2);

end



% %% Observed Number of events in each Magnitude bin
% magm=Mmin:dM:Mmax;
% for ik=1:length(magm)-1;
%     maxind=find(MT>=magm(ik) & MT<magm(ik+1));
%     cl(ik)=length(maxind); % cl:observed
%     clear maxind;
% end

%% Forecased Number of events in each Magnitude bin
for ij=1:length(mb)-1;
    mbin(ij)=mb(ij)-mb(ij+1); % mbin: forecasted
end



% difr=mbin-cl; % difference between forecasted & observed rates


%%
forecast_magbin=mbin;
% observed_magbin=cl;
% mag=magm(2:end);












