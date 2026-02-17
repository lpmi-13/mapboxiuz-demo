from django.http import JsonResponse


async def healthz(request):
    return JsonResponse({"status": "ok"})
