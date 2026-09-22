select distinct
    SG_UF as uf,
    DS_CARGO as cargo,
    SG_PARTIDO as partido,
    nullif(NM_COLIGACAO, '#NULO') as coligacao,
    nullif(SG_FEDERACAO, '#NULO') as federacao
from {{ source_csv('coligacoes', 'consulta_coligacao_2026_BRASIL.csv') }}
where SG_UF not in ('#NULO', '#NE')
