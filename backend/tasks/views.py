"""
DRF views — no Django models, delegates to CalDAVService.
"""
from datetime import datetime, timezone
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ViewSet

from .caldav_service import get_service
from .virtual_tags import add_virtual_tags, get_virtual_tag_counts
from .serializers import validate_task_input, PRIORITY_MAP


def _apply_filters(tasks: list[dict], params: dict) -> list[dict]:
    """Apply query param filters to task list."""
    # status filter
    status_filter = params.get('status', '').upper()
    if status_filter == 'PENDING':
        tasks = [t for t in tasks if t['status'] in ('NEEDS-ACTION', 'IN-PROCESS')]
    elif status_filter == 'COMPLETED':
        tasks = [t for t in tasks if t['status'] == 'COMPLETED']
    elif status_filter == 'CANCELLED':
        tasks = [t for t in tasks if t['status'] == 'CANCELLED']

    # tags filter (comma-separated, all must match)
    tags_param = params.get('tags', '')
    if tags_param:
        filter_tags = {t.strip().lower() for t in tags_param.split(',') if t.strip()}
        tasks = [
            t for t in tasks
            if filter_tags.issubset({tag.lower() for tag in (t.get('tags') or [])})
        ]

    # virtual tags filter
    virtual_param = params.get('virtual', '')
    if virtual_param:
        filter_virtual = {v.strip().upper() for v in virtual_param.split(',') if v.strip()}
        tasks = [
            t for t in tasks
            if filter_virtual.issubset(set(t.get('virtual_tags') or []))
        ]

    # priority filter
    priority_param = params.get('priority', '').lower()
    if priority_param == 'high':
        tasks = [t for t in tasks if 1 <= (t.get('priority') or 0) <= 4]
    elif priority_param == 'medium':
        tasks = [t for t in tasks if (t.get('priority') or 0) == 5]
    elif priority_param == 'low':
        tasks = [t for t in tasks if 6 <= (t.get('priority') or 0) <= 9]
    elif priority_param == 'none':
        tasks = [t for t in tasks if (t.get('priority') or 0) == 0]

    # full-text search
    search = params.get('search', '').lower().strip()
    if search:
        tasks = [
            t for t in tasks
            if search in (t.get('title') or '').lower()
            or search in (t.get('description') or '').lower()
        ]

    # parent_uid filter (get children)
    parent_uid = params.get('parent_uid', '').strip()
    if parent_uid:
        tasks = [t for t in tasks if t.get('parent_uid') == parent_uid]

    return tasks


def _apply_sort(tasks: list[dict], sort_param: str) -> list[dict]:
    """Apply sort param (e.g. '-due', 'priority', 'title')."""
    if not sort_param:
        return tasks

    reverse = sort_param.startswith('-')
    field = sort_param.lstrip('-')

    def sort_key(t):
        val = t.get(field)
        if val is None:
            # None sorts last
            return (1, '')
        return (0, str(val))

    return sorted(tasks, key=sort_key, reverse=reverse)


class TaskViewSet(ViewSet):
    """ViewSet for VTODO CRUD — delegates to CalDAVService."""

    def list(self, request):
        """GET /api/tasks/ — list with optional filters."""
        try:
            svc = get_service()
            include_completed = request.query_params.get('status', '').upper() in ('', 'ALL', 'COMPLETED')
            all_tasks = svc.get_all_tasks(include_completed=True)

            # Add virtual tags to all before filtering (PARENT detection needs full list)
            all_tasks = add_virtual_tags(all_tasks)

            filtered = _apply_filters(all_tasks, request.query_params)
            sorted_tasks = _apply_sort(filtered, request.query_params.get('sort', ''))

            return Response({'tasks': sorted_tasks, 'total': len(sorted_tasks)})
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def create(self, request):
        """POST /api/tasks/ — create new task."""
        try:
            data, errors = validate_task_input(request.data)
            if errors:
                return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

            svc = get_service()
            task = svc.create_task(data)
            if task:
                all_tasks = svc.get_all_tasks(include_completed=True)
                add_virtual_tags(all_tasks)
                # Find our task in the enriched list
                enriched = next((t for t in all_tasks if t['uid'] == task['uid']), task)
                return Response(enriched, status=status.HTTP_201_CREATED)
            return Response({'error': 'Failed to create task'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def retrieve(self, request, pk=None):
        """GET /api/tasks/{uid}/ — get single task."""
        try:
            svc = get_service()
            task = svc.get_task(pk)
            if task is None:
                return Response({'error': 'Task not found'}, status=status.HTTP_404_NOT_FOUND)

            all_tasks = svc.get_all_tasks(include_completed=True)
            add_virtual_tags(all_tasks)
            enriched = next((t for t in all_tasks if t['uid'] == pk), task)
            return Response(enriched)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def update(self, request, pk=None):
        """PUT /api/tasks/{uid}/ — full update."""
        try:
            data, errors = validate_task_input(request.data)
            if errors:
                return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

            svc = get_service()
            task = svc.update_task(pk, data)
            if task is None:
                return Response({'error': 'Task not found'}, status=status.HTTP_404_NOT_FOUND)

            all_tasks = svc.get_all_tasks(include_completed=True)
            add_virtual_tags(all_tasks)
            enriched = next((t for t in all_tasks if t['uid'] == pk), task)
            return Response(enriched)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def partial_update(self, request, pk=None):
        """PATCH /api/tasks/{uid}/ — partial update (no required field validation)."""
        try:
            svc = get_service()
            task = svc.update_task(pk, request.data)
            if task is None:
                return Response({'error': 'Task not found'}, status=status.HTTP_404_NOT_FOUND)

            all_tasks = svc.get_all_tasks(include_completed=True)
            add_virtual_tags(all_tasks)
            enriched = next((t for t in all_tasks if t['uid'] == pk), task)
            return Response(enriched)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def destroy(self, request, pk=None):
        """DELETE /api/tasks/{uid}/ — delete task."""
        try:
            svc = get_service()
            deleted = svc.delete_task(pk)
            if not deleted:
                return Response({'error': 'Task not found'}, status=status.HTTP_404_NOT_FOUND)
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        """POST /api/tasks/{uid}/complete/ — mark task as completed."""
        try:
            svc = get_service()
            task = svc.complete_task(pk)
            if task is None:
                return Response({'error': 'Task not found'}, status=status.HTTP_404_NOT_FOUND)

            all_tasks = svc.get_all_tasks(include_completed=True)
            add_virtual_tags(all_tasks)
            enriched = next((t for t in all_tasks if t['uid'] == pk), task)
            return Response(enriched)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class TagListView(APIView):
    """GET /api/tags/ — list all unique tags across all tasks."""

    def get(self, request):
        try:
            svc = get_service()
            tasks = svc.get_all_tasks(include_completed=True)
            all_tags: set[str] = set()
            for task in tasks:
                for tag in (task.get('tags') or []):
                    all_tags.add(tag)
            return Response({'tags': sorted(all_tags)})
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class VirtualTagListView(APIView):
    """GET /api/virtual-tags/ — virtual tag counts."""

    def get(self, request):
        try:
            svc = get_service()
            tasks = svc.get_all_tasks(include_completed=True)
            counts = get_virtual_tag_counts(tasks)
            return Response({'virtual_tags': counts})
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
