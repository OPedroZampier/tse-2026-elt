select * replace (
    codigo_cargo::integer as codigo_cargo, turno::integer as turno,
    ano_eleicao::integer as ano_eleicao, eleicao::integer as eleicao,
    strptime(data_geracao, '%d/%m/%Y')::date as data_geracao,
    votos::bigint as votos, percentual_oficial::double as percentual_oficial
)
from {{ source_csv('resultados_segundo_turno', 'candidatos.csv') }}
