# constants.py

# Routing-Informationen für die Riot API
RIOT_ROUTING = {
    'americas': ['br1', 'la1', 'la2', 'na1'],
    'asia': ['jp1', 'kr','oc1','sg2','tw2','vn2'],
    'europe': ['eun1', 'euw1', 'tr1', 'ru','me1'],
    'esports':['esports']
}
VALID_REGIONS = {'br1', 'eun1', 'euw1', 'jp1', 'kr', 'la1', 'la2', 'na1', 'oc1', 'tr1', 'ru', 'sg2', 'tw2', 'vn2'}

# Mapping für gängige Tippfehler bei Regionen zu den korrekten API-Regionen
REGION_CORRECTIONS = {
    "euw": "euw1",
    "eune": "eun1",
    "na": "na1",
    "kr": "kr",
    "jp": "jp1",
    "oce": "oc1",
    "br": "br1",
    "las": "la2",
    "lan": "la1",
    "tr": "tr1",
    "ru": "ru",
    "me": "me1",
    "eu1":"euw1"
}