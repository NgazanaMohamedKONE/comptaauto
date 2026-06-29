"""
Entrainement ML pour catégorisation SYSCOHADA
Usage: python ml_models/train.py
"""
import os, sys, pickle
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'comptaauto.settings')
import django
django.setup()

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.ensemble import RandomForestClassifier
from sklearn.pipeline import Pipeline
from comptabilite.models import Ecriture

def train():
    ecritures = Ecriture.objects.filter(statut='VALIDEE')
    if ecritures.count() < 5:
        print("Pas assez d'ecritures validees pour entrainer (minimum 5).")
        return
    X = [e.libelle for e in ecritures]
    y = [e.compte_debit.numero for e in ecritures]
    pipe = Pipeline([
        ('tfidf', TfidfVectorizer(max_features=300, ngram_range=(1,2))),
        ('clf', RandomForestClassifier(n_estimators=100, random_state=42))
    ])
    pipe.fit(X, y)
    with open('ml_models/classifier.pkl', 'wb') as f:
        pickle.dump(pipe, f)
    print(f"Modele entraine sur {len(X)} ecritures. Sauvegarde: ml_models/classifier.pkl")

if __name__ == '__main__':
    train()
