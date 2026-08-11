import mimetypes
import os
import re

from django.conf import settings
from django.http import FileResponse, Http404, HttpResponse, StreamingHttpResponse
from django.utils._os import safe_join


RANGE_RE = re.compile(r"bytes=(\d*)-(\d*)$")
CHUNK_SIZE = 8192


def _file_iterator(path, start, length):
    with open(path, "rb") as file_obj:
        file_obj.seek(start)
        remaining = length
        while remaining > 0:
            chunk = file_obj.read(min(CHUNK_SIZE, remaining))
            if not chunk:
                break
            remaining -= len(chunk)
            yield chunk


def serve_media(request, path):
    try:
        full_path = safe_join(settings.MEDIA_ROOT, path)
    except ValueError:
        raise Http404("Media file not found")

    if not os.path.isfile(full_path):
        raise Http404("Media file not found")

    file_size = os.path.getsize(full_path)
    content_type = mimetypes.guess_type(full_path)[0] or "application/octet-stream"
    range_header = request.headers.get("Range", "")

    if not range_header:
        response = FileResponse(open(full_path, "rb"), content_type=content_type)
        response["Content-Length"] = str(file_size)
        response["Accept-Ranges"] = "bytes"
        return response

    match = RANGE_RE.match(range_header.strip())
    if not match:
        response = HttpResponse(status=416)
        response["Content-Range"] = f"bytes */{file_size}"
        response["Accept-Ranges"] = "bytes"
        return response

    start_text, end_text = match.groups()
    if start_text == "" and end_text == "":
        response = HttpResponse(status=416)
        response["Content-Range"] = f"bytes */{file_size}"
        response["Accept-Ranges"] = "bytes"
        return response

    if start_text == "":
        suffix_length = int(end_text)
        if suffix_length == 0:
            response = HttpResponse(status=416)
            response["Content-Range"] = f"bytes */{file_size}"
            response["Accept-Ranges"] = "bytes"
            return response
        start = max(file_size - suffix_length, 0)
        end = file_size - 1
    else:
        start = int(start_text)
        end = int(end_text) if end_text else file_size - 1

    if start >= file_size or end < start:
        response = HttpResponse(status=416)
        response["Content-Range"] = f"bytes */{file_size}"
        response["Accept-Ranges"] = "bytes"
        return response

    end = min(end, file_size - 1)
    length = end - start + 1
    response = StreamingHttpResponse(
        _file_iterator(full_path, start, length),
        status=206,
        content_type=content_type,
    )
    response["Content-Length"] = str(length)
    response["Content-Range"] = f"bytes {start}-{end}/{file_size}"
    response["Accept-Ranges"] = "bytes"
    return response
