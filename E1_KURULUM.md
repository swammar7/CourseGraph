# CourseGraph E1 — Ahmet'in 31 Ekim teslimi

Bu paket `github.com/MelisaZS/pdf-ai-query` ana dalındaki prototipin **üzerine eklenmek** üzere hazırlanmıştır. Eski `embed (1).py`, `query.py`, `index.json`, `example.pdf`, `templates.zip` dosyalarını silmez. `app.py` ve `requirements.txt` güncellenir, yeni `templates/index.html` oluşturulur. GitHub deposuna otomatik push yapılmamıştır.

## 1. Kurulum

```bash
git clone https://github.com/MelisaZS/pdf-ai-query.git
cd pdf-ai-query
# Bu ZIP'in içeriğini bu dizinin köküne çıkarın (app.py ve requirements.txt değişsin).
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
# Windows CMD: .venv\Scripts\activate.bat
# macOS/Linux: source .venv/bin/activate
pip install -r requirements-dev.txt
python prepare_model.py
python app.py
```

`http://127.0.0.1:5000` adresinden bir PDF yükleyin. `python prepare_model.py` yalnızca modeli ilk kez indirmek için internete bağlanabilir; belgeler hiçbir API'ye gönderilmez. Model `models/all-MiniLM-L6-v2/` altında tutulur. Sonraki yüklemelerde `LocalEmbedder` yalnızca yerel dizini kullanır. Git öncesi `git status` çıktısında `models/` ve `data/` görünmemeli.

> Dosya yükleme sınırı 20 MB. E1 yüklemeler **tek işlemli yerel Flask** için tasarlanmıştır; çok worker'da işleyen prod sunucu için işlemsel RDF veritabanı / dosya kilidi gerekir.

## 2. Çalışan endpointler

`POST /api/upload` (`multipart/form-data`):

- `pdf`: dosya
- `course_id`: ör. `SEN0414`
- `topics`: isteğe bağlı, virgülle ayrılmış `RDF, SPARQL` (verilmezse `Genel`)

Başarılı ilk yükleme: HTTP 201, `status=created`, `document_uri`, `page_count`, `chunk_count`, `shacl_conforms=true`, `embedding_dimension`.
Aynı ders ve aynı PDF: HTTP 200, `status=already_exists`.
Hatalı/boş veya taranmış PDF: HTTP 422. Desteklenmeyen form: HTTP 400. Model yerelde yok: HTTP 503.

```bash
curl -F "pdf=@example.pdf" -F "course_id=SEN0414" -F "topics=Python,RDF" \
  http://127.0.0.1:5000/api/upload
curl http://127.0.0.1:5000/api/documents
```

`POST /upload`: aynı işlem + web arayüzüne yönlendirme. `GET /`: arşiv listesi ve geçici eski sorgu formu. `GET /api/documents`: kaydedilen belgelerin listesi.

## 3. RDF, SHACL ve sonraki E2 entegrasyonu

- `ontology/coursegraph.ttl` — sınıflar (`cg:Course`, `cg:Document`, `cg:Page`, `cg:Chunk`), RDF ilişkileri.
- `ontology/shapes.ttl` — `pySHACL` ile alan / tip / sayfa numarası / konu kontrolleri.
- `data/graph.ttl` — RDF grafı, her chunk için `cg:text`, `cg:chunkPageNumber`, `cg:embeddingJson`.
- `data/uploads/` — ders + SHA256 ile adlandırılmış orijinal PDF dosyaları.
- `skos:Concept` — yükleme formunda verilen konular tüm belge chunk'larına bağlanır; otomatik konu tespiti henüz yoktur.

Melisa'nın retriever modülü için örnek SPARQL:

```sparql
PREFIX cg: <https://coursegraph.local/ontology#>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
SELECT ?document ?pageNumber ?chunk ?text ?embeddingJson
WHERE {
  ?course a cg:Course ; skos:prefLabel ?courseLabel ; cg:hasDocument ?document .
  FILTER(STR(?courseLabel) = "SEN0414")
  ?document cg:hasPage ?page .
  ?page cg:pageNumber ?pageNumber ; cg:hasChunk ?chunk .
  ?chunk cg:text ?text ; cg:embeddingJson ?embeddingJson .
}
ORDER BY ?document ?pageNumber ?chunk
```

`embeddingJson` bir JSON sayı dizisidir; `json.loads(str(value))` ile okunur. Vektör boyutu, kullanılan embedding modeline bağlıdır. E2 ekibi daha sonra top-3 benzerlik, atıflı Ollama yanıtı ve PROV-O kaydı ekleyecek. Bu sürüm **bunları yaptığını iddia etmez**.

`GraphStore.validate_graph(graph)` bozuk graf için `(False, shacl_report)` döndürür; yükleme aday grafı doğrulanmadan kaydedilmez. Taranmış tamamen metinsiz PDF OCR yapılmadığı için yükleme öncesinde reddedilir.

## 4. Testler

```bash
pytest -q
```

`tests/fixtures/two_pages.pdf` iki metin sayfası içerir. Testler embedding modelini indirmeden sahte (`FakeEmbedder`) model kullanır. Kontroller: sayfa bilgisi, sayfa sınırında chunk bölmeme, boş PDF reddi, geçerli RDF/SKOS grafı, SHACL sayfa numarası reddi, tekrar yükleme, JSON upload endpoint.

## 5. İşin sınırları

Bu ilk sürümde otomatik konu çıkarımı, OCR, oturum açma, bulut API, GraphRAG top-3, Ollama cevabı, PROV-O, `/report` veya CI bulunmaz. Eski `index.json` sorgusu uyumluluk için korunmuştur; yüklenen PDF'leri arama özelliği E2'ye kalır.

## 6. Önerilen commit planı

1. `feat(e1): preserve PDF page metadata during chunking`
2. `feat(e1): implement RDF/SKOS graph and SHACL validation`
3. `feat(e1): add Flask PDF upload and ingestion tests`

Değişiklikleri kendi GitHub hesabından commitleyin; Workbench work-log girişlerine gerçek commit linklerini ekleyin.

## 7. E1 → E2 entegrasyon ve negatif SHACL testleri (ek güncelleme)

- **Python:** `GraphStore.get_course_chunks("SEN0414", topic="RDF")` ders ve isteğe bağlı SKOS etiketiyle SPARQL filtreler; belge adı, sayfa, metin ve `list[float]` embedding döndürür.
- **HTTP:** `GET /api/courses/SEN0414/chunks?topic=RDF&limit=50&offset=0` sayfalı sonuç verir; `include_embeddings=1` ile vektörler istenebilir.
- **SHACL:** `cg:text` yalnız boş dizeyi değil, sadece boşluk içeren metni de reddeder. Eksik sayfa numarası, boş chunk, eksik ilişki ve konu etiketi için negatif testler vardır.
- **Gerçek veri kanıtı:** `python scripts/verify_e1.py --course SEN0414` kaydedilmiş grafı doğrular ve üç farklı geçersiz veri örneğini bellekte test eder; diskteki RDF'ye dokunmaz.
- **Tam sözleşme ve örnekler:** [`docs/E1_INTEGRATION.md`](docs/E1_INTEGRATION.md).
- **Test kapsamı ve sınırlar:** [`docs/E1_SHACL_AND_TESTS.md`](docs/E1_SHACL_AND_TESTS.md).

Bu güncelleme E2'nin Retriever/Ollama sorumluluklarını **üstlenmez**; veriyi kullanıma hazır şekilde sunar.
