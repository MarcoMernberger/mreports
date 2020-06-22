%%writefile mytemplate.tpl

{% extends 'full.tpl'%}
{% block any_cell %}
{% if 'red' in cell['metadata'].get('tags', []) %}
    <div style="border:thin solid red">
        {{ super() }}
    </div>
{% elif 'orange' in cell['metadata'].get('tags', []) %}
    <div style="border:thin solid orange">
        {{ super() }}
    </div>
{% elif 'green' in cell['metadata'].get('tags', []) %}
    <div style="border:thin solid green">
        {{ super() }}
    </div>
{% elif 'blue' in cell['metadata'].get('tags', []) %}
    <div style="border:thin solid blue">
        {{ super() }}
    </div>
{% else %}
    {{ super() }}
{% endif %}
{% endblock any_cell %}