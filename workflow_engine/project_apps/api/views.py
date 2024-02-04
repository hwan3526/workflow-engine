from django.core.exceptions import ValidationError

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from project_apps.service.workflow_service import WorkflowService, WorkflowExecutor


class WorkflowCreateAPIView(APIView):
    '''
    API View for creating a new Workflow instance along with associated Job instances.
    '''
    def post(self, request):
        name = request.data.get('name')
        description = request.data.get('description')
        jobs_data = request.data.get('jobs', [])

        if not name or not description:
            return Response({'error': 'name and description are required.'}, status=status.HTTP_400_BAD_REQUEST)

        workflow_service = WorkflowService()
        try:
            workflow = workflow_service.create_workflow(name, description, jobs_data)
        except ValidationError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        
        return Response(workflow, status=status.HTTP_201_CREATED)


class WorkflowDeleteAPIView(APIView):
    '''
    API View for deleting a Workflow instance along with associated Job instances.
    '''

    def delete(self, request, workflow_uuid):
        workflow_service = WorkflowService()

        try:
            # Workflow 및 해당 Workflow에 종속된 Jobs를 삭제
            workflow_service.delete_workflow(workflow_uuid)
        except ValidationError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response({'success': f'Workflow with uuid {workflow_uuid} and associated jobs deleted successfully.'},
                        status=status.HTTP_204_NO_CONTENT)

      
class WorkflowExecuteAPIView(APIView):
    def get(self, request, workflow_uuid):
        '''
        Fetch the list of jobs to execute, belonging to the corresponding workflow uuid and cache it into Redis storage.

        Request data
        - uuid: workflow's uuid that you want to execute.
        '''
        workflow_executor = WorkflowExecutor()
        result = workflow_executor.execute_workflow(workflow_uuid)

        if result:
            return Response(status=status.HTTP_204_NO_CONTENT)
        else:
            return Response(status=status.HTTP_404_NOT_FOUND)