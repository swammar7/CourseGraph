from sentence_transformers import SentenceTransformer

import PyPDF2

import json

import os



model = SentenceTransformer('all-MiniLM-L6-v2')



def read_pdf(path):

    reader = PyPDF2.PdfReader(path)

    text = ""

    for page in reader.pages:

        text += page.extract_text() + "\n"

    return text



def chunk_text(text, size=500):

    words = text.split()

    return [" ".join(words[i:i+size]) for i in range(0, len(words), size)]



print("📄 PDF yükleniyor: example.pdf")

text = read_pdf("example.pdf")

chunks = chunk_text(text)



print("🔍 Embedding oluşturuluyor...")

embeddings = model.encode(chunks, convert_to_tensor=False)



# Kaydedelim

data = {

    "chunks": chunks,

    "embeddings": [e.tolist() for e in embeddings]

}



with open("index.json", "w", encoding="utf-8") as f:

    json.dump(data, f, ensure_ascii=False, indent=2)



print("🚀 Embedding tamamlandı! index.json oluşturuldu.")


