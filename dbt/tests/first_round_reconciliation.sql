-- Data quality tests return the records violating the source identities.
select chave_resultado
from {{ ref('resultados_primeiro_turno') }}
where votos_validos != votos_nominais + votos_legenda
   or comparecimento + abstencoes != eleitores_secoes_apuradas
   or votos_total != votos_validos + votos_brancos + votos_nulos_total + votos_anulados + votos_anulados_sub_judice
   or uf = 'BR' or turno != 1 or ano_eleicao != 2026
