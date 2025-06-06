import time
import re


class MessageBus:
    def __init__(self):
        self.subscribers = {}

    def subscribe(self, event_type, callback):
        if event_type not in self.subscribers:
            self.subscribers[event_type] = []
        self.subscribers[event_type].append(callback)

    def emit(self, event_type, event_data):
        if event_type in self.subscribers:
            for callback in self.subscribers[event_type]:
                callback(event_data)


class IngestorAgent:
    def __init__(self, bus):
        self.bus = bus

    def ingest(self, doc):
        print(f"[Ingestor] Ingesting document: {doc['name']}")
        doc['state'] = 'received'
        doc['priority'] = 'high' if len(doc.get('content', '')) > 50000 else 'normal'
        doc['metadata'] = {
            'received_at': time.time(),
            'size': len(doc.get('content', ''))
        }
        self.bus.emit('doc.received', doc)


class ExtractorAgent:
    def __init__(self, bus):
        self.bus = bus
        bus.subscribe('doc.received', self.on_doc_received)

    def on_doc_received(self, doc):
        print(f"[Extractor] Extracting document: {doc['name']}")
        time.sleep(1)
        text = doc.get('content', '')

        entities = self.extract_entities(text)
        doc['text'] = text
        doc['entities'] = entities
        doc['state'] = 'extracted'
        doc['extracted_at'] = time.time()

        self.bus.emit('doc.extracted', doc)

    def extract_entities(self, text):
        entities = {}
        dates = re.findall(r'(\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4})', text)
        if dates:
            entities['dates'] = dates
        amounts = re.findall(r'\$\d+(?:,\d{3})*(?:\.\d{2})?', text)
        if amounts:
            entities['amounts'] = amounts
        parties = re.findall(r'Party:\s*([A-Za-z0-9 &]+)', text)
        if parties:
            entities['parties'] = parties
        return entities


class ClassifierAgent:
    def __init__(self, bus):
        self.bus = bus
        bus.subscribe('doc.extracted', self.on_doc_extracted)

    def on_doc_extracted(self, doc):
        print(f"[Classifier] Classifying document: {doc['name']}")
        time.sleep(1)
        text = doc.get('text', '').lower()

        if 'invoice' in text:
            doc_type = 'Invoice'
            confidence = 0.95
        elif 'contract' in text:
            doc_type = 'Contract'
            confidence = 0.90
        elif 'report' in text:
            doc_type = 'Report'
            confidence = 0.85
        else:
            doc_type = 'Unknown'
            confidence = 0.5

        doc['type'] = doc_type
        doc['confidence'] = confidence
        doc['state'] = 'classified'
        doc['classified_at'] = time.time()
        doc['needs_review'] = confidence < 0.7

        self.bus.emit('doc.classified', doc)


class RouterAgent:
    def __init__(self, bus):
        self.bus = bus
        bus.subscribe('doc.classified', self.on_doc_classified)

    def on_doc_classified(self, doc):
        print(f"[Router] Routing document: {doc['name']} (Type: {doc['type']})")
        time.sleep(0.5)

        if doc['type'] == 'Invoice':
            routing_command = 'Send to Accounting ERP system'
        elif doc['type'] == 'Contract':
            routing_command = 'Upload to Document Management System (DMS)'
        elif doc['type'] == 'Report':
            routing_command = 'Email alert to stakeholders'
        else:
            routing_command = 'Send to manual review queue'

        doc['routing_command'] = routing_command
        doc['state'] = 'routed'
        doc['routed_at'] = time.time()

        self.bus.emit('doc.routed', doc)
