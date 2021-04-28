%%writefile mytemplate.tpl

{% extends 'full.tpl'%}
.output_png {
        display: table-cell;
        text-align: center;
        vertical-align: middle;
    }
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
{% elif 'yellow' in cell['metadata'].get('tags', []) %}
    <div style="border:thin solid yellow">
        {{ super() }}
    </div>
{% elif 'cyan' in cell['metadata'].get('tags', []) %}
    <div style="border:thin solid cyan">
        {{ super() }}
    </div>
{% elif 'purple' in cell['metadata'].get('tags', []) %}
    <div style="border:thin solid purple">
        {{ super() }}
    </div>
{% else %}
    {{ super() }}
{% endif %}
{% endblock any_cell %}