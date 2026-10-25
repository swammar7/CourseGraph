from sentence_transformers import SentenceTransformer

import json

import numpy as np



model = SentenceTransformer('all-MiniLM-L6-v2')



def load_index():

    with open("index.json", "r", encoding="utf-8") as f:

        return json.load(f)



def cosine_similarity(a, b):

    return np.dot(a, b) / (np.linalg.norm(a)*np.linalg.norm(b))



def search(query, index_data):

    q_emb = model.encode([query])[0]

    scores = []

    for i, emb in enumerate(index_data["embeddings"]):

        score = cosine_similarity(q_emb, np.array(emb))

        scores.append((score, index_data["chunks"][i]))

    scores.sort(reverse=True)

    return scores[0][1]



# Test query

query_text = input("Soru: ")

index = load_index()

answer = search(query_text, index)



print("\nCevap:")

print(answer)


