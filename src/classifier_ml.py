import joblib

_model = None

def load_model(path="models/classifier.joblib"):
    global _model
    if _model is None:
        _model = joblib.load(path)
    return _model

def classify_ml(description: str) -> str:
    model = load_model()
    return model.predict([description])[0]