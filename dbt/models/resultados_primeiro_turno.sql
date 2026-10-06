select * replace (
    codigo_cargo::integer as codigo_cargo, turno::integer as turno,
    ano_eleicao::integer as ano_eleicao, eleicao::integer as eleicao,
    strptime(data_geracao, '%d/%m/%Y')::date as data_geracao,
    secoes_total::bigint as secoes_total, secoes_totalizadas::bigint as secoes_totalizadas,
    eleitorado::bigint as eleitorado, eleitores_secoes_apuradas::bigint as eleitores_secoes_apuradas,
    comparecimento::bigint as comparecimento, abstencoes::bigint as abstencoes,
    votos_total::bigint as votos_total, votos_validos::bigint as votos_validos,
    votos_nominais::bigint as votos_nominais, votos_legenda::bigint as votos_legenda,
    votos_brancos::bigint as votos_brancos, votos_nulos_total::bigint as votos_nulos_total,
    votos_anulados::bigint as votos_anulados, votos_anulados_sub_judice::bigint as votos_anulados_sub_judice
)
from {{ source_csv('resultados_primeiro_turno', 'abrangencia.csv') }}
