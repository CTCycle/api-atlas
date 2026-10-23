# Reference question checks

Generated 2026-10-23 by `python scripts/answer_checks.py`.

Each block is the literal output of the command shown above it.

## Historical weather observations for Europe

```bash
python -m regipy.cli search historical --category weather-climate --limit 8
```

```text
ID                                  NAME               CATEGORY         PRICING   ACCESS   VERIFIED  STATUS     
----------------------------------  -----------------  ---------------  --------  -------  --------  -----------
visualcrossing.com/visual-crossing  Visual Crossing    weather-climate  freemium  api_key  verified  active     
weatherstack.com/weatherstack       Weatherstack       weather-climate  unknown   api_key  partial   active     
m3o.com/micro-weather               Micro Weather      weather-climate  unknown   api_key  imported  unavailable
tomorrow.io/tomorrow-io             Tomorrow.io        weather-climate  freemium  api_key  verified  active     
inpe.br/brazilian-weather           Brazilian Weather  weather-climate  unknown   unknown  partial   active     
openweathermap.org/openweathermap   OpenWeatherMap     weather-climate  freemium  api_key  verified  active     
oikolab.com/oikolab                 Oikolab            weather-climate  unknown   api_key  partial   active     
open-meteo.com/open-meteo           Open-Meteo         weather-climate  freemium  public   verified  active     

8 result(s)
```

## Free geospatial sources that allow commercial use

```bash
python -m regipy.cli search --category geospatial --commercial allowed --limit 8
```

```text
ID                                     NAME                CATEGORY    PRICING  ACCESS        VERIFIED  STATUS
-------------------------------------  ------------------  ----------  -------  ------------  --------  ------
nasa.gov/nasa-earthdata                NASA Earthdata      geospatial  free     registration  verified  active
nominatim.openstreetmap.org/nominatim  Nominatim           geospatial  free     public        verified  active
openstreetmap.org/openstreetmap        OpenStreetMap       geospatial  free     public        verified  active
usgs.gov/usgs-earthexplorer            USGS EarthExplorer  geospatial  free     registration  verified  active

4 result(s)
```

## Medical datasets downloadable without authentication

```bash
python -m regipy.cli search --category health-medical --kind dataset --access public --limit 8
```

```text
ID                NAME      CATEGORY        PRICING  ACCESS  VERIFIED  STATUS
----------------  --------  --------------  -------  ------  --------  ------
cdc.gov/cdc       CDC       health-medical  free     public  verified  active
who.int/who-data  WHO Data  health-medical  free     public  verified  active

2 result(s)
```

## Freemium providers with a documented free tier

```bash
python -m regipy.cli search --pricing freemium --free-tier --limit 8
```

```text
ID                               NAME            CATEGORY                  PRICING   ACCESS        VERIFIED  STATUS
-------------------------------  --------------  ------------------------  --------  ------------  --------  ------
adsbexchange.com/ads-b-exchange  ADS-B Exchange  logistics-transportation  freemium  api_key       verified  active
cohere.com/cohere                Cohere          ai-ml                     freemium  api_key       verified  active
ebay.com/ebay                    eBay            business-commerce         freemium  restricted    verified  active
etsy.com/etsy                    Etsy            business-commerce         freemium  registration  verified  active
ai.google.dev/google-ai          Google AI       ai-ml                     freemium  api_key       verified  active
groq.com/groq                    Groq            ai-ml                     freemium  api_key       verified  active
huggingface.co/hugging-face      Hugging Face    ai-ml                     freemium  api_key       verified  active
mapbox.com/mapbox                Mapbox          geospatial                freemium  api_key       verified  active

8 result(s)
```

## Alternatives to a paid or freemium provider

```bash
python -m regipy.cli alternatives openweathermap.org/openweathermap --pricing free,freemium --limit 6
```

```text
alternatives for openweathermap.org/openweathermap (weather-climate, freemium)
SCORE  ID                                  NAME             PRICING   ACCESS   COMMERCIAL
-----  ----------------------------------  ---------------  --------  -------  ----------
7      visualcrossing.com/visual-crossing  Visual Crossing  freemium  api_key  unknown   
7      weatherapi.com/weatherapi           WeatherAPI       freemium  api_key  unknown   
5      api.met.no/met-norway               MET Norway       free      public   unknown   
5      open-meteo.com/open-meteo           Open-Meteo       freemium  public   allowed   
5      tomorrow.io/tomorrow-io             Tomorrow.io      freemium  api_key  unknown
```

## Realtime sources

```bash
python -m regipy.cli search --update-frequency realtime --limit 8
```

```text
ID                               NAME            CATEGORY                  PRICING   ACCESS      VERIFIED  STATUS
-------------------------------  --------------  ------------------------  --------  ----------  --------  ------
adsbexchange.com/ads-b-exchange  ADS-B Exchange  logistics-transportation  freemium  api_key     verified  active
adyen.com/adyen                  Adyen           payments                  paid      restricted  verified  active
alphavantage.co/alpha-vantage    Alpha Vantage   finance                   freemium  api_key     verified  active
amadeus.com/amadeus              Amadeus         logistics-transportation  paid      restricted  verified  active
anthropic.com/anthropic          Anthropic       ai-ml                     paid      api_key     verified  active
braintreepayments.com/braintree  Braintree       payments                  paid      api_key     verified  active
cohere.com/cohere                Cohere          ai-ml                     freemium  api_key     verified  active
ebay.com/ebay                    eBay            business-commerce         freemium  restricted  verified  active

8 result(s)
```

## Static or periodic archive sources

```bash
python -m regipy.cli search --update-frequency static,periodic --limit 8
```

```text
ID                             NAME            CATEGORY          PRICING  ACCESS  VERIFIED  STATUS
-----------------------------  --------------  ----------------  -------  ------  --------  ------
cdc.gov/cdc                    CDC             health-medical    free     public  verified  active
ebi.ac.uk/chembl               ChEMBL          life-sciences     free     public  verified  active
crossref.org/crossref          Crossref        science-research  free     public  verified  active
data.europa.eu/data-europa-eu  data.europa.eu  open-data         free     public  verified  active
data.gov/data-gov              data.gov        open-data         free     public  verified  active
data.gov.uk/data-gov-uk        data.gov.uk     open-data         free     public  verified  active
datacite.org/datacite          DataCite        science-research  free     public  verified  active
ebi.ac.uk/ebi                  EBI             life-sciences     free     public  verified  active

8 result(s)
```

## Verified entries only

```bash
python -m regipy.cli search --confidence verified --limit 8
```

```text
ID                               NAME            CATEGORY                  PRICING   ACCESS      VERIFIED  STATUS
-------------------------------  --------------  ------------------------  --------  ----------  --------  ------
adsbexchange.com/ads-b-exchange  ADS-B Exchange  logistics-transportation  freemium  api_key     verified  active
adyen.com/adyen                  Adyen           payments                  paid      restricted  verified  active
alphavantage.co/alpha-vantage    Alpha Vantage   finance                   freemium  api_key     verified  active
amadeus.com/amadeus              Amadeus         logistics-transportation  paid      restricted  verified  active
anthropic.com/anthropic          Anthropic       ai-ml                     paid      api_key     verified  active
arxiv.org/arxiv                  arXiv           science-research          free      public      verified  active
braintreepayments.com/braintree  Braintree       payments                  paid      api_key     verified  active
cdc.gov/cdc                      CDC             health-medical            free      public      verified  active

8 result(s)
```
