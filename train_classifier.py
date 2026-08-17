import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.model_selection import train_test_split
import joblib

from src.classifier_rules import classify_rule_based

def build_training_set(all_transactions_df: pd.DataFrame) -> pd.DataFrame:
    all_transactions_df["category"] = all_transactions_df["desc"].apply(classify_rule_based)
    return all_transactions_df.dropna(subset=["category"])

def train(all_transactions_df: pd.DataFrame, out_path="models/classifier.joblib"):
    labeled = build_training_set(all_transactions_df)
    X_train, X_test, y_train, y_test = train_test_split(
        labeled["desc"], labeled["category"], test_size=0.2, random_state=42
    )

    pipeline = Pipeline([
        ("tfidf", TfidfVectorizer(ngram_range=(1, 2), min_df=1)),
        ("clf", LogisticRegression(max_iter=1000)),
    ])
    pipeline.fit(X_train, y_train)
    print("Test accuracy:", pipeline.score(X_test, y_test))

    joblib.dump(pipeline, out_path)
    return pipeline