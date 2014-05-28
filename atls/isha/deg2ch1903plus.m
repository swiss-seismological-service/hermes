function[x,y] = deg2ch1903plus(lat,lng)

% [y,x] = deg2CH1903plus(lat,lng) converts decimal degrees to Swiss 1903+
% Co-ordinates in metres.
% 
%
% WGS84 global geographic coordinates (degrees)
% Swiss national coordinates (CH1903/LV03)
%  
% 
% Map projection
% 
% Oblique, conformal cylindrical projection (Mercator projection)
% Bessel ellipsoid 1841
% The projection center is the fundamental point at the old observatory in Bern 
% (Longitude 7 ? 26 '22:50 "/ latitude 46 ? 57' 08.66" -> coordinates 600'000 .000 East / North 200'000 .000)
% Approximation (accuracy on the 1-meter level) 
% 
% 
% EXAMPLE:
% lat = 46.3162
% lng = 7.2078
% 
% [x,y] = deg2CH1903plus(lat,lng)
% 
% x = 5.8222e+005
% y = 1.2945e+005
% 
%
%
% Original code written in Java available at:
% http://alturl.com/75iob from SwissTopo.ch
%
%
% email: s.l.roberson@tudelft.nl / roberson.sam@gmail.com
% SAM ROBERSON: TU DELFT, THE NETHERLANDS : 05.07.2011

lat = DECtoSEX(lat);
lng = DECtoSEX(lng);

lat = DEGtoSEC(lat);
lng = DEGtoSEC(lng);

lat_aux = (lat - 169028.66)/10000;
lng_aux = (lng - 26782.5)/10000;

% Process Y
x = 600072.37 ...
    + 211455.93 .* lng_aux ...
    - 10938.51 .* lng_aux .* lat_aux ...
    -   0.36 .* lng_aux .* lat_aux.^2 ...
    -   44.54 .* lng_aux.^3;

%  Process X
y = 200147.07 ...
    + 308807.95 .* lat_aux ...
    +  3745.25 .* lng_aux.^2 ...
    +   76.63 .* lat_aux.^2 ...
    -  194.56 .* lng_aux.^2 .* lat_aux ...
    +  119.79 .* lat_aux.^3;

function[sex] = DECtoSEX(angle)

% Extract DMS
deg = round(angle);
min = round((angle-deg).*60);
sec = (((angle-deg)*60)-min).*60;

% Result in degrees ...___ (dd.mmss)
sex = deg + min./100 + sec./10000;

function[sec] = DEGtoSEC(angle)

% Extract DMS
deg = round( angle );
min = round( (angle-deg).*100 );
sec = (((angle-deg).*100) - min).* 100;

% Result in degrees ...___ (dd.mmss)
sec = sec + min.*60 + deg.*3600;