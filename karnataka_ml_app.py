from flask import Flask, jsonify
from src.cost_api import cost_bp
from src.anomaly_api import anomaly_bp
from src.evidence_api import evidence_bp
from src.recommendation_api import recommendation_bp

def create_app():
    app = Flask(__name__)

    app.register_blueprint(cost_bp)
    app.register_blueprint(anomaly_bp)
    app.register_blueprint(evidence_bp)
    app.register_blueprint(recommendation_bp)

    @app.route("/", methods=["GET"])
    def home():
        return jsonify({
            "project": "EvidenceBridge Karnataka ML API",
            "status": "running",
            "components": [
                "Treatment Package Cost Prediction",
                "Hospital Anomaly Detection",
                "Hospital Directory Evidence Assessment",
                "Hospital Recommendation"
            ]
        })

    @app.route("/api/health", methods=["GET"])
    def health():
        return jsonify({
            "success": True,
            "service": "EvidenceBridge ML API",
            "status": "healthy",
            "components": [
                "Treatment Cost Prediction",
                "Hospital Anomaly Detection",
                "Evidence Assessment",
                "Hospital Recommendation"
            ]
        })

    return app

app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
