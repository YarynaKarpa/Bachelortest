from django.shortcuts import render


import json
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from .rag import get_engine


def index(request):
    engine = get_engine()
    return render(request, "chat/index.html", {"doc_count": engine.count()})


@csrf_exempt
@require_POST
def ask(request):
    try:
        data = json.loads(request.body)
        question = data.get("question", "").strip()
        if not question:
            return JsonResponse({"error": "Keine Frage angegeben."}, status=400)

        engine = get_engine()
        result = engine.ask(question)
        return JsonResponse(result)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)