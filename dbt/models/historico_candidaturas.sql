select
    try_cast(SQ_CANDIDATO_ATUAL as bigint) as id_candidato,
    count(*) as candidaturas_anteriores,
    min(try_cast(ANO_ELEICAO as integer)) as primeira_eleicao
from {{ source_csv('historico_candidatura', 'historico_candidatura_2026_BRASIL.csv') }}
where try_cast(SQ_CANDIDATO_ATUAL as bigint) is not null
group by 1
