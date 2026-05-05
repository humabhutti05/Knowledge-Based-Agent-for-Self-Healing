import pandas as pd
import json
import re
from collections import Counter
import os

def train_model():
    csv_path = r'c:\Users\SUPREMETRDAER\Downloads\self_healup_project\self_healup\data\Combined_Data.csv'
    if not os.path.exists(csv_path): return

    df = pd.read_csv(csv_path)
    df = df.dropna(subset=['statement', 'status'])
    
    classes = df['status'].unique()
    class_word_counts = {c: Counter() for c in classes}
    class_totals = {c: 0 for c in classes}
    
    # Faster tokenization using vectorization
    print("Tokenizing data...")
    for c in classes:
        subset = df[df['status'] == c]['statement'].astype(str).str.lower()
        all_text = " ".join(subset)
        tokens = re.findall(r'\w+', all_text)
        class_word_counts[c] = Counter(tokens)
        class_totals[c] = len(tokens)

    vocab = set()
    for c in classes: vocab.update(class_word_counts[c].keys())

    model = {
        "classes": list(classes),
        "vocab_size": len(vocab),
        "class_totals": class_totals,
        "class_priors": df['status'].value_counts(normalize=True).to_dict(),
        "word_probs": {}
    }

    word_global_counts = Counter()
    for c in classes: word_global_counts.update(class_word_counts[c])

    for word, count in word_global_counts.items():
        if count >= 3:
            model["word_probs"][word] = {c: class_word_counts[c][word] for c in classes if class_word_counts[c][word] > 0}

    output_path = r'c:\Users\SUPREMETRDAER\Downloads\self_healup_project\self_healup\data\model.json'
    with open(output_path, 'w') as f:
        json.dump(model, f)
    print("Model ready")

if __name__ == "__main__":
    train_model()
