select
    try_cast(SQ_CANDIDATO as bigint) as id_candidato,
    count(*) as quantidade_redes
from {{ source_csv('redes_sociais', 'rede_social_candidato_2026_BRASIL.csv') }}
where nullif(trim(DS_URL), '#NULO') is not null
group by 1
