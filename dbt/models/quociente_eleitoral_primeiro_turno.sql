select * replace (
    codigo_cargo::integer as codigo_cargo, turno::integer as turno,
    ano_eleicao::integer as ano_eleicao, eleicao::integer as eleicao,
    strptime(data_geracao, '%d/%m/%Y')::date as data_geracao,
    quociente_eleitoral::bigint as quociente_eleitoral, vagas::integer as vagas
)
from {{ source_csv('resultados_primeiro_turno', 'quocientes.csv') }}
