{% macro source_csv(source_name, filename) %}
read_csv(
    '{{ env_var("TSE_WORKDIR", "work") }}/raw/{{ source_name }}/{{ filename }}',
    delim=';', header=true, quote='"', escape='"', encoding='utf-8', all_varchar=true,
    ignore_errors=false
)
{% endmacro %}
