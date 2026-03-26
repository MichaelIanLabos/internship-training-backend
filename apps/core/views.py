import math

from rest_framework.views import APIView


class API(APIView):
    """Base API class for all views."""
    pass


class ObjectManager:
    """Mixin providing pagination utilities."""
    def generate_pagination(self, current_page, page_size, records):
        total = records.count()
        total_pages = max(1, math.ceil(total / page_size))
        start = (current_page - 1) * page_size
        end = start + page_size
        return {
            "total_records": total,
            "total_pages": total_pages,
            "current_page": current_page,
            "records": records[start:end],
        }
