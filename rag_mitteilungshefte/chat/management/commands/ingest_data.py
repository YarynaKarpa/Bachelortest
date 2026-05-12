import json
from django.core.management.base import BaseCommand
from django.conf import settings
from chat.rag import get_engine


class Command(BaseCommand):
    help = "Testdaten in ChromaDB einlesen"

    def handle(self, *args, **options):
        with open(settings.TESTDATA_PATH, encoding="utf-8") as f:
            docs = json.load(f)
        engine = get_engine()
        n = engine.ingest(docs)
        self.stdout.write(self.style.SUCCESS(
            f"✅ Fertig. {n} neue Dokumente | Gesamt: {engine.count()}"
        ))