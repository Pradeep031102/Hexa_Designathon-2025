from flask import Flask, request, jsonify
import time
 
from document_mas_backend import MessageBus, IngestorAgent, ExtractorAgent, ClassifierAgent, RouterAgent
 
app = Flask(__name__)
 
# Initialize message bus and agents
bus = MessageBus()
ingestor = IngestorAgent(bus)
extractor = ExtractorAgent(bus)
classifier = ClassifierAgent(bus)
router = RouterAgent(bus)
 
# In-memory document storage
documents = {}
 
# Update documents dict when routing finishes
def on_doc_routed(doc):
    documents[doc['id']] = doc
 
bus.subscribe('doc.routed', on_doc_routed)
 
@app.route('/')
def home():
    return ("<h1>Welcome to the Document Ingestion & Classification API!</h1>"
            "<p>Use <code>/upload</code> (POST) to upload documents and "
            "<code>/documents</code> (GET) to list processed documents.</p>")
 
@app.route('/upload', methods=['POST'])
def upload_documents():
    uploaded_files = request.files.getlist('files')
    if not uploaded_files:
        return jsonify({"error": "No files uploaded"}), 400
 
    uploaded_ids = []
 
    for file in uploaded_files:
        content = file.read().decode('utf-8')
        doc_id = f"{file.filename}_{int(time.time()*1000)}"
        doc = {
            'id': doc_id,
            'name': file.filename,
            'content': content,
            'state': 'received',
        }
        documents[doc_id] = doc
        ingestor.ingest(doc)
        uploaded_ids.append(doc_id)
 
    return jsonify({'uploaded': uploaded_ids})
 
@app.route('/documents', methods=['GET'])
def list_documents():
    return jsonify(list(documents.values()))
 
@app.route('/documents/<doc_id>/re-extract', methods=['POST'])
def re_extract(doc_id):
    doc = documents.get(doc_id)
    if not doc:
        return jsonify({"error": "Document not found"}), 404
 
    # Reset state and restart ingestion
    doc['state'] = 'received'
    doc['entities'] = {}
    doc['confidence'] = 0
    doc['type'] = None
    doc['needs_review'] = False
    doc['routing_command'] = None
    ingestor.ingest(doc)
 
    return jsonify({"message": f"Re-extract started for {doc_id}"})
 
 
@app.route('/documents/<doc_id>/re-classify', methods=['POST'])
def re_classify(doc_id):
    doc = documents.get(doc_id)
    if not doc:
        return jsonify({"error": "Document not found"}), 404
    if doc.get('state') not in ['extracted', 'classified', 'routed']:
        return jsonify({"error": "Document not ready for classification"}), 400
 
    doc['state'] = 'extracted'
    doc['confidence'] = 0
    doc['type'] = None
    doc['needs_review'] = False
    doc['routing_command'] = None
    bus.emit('doc.extracted', doc)
 
    return jsonify({"message": f"Re-classify started for {doc_id}"})
 
 
@app.route('/documents/<doc_id>/re-route', methods=['POST'])
def re_route(doc_id):
    doc = documents.get(doc_id)
    if not doc:
        return jsonify({"error": "Document not found"}), 404
    if doc.get('state') not in ['classified', 'routed']:
        return jsonify({"error": "Document not ready for routing"}), 400
 
    doc['state'] = 'classified'
    doc['routing_command'] = None
    bus.emit('doc.classified', doc)
 
    return jsonify({"message": f"Re-route started for {doc_id}"})
 
 
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
