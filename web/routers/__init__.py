from fastapi import Response


class XMLResponse(Response):
    media_type = "application/xml"
