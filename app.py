from flask import Flask, render_template, request, jsonify
import plotly.graph_objects as go
import plotly.utils  # Importa o módulo utils do Plotly
import json
import math
import os  # Para ler a variável de ambiente PORT

app = Flask(__name__)

def calculate_risk_score(gestational_age, weight, hours_vmi, last_fio2, peep, map_value, spO2, cafeina, atb, cpap):
    """
    Calcula o score de risco com base nas variáveis, usando os seguintes coeficientes:
    - (42 - GA) * 0.3: Para cada semana de déficit em relação a 42 semanas, adiciona 0,3 pontos.
    - (3000 - weight) * 0.001: Para cada grama abaixo de 3000, adiciona 0,001 pontos.
    - hours_vmi * 0.05: Cada hora de ventilação mecânica aumenta o score em 0,05 pontos.
    - last_fio2 * 2: Valores maiores de FiO₂ somam 2 pontos por unidade.
    - peep * 0.4: Cada cmH₂O de PEEP soma 0,4 pontos.
    - map_value * 0.3: Cada cmH₂O de MAP soma 0,3 pontos.
    - (100 - spO2) * 0.25: Déficit de saturação, onde cada ponto abaixo de 100 soma 0,25 pontos.
    - Se cafeína for 0 (não administrada), adiciona 5 pontos (indicando maior risco).
    - Se antibióticos forem utilizados (1), adiciona 5 pontos (indicando possível infecção).
    - Se CPAP for utilizado (1), subtrai 3 pontos, refletindo seu efeito protetor.
    """
    score = 0
    score += (42 - gestational_age) * 0.3
    score += (3000 - weight) * 0.001
    score += hours_vmi * 0.05
    score += last_fio2 * 2
    score += peep * 0.4
    score += map_value * 0.3
    score += (100 - spO2) * 0.25
    score += 5 if cafeina == 0 else 0
    score += 5 if atb == 1 else 0
    score -= 3 if cpap == 1 else 0  # CPAP como fator protetor
    return score

def risk_probability(score, offset=17, k=15):
    """
    Converte o score de risco em probabilidade de falha de extubação.
    - offset: subtrai um valor fixo para calibrar os scores.
    - k: fator de escala para suavizar a função logística.
    """
    adjusted_score = score - offset
    return 1 / (1 + math.exp(-adjusted_score / k))

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/predict', methods=['POST'])
def predict():
    data = request.get_json()
    score = calculate_risk_score(
        data.get('gestational_age', 0),
        data.get('weight', 0),
        data.get('hours_vmi', 0),
        data.get('last_fio2', 0),
        data.get('peep', 0),
        data.get('map_value', 0),
        data.get('spO2', 0),
        data.get('cafeina', 0),
        data.get('atb', 0),
        data.get('cpap', 0)
    )
    prob = risk_probability(score)
    risk_percent = prob * 100

    # Cria o gráfico tipo gauge com Plotly
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=risk_percent,
        number={"suffix": "%"},
        title={"text": "Risco de Falha de Extubação"},
        gauge={
            "axis": {"range": [0, 100]},
            "bar": {"color": "darkblue"},
            "steps": [
                {"range": [0, 20], "color": "green"},
                {"range": [20, 40], "color": "yellow"},
                {"range": [40, 60], "color": "orange"},
                {"range": [60, 100], "color": "red"}
            ],
            "threshold": {
                "line": {"color": "black", "width": 4},
                "thickness": 0.75,
                "value": risk_percent
            }
        }
    ))

    # Serializa o gráfico para JSON
    graphJSON = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)

    return jsonify({
        'risk_score': score,
        'risk_probability': prob,
        'risk_percent': risk_percent,
        'graphJSON': graphJSON
    })

if __name__ == '__main__':
    # Render define a variável de ambiente PORT; caso não esteja definida, usa 8000
    port = int(os.environ.get('PORT', 8000))
    app.run(host='0.0.0.0', port=port, debug=True, use_reloader=False)
