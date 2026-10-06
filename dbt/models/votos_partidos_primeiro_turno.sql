select * replace (
    codigo_cargo::integer as codigo_cargo, turno::integer as turno,
    ano_eleicao::integer as ano_eleicao, eleicao::integer as eleicao,
    strptime(data_geracao, '%d/%m/%Y')::date as data_geracao,
    votos_nominais::bigint as votos_nominais, votos_legenda::bigint as votos_legenda,
    votos_anulados::bigint as votos_anulados
)
from {{ source_csv('resultados_primeiro_turno', 'partidos.csv') }}
