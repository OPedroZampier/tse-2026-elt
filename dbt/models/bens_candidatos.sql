select
    try_cast(SQ_CANDIDATO as bigint) as id_candidato,
    count(*) as quantidade_bens,
    sum(try_cast(replace(VR_BEM_CANDIDATO, ',', '.') as decimal(20, 2))) as valor_bens_brl
from {{ source_csv('bens', 'bem_candidato_2026_BRASIL.csv') }}
where try_cast(SQ_CANDIDATO as bigint) is not null
group by 1
