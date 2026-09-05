import os
import joblib
import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report

print('Building robust patient intent dataset...')

data = [
    # Refills
    ('I need a refill for my Amlodipine', 'refill'),
    ('Can you renew my prescription?', 'refill'),
    ('Im almost out of meds', 'refill'),
    ('pharmacy said I have no refills left', 'refill'),
    ('need more atorvastatin', 'refill'),
    ('Please authorize a refill', 'refill'),
    ('I ran out of my pills', 'refill'),
    ('can I get a new script', 'refill'),
    ('prescription renewal', 'refill'),
    ('call the pharmacy', 'refill'),
    ('my medication is empty', 'refill'),
    ('need another bottle of painkillers', 'refill'),
    
    # Symptoms & Medical Advice
    ('My chest hurts a lot today', 'symptoms'),
    ('I have a fever of 102', 'symptoms'),
    ('The pain in my knee is getting worse', 'symptoms'),
    ('Im feeling very dizzy and nauseous', 'symptoms'),
    ('Is it normal to have a headache after taking this?', 'symptoms'),
    ('My symptoms are not improving', 'symptoms'),
    ('My arm is swelling up', 'symptoms'),
    ('I am bleeding', 'symptoms'),
    ('I threw up', 'symptoms'),
    ('feeling sick', 'symptoms'),
    ('side effects are bad', 'symptoms'),
    ('I have a rash on my back', 'symptoms'),
    ('can you look at my throat', 'symptoms'),
    ('my stomach is killing me', 'symptoms'),
    
    # Scheduling & Appointments
    ('Do I need to come in for a follow up?', 'scheduling'),
    ('Can we reschedule my appointment?', 'scheduling'),
    ('What time is my visit tomorrow?', 'scheduling'),
    ('I need to cancel my appointment', 'scheduling'),
    ('Can I see the doctor earlier?', 'scheduling'),
    ('booking a new visit', 'scheduling'),
    ('when is my next checkup', 'scheduling'),
    ('I am running 10 minutes late', 'scheduling'),
    ('can we change the time', 'scheduling'),
    ('I need to book a physical', 'scheduling'),
    
    # Billing & Financial
    ('how much do I owe', 'billing'),
    ('did my insurance cover this', 'billing'),
    ('where is my invoice', 'billing'),
    ('I have a question about my bill', 'billing'),
    ('what is my copay', 'billing'),
    ('can I pay online', 'billing'),
    
    # Records & Labs
    ('are my lab results back', 'records'),
    ('what did the blood work show', 'records'),
    ('can you send me my MRI results', 'records'),
    ('I need a copy of my medical records', 'records'),
    ('did the x-ray come back', 'records'),
    ('cholesterol test results', 'records'),
    
    # General / Greetings
    ('Thank you doctor', 'general'),
    ('Sounds good, see you then', 'general'),
    ('Got it, thanks', 'general'),
    ('Hi doctor, just checking in', 'general'),
    ('Everything is going well', 'general'),
    ('thanks a lot', 'general'),
    ('hello', 'general'),
    ('ok', 'general'),
    ('good morning', 'general')
]

df = pd.DataFrame(data, columns=['text', 'intent'])

# Advanced TF-IDF + Logistic Regression with proper regularization
print('Training model with n-grams and calibrated probabilities...')
pipeline = Pipeline([
    ('tfidf', TfidfVectorizer(ngram_range=(1, 3), lowercase=True, stop_words='english', max_features=500)),
    ('clf', LogisticRegression(C=5.0, class_weight='balanced', max_iter=1000, random_state=42))
])

pipeline.fit(df['text'], df['intent'])

print("\nModel Evaluation on Training Set:")
preds = pipeline.predict(df['text'])
print(classification_report(df['intent'], preds))

# Test Probability Calibration
print("\nTesting Confidence Thresholds:")
test_phrases = ['I ran out of my pills', 'how much is the copay', 'what did the blood test say', 'apple pie is tasty']
for p in test_phrases:
    probs = pipeline.predict_proba([p])[0]
    best_idx = np.argmax(probs)
    intent = pipeline.classes_[best_idx]
    conf = probs[best_idx]
    print(f' - "{p}" -> {intent} (Confidence: {conf:.2f})')

# Save the model
model_path = os.path.join('models', 'chat_intent_model.pkl')
os.makedirs('models', exist_ok=True)
joblib.dump(pipeline, model_path)
print(f'\nRobust ML model successfully saved to {model_path}')
