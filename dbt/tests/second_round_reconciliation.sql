select r.chave_resultado
from {{ ref('resultados_segundo_turno') }} r
where r.turno != 2 or r.uf = 'BR' or r.codigo_cargo not in (1,3)
   or r.comparecimento + r.abstencoes != r.eleitores_secoes_apuradas
   or r.votos_validos != r.votos_nominais + r.votos_legenda
   or r.secoes_totalizadas != r.secoes_total
   or r.votos_legenda != 0
   or r.votos_total != r.votos_validos + r.votos_brancos + r.votos_nulos_total + r.votos_anulados + r.votos_anulados_sub_judice
